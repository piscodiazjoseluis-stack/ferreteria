"""Real PostgreSQL, real API validation/RLS, substituted LOCAL identities only."""
import json
import sys
import time
from pathlib import Path
from uuid import uuid4
import psycopg
from fastapi.testclient import TestClient
from final_test_app import app

ROOT=Path(__file__).resolve().parents[2]
(ROOT/'.artifacts').mkdir(exist_ok=True)
checks=[]; client=TestClient(app)
def request(method,path,data=None,role='gerente',status=200):
    t=time.perf_counter();r=client.request(method,'/api'+path,json=data,headers={'Authorization':'Bearer '+role})
    assert r.status_code==status,(method,path,r.status_code,r.text[:500])
    checks.append({'method':method,'path':path,'role':role,'status':status,'seconds':round(time.perf_counter()-t,3)})
    return r.json() if 'json' in r.headers.get('content-type','') else r.content

def run():
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/ferreteria_final_test',autocommit=True) as c:
        for n,role in enumerate(('gerente','vendedor','almacenero','cajero'),1):
            id=f'00000000-0000-4000-8000-{n:012}'
            c.execute('INSERT INTO auth.users VALUES(%s) ON CONFLICT DO NOTHING',(id,))
            c.execute('INSERT INTO ferreteria.perfiles(id,nombre,rol) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(id,role.title()+' de prueba',role))
    category=request('GET','/categories')[0]['id']; suffix=uuid4().hex[:7]
    def product(code,kind,unit,stock,cost,price=10):
        return request('POST','/products',{'codigo':code+suffix,'nombre':code+' de prueba','categoria_id':category,'unidad_venta':unit,'precio_venta':price,'stock_minimo':0,'stock_objetivo':10,'saldo_inicial':stock,'costo_unitario':cost,'tipo':kind},status=201)
    base=product('BASE','insumo','ml',1000,.02)
    tint=product('TINTE','insumo','g',50,.2)
    output=product('PINTURA','preparado','unidad',0,0,25)
    saleproduct=product('CINTA','mercaderia','unidad',10,4,7.5)
    request('POST','/inventory/'+saleproduct['id']+'/entries',{'cantidad':.5,'motivo':'Fracción inválida'},status=422)
    cust=request('POST','/customers',{'nombre':'Cliente de integración','documento':'D'+suffix,'segmento':'maestro','limite_credito':100},status=201)
    request('POST','/customers',{'nombre':'Crédito no autorizado','documento':'X'+suffix,'limite_credito':1},role='vendedor',status=403)
    f=request('POST','/mixing/formulas',{'codigo':'COLOR-'+suffix,'tono':'Azul de prueba','cliente_id':cust['id'],'salida_id':output['id'],'rendimiento':1,'margen':30,'componentes':[{'producto_id':base['id'],'cantidad':250.5,'funcion':'base'},{'producto_id':tint['id'],'cantidad':2.125,'funcion':'colorante'}]},role='vendedor',status=201)
    key=str(uuid4());prepare={'id':key,'formula_id':f['id'],'lotes':1}
    p=request('POST','/mixing/preparations',prepare,role='vendedor',status=201)
    assert float(p['costo'])==5.44 and float(p['precio_sugerido'])==7.07
    request('POST','/mixing/preparations',prepare,role='vendedor',status=201)
    stocks={p['id']:float(p['stock']) for p in request('GET','/products')};assert stocks[base['id']]==749.5 and stocks[tint['id']]==47.875 and stocks[output['id']]==1
    request('POST','/mixing/preparations',{**prepare,'lotes':2},role='vendedor',status=409)
    request('POST','/mixing/preparations',{'id':str(uuid4()),'formula_id':f['id'],'lotes':100},role='vendedor',status=409)
    request('POST','/mixing/preparations',{'id':str(uuid4()),'formula_id':f['id']},role='cajero',status=403)
    request('POST','/cash',{'fondo':100},role='cajero',status=201)
    def sell(pay='efectivo',prod=saleproduct,qty=2):
        return request('POST','/sales',{'clave_idempotencia':str(uuid4()),'cliente_id':cust['id'],'metodo_pago':pay,'items':[{'producto_id':prod['id'],'cantidad':qty,'precio_esperado':prod['precio_venta']}]},role='vendedor',status=201)
    cash_sale=sell();credit=sell('credito',output,1)
    today=request('GET','/cash/status',role='vendedor')['fecha'];box=request('GET','/cash/day/'+today,role='cajero')
    assert float(box['totales']['efectivo_esperado'])==115
    account=request('GET','/customers/'+cust['id']+'/account');assert float(account['saldo'])==25
    abono={'id':str(uuid4()),'venta_id':credit['id'],'importe':10,'metodo_pago':'efectivo'}
    request('POST','/customers/payments',abono,role='cajero',status=201);request('POST','/customers/payments',abono,role='cajero',status=201)
    request('POST','/customers/payments',{**abono,'id':str(uuid4()),'importe':16},role='cajero',status=409)
    request('POST','/customers/payments',{**abono,'id':str(uuid4()),'importe':1},role='vendedor',status=403)
    assert float(request('GET','/cash/day/'+today,role='cajero')['totales']['efectivo_esperado'])==125
    request('POST','/sales/'+credit['id']+'/void',{'motivo':'Tiene abonos'},status=409)
    pdf=request('GET','/sales/'+cash_sale['id']+'/pdf');assert pdf.startswith(b'%PDF')
    request('POST','/sales/'+cash_sale['id']+'/void',{'motivo':'Error de registro'})
    request('POST','/sales/'+cash_sale['id']+'/void',{'motivo':'Error de registro'})
    assert float(request('GET','/cash/day/'+today,role='cajero')['totales']['efectivo_esperado'])==110
    public=request('GET','/public/catalog?buscar=CINTA')
    assert all('costo_unitario' not in p and p['disponible'] for p in public['productos'])
    assert not request('GET','/public/catalog?buscar=BASE')['productos']
    request('GET','/management/audit',role='vendedor',status=403)
    audit=request('GET','/management/audit');assert any(a['tabla']=='anulaciones' for a in audit)
    report=request('GET','/reports?tipo=ventas&buscar='+saleproduct['codigo']);assert report['totales']['registros']==0
    supplier=request('POST','/suppliers',{'nombre':'Distribución '+suffix,'condiciones_pago':'Contado'},status=201)
    draft=request('POST','/purchases',{'proveedor_id':supplier['id'],'borrador':True,'items':[{'producto_id':base['id'],'cantidad':1,'costo_unitario':.04}]},status=201)
    request('POST','/purchases/'+draft['id']+'/receive',{'clave_idempotencia':str(uuid4()),'items':[{'detalle_id':draft['items'][0]['id'],'cantidad_fisica':1}]},role='almacenero',status=409)
    sent=request('POST','/purchases/'+draft['id']+'/send');assert sent['estado']=='pendiente'
    request('POST','/purchases/'+draft['id']+'/cancel')
    purchase=request('POST','/purchases',{'proveedor_id':supplier['id'],'items':[{'producto_id':base['id'],'cantidad':10.5,'costo_unitario':.04}]},status=201)
    receipt={'clave_idempotencia':str(uuid4()),'items':[{'detalle_id':purchase['items'][0]['id'],'cantidad_fisica':4.25}]}
    partial=request('POST','/purchases/'+purchase['id']+'/receive',receipt,role='almacenero')
    assert float(partial['items'][0]['pendiente'])==6.25 and 'total_estimado' not in partial
    from app.reporting import replenishment
    from app.auth import Profile
    from uuid import UUID
    suggestions=replenishment(Profile(id=UUID('00000000-0000-4000-8000-000000000001'),nombre='Gerente de prueba',rol='gerente',activo=True))
    assert float(next(r for r in suggestions if str(r['id'])==base['id'])['pendiente'])==6.25
    request('POST','/purchases/'+purchase['id']+'/receive',receipt,role='almacenero')
    product_after=next(p for p in request('GET','/products') if p['id']==base['id'])
    assert float(product_after['stock'])==753.75 and float(product_after['costo_unitario'])==.0201
    public=request('GET','/public/catalog?buscar='+suffix)
    assert len(public['productos'])==2 and all('costo_unitario' not in p for p in public['productos'])
    request('GET','/customers',role='almacenero',status=403)
    request('POST','/sales',{'clave_idempotencia':str(uuid4()),'cliente_id':cust['id'],'metodo_pago':'credito','items':[{'producto_id':saleproduct['id'],'cantidad':20,'precio_esperado':7.5}]},role='vendedor',status=409)
    request('GET','/reports?tipo=ventas&buscar='+output['codigo']+'&csv_export=true')
    request('GET','/management/analytics?desde='+today+'&hasta='+today)
    if '--demo' in sys.argv:
        print('Datos locales de demostración listos; caja abierta.'); return
    request('POST','/cash/'+box['id']+'/close',{'contado':109},role='cajero',status=422)
    closed=request('POST','/cash/'+box['id']+'/close',{'contado':109,'motivo':'Diferencia simulada'},role='cajero');assert float(closed['diferencia'])==-1
    request('POST','/customers/payments',{**abono,'id':str(uuid4()),'importe':1},role='cajero',status=409)
    # Check exact ledger reconciliation, including fractional consumption and reversals.
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/ferreteria_final_test') as c:
        assert not c.execute('''SELECT e.producto_id FROM ferreteria.existencias e LEFT JOIN ferreteria.movimientos_inventario m ON m.producto_id=e.producto_id GROUP BY e.producto_id,e.cantidad HAVING e.cantidad<>coalesce(sum(m.variacion),0)''').fetchall()
    (ROOT/'.artifacts/final-validation.json').write_text(json.dumps({'identity':'LOCAL dependency override; not Supabase Auth','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS:',len(checks),'requests; ledger reconciled; local PostgreSQL and RLS.')

if __name__=='__main__':run()
