"""Ventas al contado: precio del servidor, stock bloqueado e historial atÃÆ’Â³mico."""

import hashlib
import json
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth import Profile, require_sales_access, require_manager
from app.values import Quantity, money, check_unit
from app.database import user_connection
from app.cash import require_open_cash

router = APIRouter(prefix='/api/sales', tags=['Ventas'])


class SaleLine(BaseModel):
    producto_id: UUID
    cantidad: Quantity
    precio_esperado: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SaleRequest(BaseModel):
    clave_idempotencia: UUID
    metodo_pago: Literal['efectivo', 'yape', 'plin', 'transferencia', 'tarjeta', 'credito']
    cliente_id: UUID | None = None
    items: list[SaleLine] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def distinct_products(self):
        if len({item.producto_id for item in self.items}) != len(self.items):
            raise ValueError('Cada producto debe aparecer una sola vez en la venta.')
        return self


def request_hash(data: SaleRequest) -> str:
    canonical = {
        'metodo_pago': data.metodo_pago,
        'cliente_id': str(data.cliente_id),
        'items': sorted((str(i.producto_id), str(i.cantidad.normalize())) for i in data.items),
    }
    return hashlib.sha256(json.dumps(canonical, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def receipt(connection, sale_id: UUID, profile: Profile):
    row = connection.execute(text('''
      SELECT id,numero,usuario_id,usuario_nombre,fecha,metodo_pago,total,clave_idempotencia,cliente_id,cliente_nombre,condicion,
        EXISTS(SELECT 1 FROM ferreteria.anulaciones a WHERE a.venta_id=ventas.id) AS anulada
      FROM ferreteria.ventas WHERE id=:id
    '''), {'id': sale_id}).mappings().one_or_none()
    if row is None or (profile.rol == 'vendedor' and row['usuario_id'] != profile.id):
        raise HTTPException(404, 'Venta no encontrada.')
    lines = connection.execute(text('''
      SELECT producto_id,codigo_producto,nombre_producto,unidad_venta,cantidad,
             precio_unitario,subtotal
      FROM ferreteria.detalle_venta WHERE venta_id=:id ORDER BY codigo_producto
    '''), {'id': sale_id}).mappings().all()
    return {**dict(row), 'usuario': row['usuario_nombre'],
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

            require_open_cash(connection)
            client_name=''
            if data.metodo_pago=='credito' and not data.cliente_id: raise HTTPException(422,'Selecciona un cliente con crÃ©dito autorizado.')
            if data.cliente_id:
                connection.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'client:'+str(data.cliente_id)})
                client=connection.execute(text('SELECT * FROM ferreteria.clientes WHERE id=:id AND activo'),{'id':data.cliente_id}).mappings().one_or_none()
                if not client: raise HTTPException(422,'Cliente no activo.')
                client_name=client['nombre']

            stock = {}
            for item in sorted(data.items, key=lambda line: str(line.producto_id)):
                row = connection.execute(text('''
                  SELECT p.id,p.codigo,p.nombre,p.unidad_venta,p.precio_venta,p.activo,p.tipo,
                         e.cantidad AS disponible
                  FROM ferreteria.productos p
                  JOIN ferreteria.existencias e ON e.producto_id=p.id
                  WHERE p.id=:id FOR UPDATE OF e
                '''), {'id': item.producto_id}).mappings().one_or_none()
                if row is None or not row['activo']:
                    raise HTTPException(422, 'Un producto no existe o estÃÆ’Â¡ inactivo.')
                check_unit(row['unidad_venta'],item.cantidad)
                if row['tipo']=='insumo': raise HTTPException(422,'Los insumos se consumen desde Matizado, no se venden en mostrador.')
                if row['disponible'] < item.cantidad:
                    raise HTTPException(409, f"Stock insuficiente para {row['nombre']}: quedan {row['disponible']}.")
                if row['precio_venta'] != item.precio_esperado:
                    raise HTTPException(409, f"El precio de {row['nombre']} cambiÃÆ’Â³. Revisa el precio actualizado antes de confirmar.")
                stock[item.producto_id] = row

            total = sum((money(stock[i.producto_id]['precio_venta'] * i.cantidad) for i in data.items), Decimal('0'))
            if total < Decimal('.01'):
                raise HTTPException(422, 'El total debe ser al menos un céntimo.')
            if total > Decimal('9999999999.99'):
                raise HTTPException(422, 'El total supera el importe permitido.')
            if data.metodo_pago=='credito':
                from app.customers import debt
                if debt(connection,data.cliente_id)+total>client['limite_credito']:
                    raise HTTPException(409,'La venta supera el crÃ©dito autorizado disponible.')
            sale_id = connection.execute(text('''
              INSERT INTO ferreteria.ventas(usuario_id,metodo_pago,total,clave_idempotencia,huella_solicitud,cliente_id,cliente_nombre,condicion)
              VALUES (:user_id,:payment,:total,:key,:fingerprint,:client,:client_name,:condition) RETURNING id
            '''), {'user_id': profile.id, 'payment': data.metodo_pago, 'total': total,
                   'key': data.clave_idempotencia, 'fingerprint': fingerprint,'client':data.cliente_id,'client_name':client_name,'condition':'credito' if data.metodo_pago=='credito' else 'contado'}).scalar_one()

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
          SELECT v.id,v.numero,v.usuario_id,v.usuario_nombre,v.fecha,v.metodo_pago,v.total,EXISTS(SELECT 1 FROM ferreteria.anulaciones a WHERE a.venta_id=v.id) AS anulada,
                 count(d.id) AS lineas,coalesce(sum(d.cantidad),0) AS unidades
          FROM ferreteria.ventas v
          JOIN ferreteria.detalle_venta d ON d.venta_id=v.id
          WHERE (:manager OR v.usuario_id=:user_id)
          GROUP BY v.id ORDER BY v.fecha DESC,v.numero DESC LIMIT 100
        '''), {'manager': profile.rol == 'gerente', 'user_id': profile.id}).mappings()
        return [{**dict(row), 'usuario': row['usuario_nombre']}
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
          WHERE (:manager OR usuario_id=:user_id) AND NOT EXISTS(SELECT 1 FROM ferreteria.anulaciones a WHERE a.venta_id=ventas.id)
        '''), {'manager': profile.rol == 'gerente', 'user_id': profile.id}).mappings().one()
        return dict(row)


@router.get('/{sale_id}')
def get_sale(sale_id: UUID, profile: Annotated[Profile, Depends(require_sales_access)]):
    with user_connection(profile.id) as connection:
        return receipt(connection, sale_id, profile)


class VoidInput(BaseModel):
    motivo: str = Field(min_length=3,max_length=500)


@router.post('/{sale_id}/void')
def void_sale(sale_id:UUID,data:VoidInput,profile:Annotated[Profile,Depends(require_manager)]):
    if len(data.motivo.strip())<3: raise HTTPException(422,'Explica el motivo de la anulaciÃ³n.')
    with user_connection(profile.id) as c:
        # All operations touching today's cash acquire the day lock first.
        require_open_cash(c)
        sale=c.execute(text('SELECT * FROM ferreteria.ventas WHERE id=:id'),{'id':sale_id}).mappings().one_or_none()
        if not sale: raise HTTPException(404,'Venta no encontrada.')
        previous=c.execute(text('SELECT motivo FROM ferreteria.anulaciones WHERE venta_id=:id'),{'id':sale_id}).scalar_one_or_none()
        if previous:
            if previous!=data.motivo.strip(): raise HTTPException(409,'La venta ya tiene otra anulaciÃ³n.')
            return receipt(c,sale_id,profile)
        same_day=c.execute(text("SELECT (:fecha AT TIME ZONE 'America/Lima')::date=(now() AT TIME ZONE 'America/Lima')::date"),{'fecha':sale['fecha']}).scalar_one()
        if not same_day: raise HTTPException(409,'Solo se anulan ventas del dÃ­a con caja abierta; los perÃ­odos cerrados se conservan.')
        if sale['cliente_id']:
            c.execute(text('SELECT id FROM ferreteria.clientes WHERE id=:id FOR UPDATE'),{'id':sale['cliente_id']})
        if c.execute(text('SELECT 1 FROM ferreteria.abonos WHERE venta_id=:id'),{'id':sale_id}).first():
            raise HTTPException(409,'Una venta con abonos requiere un proceso de devoluciÃ³n; no se anula desde este flujo.')
        id=c.execute(text('''INSERT INTO ferreteria.anulaciones(venta_id,motivo,usuario_id,usuario_nombre)
          VALUES(:id,:reason,:user,:name) RETURNING id'''),{'id':sale_id,'reason':data.motivo.strip(),'user':profile.id,'name':profile.nombre}).scalar_one()
        for line in c.execute(text('SELECT * FROM ferreteria.detalle_venta WHERE venta_id=:id ORDER BY producto_id'),{'id':sale_id}).mappings().all():
            before=c.execute(text('SELECT cantidad FROM ferreteria.existencias WHERE producto_id=:id FOR UPDATE'),{'id':line['producto_id']}).scalar_one()
            after=before+line['cantidad']
            if after>2147483647: raise HTTPException(422,'La devoluciÃ³n supera el lÃ­mite de existencias.')
            c.execute(text('UPDATE ferreteria.existencias SET cantidad=:q,actualizado_en=now() WHERE producto_id=:id'),{'id':line['producto_id'],'q':after})
            c.execute(text('''INSERT INTO ferreteria.movimientos_inventario(producto_id,tipo,variacion,stock_anterior,stock_resultante,motivo,usuario_id,anulacion_id)
              VALUES(:product,'anulacion',:delta,:before,:after,:reason,:user,:id)'''),{'product':line['producto_id'],'delta':line['cantidad'],'before':before,'after':after,'reason':data.motivo.strip(),'user':profile.id,'id':id})
        return receipt(c,sale_id,profile)
