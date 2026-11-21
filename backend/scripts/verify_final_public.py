"""Real production login and explicit demonstration transactions.

Requires MF_MANAGER_TEST_PASSWORD. Idempotent demo manifest in ignored .artifacts.
Never closes a real box. Other accounts are read from private provisioning files.
"""
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4
import httpx
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.config import get_settings
s=get_settings();base='https://ferreteria-miguel-v2.vercel.app';client=httpx.Client(timeout=30)
headers={};checks=[]
accounts=json.loads((ROOT/'.artifacts/demo-accounts.json').read_text())
roles={'gerente':{'email':'gerente.ferreteria3@gmail.com','password':os.environ['MF_MANAGER_TEST_PASSWORD']},'vendedor':next(a for a in accounts if a['rol']=='vendedor'),'almacenero':json.loads((ROOT/'.artifacts/warehouse-account.json').read_text()),'cajero':json.loads((ROOT/'.artifacts/cashier-account.json').read_text())}
for role,a in roles.items():
    r=client.post(s.supabase_url+'/auth/v1/token?grant_type=password',headers={'apikey':s.supabase_publishable_key},json={k:a[k] for k in ['email','password']});r.raise_for_status();headers[role]={'Authorization':'Bearer '+r.json()['access_token']}

def call(method,path,data=None,role='gerente',status=200):
    t=time.perf_counter();r=client.request(method,base+'/api'+path,json=data,headers=headers[role]);assert r.status_code==status,(method,path,r.status_code,r.text[:350]);checks.append({'path':path,'role':role,'status':status,'seconds':round(time.perf_counter()-t,3)})
    return r.json() if 'json' in r.headers.get('content-type','') else r.content

for role in roles:assert call('GET','/auth/me',role=role)['rol']==role
manifest=ROOT/'.artifacts/final-public-demo.json'
if manifest.exists():demo=json.loads(manifest.read_text())
else:
    demo={};manifest.write_text('{}')

def keep(key,value):
    demo[key]=value;manifest.write_text(json.dumps(demo,ensure_ascii=False,indent=2));return value

category=call('GET','/categories')[0]['id']
def product(key,code,name,kind,unit,stock,cost,price):
    if key in demo:return demo[key]
    existing=next((p for p in call('GET','/products') if p['codigo']==code),None)
    p=existing or call('POST','/products',{'codigo':code,'nombre':name,'categoria_id':category,'unidad_venta':unit,'saldo_inicial':stock,'stock_minimo':0,'stock_objetivo':stock,'precio_venta':price,'costo_unitario':cost,'tipo':kind,'marca':'Demostración académica'},status=201)
    return keep(key,p)
base_product=product('base','FINAL-BASE-001','Base blanca demo final','insumo','ml',1000,.02,.03)
tint=product('tint','FINAL-TINTE-001','Colorante azul demo final','insumo','g',50,.2,.3)
output=product('output','FINAL-PINTURA-001','Pintura azul preparada demo final','preparado','unidad',0,0,25)
if 'customer' not in demo:
    old=next((r for r in call('GET','/customers') if r['documento']=='DEMO-FINAL-001'),None)
    keep('customer',old or call('POST','/customers',{'nombre':'Cliente ficticio de demostración final','documento':'DEMO-FINAL-001','segmento':'maestro','limite_credito':100},status=201))
if 'formula' not in demo:
    old=next((r for r in call('GET','/mixing/formulas',role='vendedor') if r['codigo']=='FINAL-AZUL-001'),None)
    keep('formula',old or call('POST','/mixing/formulas',{'codigo':'FINAL-AZUL-001','tono':'Azul de demostración final','referencia':'Receta académica, validar muestra física','cliente_id':demo['customer']['id'],'salida_id':output['id'],'rendimiento':1,'margen':30,'componentes':[{'producto_id':base_product['id'],'cantidad':250.5,'funcion':'base'},{'producto_id':tint['id'],'cantidad':2.125,'funcion':'colorante'}]},role='vendedor',status=201))
if 'prepare_key' not in demo:keep('prepare_key',str(uuid4()))
if 'preparation' not in demo:keep('preparation',call('POST','/mixing/preparations',{'id':demo['prepare_key'],'formula_id':demo['formula']['id'],'lotes':1},role='vendedor',status=201))
today=call('GET','/cash/status',role='cajero')['fecha'];box=call('GET','/cash/day/'+today,role='cajero')
if box is None:box=call('POST','/cash',{'fondo':100},role='cajero',status=201)
if 'sale_key' not in demo:keep('sale_key',str(uuid4()))
if 'sale' not in demo:keep('sale',call('POST','/sales',{'clave_idempotencia':demo['sale_key'],'cliente_id':demo['customer']['id'],'metodo_pago':'credito','items':[{'producto_id':output['id'],'cantidad':1,'precio_esperado':25}]},role='vendedor',status=201))
if 'payment_key' not in demo:keep('payment_key',str(uuid4()))
if 'payment' not in demo:keep('payment',call('POST','/customers/payments',{'id':demo['payment_key'],'venta_id':demo['sale']['id'],'importe':10,'metodo_pago':'efectivo'},role='cajero',status=201))
account=call('GET','/customers/'+demo['customer']['id']+'/account');assert float(account['saldo'])==15
assert call('GET','/sales/'+demo['sale']['id']+'/pdf',role='vendedor').startswith(b'%PDF')
call('GET','/management/audit',role='vendedor',status=403);call('GET','/customers',role='almacenero',status=403);call('GET','/cash',role='vendedor',status=403)
report=call('GET','/reports?tipo=ventas&buscar=FINAL-PINTURA-001');assert float(report['totales']['importe'])==25
csv=call('GET','/reports?tipo=ventas&buscar=FINAL-PINTURA-001&csv_export=true');assert b'credito' in csv
public=client.get(base+'/api/public/catalog?buscar=FINAL-').json();assert all('costo_unitario' not in p for p in public['productos']) and len(public['productos'])==1
stocks={r['codigo']:float(r['stock']) for r in call('GET','/products')};assert stocks['FINAL-BASE-001']==749.5 and stocks['FINAL-TINTE-001']==47.875
cash=call('GET','/cash/day/'+today,role='cajero');assert float(cash['totales']['abonos_efectivo'])>=10
(ROOT/'.artifacts/final-public-validation.json').write_text(json.dumps({'url':base,'real_auth':list(roles),'checks':checks,'debt':account['saldo'],'cash_open':cash['estado']},ensure_ascii=False,indent=2),encoding='utf-8')
print('PRODUCTION PASS:',len(checks),'checks, 4 real logins, debt=15, cash remains',cash['estado'])
