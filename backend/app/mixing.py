"""Immutable formulas and preparations; exact consumption and stored valuation."""
import hashlib
import json
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.auth import Profile, require_sales_access
from app.database import user_connection
from app.values import Quantity, check_unit, money, photo

router=APIRouter(prefix='/api/mixing',tags=['Matizado'])
Staff=Annotated[Profile,Depends(require_sales_access)]

def operator(profile):
    if profile.rol=='cajero': raise HTTPException(403,'Caja consulta fórmulas; la preparación corresponde a Gerencia o Ventas.')

class Component(BaseModel):
    producto_id:UUID
    cantidad:Quantity
    funcion:Literal['base','colorante']

class FormulaInput(BaseModel):
    codigo:str=Field(min_length=1,max_length=40)
    tono:str=Field(min_length=2,max_length=160)
    referencia:str=Field(default='',max_length=120)
    cliente_id:UUID|None=None
    salida_id:UUID
    rendimiento:Quantity
    margen:Decimal=Field(default=30,ge=0,le=500,max_digits=6,decimal_places=2)
    foto:str=''
    notas:str=Field(default='',max_length=1000)
    componentes:list[Component]=Field(min_length=2,max_length=30)
    _photo=field_validator('foto')(photo)

    @model_validator(mode='after')
    def components(self):
        if len({i.producto_id for i in self.componentes})!=len(self.componentes) or sum(i.funcion=='base' for i in self.componentes)!=1:
            raise ValueError('Usa una sola base y colorantes distintos, sin repetir insumos.')
        if self.salida_id in {i.producto_id for i in self.componentes}: raise ValueError('La salida no puede ser un insumo.')
        return self


def formula_view(c,id):
    f=c.execute(text('''SELECT f.*,p.nombre AS salida,p.unidad_venta AS unidad_salida,cl.nombre AS cliente
      FROM ferreteria.formulas f JOIN ferreteria.productos p ON p.id=f.salida_id LEFT JOIN ferreteria.clientes cl ON cl.id=f.cliente_id WHERE f.id=:id'''),{'id':id}).mappings().one_or_none()
    if not f: raise HTTPException(404,'Fórmula no encontrada.')
    components=[dict(r) for r in c.execute(text('''SELECT cf.*,p.nombre,p.codigo,p.unidad_venta,p.costo_unitario,e.cantidad AS disponible
      FROM ferreteria.componentes_formula cf JOIN ferreteria.productos p ON p.id=cf.producto_id JOIN ferreteria.existencias e ON e.producto_id=p.id
      WHERE cf.formula_id=:id ORDER BY cf.funcion,cf.id'''),{'id':id}).mappings()]
    cost=money(sum((r['cantidad']*r['costo_unitario'] for r in components),Decimal(0)))
    return {**dict(f),'componentes':components,'costo':cost,'precio_sugerido':money(cost*(1+f['margen']/100))}


@router.get('/formulas')
def formulas(profile:Staff):
    with user_connection(profile.id) as c:
        ids=c.execute(text('SELECT id FROM ferreteria.formulas ORDER BY creado_en DESC LIMIT 300')).scalars()
        return [formula_view(c,id) for id in ids]


@router.post('/formulas',status_code=201)
def create(data:FormulaInput,profile:Staff):
    operator(profile)
    if len(data.codigo.strip())<1 or len(data.tono.strip())<2: raise HTTPException(422,'Completa código y tono.')
    try:
        with user_connection(profile.id) as c:
            out=c.execute(text('SELECT tipo,unidad_venta FROM ferreteria.productos WHERE id=:id AND activo'),{'id':data.salida_id}).mappings().one_or_none()
            if not out or out['tipo']!='preparado': raise HTTPException(422,'La salida debe ser un producto de tipo preparado.')
            check_unit(out['unidad_venta'],data.rendimiento)
            if data.cliente_id and not c.execute(text('SELECT 1 FROM ferreteria.clientes WHERE id=:id AND activo'),{'id':data.cliente_id}).first(): raise HTTPException(422,'Cliente no activo.')
            for line in data.componentes:
                product=c.execute(text("SELECT unidad_venta FROM ferreteria.productos WHERE id=:id AND activo AND tipo='insumo'"),{'id':line.producto_id}).mappings().one_or_none()
                if not product: raise HTTPException(422,'Cada componente debe ser un insumo activo.')
                check_unit(product['unidad_venta'],line.cantidad)
            id=c.execute(text('''INSERT INTO ferreteria.formulas(codigo,tono,referencia,cliente_id,salida_id,rendimiento,margen,foto,notas,usuario_id)
              VALUES(:codigo,:tono,:referencia,:cliente_id,:salida_id,:rendimiento,:margen,:foto,:notas,:user) RETURNING id'''),{**data.model_dump(exclude={'componentes'}),'codigo':data.codigo.strip().upper(),'tono':data.tono.strip(),'user':profile.id}).scalar_one()
            for line in data.componentes:
                c.execute(text('INSERT INTO ferreteria.componentes_formula(formula_id,producto_id,cantidad,funcion) VALUES(:id,:producto_id,:cantidad,:funcion)'),{'id':id,**line.model_dump()})
            return formula_view(c,id)
    except IntegrityError: raise HTTPException(409,'Código de fórmula duplicado o datos no válidos.') from None


class PrepareInput(BaseModel):
    id:UUID
    formula_id:UUID
    lotes:Quantity=Decimal('1')
    reproceso_de:UUID|None=None
    motivo:str=Field(default='',max_length=500)


@router.post('/preparations',status_code=201)
def prepare(data:PrepareInput,profile:Staff):
    operator(profile)
    huella=hashlib.sha256(json.dumps([str(data.formula_id),str(data.lotes.normalize()),str(data.reproceso_de),data.motivo.strip()]).encode()).hexdigest()
    with user_connection(profile.id) as c:
        c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':str(data.id)})
        old=c.execute(text('SELECT * FROM ferreteria.preparaciones WHERE id=:id'),{'id':data.id}).mappings().one_or_none()
        if old:
            if old['huella']!=huella: raise HTTPException(409,'El reintento no coincide con la preparación.')
            return dict(old)
        f=formula_view(c,data.formula_id)
        if data.reproceso_de:
            prev=c.execute(text('SELECT formula_id FROM ferreteria.preparaciones WHERE id=:id'),{'id':data.reproceso_de}).scalar_one_or_none()
            if prev!=data.formula_id or len(data.motivo.strip())<3: raise HTTPException(422,'El reproceso necesita preparación de la misma fórmula y motivo.')
        ids=sorted({r['producto_id'] for r in f['componentes']}|{f['salida_id']},key=str)
        locked={}
        for id in ids:
            row=c.execute(text('''SELECT p.id,p.tipo,p.nombre,p.unidad_venta,p.costo_unitario,p.activo,e.cantidad
              FROM ferreteria.productos p JOIN ferreteria.existencias e ON e.producto_id=p.id WHERE p.id=:id FOR UPDATE OF e'''),{'id':id}).mappings().one()
            if not row['activo']: raise HTTPException(409,'Hay productos inactivos en la fórmula.')
            locked[id]=row
        if locked[f['salida_id']]['tipo']!='preparado': raise HTTPException(409,'La salida ya no es un producto preparado.')
        detail=[]
        for comp in f['componentes']:
            row=locked[comp['producto_id']];q=comp['cantidad']*data.lotes
            if q!=q.quantize(Decimal('.001')): raise HTTPException(422,'La escala requiere más de tres decimales. Usa otro número de lotes.')
            check_unit(row['unidad_venta'],q)
            if row['tipo']!='insumo' or q>row['cantidad'] or row['costo_unitario']<=0: raise HTTPException(409,'Insumo sin stock suficiente o sin costo configurado.')
            detail.append({'producto_id':str(row['id']),'nombre':row['nombre'],'unidad':row['unidad_venta'],'cantidad':str(q),'costo_unitario':str(row['costo_unitario'])})
        quantity=f['rendimiento']*data.lotes
        if quantity!=quantity.quantize(Decimal('.001')): raise HTTPException(422,'El rendimiento requiere más de tres decimales.')
        check_unit(locked[f['salida_id']]['unidad_venta'],quantity)
        cost=money(sum((Decimal(r['cantidad'])*Decimal(r['costo_unitario']) for r in detail),Decimal(0)))
        result=c.execute(text('''INSERT INTO ferreteria.preparaciones(id,formula_id,cliente_id,salida_id,cantidad,costo,precio_sugerido,detalle,huella,usuario_id,usuario_nombre,reproceso_de,motivo)
          VALUES(:id,:formula,:client,:output,:quantity,:cost,:price,CAST(:detail AS jsonb),:hash,:user,:name,:previous,:reason) RETURNING *'''),
          {'id':data.id,'formula':data.formula_id,'client':f['cliente_id'],'output':f['salida_id'],'quantity':quantity,'cost':cost,'price':money(cost*(1+f['margen']/100)),
           'detail':json.dumps(detail),'hash':huella,'user':profile.id,'name':profile.nombre,'previous':data.reproceso_de,'reason':data.motivo.strip()}).mappings().one()
        changes=[(UUID(r['producto_id']),-Decimal(r['cantidad']),'matizado') for r in detail]+[(f['salida_id'],quantity,'preparacion')]
        for id,delta,kind in changes:
            before=locked[id]['cantidad'];after=before+delta
            if after>2147483647: raise HTTPException(422,'Las existencias superan el límite permitido.')
            c.execute(text('UPDATE ferreteria.existencias SET cantidad=:q,actualizado_en=now() WHERE producto_id=:id'),{'q':after,'id':id})
            c.execute(text('''INSERT INTO ferreteria.movimientos_inventario(producto_id,tipo,variacion,stock_anterior,stock_resultante,motivo,usuario_id,preparacion_id)
              VALUES(:product,:type,:delta,:before,:after,:reason,:user,:id)'''),{'product':id,'type':kind,'delta':delta,'before':before,'after':after,'reason':f"Preparación {f['codigo']}",'user':profile.id,'id':data.id})
        return dict(result)


@router.get('/preparations')
def preparations(profile:Staff):
    with user_connection(profile.id) as c:
        return [dict(r) for r in c.execute(text('''SELECT pr.*,f.codigo,f.tono,cl.nombre AS cliente FROM ferreteria.preparaciones pr JOIN ferreteria.formulas f ON f.id=pr.formula_id
          LEFT JOIN ferreteria.clientes cl ON cl.id=pr.cliente_id ORDER BY pr.fecha DESC LIMIT 300''')).mappings()]
