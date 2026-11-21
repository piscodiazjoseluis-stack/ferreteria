"""Downloadable internal sales receipt; never claims SUNAT validity."""
from io import BytesIO
from typing import Annotated
from uuid import UUID
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from app.auth import Profile, require_sales_access
from app.database import user_connection
from app.sales import receipt

router=APIRouter(tags=['Comprobantes'])

@router.get('/api/sales/{sale_id}/pdf')
def sale_pdf(sale_id:UUID,profile:Annotated[Profile,Depends(require_sales_access)]):
    with user_connection(profile.id) as c: sale=receipt(c,sale_id,profile)
    b=BytesIO(); styles=getSampleStyleSheet(); p=lambda s:Paragraph(escape(str(s)),styles['Normal'])
    content=[Paragraph('Ferretería y Matizados Miguel',styles['Title']),p(f"Comprobante interno #{sale['numero']}"),p('No es una boleta ni factura electrónica SUNAT.'),p(f"Estado: {'ANULADA' if sale['anulada'] else 'Confirmada'}"),p(f"Cliente: {sale['cliente_nombre'] or 'Público general'}"),p(f"Condición: {sale['condicion']} / Medio: {sale['metodo_pago']}"),p(f"Fecha registrada: {sale['fecha'].isoformat()}"),Spacer(1,16)]
    data=[[p('Producto'),p('Cantidad'),p('Precio S/'),p('Subtotal S/')]]+[[p(i['nombre_producto']),p(i['cantidad']),p(f"{i['precio_unitario']:.2f}"),p(f"{i['subtotal']:.2f}")] for i in sale['items']]
    t=Table(data,colWidths=[240,60,75,90],repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E5F2EB')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.5,colors.lightgrey)]))
    content.extend([t,Spacer(1,15),p(f"TOTAL: S/ {sale['total']:.2f}")]);SimpleDocTemplate(b,title='Comprobante interno de venta').build(content)
    return Response(b.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="venta-{sale["numero"]}.pdf"'})
