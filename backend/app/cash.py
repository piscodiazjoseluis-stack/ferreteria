"""Caja global por día de Lima y cierre inmutable, coordinado con ventas."""
import json
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from app.auth import Profile, require_manager, require_sales_access
from app.database import user_connection

router = APIRouter(prefix='/api/cash', tags=['Caja diaria'])
Manager = Annotated[Profile, Depends(require_manager)]


def today(c):
    return c.execute(text("SELECT (now() AT TIME ZONE 'America/Lima')::date")).scalar_one()


def lock_day(c, day):
    c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'), {'key': f'cash:{day}'})


def require_open_cash(c):
    day = today(c)
    lock_day(c, day)
    state = c.execute(text('SELECT estado FROM ferreteria.cajas WHERE fecha=:day'), {'day': day}).scalar_one_or_none()
    if state != 'abierta':
        raise HTTPException(409, 'Gerencia debe abrir la caja de hoy antes de vender.' if state is None else 'La caja de hoy ya está cerrada. No se admiten nuevas ventas.')


def totals(c, box):
    sales = c.execute(text('''SELECT metodo_pago,count(*) AS operaciones,sum(total) AS total FROM ferreteria.ventas
      WHERE fecha>=CAST(:day AS date) AT TIME ZONE 'America/Lima'
      AND fecha<(CAST(:day AS date)+1) AT TIME ZONE 'America/Lima' GROUP BY metodo_pago'''), {'day':box['fecha']}).mappings().all()
    payments = {k:Decimal('0') for k in ('efectivo','yape','plin','transferencia','tarjeta')}
    for s in sales: payments[s['metodo_pago']] = s['total']
    m = c.execute(text('''SELECT coalesce(sum(importe) FILTER(WHERE tipo='ingreso'),0) AS ingresos,
      coalesce(sum(importe) FILTER(WHERE tipo='retiro'),0) AS retiros FROM ferreteria.movimientos_caja WHERE caja_id=:id'''), {'id':box['id']}).mappings().one()
    return {'pagos':payments,'ventas_total':sum(payments.values()),'operaciones':sum(s['operaciones'] for s in sales),
            **dict(m),'efectivo_esperado':box['fondo']+payments['efectivo']+m['ingresos']-m['retiros']}


def view(c, box):
    movements = [dict(r) for r in c.execute(text('SELECT * FROM ferreteria.movimientos_caja WHERE caja_id=:id ORDER BY fecha DESC,id'), {'id':box['id']}).mappings()]
    return {**dict(box),'totales':box['resumen'] if box['estado']=='cerrada' else totals(c,box),'movimientos':movements}


def locked_box(c, box_id):
    day = c.execute(text('SELECT fecha FROM ferreteria.cajas WHERE id=:id'), {'id':box_id}).scalar_one_or_none()
    if day is None: raise HTTPException(404, 'Caja no encontrada.')
    lock_day(c,day)
    return c.execute(text('SELECT * FROM ferreteria.cajas WHERE id=:id FOR UPDATE'), {'id':box_id}).mappings().one()


@router.get('/status')
def status(profile: Annotated[Profile, Depends(require_sales_access)]):
    with user_connection(profile.id) as c:
        day = today(c)
        state = c.execute(text('SELECT estado FROM ferreteria.cajas WHERE fecha=:day'), {'day':day}).scalar_one_or_none()
        return {'fecha':day,'estado':state or 'sin_abrir'}


@router.get('')
def list_boxes(profile: Manager):
    with user_connection(profile.id) as c:
        return [dict(r) for r in c.execute(text('SELECT id,fecha,estado,fondo,contado,diferencia,abierto_nombre,cerrado_nombre FROM ferreteria.cajas ORDER BY fecha DESC LIMIT 60')).mappings()]


@router.get('/day/{day}')
def get_day(day:date, profile:Manager):
    with user_connection(profile.id) as c:
        box = c.execute(text('SELECT * FROM ferreteria.cajas WHERE fecha=:day'), {'day':day}).mappings().one_or_none()
        return view(c,box) if box else None


class OpenInput(BaseModel):
    fondo:Decimal = Field(ge=0,max_digits=12,decimal_places=2)


@router.post('',status_code=201)
def open_box(data:OpenInput, profile:Manager):
    with user_connection(profile.id) as c:
        day=today(c); lock_day(c,day)
        old=c.execute(text('SELECT * FROM ferreteria.cajas WHERE fecha=:day'), {'day':day}).mappings().one_or_none()
        if old:
            if old['estado']=='abierta' and old['fondo']==data.fondo: return view(c,old)
            raise HTTPException(409,'Ya existe una caja para hoy. Abre su detalle.')
        box=c.execute(text('''INSERT INTO ferreteria.cajas(fecha,fondo,abierto_por,abierto_nombre)
          VALUES (:day,:amount,:user,:name) RETURNING *'''), {'day':day,'amount':data.fondo,'user':profile.id,'name':profile.nombre}).mappings().one()
        return view(c,box)


class MovementInput(BaseModel):
    id:UUID
    tipo:Literal['ingreso','retiro']
    importe:Decimal = Field(gt=0,max_digits=12,decimal_places=2)
    motivo:str = Field(min_length=3,max_length=500)


@router.post('/{box_id}/movements',status_code=201)
def add_movement(box_id:UUID,data:MovementInput,profile:Manager):
    if len(data.motivo.strip())<3: raise HTTPException(422,'Explica el motivo del movimiento.')
    with user_connection(profile.id) as c:
        box=locked_box(c,box_id)
        old=c.execute(text('SELECT * FROM ferreteria.movimientos_caja WHERE id=:id'), {'id':data.id}).mappings().one_or_none()
        if old:
            if old['caja_id']!=box_id or old['tipo']!=data.tipo or old['importe']!=data.importe or old['motivo']!=data.motivo.strip():
                raise HTTPException(409,'El reintento no coincide con el movimiento original.')
            return view(c,box)
        if box['estado']!='abierta': raise HTTPException(409,'La caja está cerrada.')
        available=totals(c,box)['efectivo_esperado']
        if data.tipo=='retiro' and data.importe>available: raise HTTPException(409,'El retiro supera el efectivo esperado disponible.')
        if data.tipo=='ingreso' and available+data.importe>Decimal('9999999999.99'): raise HTTPException(422,'El efectivo supera el límite permitido.')
        c.execute(text('''INSERT INTO ferreteria.movimientos_caja(id,caja_id,tipo,importe,motivo,usuario_id,usuario_nombre)
          VALUES (:id,:box,:type,:amount,:reason,:user,:name)'''), {'id':data.id,'box':box_id,'type':data.tipo,'amount':data.importe,'reason':data.motivo.strip(),'user':profile.id,'name':profile.nombre})
        return view(c,box)


class CloseInput(BaseModel):
    contado:Decimal = Field(ge=0,max_digits=12,decimal_places=2)
    motivo:str = Field(default='',max_length=500)


@router.post('/{box_id}/close')
def close_box(box_id:UUID,data:CloseInput,profile:Manager):
    with user_connection(profile.id) as c:
        box=locked_box(c,box_id)
        if box['estado']=='cerrada':
            if box['contado']==data.contado and box['motivo']==data.motivo.strip(): return view(c,box)
            raise HTTPException(409,'El cierre ya está confirmado y no puede modificarse.')
        summary=totals(c,box); expected=summary['efectivo_esperado']; difference=data.contado-expected
        if difference and len(data.motivo.strip())<3: raise HTTPException(422,'Hay una diferencia. Explica el motivo antes de cerrar.')
        if expected>Decimal('9999999999.99') or abs(difference)>Decimal('9999999999.99'): raise HTTPException(422,'El cierre supera el límite de importe permitido.')
        box=c.execute(text('''UPDATE ferreteria.cajas SET estado='cerrada',contado=:count,esperado=:expected,diferencia=:difference,
          resumen=CAST(:summary AS jsonb),motivo=:reason,cerrado_por=:user,cerrado_nombre=:name,cerrado_en=now() WHERE id=:id RETURNING *'''),
          {'id':box_id,'count':data.contado,'expected':expected,'difference':difference,'summary':json.dumps(summary,default=str),'reason':data.motivo.strip(),'user':profile.id,'name':profile.nombre}).mappings().one()
        return view(c,box)
