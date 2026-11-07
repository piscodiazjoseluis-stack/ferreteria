"""Indicadores gerenciales derivados de ventas, inventario y pedidos reales."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.auth import Profile, require_manager
from app.database import user_connection

router = APIRouter(prefix='/api/management', tags=['Gerencia'])


@router.get('/replenishment')
def replenishment(profile: Annotated[Profile, Depends(require_manager)]):
    with user_connection(profile.id) as connection:
        rows = connection.execute(text('''
          WITH received AS (SELECT detalle_compra_id,sum(cantidad) AS cantidad FROM ferreteria.detalle_recepcion GROUP BY detalle_compra_id),
          pending AS (SELECT d.producto_id,sum(d.cantidad-coalesce(r.cantidad,0)) AS cantidad
            FROM ferreteria.detalle_compra d JOIN ferreteria.compras c ON c.id=d.compra_id
            LEFT JOIN received r ON r.detalle_compra_id=d.id WHERE c.estado IN ('pendiente','parcial') GROUP BY d.producto_id)
          SELECT p.id,p.codigo,p.nombre,p.stock_minimo,p.stock_objetivo,e.cantidad AS stock,
            coalesce(x.cantidad,0)::bigint AS pendiente,
            greatest(0,p.stock_objetivo::bigint-e.cantidad-coalesce(x.cantidad,0)) AS sugerida
          FROM ferreteria.productos p JOIN ferreteria.existencias e ON e.producto_id=p.id
          LEFT JOIN pending x ON x.producto_id=p.id WHERE p.activo
          ORDER BY greatest(0,p.stock_objetivo::bigint-e.cantidad-coalesce(x.cantidad,0)) DESC,p.nombre
        ''')).mappings()
        return [dict(r) for r in rows]


@router.get('/overview')
def overview(profile: Annotated[Profile, Depends(require_manager)]):
    with user_connection(profile.id) as connection:
        sales = connection.execute(text('''
          SELECT count(*) FILTER (WHERE (fecha AT TIME ZONE 'America/Lima')::date=
            (now() AT TIME ZONE 'America/Lima')::date) AS ventas_hoy,
            coalesce(sum(total) FILTER (WHERE (fecha AT TIME ZONE 'America/Lima')::date=
            (now() AT TIME ZONE 'America/Lima')::date),0) AS importe_hoy,
            count(*) FILTER (WHERE fecha >= date_trunc('month', now() AT TIME ZONE 'America/Lima')
              AT TIME ZONE 'America/Lima') AS ventas_mes,
            coalesce(sum(total) FILTER (WHERE fecha >= date_trunc('month', now() AT TIME ZONE 'America/Lima')
              AT TIME ZONE 'America/Lima'),0) AS importe_mes
          FROM ferreteria.ventas
        ''')).mappings().one()
        pending = connection.execute(text('''
          SELECT count(*) FROM ferreteria.compras WHERE estado IN ('pendiente','parcial')
        ''')).scalar_one()
        top = connection.execute(text('''
          SELECT d.codigo_producto,d.nombre_producto,sum(d.cantidad) AS unidades,
                 sum(d.subtotal) AS importe
          FROM ferreteria.detalle_venta d JOIN ferreteria.ventas v ON v.id=d.venta_id
          WHERE v.fecha >= date_trunc('month', now() AT TIME ZONE 'America/Lima')
            AT TIME ZONE 'America/Lima'
          GROUP BY d.codigo_producto,d.nombre_producto
          ORDER BY unidades DESC,importe DESC LIMIT 5
        ''')).mappings().all()
        return {**dict(sales), 'pedidos_pendientes': pending,
                'productos_mas_vendidos': [dict(row) for row in top]}
