"""Ventas al contado: precio del servidor, stock bloqueado e historial atómico."""

import hashlib
import json
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth import Profile, require_sales_access
from app.database import user_connection

router = APIRouter(prefix='/api/sales', tags=['Ventas'])


class SaleLine(BaseModel):
    producto_id: UUID
    cantidad: int = Field(gt=0, le=2_147_483_647)
    precio_esperado: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SaleRequest(BaseModel):
    clave_idempotencia: UUID
    metodo_pago: Literal['efectivo', 'yape', 'plin', 'transferencia', 'tarjeta']
    items: list[SaleLine] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def distinct_products(self):
        if len({item.producto_id for item in self.items}) != len(self.items):
            raise ValueError('Cada producto debe aparecer una sola vez en la venta.')
        return self


def request_hash(data: SaleRequest) -> str:
    canonical = {
        'metodo_pago': data.metodo_pago,
        'items': sorted((str(i.producto_id), i.cantidad) for i in data.items),
    }
    return hashlib.sha256(json.dumps(canonical, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def receipt(connection, sale_id: UUID, profile: Profile):
    row = connection.execute(text('''
      SELECT id,numero,usuario_id,fecha,metodo_pago,total,clave_idempotencia
      FROM ferreteria.ventas WHERE id=:id
    '''), {'id': sale_id}).mappings().one_or_none()
    if row is None or (profile.rol == 'vendedor' and row['usuario_id'] != profile.id):
        raise HTTPException(404, 'Venta no encontrada.')
    lines = connection.execute(text('''
      SELECT producto_id,codigo_producto,nombre_producto,unidad_venta,cantidad,
             precio_unitario,subtotal
      FROM ferreteria.detalle_venta WHERE venta_id=:id ORDER BY codigo_producto
    '''), {'id': sale_id}).mappings().all()
    return {**dict(row), 'usuario': profile.nombre if row['usuario_id'] == profile.id else 'Otro colaborador',
            'items': [dict(line) for line in lines]}


@router.post('', status_code=201)
def create_sale(data: SaleRequest, profile: Annotated[Profile, Depends(require_sales_access)]):
    fingerprint = request_hash(data)
    try:
        with user_connection(profile.id) as connection:
            # Serialize requests with the same key before reading or changing stock.
            connection.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                               {'key': str(data.clave_idempotencia)})
            existing = connection.execute(text('''
              SELECT id,huella_solicitud FROM ferreteria.ventas WHERE clave_idempotencia=:key
            '''), {'key': data.clave_idempotencia}).mappings().one_or_none()
            if existing:
                if existing['huella_solicitud'] != fingerprint:
                    raise HTTPException(409, 'Esta clave ya corresponde a una venta diferente.')
                return receipt(connection, existing['id'], profile)

            stock = {}
            for item in sorted(data.items, key=lambda line: str(line.producto_id)):
                row = connection.execute(text('''
                  SELECT p.id,p.codigo,p.nombre,p.unidad_venta,p.precio_venta,p.activo,
                         e.cantidad AS disponible
                  FROM ferreteria.productos p
                  JOIN ferreteria.existencias e ON e.producto_id=p.id
                  WHERE p.id=:id FOR UPDATE OF e
                '''), {'id': item.producto_id}).mappings().one_or_none()
                if row is None or not row['activo']:
                    raise HTTPException(422, 'Un producto no existe o está inactivo.')
                if row['disponible'] < item.cantidad:
                    raise HTTPException(409, f"Stock insuficiente para {row['nombre']}: quedan {row['disponible']}.")
                if row['precio_venta'] != item.precio_esperado:
                    raise HTTPException(409, f"El precio de {row['nombre']} cambió. Revisa el precio actualizado antes de confirmar.")
                stock[item.producto_id] = row

            total = sum((stock[i.producto_id]['precio_venta'] * i.cantidad for i in data.items), Decimal('0'))
            if total > Decimal('9999999999.99'):
                raise HTTPException(422, 'El total supera el importe permitido.')
            sale_id = connection.execute(text('''
              INSERT INTO ferreteria.ventas(usuario_id,metodo_pago,total,clave_idempotencia,huella_solicitud)
              VALUES (:user_id,:payment,:total,:key,:fingerprint) RETURNING id
            '''), {'user_id': profile.id, 'payment': data.metodo_pago, 'total': total,
                   'key': data.clave_idempotencia, 'fingerprint': fingerprint}).scalar_one()

            for item in data.items:
                product = stock[item.producto_id]
                detail_id = connection.execute(text('''
                  INSERT INTO ferreteria.detalle_venta
                    (venta_id,producto_id,codigo_producto,nombre_producto,unidad_venta,cantidad,precio_unitario)
                  VALUES (:sale_id,:product_id,:code,:name,:unit,:quantity,:price) RETURNING id
                '''), {'sale_id': sale_id, 'product_id': item.producto_id,
                       'code': product['codigo'], 'name': product['nombre'],
                       'unit': product['unidad_venta'], 'quantity': item.cantidad,
                       'price': product['precio_venta']}).scalar_one()
                before = product['disponible']
                after = before - item.cantidad
                connection.execute(text('''
                  UPDATE ferreteria.existencias SET cantidad=:after,actualizado_en=now()
                  WHERE producto_id=:id
                '''), {'after': after, 'id': item.producto_id})
                connection.execute(text('''
                  INSERT INTO ferreteria.movimientos_inventario
                    (producto_id,tipo,variacion,stock_anterior,stock_resultante,motivo,usuario_id,detalle_venta_id)
                  VALUES (:id,'venta',:delta,:before,:after,:reason,:user_id,:detail_id)
                '''), {'id': item.producto_id, 'delta': -item.cantidad, 'before': before,
                       'after': after, 'reason': 'Venta confirmada', 'user_id': profile.id,
                       'detail_id': detail_id})
            return receipt(connection, sale_id, profile)
    except IntegrityError:
        raise HTTPException(409, 'La venta ya fue registrada o no cumple las reglas de datos.') from None


@router.get('')
def list_sales(profile: Annotated[Profile, Depends(require_sales_access)]):
    with user_connection(profile.id) as connection:
        rows = connection.execute(text('''
          SELECT v.id,v.numero,v.usuario_id,v.fecha,v.metodo_pago,v.total,
                 count(d.id) AS lineas,coalesce(sum(d.cantidad),0) AS unidades
          FROM ferreteria.ventas v
          JOIN ferreteria.detalle_venta d ON d.venta_id=v.id
          WHERE (:manager OR v.usuario_id=:user_id)
          GROUP BY v.id ORDER BY v.fecha DESC,v.numero DESC LIMIT 100
        '''), {'manager': profile.rol == 'gerente', 'user_id': profile.id}).mappings()
        return [{**dict(row), 'usuario': profile.nombre if row['usuario_id'] == profile.id else 'Otro colaborador'}
                for row in rows]


@router.get('/summary')
def sales_summary(profile: Annotated[Profile, Depends(require_sales_access)]):
    with user_connection(profile.id) as connection:
        row = connection.execute(text('''
          SELECT count(*) AS total_ventas,
                 count(*) FILTER (WHERE (fecha AT TIME ZONE 'America/Lima')::date =
                   (now() AT TIME ZONE 'America/Lima')::date) AS ventas_hoy,
                 coalesce(sum(total) FILTER (WHERE (fecha AT TIME ZONE 'America/Lima')::date =
                   (now() AT TIME ZONE 'America/Lima')::date),0) AS importe_hoy
          FROM ferreteria.ventas
          WHERE (:manager OR usuario_id=:user_id)
        '''), {'manager': profile.rol == 'gerente', 'user_id': profile.id}).mappings().one()
        return dict(row)


@router.get('/{sale_id}')
def get_sale(sale_id: UUID, profile: Annotated[Profile, Depends(require_sales_access)]):
    with user_connection(profile.id) as connection:
        return receipt(connection, sale_id, profile)
