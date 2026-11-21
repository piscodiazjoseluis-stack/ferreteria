"""Final dashboard and sensitive-action log."""
from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from app.auth import Profile, require_manager
from app.database import user_connection

router=APIRouter(prefix='/api/management',tags=['Gerencia'])
Manager=Annotated[Profile,Depends(require_manager)]

@router.get('/audit')
def audit(profile:Manager):
    with user_connection(profile.id) as c:
        return [dict(r) for r in c.execute(text('SELECT * FROM ferreteria.auditoria ORDER BY id DESC LIMIT 200')).mappings()]

@router.get('/analytics')
def analytics(profile:Manager,desde:date,hasta:date):
    if desde>hasta: raise HTTPException(422,'Revisa las fechas del período.')
    params={'since':desde,'until':hasta}
    base="""WITH periodo AS (SELECT v.* FROM ferreteria.ventas v WHERE fecha>=CAST(:since AS date) AT TIME ZONE 'America/Lima'
      AND fecha<(CAST(:until AS date)+1) AT TIME ZONE 'America/Lima' AND NOT EXISTS(SELECT 1 FROM ferreteria.anulaciones a WHERE a.venta_id=v.id)) """
    with user_connection(profile.id) as c:
        totals=c.execute(text(base+'SELECT count(*) AS comprobantes,coalesce(sum(total),0) AS vendido,coalesce(round(avg(total),2),0) AS ticket_promedio FROM periodo'),params).mappings().one()
        days=c.execute(text(base+"SELECT extract(isodow FROM fecha AT TIME ZONE 'America/Lima') AS dia,sum(total) AS importe FROM periodo GROUP BY 1 ORDER BY 1"),params).mappings().all()
        top=c.execute(text(base+'''SELECT d.codigo_producto,d.nombre_producto,sum(d.cantidad) AS unidades,sum(d.subtotal) AS importe FROM periodo v JOIN ferreteria.detalle_venta d ON d.venta_id=v.id GROUP BY d.codigo_producto,d.nombre_producto ORDER BY unidades DESC,importe DESC LIMIT 10'''),params).mappings().all()
        segments=c.execute(text(base+'''SELECT coalesce(c.segmento,'sin_cliente') AS segmento,count(*) AS ventas,sum(v.total) AS importe FROM periodo v LEFT JOIN ferreteria.clientes c ON c.id=v.cliente_id GROUP BY 1 ORDER BY 1'''),params).mappings().all()
        return {'totales':dict(totals),'dias':[dict(r) for r in days],'top':[dict(r) for r in top],'segmentos':[dict(r) for r in segments]}
