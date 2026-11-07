"""Historial paginado y CSV con los mismos filtros y totales de todo el período."""
import csv
import io
from datetime import date
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from app.auth import Profile, current_profile
from app.database import user_connection

router=APIRouter(prefix='/api/reports',tags=['Reportes'])


@router.get('')
def report(profile:Annotated[Profile,Depends(current_profile)],
           tipo:Literal['ventas','compras','movimientos']='ventas', desde:date|None=None,hasta:date|None=None,
           buscar:str=Query(default='',max_length=120),estado:str=Query(default='',max_length=30),
           responsable:str=Query(default='',max_length=120),pago:str=Query(default='',max_length=30),
           pagina:int=Query(default=1,ge=1,le=1000000),tamano:int=Query(default=20,ge=1,le=100),csv_export:bool=False):
    if profile.rol=='vendedor' and tipo!='ventas': raise HTTPException(403,'El vendedor solo puede consultar sus ventas.')
    if profile.rol=='almacenero' and tipo=='ventas': raise HTTPException(403,'Almacén no puede consultar ventas.')
    if desde and hasta and desde>hasta: raise HTTPException(422,'La fecha inicial debe ser anterior o igual a la final.')
    if tipo=='ventas':
        source='''SELECT v.id,v.numero,v.fecha,v.usuario_id,v.usuario_nombre AS responsable,v.metodo_pago AS pago,v.total,
          (SELECT sum(cantidad) FROM ferreteria.detalle_venta WHERE venta_id=v.id) AS unidades
          FROM ferreteria.ventas v WHERE (:manager OR v.usuario_id=:user)
          AND (:search='' OR EXISTS(SELECT 1 FROM ferreteria.detalle_venta d WHERE d.venta_id=v.id AND (d.nombre_producto ILIKE :q OR d.codigo_producto ILIKE :q)) OR CAST(v.numero AS text)=:search)'''
        columns=['numero','fecha','responsable','pago','unidades','total']; amount='total'; units='unidades'
    elif tipo=='compras':
        source='''SELECT c.id,c.numero,c.creado_en AS fecha,c.creado_nombre AS responsable,p.nombre AS proveedor,c.estado,c.total_estimado,
          (SELECT sum(d.cantidad) FROM ferreteria.detalle_compra d WHERE d.compra_id=c.id) AS unidades,
          coalesce((SELECT sum(dr.cantidad) FROM ferreteria.recepciones r JOIN ferreteria.detalle_recepcion dr ON dr.recepcion_id=r.id WHERE r.compra_id=c.id),0) AS recibidas
          FROM ferreteria.compras c JOIN ferreteria.proveedores p ON p.id=c.proveedor_id
          WHERE (:search='' OR p.nombre ILIKE :q OR CAST(c.numero AS text)=:search OR EXISTS(SELECT 1 FROM ferreteria.detalle_compra d WHERE d.compra_id=c.id AND (d.nombre_producto ILIKE :q OR d.codigo_producto ILIKE :q)))'''
        columns=['numero','fecha','responsable','proveedor','estado','unidades','recibidas']
        if profile.rol=='gerente': columns.append('total_estimado')
        amount='total_estimado' if profile.rol=='gerente' else None; units='unidades'
    else:
        source='''SELECT m.id,m.fecha,p.nombre AS producto,p.codigo,m.tipo AS estado,m.variacion,m.stock_anterior,m.stock_resultante,
          m.motivo,m.usuario_nombre AS responsable FROM ferreteria.movimientos_inventario m JOIN ferreteria.productos p ON p.id=m.producto_id
          WHERE (:search='' OR p.nombre ILIKE :q OR p.codigo ILIKE :q OR m.motivo ILIKE :q)'''
        columns=['fecha','producto','codigo','estado','variacion','stock_anterior','stock_resultante','motivo','responsable']; amount=None; units='variacion'
    where=" WHERE (CAST(:since AS date) IS NULL OR fecha>=CAST(:since AS date) AT TIME ZONE 'America/Lima') AND (CAST(:until AS date) IS NULL OR fecha<(CAST(:until AS date)+1) AT TIME ZONE 'America/Lima') AND (:owner='' OR responsable ILIKE :owner_q)"
    if tipo!='ventas': where+=' AND (:state=\'\' OR estado=:state)'
    else: where+=' AND (:payment=\'\' OR pago=:payment)'
    params={'manager':profile.rol=='gerente','user':profile.id,'search':buscar.strip(),'q':f'%{buscar.strip()}%',
      'since':desde,'until':hasta,'owner':responsable.strip(),'owner_q':f'%{responsable.strip()}%','state':estado,'payment':pago}
    base=f'WITH datos AS ({source})'
    with user_connection(profile.id) as c:
        stats=c.execute(text(base+f' SELECT count(*) AS registros,coalesce(sum({units}),0) AS unidades'+(f',coalesce(sum({amount}),0) AS importe' if amount else '')+' FROM datos'+where),params).mappings().one()
        if csv_export and stats['registros']>50000: raise HTTPException(422,'El resultado supera 50 000 filas. Reduce el período para exportar.')
        query=base+' SELECT '+','.join(columns)+' FROM datos'+where+' ORDER BY fecha DESC,id DESC LIMIT :limit OFFSET :offset'
        rows=[dict(r) for r in c.execute(text(query),{**params,'limit':50000 if csv_export else tamano,'offset':0 if csv_export else (pagina-1)*tamano}).mappings()]
    if csv_export:
        buffer=io.StringIO(newline=''); writer=csv.writer(buffer,delimiter=';'); writer.writerow(columns)
        def safe(value):
            s=str(value) if value is not None else ''
            return "'"+s if isinstance(value,str) and s.lstrip().startswith(('=','+','-','@','\t','\r')) else s
        for row in rows: writer.writerow([safe(row[k]) for k in columns])
        return Response('\ufeff'+buffer.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{tipo}.csv"'})
    return {'columnas':columns,'filas':rows,'totales':dict(stats),'pagina':pagina,'tamano':tamano}
