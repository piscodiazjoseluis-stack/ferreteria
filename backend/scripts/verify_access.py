"""Pruebas de integración reales. Los cambios comerciales se revierten."""
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'backend'))
from app.main import app
from app.auth import verify_identity, require_manager, current_profile
from app.config import get_settings
from app.database import get_engine

config = get_settings()
accounts = json.loads((root / '.artifacts/demo-accounts.json').read_text(encoding='utf-8'))
client = TestClient(app)
assert client.get('/api/auth/me').status_code == 401
assert client.get('/api/auth/me', headers={'Authorization':'Bearer invalid-token'}).status_code == 401
print('PASS: API rechaza solicitudes sin token y tokens inválidos')
for account in accounts:
    response = httpx.post(config.supabase_url+'/auth/v1/token?grant_type=password',
        headers={'apikey':config.supabase_publishable_key},
        json={'email':account['email'],'password':account['password']},timeout=15)
    assert response.status_code == 200, f'Auth {account["rol"]}: HTTP {response.status_code}'
    token=response.json()['access_token']
    result=client.get('/api/auth/me',headers={'Authorization':f'Bearer {token}'})
    assert result.status_code == 200, f'Perfil {account["rol"]}: {result.status_code} {result.text}'
    assert result.json()['rol'] == account['rol']
    print(f'PASS: Auth -> FastAPI -> PostgreSQL reconoce {account["rol"]}')
    if account['rol']=='vendedor':
        from fastapi import HTTPException
        from app.auth import Profile
        try: require_manager(Profile(**result.json()))
        except HTTPException as error: assert error.status_code==403
        else: raise AssertionError('Vendedor aceptado como gerente')
        print('PASS: dependencia de gerente rechaza vendedor')

app.dependency_overrides[verify_identity] = lambda: uuid4()
assert client.get('/api/auth/me').status_code == 403
app.dependency_overrides.clear()
print('PASS: identidad sin perfil no tiene acceso')

manager = next(a for a in accounts if a['rol']=='gerente')
seller = next(a for a in accounts if a['rol']=='vendedor')
engine=get_engine()
with engine.connect() as c:
    tx=c.begin()
    try:
        assert c.execute(text('SELECT count(*) FROM ferreteria.categorias')).scalar()==0
        c.execute(text("SELECT set_config('app.user_id',:id,true)"),{'id':manager['id']})
        category=c.execute(text('SELECT id FROM ferreteria.categorias LIMIT 1')).scalar_one()
        product=uuid4()
        c.execute(text("INSERT INTO ferreteria.productos(id,codigo,nombre,categoria_id,unidad_venta,precio_venta) VALUES(:id,:code,'Prueba reversible',:cat,'unidad',25)"),{'id':product,'code':'QA-'+uuid4().hex[:12].upper(),'cat':category})
        c.execute(text('INSERT INTO ferreteria.existencias(producto_id,cantidad) VALUES(:id,10)'),{'id':product})

        def rejected(statement,params=None):
            sp=c.begin_nested()
            try:
                c.execute(text(statement),params or {})
            except DBAPIError:
                sp.rollback()
            else:
                sp.rollback()
                raise AssertionError('La base aceptó una operación prohibida')

        rejected('UPDATE ferreteria.existencias SET cantidad=-1 WHERE producto_id=:id',{'id':product})
        rejected('UPDATE ferreteria.productos SET precio_venta=0 WHERE id=:id',{'id':product})
        rejected("UPDATE ferreteria.productos SET precio_venta='NaN'::numeric WHERE id=:id",{'id':product})
        print('PASS: gerente puede crear; restricciones rechazan stock negativo y precios inválidos')
        c.execute(text("SELECT set_config('app.user_id',:id,true)"),{'id':seller['id']})
        assert c.execute(text('SELECT count(*) FROM ferreteria.productos WHERE id=:id'),{'id':product}).scalar()==1
        changed=c.execute(text('UPDATE ferreteria.productos SET precio_venta=99 WHERE id=:id'),{'id':product})
        assert changed.rowcount==0
        rejected("UPDATE ferreteria.perfiles SET rol='gerente' WHERE id=:id",{'id':UUID(seller['id'])})
        rejected("INSERT INTO ferreteria.categorias(nombre) VALUES('QA no permitida')")
        rejected('DELETE FROM ferreteria.productos WHERE id=:id',{'id':product})
        print('PASS: vendedor consulta, no cambia precios, no crea categorías ni eleva su rol')
    finally:
        tx.rollback()
with engine.connect() as c:
    assert c.execute(text('SELECT count(*) FROM ferreteria.categorias')).scalar()==0
print('PASS: rollback completo y contexto de usuario no filtrado entre transacciones')
print('VERIFICACIÓN DE ACCESO COMPLETADA')
