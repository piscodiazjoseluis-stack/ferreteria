"""Catálogo y movimientos de inventario del primer avance comercial."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth import Profile, current_profile, require_manager
from app.database import user_connection

router = APIRouter(prefix='/api', tags=['Catálogo e inventario'])


class ProductInput(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=160)
    categoria_id: UUID
    unidad_venta: Literal['unidad', 'caja', 'bolsa', 'paquete', 'galon', 'balde']
    precio_venta: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock_minimo: int = Field(ge=0, le=2_147_483_647)

    @field_validator('codigo')
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError('El código es obligatorio.')
        return value

    @field_validator('nombre')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('El nombre es obligatorio.')
        return value


class ProductCreate(ProductInput):
    saldo_inicial: int = Field(default=0, ge=0, le=2_147_483_647)


class ProductUpdate(ProductInput):
    activo: bool


class StockEntry(BaseModel):
    cantidad: int = Field(gt=0, le=2_147_483_647)
    motivo: str = Field(min_length=3, max_length=500)

    @field_validator('motivo')
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError('Indica un motivo de al menos 3 caracteres.')
        return value


class StockAdjustment(BaseModel):
    cantidad_fisica: int = Field(ge=0, le=2_147_483_647)
    motivo: str = Field(min_length=3, max_length=500)

    @field_validator('motivo')
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError('Indica un motivo de al menos 3 caracteres.')
        return value


PRODUCT_QUERY = text('''
 SELECT p.id,p.codigo,p.nombre,p.categoria_id,c.nombre AS categoria,
        p.unidad_venta,p.precio_venta,p.stock_minimo,p.activo,
        coalesce(e.cantidad,0) AS stock,p.creado_en,p.actualizado_en
 FROM ferreteria.productos p
 JOIN ferreteria.categorias c ON c.id=p.categoria_id
 LEFT JOIN ferreteria.existencias e ON e.producto_id=p.id
''')


def fetch_product(connection, product_id: UUID):
    return connection.execute(
        text(PRODUCT_QUERY.text + ' WHERE p.id=:id'), {'id': product_id}
    ).mappings().one_or_none()


def require_category(connection, category_id: UUID):
    row = connection.execute(
        text('SELECT id FROM ferreteria.categorias WHERE id=:id AND activo'),
        {'id': category_id},
    ).first()
    if row is None:
        raise HTTPException(422, 'Selecciona una categoría activa.')


@router.get('/categories')
def categories(profile: Annotated[Profile, Depends(current_profile)]):
    with user_connection(profile.id) as connection:
        return [dict(row) for row in connection.execute(
            text('SELECT id,nombre FROM ferreteria.categorias WHERE activo ORDER BY nombre')
        ).mappings()]


@router.get('/products')
def products(profile: Annotated[Profile, Depends(current_profile)]):
    with user_connection(profile.id) as connection:
        return [dict(row) for row in connection.execute(
            text(PRODUCT_QUERY.text + ' ORDER BY p.nombre,p.codigo')
        ).mappings()]


@router.post('/products', status_code=201)
def create_product(data: ProductCreate, profile: Annotated[Profile, Depends(require_manager)]):
    try:
        with user_connection(profile.id) as connection:
            require_category(connection, data.categoria_id)
            product_id = connection.execute(text('''
              INSERT INTO ferreteria.productos
                (codigo,nombre,categoria_id,unidad_venta,precio_venta,stock_minimo)
              VALUES (:codigo,:nombre,:categoria_id,:unidad_venta,:precio_venta,:stock_minimo)
              RETURNING id
            '''), data.model_dump(exclude={'saldo_inicial'})).scalar_one()
            connection.execute(text('''
              INSERT INTO ferreteria.existencias(producto_id,cantidad)
              VALUES (:id,:quantity)
            '''), {'id': product_id, 'quantity': data.saldo_inicial})
            if data.saldo_inicial:
                connection.execute(text('''
                  INSERT INTO ferreteria.movimientos_inventario
                    (producto_id,tipo,variacion,stock_anterior,stock_resultante,motivo,usuario_id)
                  VALUES (:id,'saldo_inicial',:quantity,0,:quantity,'Saldo inicial registrado al crear el producto',:user_id)
                '''), {'id': product_id, 'quantity': data.saldo_inicial, 'user_id': profile.id})
            return dict(fetch_product(connection, product_id))
    except IntegrityError as error:
        if getattr(error.orig, 'sqlstate', '') == '23505':
            raise HTTPException(409, 'Ya existe un producto con ese código.') from None
        raise HTTPException(422, 'No se pudo registrar el producto con esos datos.') from None


@router.put('/products/{product_id}')
def update_product(product_id: UUID, data: ProductUpdate,
                   profile: Annotated[Profile, Depends(require_manager)]):
    try:
        with user_connection(profile.id) as connection:
            require_category(connection, data.categoria_id)
            updated = connection.execute(text('''
              UPDATE ferreteria.productos
              SET codigo=:codigo,nombre=:nombre,categoria_id=:categoria_id,
                  unidad_venta=:unidad_venta,precio_venta=:precio_venta,
                  stock_minimo=:stock_minimo,activo=:activo
              WHERE id=:id RETURNING id
            '''), {'id': product_id, **data.model_dump()}).scalar_one_or_none()
            if updated is None:
                raise HTTPException(404, 'Producto no encontrado.')
            return dict(fetch_product(connection, product_id))
    except IntegrityError as error:
        if getattr(error.orig, 'sqlstate', '') == '23505':
            raise HTTPException(409, 'Ya existe un producto con ese código.') from None
        raise HTTPException(422, 'Los cambios no cumplen las reglas del producto.') from None
    except SQLAlchemyError:
        raise HTTPException(422, 'No se puede cambiar la unidad de un producto con movimientos.') from None


def change_stock(product_id: UUID, profile: Profile, movement_type: str,
                 quantity: int | None, physical: int | None, reason: str):
    with user_connection(profile.id) as connection:
        product = connection.execute(text('''
          SELECT p.activo,e.cantidad FROM ferreteria.productos p
          JOIN ferreteria.existencias e ON e.producto_id=p.id
          WHERE p.id=:id FOR UPDATE OF e
        '''), {'id': product_id}).mappings().one_or_none()
        if product is None:
            raise HTTPException(404, 'Producto no encontrado.')
        if not product['activo']:
            raise HTTPException(409, 'Activa el producto antes de modificar sus existencias.')
        before = product['cantidad']
        after = physical if physical is not None else before + quantity
        if after == before:
            raise HTTPException(422, 'La cantidad física coincide con el stock actual.')
        if after > 2_147_483_647:
            raise HTTPException(422, 'La cantidad supera el límite permitido.')
        connection.execute(text('''
          UPDATE ferreteria.existencias SET cantidad=:quantity,actualizado_en=now()
          WHERE producto_id=:id
        '''), {'quantity': after, 'id': product_id})
        connection.execute(text('''
          INSERT INTO ferreteria.movimientos_inventario
            (producto_id,tipo,variacion,stock_anterior,stock_resultante,motivo,usuario_id)
          VALUES (:id,:type,:delta,:before,:after,:reason,:user_id)
        '''), {'id': product_id, 'type': movement_type, 'delta': after-before,
               'before': before, 'after': after, 'reason': reason, 'user_id': profile.id})
        return dict(fetch_product(connection, product_id))


@router.post('/inventory/{product_id}/entries')
def add_stock(product_id: UUID, data: StockEntry,
              profile: Annotated[Profile, Depends(require_manager)]):
    return change_stock(product_id, profile, 'entrada', data.cantidad, None, data.motivo)


@router.post('/inventory/{product_id}/adjustments')
def adjust_stock(product_id: UUID, data: StockAdjustment,
                 profile: Annotated[Profile, Depends(require_manager)]):
    return change_stock(product_id, profile, 'ajuste', None, data.cantidad_fisica, data.motivo)


@router.get('/inventory/movements')
def movements(profile: Annotated[Profile, Depends(current_profile)]):
    with user_connection(profile.id) as connection:
        return [dict(row) for row in connection.execute(text('''
          SELECT m.id,m.producto_id,p.codigo,p.nombre AS producto,m.tipo,
                 m.variacion,m.stock_anterior,m.stock_resultante,m.motivo,m.fecha,
                 CASE WHEN m.usuario_id=:user_id THEN :user_name ELSE 'Personal autorizado' END AS usuario
          FROM ferreteria.movimientos_inventario m
          JOIN ferreteria.productos p ON p.id=m.producto_id
          ORDER BY m.fecha DESC,m.id DESC LIMIT 200
        '''), {'user_id': profile.id, 'user_name': profile.nombre}).mappings()]
