"""Indicadores gerenciales derivados de ventas, inventario y pedidos reales."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.auth import Profile, require_manager
from app.database import user_connection

router = APIRouter(prefix='/api/management', tags=['Gerencia'])


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
          SELECT count(*) FROM ferreteria.compras WHERE estado='pendiente'
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
