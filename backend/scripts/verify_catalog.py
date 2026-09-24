"""Prueba real de API comercial y deja un producto de muestra listo para la demo."""
import json
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'backend'))
from app.config import get_settings
from app.main import app

settings = get_settings()
accounts = json.loads((root / '.artifacts/demo-accounts.json').read_text(encoding='utf-8'))
client = TestClient(app)


def headers(role):
    account = next(a for a in accounts if a['rol'] == role)
    response = httpx.post(
        settings.supabase_url + '/auth/v1/token?grant_type=password',
        headers={'apikey': settings.supabase_publishable_key},
        json={'email': account['email'], 'password': account['password']}, timeout=15,
    )
    assert response.status_code == 200, (role, response.status_code)
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


manager = headers('gerente')
seller = headers('vendedor')
assert client.get('/api/products').status_code == 401
assert client.get('/api/products', headers={'Authorization': 'Bearer incorrecto'}).status_code == 401
categories = client.get('/api/categories', headers=manager)
assert categories.status_code == 200 and len(categories.json()) >= 5
paint = next(c for c in categories.json() if c['nombre'] == 'Pinturas')
payload = {
    'codigo': 'PIN-001', 'nombre': 'Pintura látex blanca 1 galón',
    'categoria_id': paint['id'], 'unidad_venta': 'galon',
    'precio_venta': 25, 'stock_minimo': 8, 'saldo_inicial': 10,
}
assert client.post('/api/products', json=payload, headers=seller).status_code == 403
existing = next((p for p in client.get('/api/products', headers=manager).json()
                 if p['codigo'] == payload['codigo']), None)
if existing is None:
    created = client.post('/api/products', json=payload, headers=manager)
    assert created.status_code == 201, (created.status_code, created.text)
    product = created.json()
    assert product['stock'] == 10
    print('PASS: producto y saldo inicial creados en Supabase')
else:
    product = existing
    print('PASS: producto de demostración ya presente')

product_id = product['id']
assert client.post('/api/products', json=payload, headers=manager).status_code == 409
edit = {key: value for key, value in payload.items() if key != 'saldo_inicial'}
edit['activo'] = True
assert client.put(f'/api/products/{product_id}', json=edit, headers=manager).status_code == 200
assert client.put(f'/api/products/{product_id}', json=edit, headers=seller).status_code == 403
assert client.put(f'/api/products/{product_id}', json={**edit, 'unidad_venta': 'unidad'}, headers=manager).status_code == 422
assert client.post(f'/api/inventory/{product_id}/entries', json={'cantidad': 1, 'motivo': 'No autorizado'}, headers=seller).status_code == 403
assert client.post(f'/api/inventory/{product_id}/adjustments', json={'cantidad_fisica': -1, 'motivo': 'Conteo físico'}, headers=manager).status_code == 422
assert client.put(f'/api/products/{product_id}', json={**payload, 'precio_venta': 0, 'activo': True}, headers=manager).status_code == 422
assert any(p['id'] == product_id for p in client.get('/api/products', headers=seller).json())
print('PASS: vendedor consulta; escritura sin permiso, duplicados y datos inválidos rechazados')

if existing is None:
    entry = client.post(f'/api/inventory/{product_id}/entries', json={'cantidad': 2, 'motivo': 'Reposición de prueba'}, headers=manager)
    assert entry.status_code == 200 and entry.json()['stock'] == 12, (entry.status_code, entry.text)
    adjustment = client.post(f'/api/inventory/{product_id}/adjustments', json={'cantidad_fisica': 10, 'motivo': 'Conteo físico de demostración'}, headers=manager)
    assert adjustment.status_code == 200 and adjustment.json()['stock'] == 10, (adjustment.status_code, adjustment.text)
    print('PASS: entrada y ajuste físicos persistidos con stock coherente')

history = client.get('/api/inventory/movements', headers=seller)
assert history.status_code == 200, (history.status_code, history.text)
mine = [m for m in history.json() if m['producto_id'] == product_id]
current = next(p for p in client.get('/api/products', headers=manager).json() if p['id'] == product_id)
assert mine and mine[0]['stock_resultante'] == current['stock']
print('PASS: historial y existencias reales concuerdan tras las ventas posteriores')
print('VERIFICACIÓN COMERCIAL COMPLETADA')
