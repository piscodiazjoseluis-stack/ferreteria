"""Public, read-only projection with a dedicated restricted PostgreSQL role."""
from fastapi import APIRouter, Query
from sqlalchemy import text
from app.database import get_engine
from app.config import get_settings

router=APIRouter(prefix='/api/public',tags=['Catálogo público'])

@router.get('/catalog')
def catalog(buscar:str=Query(default='',max_length=100),categoria:str=Query(default='',max_length=100),pagina:int=Query(default=1,ge=1),tamano:int=Query(default=24,ge=1,le=100)):
    with get_engine().begin() as c:
        c.execute(text('SET LOCAL ROLE ferreteria_public'))
        source=''' FROM ferreteria.productos p JOIN ferreteria.categorias c ON c.id=p.categoria_id JOIN ferreteria.existencias e ON e.producto_id=p.id
          WHERE p.activo AND c.activo AND p.tipo<>'insumo' AND (:q='' OR p.nombre ILIKE :pattern OR p.codigo ILIKE :pattern) AND (:category='' OR c.nombre=:category)'''
        params={'q':buscar.strip(),'pattern':f'%{buscar.strip()}%','category':categoria}
        total=c.execute(text('SELECT count(*)'+source),params).scalar_one()
        rows=c.execute(text('''SELECT p.id,p.codigo,p.nombre,p.marca,p.foto,p.precio_venta,p.unidad_venta,c.nombre AS categoria,(e.cantidad>0) AS disponible'''+source+' ORDER BY p.nombre,p.id LIMIT :limit OFFSET :offset'),{**params,'limit':tamano,'offset':(pagina-1)*tamano}).mappings().all()
        cats=c.execute(text('SELECT nombre FROM ferreteria.categorias WHERE activo ORDER BY nombre')).scalars().all()
        return {'productos':[dict(r) for r in rows],'total':total,'categorias':cats,'whatsapp':get_settings().public_whatsapp}
