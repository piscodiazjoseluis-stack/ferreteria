"""Customer accounts: immutable charges and payments, computed debt."""
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.auth import Profile, require_sales_access, require_manager, require_cashier
from app.database import user_connection
from app.cash import require_open_cash

router=APIRouter(prefix='/api/customers',tags=['Clientes y crÃ©dito'])
Staff=Annotated[Profile,Depends(require_sales_access)]

class CustomerInput(BaseModel):
    nombre:str=Field(min_length=2,max_length=160)
    documento:str=Field(min_length=5,max_length=20)
    segmento:Literal['publico','maestro','empresa']='publico'
    contacto:str=Field(default='',max_length=160)
    direccion:str=Field(default='',max_length=250)
    limite_credito:Decimal=Field(default=0,ge=0,max_digits=12,decimal_places=2)
    activo:bool=True

    @field_validator('nombre','documento')
    @classmethod
    def trimmed(cls,v):
        if len(v.strip())<2: raise ValueError('Completa el nombre y documento.')
        return v.strip()


def debt(c,client_id):
    return c.execute(text('''SELECT coalesce(sum(v.total-coalesce((SELECT sum(a.importe) FROM ferreteria.abonos a WHERE a.venta_id=v.id),0)),0)
      FROM ferreteria.ventas v WHERE v.cliente_id=:id AND v.condicion='credito'
      AND NOT EXISTS(SELECT 1 FROM ferreteria.anulaciones x WHERE x.venta_id=v.id)'''),{'id':client_id}).scalar_one()


@router.get('')
def customers(profile:Staff):
    with user_connection(profile.id) as c:
        rows=c.execute(text('SELECT * FROM ferreteria.clientes ORDER BY nombre')).mappings().all()
        # One grouped aggregation instead of a query per customer.
        balances={r['cliente_id']:r['saldo'] for r in c.execute(text('''SELECT v.cliente_id,sum(v.total-coalesce(a.pagado,0)) AS saldo
          FROM ferreteria.ventas v LEFT JOIN (SELECT venta_id,sum(importe) pagado FROM ferreteria.abonos GROUP BY venta_id) a ON a.venta_id=v.id
          WHERE v.condicion='credito' AND NOT EXISTS(SELECT 1 FROM ferreteria.anulaciones x WHERE x.venta_id=v.id) GROUP BY v.cliente_id''')).mappings()}
        return [{**dict(r),'saldo':balances.get(r['id'],0)} for r in rows]


@router.post('',status_code=201)
def create(data:CustomerInput,profile:Staff):
    if profile.rol!='gerente' and (data.limite_credito or not data.activo):
        raise HTTPException(403,'Solo Gerencia autoriza un lÃ­mite de crÃ©dito o desactiva clientes.')
    try:
        with user_connection(profile.id) as c:
            return dict(c.execute(text('''INSERT INTO ferreteria.clientes(nombre,documento,segmento,contacto,direccion,limite_credito,activo)
              VALUES(:nombre,:documento,:segmento,:contacto,:direccion,:limite_credito,:activo) RETURNING *'''),data.model_dump()).mappings().one())
    except IntegrityError:
        raise HTTPException(409,'El documento ya existe o los datos no son vÃ¡lidos.') from None


@router.put('/{client_id}')
def update(client_id:UUID,data:CustomerInput,profile:Annotated[Profile,Depends(require_manager)]):
    try:
        with user_connection(profile.id) as c:
            c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'client:'+str(client_id)})
            old=c.execute(text('SELECT id FROM ferreteria.clientes WHERE id=:id FOR UPDATE'),{'id':client_id}).first()
            if not old: raise HTTPException(404,'Cliente no encontrado.')
            if data.limite_credito<debt(c,client_id): raise HTTPException(409,'El lÃ­mite no puede ser menor a la deuda actual.')
            return dict(c.execute(text('''UPDATE ferreteria.clientes SET nombre=:nombre,documento=:documento,segmento=:segmento,
              contacto=:contacto,direccion=:direccion,limite_credito=:limite_credito,activo=:activo WHERE id=:id RETURNING *'''),{'id':client_id,**data.model_dump()}).mappings().one())
    except IntegrityError:
        raise HTTPException(409,'Documento duplicado o datos no vÃ¡lidos.') from None


@router.get('/{client_id}/account')
def account(client_id:UUID,profile:Staff):
    with user_connection(profile.id) as c:
        client=c.execute(text('SELECT * FROM ferreteria.clientes WHERE id=:id'),{'id':client_id}).mappings().one_or_none()
        if not client: raise HTTPException(404,'Cliente no encontrado.')
        invoices=[dict(r) for r in c.execute(text('''SELECT v.id,v.numero,v.fecha,v.total,
          coalesce((SELECT sum(importe) FROM ferreteria.abonos WHERE venta_id=v.id),0) AS pagado
          FROM ferreteria.ventas v WHERE v.cliente_id=:id AND v.condicion='credito'
          AND NOT EXISTS(SELECT 1 FROM ferreteria.anulaciones x WHERE x.venta_id=v.id) ORDER BY v.fecha DESC'''),{'id':client_id}).mappings()]
        payments=[dict(r) for r in c.execute(text('''SELECT a.* FROM ferreteria.abonos a JOIN ferreteria.ventas v ON v.id=a.venta_id WHERE v.cliente_id=:id ORDER BY a.fecha DESC'''),{'id':client_id}).mappings()]
        return {'cliente':dict(client),'saldo':debt(c,client_id),'ventas':invoices,'abonos':payments}


class PaymentInput(BaseModel):
    id:UUID
    venta_id:UUID
    importe:Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    metodo_pago:Literal['efectivo','yape','plin','transferencia','tarjeta']


@router.post('/payments',status_code=201)
def pay(data:PaymentInput,profile:Annotated[Profile,Depends(require_cashier)]):
    with user_connection(profile.id) as c:
        c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':str(data.id)})
        old=c.execute(text('SELECT * FROM ferreteria.abonos WHERE id=:id'),{'id':data.id}).mappings().one_or_none()
        if old:
            if old['venta_id']!=data.venta_id or old['importe']!=data.importe or old['metodo_pago']!=data.metodo_pago:
                raise HTTPException(409,'El reintento no coincide con el cobro registrado.')
            return dict(old)
        require_open_cash(c)
        sale=c.execute(text("SELECT * FROM ferreteria.ventas WHERE id=:id AND condicion='credito'"),{'id':data.venta_id}).mappings().one_or_none()
        if not sale or c.execute(text('SELECT 1 FROM ferreteria.anulaciones WHERE venta_id=:id'),{'id':data.venta_id}).first():
            raise HTTPException(404,'Venta a crÃ©dito vigente no encontrada.')
        c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'client:'+str(sale['cliente_id'])})
        paid=c.execute(text('SELECT coalesce(sum(importe),0) FROM ferreteria.abonos WHERE venta_id=:id'),{'id':data.venta_id}).scalar_one()
        if data.importe>sale['total']-paid: raise HTTPException(409,'El abono supera el saldo pendiente.')
        return dict(c.execute(text('''INSERT INTO ferreteria.abonos(id,venta_id,importe,metodo_pago,usuario_id,usuario_nombre)
          VALUES(:id,:venta_id,:importe,:metodo_pago,:user,:name) RETURNING *'''),{**data.model_dump(),'user':profile.id,'name':profile.nombre}).mappings().one())
