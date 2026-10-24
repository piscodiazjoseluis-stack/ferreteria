"""Pedidos a proveedores y recepción completa con movimiento de stock atómico."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth import Profile, require_manager, require_storekeeper, require_warehouse
from app.database import user_connection

router = APIRouter(prefix='/api', tags=['Compras y proveedores'])


class SupplierInput(BaseModel):
    nombre: str = Field(min_length=2, max_length=160)
    documento: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=30)
    correo: str | None = Field(default=None, max_length=160)

    @field_validator('nombre')
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator('documento', 'telefono', 'correo')
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SupplierUpdate(SupplierInput):
    activo: bool


class PurchaseLine(BaseModel):
    producto_id: UUID
    cantidad: int = Field(gt=0, le=2_147_483_647)
    costo_unitario: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PurchaseInput(BaseModel):
    proveedor_id: UUID
    observacion: str = Field(default='', max_length=500)
    items: list[PurchaseLine] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def unique_products(self):
        if len({line.producto_id for line in self.items}) != len(self.items):
            raise ValueError('Cada producto debe aparecer una sola vez en el pedido.')
        return self


class ReceivedLine(BaseModel):
    detalle_id: UUID
    cantidad_fisica: int = Field(ge=0, le=2_147_483_647)


class ReceiveInput(BaseModel):
    items: list[ReceivedLine] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def unique_details(self):
        if len({line.detalle_id for line in self.items}) != len(self.items):
            raise ValueError('Cada renglón debe contarse una sola vez.')
        return self


def purchase_view(connection, purchase_id: UUID, profile: Profile):
    header = connection.execute(text('''
      SELECT c.id,c.numero,c.proveedor_id,p.nombre AS proveedor,c.creado_por,c.creado_nombre,
             c.creado_en,c.estado,c.total_estimado,c.observacion,c.recibido_por,c.recibido_nombre,c.recibido_en
      FROM ferreteria.compras c JOIN ferreteria.proveedores p ON p.id=c.proveedor_id
      WHERE c.id=:id
    '''), {'id': purchase_id}).mappings().one_or_none()
    if header is None:
        raise HTTPException(404, 'Pedido no encontrado.')
    lines = connection.execute(text('''
      SELECT id,producto_id,codigo_producto,nombre_producto,cantidad,costo_unitario,subtotal
      FROM ferreteria.detalle_compra WHERE compra_id=:id ORDER BY codigo_producto
    '''), {'id': purchase_id}).mappings().all()
    result = dict(header)
    if profile.rol == 'almacenero':
        result.pop('total_estimado')
        result['items'] = [{key: value for key, value in line.items()
                            if key not in ('costo_unitario', 'subtotal')} for line in lines]
    else:
        result['items'] = [dict(line) for line in lines]
    return result


@router.get('/suppliers')
def suppliers(profile: Annotated[Profile, Depends(require_warehouse)]):
    with user_connection(profile.id) as connection:
        return [dict(row) for row in connection.execute(text('''
          SELECT id,nombre,documento,telefono,correo,activo,creado_en
          FROM ferreteria.proveedores ORDER BY nombre
        ''')).mappings()]


@router.post('/suppliers', status_code=201)
def create_supplier(data: SupplierInput, profile: Annotated[Profile, Depends(require_manager)]):
    try:
        with user_connection(profile.id) as connection:
            return dict(connection.execute(text('''
              INSERT INTO ferreteria.proveedores(nombre,documento,telefono,correo)
              VALUES (:nombre,:documento,:telefono,:correo)
              RETURNING id,nombre,documento,telefono,correo,activo,creado_en
            '''), data.model_dump()).mappings().one())
    except IntegrityError:
        raise HTTPException(409, 'Ya existe un proveedor con ese documento o los datos no son válidos.') from None


@router.put('/suppliers/{supplier_id}')
def update_supplier(supplier_id: UUID, data: SupplierUpdate,
                    profile: Annotated[Profile, Depends(require_manager)]):
    try:
        with user_connection(profile.id) as connection:
            row = connection.execute(text('''
              UPDATE ferreteria.proveedores
              SET nombre=:nombre,documento=:documento,telefono=:telefono,correo=:correo,activo=:activo
              WHERE id=:id RETURNING id,nombre,documento,telefono,correo,activo,creado_en
            '''), {'id': supplier_id, **data.model_dump()}).mappings().one_or_none()
            if row is None:
                raise HTTPException(404, 'Proveedor no encontrado.')
            return dict(row)
    except IntegrityError:
        raise HTTPException(409, 'Ya existe un proveedor con ese documento o los datos no son válidos.') from None


@router.get('/purchases')
def purchases(profile: Annotated[Profile, Depends(require_warehouse)]):
    with user_connection(profile.id) as connection:
        rows = [dict(row) for row in connection.execute(text('''
          SELECT c.id,c.numero,c.proveedor_id,p.nombre AS proveedor,c.creado_en,c.estado,
                 c.total_estimado,c.recibido_en,count(d.id) AS lineas
          FROM ferreteria.compras c JOIN ferreteria.proveedores p ON p.id=c.proveedor_id
          JOIN ferreteria.detalle_compra d ON d.compra_id=c.id
          GROUP BY c.id,p.nombre ORDER BY c.creado_en DESC,c.numero DESC LIMIT 100
        ''')).mappings()]
        if profile.rol == 'almacenero':
            for row in rows:
                row.pop('total_estimado')
        return rows


@router.get('/purchases/{purchase_id}')
def get_purchase(purchase_id: UUID, profile: Annotated[Profile, Depends(require_warehouse)]):
    with user_connection(profile.id) as connection:
        return purchase_view(connection, purchase_id, profile)


@router.post('/purchases', status_code=201)
def create_purchase(data: PurchaseInput, profile: Annotated[Profile, Depends(require_manager)]):
    with user_connection(profile.id) as connection:
        supplier = connection.execute(text('''
          SELECT id FROM ferreteria.proveedores WHERE id=:id AND activo
        '''), {'id': data.proveedor_id}).first()
        if supplier is None:
            raise HTTPException(422, 'Selecciona un proveedor activo.')
        products = {}
        for line in data.items:
            row = connection.execute(text('''
              SELECT id,codigo,nombre,activo FROM ferreteria.productos WHERE id=:id
            '''), {'id': line.producto_id}).mappings().one_or_none()
            if row is None or not row['activo']:
                raise HTTPException(422, 'Un producto no existe o está inactivo.')
            products[line.producto_id] = row
        total = sum((line.cantidad * line.costo_unitario for line in data.items), Decimal('0'))
        if total > Decimal('9999999999.99'):
            raise HTTPException(422, 'El total del pedido supera el límite permitido.')
        purchase_id = connection.execute(text('''
              INSERT INTO ferreteria.compras(proveedor_id,creado_por,creado_nombre,total_estimado,observacion)
              VALUES (:supplier,:user_id,:user_name,:total,:note) RETURNING id
        '''), {'supplier': data.proveedor_id, 'user_id': profile.id, 'total': total,
               'user_name': profile.nombre, 'note': data.observacion.strip()}).scalar_one()
        for line in data.items:
            product = products[line.producto_id]
            connection.execute(text('''
              INSERT INTO ferreteria.detalle_compra
                (compra_id,producto_id,codigo_producto,nombre_producto,cantidad,costo_unitario)
              VALUES (:purchase,:product,:code,:name,:quantity,:cost)
            '''), {'purchase': purchase_id, 'product': line.producto_id,
                   'code': product['codigo'], 'name': product['nombre'],
                   'quantity': line.cantidad, 'cost': line.costo_unitario})
        return purchase_view(connection, purchase_id, profile)


@router.post('/purchases/{purchase_id}/receive')
def receive_purchase(purchase_id: UUID, data: ReceiveInput,
                     profile: Annotated[Profile, Depends(require_storekeeper)]):
    with user_connection(profile.id) as connection:
        # El bloqueo del pedido hace que dos recepciones simultáneas no dupliquen stock.
        order = connection.execute(text('''
          SELECT id,numero,estado FROM ferreteria.compras WHERE id=:id FOR UPDATE
        '''), {'id': purchase_id}).mappings().one_or_none()
        if order is None:
            raise HTTPException(404, 'Pedido no encontrado.')
        if order['estado'] != 'pendiente':
            raise HTTPException(409, 'Este pedido ya fue recibido o cancelado.')
        details = connection.execute(text('''
          SELECT id,producto_id,cantidad,nombre_producto FROM ferreteria.detalle_compra
          WHERE compra_id=:id ORDER BY producto_id
        '''), {'id': purchase_id}).mappings().all()
        counted = {line.detalle_id: line.cantidad_fisica for line in data.items}
        if set(counted) != {line['id'] for line in details}:
            raise HTTPException(422, 'Cuenta todos los productos del pedido.')
        for line in details:
            if counted[line['id']] != line['cantidad']:
                raise HTTPException(409, f"La cantidad de {line['nombre_producto']} no coincide. Registra solo recepciones completas.")
        connection.execute(text('''
          UPDATE ferreteria.compras SET estado='recibida',recibido_por=:user_id,
            recibido_nombre=:user_name,recibido_en=now()
          WHERE id=:id
        '''), {'id': purchase_id, 'user_id': profile.id, 'user_name': profile.nombre})
        for line in details:
            row = connection.execute(text('''
              SELECT e.cantidad,p.activo FROM ferreteria.existencias e
              JOIN ferreteria.productos p ON p.id=e.producto_id
              WHERE e.producto_id=:id FOR UPDATE OF e
            '''), {'id': line['producto_id']}).mappings().one_or_none()
            if row is None or not row['activo']:
                raise HTTPException(409, f"{line['nombre_producto']} ya no está activo.")
            after = row['cantidad'] + line['cantidad']
            if after > 2_147_483_647:
                raise HTTPException(422, 'La cantidad supera el límite de existencias.')
            connection.execute(text('''
              UPDATE ferreteria.existencias SET cantidad=:after,actualizado_en=now()
              WHERE producto_id=:id
            '''), {'id': line['producto_id'], 'after': after})
            connection.execute(text('''
              INSERT INTO ferreteria.movimientos_inventario
                (producto_id,tipo,variacion,stock_anterior,stock_resultante,motivo,usuario_id,detalle_compra_id)
              VALUES (:id,'compra',:quantity,:before,:after,:reason,:user_id,:detail_id)
            '''), {'id': line['producto_id'], 'quantity': line['cantidad'],
                   'before': row['cantidad'], 'after': after,
                   'reason': f"Recepción de pedido #{order['numero']} por {profile.nombre}",
                   'user_id': profile.id, 'detail_id': line['id']})
        return purchase_view(connection, purchase_id, profile)


@router.post('/purchases/{purchase_id}/cancel')
def cancel_purchase(purchase_id: UUID, profile: Annotated[Profile, Depends(require_manager)]):
    with user_connection(profile.id) as connection:
        order = connection.execute(text('''
          SELECT estado FROM ferreteria.compras WHERE id=:id FOR UPDATE
        '''), {'id': purchase_id}).mappings().one_or_none()
        if order is None:
            raise HTTPException(404, 'Pedido no encontrado.')
        if order['estado'] != 'pendiente':
            raise HTTPException(409, 'Solo se puede cancelar un pedido pendiente.')
        connection.execute(text("UPDATE ferreteria.compras SET estado='cancelada' WHERE id=:id"), {'id': purchase_id})
        return purchase_view(connection, purchase_id, profile)
