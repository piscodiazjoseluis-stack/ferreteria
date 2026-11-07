"""Venta y cierre concurrentes con SQL/RLS reales y rollback en ambas conexiones."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID,uuid4
import httpx
from fastapi import Depends,HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'backend'))
from app import auth,cash,sales
from app.config import get_settings
from app.database import get_engine,user_connection
from app.main import app

s=get_settings();accounts=json.loads((root/'.artifacts/demo-accounts.json').read_text(encoding='utf-8'))
manager={'email':'gerente.ferreteria3@gmail.com','password':os.environ['MF_MANAGER_TEST_PASSWORD']}
seller=next(a for a in accounts if a['rol']=='vendedor');tokens={};users={}
for role,account in [('gerente',manager),('vendedor',seller)]:
    r=httpx.post(s.supabase_url+'/auth/v1/token?grant_type=password',headers={'apikey':s.supabase_publishable_key},json={k:account[k] for k in ('email','password')},timeout=20)
    r.raise_for_status();d=r.json();tokens[role]=d['access_token'];users[role]=UUID(d['user']['id'])
with user_connection(users['gerente']) as c:
    product=c.execute(text("SELECT p.id,p.precio_venta FROM ferreteria.productos p JOIN ferreteria.existencias e ON e.producto_id=p.id WHERE p.codigo='DEMO-V3-001' AND e.cantidad>0")).mappings().one()
    box=c.execute(text("SELECT * FROM ferreteria.cajas WHERE fecha=(now() AT TIME ZONE 'America/Lima')::date AND estado='abierta'")).mappings().one()
    expected=cash.totals(c,box)['efectivo_esperado']
connections={u:get_engine().connect() for u in users.values()};transactions={u:c.begin() for u,c in connections.items()}
@contextmanager
def isolated(user):
    c=connections[user]
    with c.begin_nested():
        c.execute(text("SELECT set_config('app.user_id',:id,true)"),{'id':str(user)})
        yield c
def cached(credentials=Depends(auth.bearer)):
    for role,token in tokens.items():
        if credentials and credentials.credentials==token:return users[role]
    raise HTTPException(401,'Token no válido')
modules=[auth,cash,sales];original={m:m.user_connection for m in modules}
for m in modules:m.user_connection=isolated
app.dependency_overrides[auth.verify_identity]=cached
client=TestClient(app);pool=ThreadPoolExecutor(max_workers=2)
try:
    sale=pool.submit(client.post,'/api/sales',headers={'Authorization':'Bearer '+tokens['vendedor']},json={'clave_idempotencia':str(uuid4()),'metodo_pago':'efectivo','items':[{'producto_id':str(product['id']),'cantidad':1,'precio_esperado':str(product['precio_venta'])}]})
    assert sale.result(timeout=30).status_code==201
    close=pool.submit(client.post,f"/api/cash/{box['id']}/close",headers={'Authorization':'Bearer '+tokens['gerente']},json={'contado':str(expected)})
    from concurrent.futures import TimeoutError
    try:
        close.result(timeout=.4)
        raise AssertionError('El cierre no esperó a la transacción de venta.')
    except TimeoutError:pass
    transactions[users['vendedor']].rollback()
    result=close.result(timeout=30)
    assert result.status_code==200,(result.status_code,result.text)
    assert result.json()['estado']=='cerrada' and float(result.json()['diferencia'])==0
    print('PASS: cierre esperó el bloqueo de la venta; al liberarse recalculó el efectivo correctamente.')
    (root/'.artifacts/v3-cash-concurrency.json').write_text(json.dumps({'cierre_espera_venta':True,'recalcula_totales':True,'rollback':True}),encoding='utf-8')
finally:
    for t in transactions.values():
        if t.is_active:t.rollback()
    pool.shutdown(wait=True)
    for c in connections.values():c.close()
    for m in modules:m.user_connection=original[m]
    app.dependency_overrides.clear()
    print('ROLLBACK: la caja real permanece abierta y no se conserva la venta de prueba.')
