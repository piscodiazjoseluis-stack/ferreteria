"""Prueba integral de venta real, idempotencia y stock para la demostración."""
import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

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
    response = httpx.post(settings.supabase_url + '/auth/v1/token?grant_type=password',
        headers={'apikey': settings.supabase_publishable_key},
        json={'email': account['email'], 'password': account['password']}, timeout=15)
    assert response.status_code == 200, (role, response.status_code)
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


manager = headers('gerente')
seller = headers('vendedor')
assert client.get('/api/sales').status_code == 401
products = client.get('/api/products', headers=manager).json()
sample = next((p for p in products if p['codigo'] == 'DEM-VENTA-001'), None)
if sample is None:
    category = next(c for c in client.get('/api/categories', headers=manager).json()
                    if c['nombre'] == 'Herramientas')
    created = client.post('/api/products', headers=manager, json={
        'codigo': 'DEM-VENTA-001', 'nombre': 'Martillo de carpintero',
        'categoria_id': category['id'], 'unidad_venta': 'unidad',
        'precio_venta': 25, 'stock_minimo': 8, 'saldo_inicial': 10,
    })
    assert created.status_code == 201, (created.status_code, created.text)
    sample = created.json()
assert sample['precio_venta'] == 25
key = str(uuid5(NAMESPACE_URL, 'ferreteria-demo-venta-v1'))
payload = {'clave_idempotencia': key, 'metodo_pago': 'efectivo',
           'items': [{'producto_id': sample['id'], 'cantidad': 3, 'precio_esperado': 25}]}
sale = client.post('/api/sales', headers=seller, json=payload)
assert sale.status_code == 201, (sale.status_code, sale.text)
receipt = sale.json()
assert receipt['total'] == 75 and receipt['items'][0]['precio_unitario'] == 25
assert receipt['items'][0]['cantidad'] == 3
print('PASS: vendedor confirmó venta al contado por S/ 75 con precio del servidor')

repeat = client.post('/api/sales', headers=seller, json=payload)
assert repeat.status_code == 201 and repeat.json()['id'] == receipt['id']
assert client.post('/api/sales', headers=seller,
    json={**payload, 'items': [{'producto_id': sample['id'], 'cantidad': 2, 'precio_esperado': 25}]}).status_code == 409
assert client.post('/api/sales', headers=seller, json={
    **payload, 'clave_idempotencia': str(uuid5(NAMESPACE_URL, 'ferreteria-demo-venta-rechazada')),
    'items': [{'producto_id': sample['id'], 'cantidad': 8, 'precio_esperado': 25}],
}).status_code == 409
assert client.post('/api/sales', headers=seller, json={
    **payload, 'clave_idempotencia': str(uuid5(NAMESPACE_URL, 'ferreteria-demo-precio-desactualizado')),
    'items': [{'producto_id': sample['id'], 'cantidad': 1, 'precio_esperado': 26}],
}).status_code == 409
product = next(p for p in client.get('/api/products', headers=manager).json()
               if p['id'] == sample['id'])
assert product['stock'] == 7 and product['stock'] < product['stock_minimo']
print('PASS: reintento no duplica; stock y precio desactualizado rechazados; stock 10 a 7')

seller_sales = client.get('/api/sales', headers=seller)
manager_sales = client.get('/api/sales', headers=manager)
assert seller_sales.status_code == 200 and manager_sales.status_code == 200
assert any(s['id'] == receipt['id'] for s in seller_sales.json())
assert any(s['id'] == receipt['id'] for s in manager_sales.json())
assert client.get('/api/sales/' + receipt['id'], headers=manager).json()['total'] == 75
history = client.get('/api/inventory/movements', headers=seller).json()
sales_movements = [m for m in history if m['producto_id'] == sample['id'] and m['tipo'] == 'venta']
assert len(sales_movements) == 1 and sales_movements[0]['variacion'] == -3
print('PASS: venta persistida y visible; un movimiento de venta, sin ajuste manual')

manager_sample = next((p for p in client.get('/api/products', headers=manager).json()
                       if p['codigo'] == 'DEM-GER-001'), None)
if manager_sample is None:
    category = next(c for c in client.get('/api/categories', headers=manager).json()
                    if c['nombre'] == 'Herramientas')
    created = client.post('/api/products', headers=manager, json={
        'codigo': 'DEM-GER-001', 'nombre': 'Brocha de pintor 2 pulgadas',
        'categoria_id': category['id'], 'unidad_venta': 'unidad',
        'precio_venta': 12, 'stock_minimo': 3, 'saldo_inicial': 10,
    })
    assert created.status_code == 201, (created.status_code, created.text)
    manager_sample = created.json()
manager_sale = client.post('/api/sales', headers=manager, json={
    'clave_idempotencia': str(uuid5(NAMESPACE_URL, 'ferreteria-demo-venta-gerente')),
    'metodo_pago': 'yape',
    'items': [{'producto_id': manager_sample['id'], 'cantidad': 1, 'precio_esperado': 12}],
})
assert manager_sale.status_code == 201, (manager_sale.status_code, manager_sale.text)
manager_receipt = manager_sale.json()
assert manager_receipt['total'] == 12
assert any(s['id'] == manager_receipt['id'] for s in client.get('/api/sales', headers=manager).json())
assert all(s['id'] != manager_receipt['id'] for s in client.get('/api/sales', headers=seller).json())
assert client.get('/api/sales/' + manager_receipt['id'], headers=seller).status_code == 404
manager_summary = client.get('/api/sales/summary', headers=manager)
seller_summary = client.get('/api/sales/summary', headers=seller)
assert manager_summary.status_code == 200 and seller_summary.status_code == 200
assert manager_summary.json()['total_ventas'] > seller_summary.json()['total_ventas']
print('PASS: gerente ve todas las ventas; vendedor no ve la venta ni comprobante de gerente')
print('VERIFICACIÓN DE VENTAS COMPLETADA')
