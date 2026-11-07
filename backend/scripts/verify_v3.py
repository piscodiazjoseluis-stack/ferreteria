"""Integración V3 con tokens reales, SQL/RLS reales y transacción revertida al final.

MF_MANAGER_TEST_PASSWORD se proporciona fuera del repositorio. No crea datos de
demostración permanentes ni cierra la caja real del día.
"""
import csv
import io
import json
import os
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from uuid import uuid4
import httpx
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app import auth,catalog,sales,purchasing,reporting,reports,cash
from app.config import get_settings
from app.database import get_engine
from app.main import app

settings=get_settings()
accounts=json.loads((ROOT/'.artifacts/demo-accounts.json').read_text(encoding='utf-8'))
warehouse=json.loads((ROOT/'.artifacts/warehouse-account.json').read_text(encoding='utf-8'))
manager={'email':'gerente.ferreteria3@gmail.com','password':os.environ['MF_MANAGER_TEST_PASSWORD']}
headers={}; identities={}; checks=[]
client=TestClient(app)
for role,account in [('gerente',manager),('vendedor',next(a for a in accounts if a['rol']=='vendedor')),('almacenero',warehouse)]:
    response=httpx.post(settings.supabase_url+'/auth/v1/token?grant_type=password',headers={'apikey':settings.supabase_publishable_key},json={k:account[k] for k in ('email','password')},timeout=20)
    assert response.status_code==200,(role,response.status_code)
    payload=response.json(); token=payload['access_token']; headers[role]={'Authorization':'Bearer '+token}; identities[token]=payload['user']['id']
    response=client.get('/api/auth/me',headers=headers[role]); assert response.status_code==200 and response.json()['rol']==role
    checks.append('Login real y perfil '+role)

def cached_identity(credentials=Depends(auth.bearer)):
    if credentials is None or credentials.credentials not in identities: raise HTTPException(401,'Token no válido')
    from uuid import UUID
    return UUID(identities[credentials.credentials])

# Upstream Auth has just validated these tokens; reuse only for the SQL suite.
app.dependency_overrides[auth.verify_identity]=cached_identity
connection=get_engine().connect(); transaction=connection.begin()
@contextmanager
def isolated_connection(user_id):
    with connection.begin_nested():
        connection.execute(text("SELECT set_config('app.user_id',:id,true)"),{'id':str(user_id)})
        yield connection
modules=[auth,catalog,sales,purchasing,reporting,reports,cash]
original={m:m.user_connection for m in modules}
for m in modules: m.user_connection=isolated_connection

def req(method,path,role='gerente',payload=None,status=200):
    r=client.request(method,'/api'+path,headers=headers[role],json=payload)
    assert r.status_code==status,(method,path,r.status_code,r.text[:500])
    return r.json() if 'application/json' in r.headers.get('content-type','') else r

try:
    cat=req('GET','/categories')[0]['id']
    product=req('POST','/products',payload={'codigo':'QA-V3-'+uuid4().hex[:8].upper(),'nombre':'Producto QA V3','categoria_id':cat,'unidad_venta':'unidad','precio_venta':25,'stock_minimo':8,'stock_objetivo':12,'saldo_inicial':4},status=201)
    supplier=req('POST','/suppliers',payload={'nombre':'Proveedor QA '+uuid4().hex[:8]},status=201)
    def suggest(): return next(r for r in req('GET','/management/replenishment') if r['id']==product['id'])
    assert suggest()['sugerida']==8
    order=req('POST','/purchases',payload={'proveedor_id':supplier['id'],'items':[{'producto_id':product['id'],'cantidad':10,'costo_unitario':15}]},status=201)
    assert suggest()['pendiente']==10 and suggest()['sugerida']==0
    detail=order['items'][0]['id']
    assert next(p for p in req('GET','/products') if p['id']==product['id'])['stock']==4
    empty={'clave_idempotencia':str(uuid4()),'items':[{'detalle_id':detail,'cantidad_fisica':0}]}
    req('POST',f"/purchases/{order['id']}/receive",'almacenero',empty,422)
    excess={'clave_idempotencia':str(uuid4()),'items':[{'detalle_id':detail,'cantidad_fisica':11}]}
    req('POST',f"/purchases/{order['id']}/receive",'almacenero',excess,409)
    first={'clave_idempotencia':str(uuid4()),'items':[{'detalle_id':detail,'cantidad_fisica':6}]}
    received=req('POST',f"/purchases/{order['id']}/receive",'almacenero',first)
    assert received['estado']=='parcial' and received['items'][0]['pendiente']==4 and 'total_estimado' not in received and 'costo_unitario' not in received['items'][0]
    req('POST',f"/purchases/{order['id']}/receive",'almacenero',first)
    assert next(p for p in req('GET','/products') if p['id']==product['id'])['stock']==10
    assert suggest()['pendiente']==4 and suggest()['sugerida']==0
    req('POST',f"/purchases/{order['id']}/cancel",status=409)
    changed={**first,'items':[{'detalle_id':detail,'cantidad_fisica':4}]}
    req('POST',f"/purchases/{order['id']}/receive",'almacenero',changed,409)
    final={**changed,'clave_idempotencia':str(uuid4())}
    received=req('POST',f"/purchases/{order['id']}/receive",'almacenero',final)
    assert received['estado']=='recibida' and received['items'][0]['recibida']==10 and len(received['recepciones'])==2
    req('POST',f"/purchases/{order['id']}/receive",'almacenero',final)
    assert next(p for p in req('GET','/products') if p['id']==product['id'])['stock']==14
    req('POST',f"/purchases/{order['id']}/receive",'almacenero',{**final,'clave_idempotencia':str(uuid4())},409)
    movements=[m for m in req('GET','/inventory/movements') if m['producto_id']==product['id'] and m['tipo']=='compra']
    assert len(movements)==2 and sum(m['variacion'] for m in movements)==10
    checks.append('Pedido 10, entregas 6+4, saldo pendiente, historial y stock 4 a 14')
    checks.append('Recepción vacía, exceso, repetición y cambio de reintento rechazados sin duplicar stock')
    checks.append('Reposición objetivo menos stock menos pendientes, costos ocultos para Almacén')

    req('GET','/cash/day/'+str(date.today()),'vendedor',status=403)
    req('GET','/cash','almacenero',status=403)
    req('GET','/management/replenishment','vendedor',status=403)
    req('GET','/reports?tipo=ventas','almacenero',status=403)
    req('GET','/reports?tipo=compras','vendedor',status=403)
    checks.append('Separación de permisos de los tres perfiles')

    day=req('GET','/cash/status','vendedor')['fecha']
    box=req('POST','/cash',payload={'fondo':100},status=201)
    sale_payload={'clave_idempotencia':str(uuid4()),'metodo_pago':'efectivo','items':[{'producto_id':product['id'],'cantidad':1,'precio_esperado':25}]}
    sale=req('POST','/sales','vendedor',sale_payload,201)
    req('POST','/sales','vendedor',sale_payload,201)
    req('POST','/sales','vendedor',{**sale_payload,'clave_idempotencia':str(uuid4()),'metodo_pago':'yape'},201)
    before=req('GET','/cash/day/'+day)
    movement={'id':str(uuid4()),'tipo':'ingreso','importe':20,'motivo':'Aporte QA'}
    req('POST',f"/cash/{box['id']}/movements",payload=movement,status=201)
    req('POST',f"/cash/{box['id']}/movements",payload=movement,status=201)
    req('POST',f"/cash/{box['id']}/movements",payload={**movement,'id':str(uuid4()),'tipo':'retiro','importe':10,'motivo':'Retiro QA'},status=201)
    current=req('GET','/cash/day/'+day)
    expected=float(before['totales']['efectivo_esperado'])+10
    assert float(current['totales']['efectivo_esperado'])==expected and float(current['totales']['pagos']['yape'])>=25
    req('POST',f"/cash/{box['id']}/movements",payload={**movement,'id':str(uuid4()),'tipo':'retiro','importe':99999999},status=409)
    req('POST',f"/cash/{box['id']}/close",payload={'contado':expected-1},status=422)
    closed=req('POST',f"/cash/{box['id']}/close",payload={'contado':expected-1,'motivo':'Diferencia QA'})
    assert float(closed['diferencia'])==-1 and closed['estado']=='cerrada'
    req('POST',f"/cash/{box['id']}/close",payload={'contado':expected-1,'motivo':'Diferencia QA'})
    req('POST',f"/cash/{box['id']}/close",payload={'contado':expected},status=409)
    req('POST','/sales','vendedor',{**sale_payload,'clave_idempotencia':str(uuid4())},409)
    req('POST','/sales','vendedor',sale_payload,201)
    req('POST',f"/cash/{box['id']}/movements",payload={**movement,'id':str(uuid4())},status=409)
    checks.append('Caja: fondo, efectivo vs Yape, ingresos y retiros sin duplicados')
    checks.append('Cierre: diferencia obligatoria, instantánea, bloqueo posterior y reintentos seguros')

    path='/reports?tipo=ventas&buscar='+product['codigo']
    report=req('GET',path+'&tamano=1'); page2=req('GET',path+'&tamano=1&pagina=2')
    assert report['totales']['registros']==2 and len(report['filas'])==1 and report['totales']['importe']==50
    assert page2['filas'][0]['numero']!=report['filas'][0]['numero']
    csv_response=req('GET',path+'&csv_export=true')
    records=list(csv.DictReader(io.StringIO(csv_response.content.decode('utf-8-sig')),delimiter=';'))
    assert len(records)==2 and sum(float(r['total']) for r in records)==50
    seller_report=req('GET','/reports?tipo=ventas','vendedor')
    assert all(r['responsable']==sale['usuario'] for r in seller_report['filas'])
    warehouse_report=req('GET','/reports?tipo=compras','almacenero')
    assert 'total_estimado' not in warehouse_report['columnas']
    req('GET','/reports?desde=2026-11-08&hasta=2026-11-01',status=422)
    checks.append('Reportes: filtros, permisos, paginación, totales completos y CSV reconciliado')
    # Additional relational fixtures exercise the old 100-row boundary without
    # creating 105 persistent test sales or altering any real stock.
    seller_id=identities[headers['vendedor']['Authorization'].split(' ',1)[1]]
    with isolated_connection(seller_id) as c:
        ids=c.execute(text('''INSERT INTO ferreteria.ventas(usuario_id,metodo_pago,total,clave_idempotencia,huella_solicitud)
          SELECT :user,'efectivo',25,gen_random_uuid(),repeat('a',64) FROM generate_series(1,105) RETURNING id'''), {'user':seller_id}).scalars().all()
        c.execute(text('''
          INSERT INTO ferreteria.detalle_venta(venta_id,producto_id,codigo_producto,nombre_producto,unidad_venta,cantidad,precio_unitario)
          SELECT id,:product,:code,'Producto QA V3','unidad',1,25 FROM ferreteria.ventas WHERE id=ANY(:ids)'''),
          {'ids':ids,'product':product['id'],'code':product['codigo']})
    many=req('GET',path+'&tamano=100')
    tail=req('GET',path+'&tamano=100&pagina=2')
    assert many['totales']['registros']==107 and len(many['filas'])==100 and len(tail['filas'])==7
    whole=req('GET',path+'&csv_export=true')
    assert len(list(csv.DictReader(io.StringIO(whole.content.decode('utf-8-sig')),delimiter=';')))==107
    checks.append('Más de 100 registros: acceso paginado y CSV completo de 107 ventas de prueba')
    print('\n'.join('PASS '+check for check in checks))
    (ROOT/'.artifacts/v3-validation.json').write_text(json.dumps({'checks':checks,'rollback':True},ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    transaction.rollback(); connection.close()
    for m in modules: m.user_connection=original[m]
    app.dependency_overrides.clear()
    print('ROLLBACK: no se conservan productos, ventas, pedidos ni cierres de esta prueba.')
