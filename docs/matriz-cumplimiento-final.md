# Matriz de cumplimiento de la entrega final

## Punto de venta

| ID | Requisito | Estado | Evidencia |
|---|---|---|---|
| POS01 | Buscar productos y centralizar precios | Cumple | Sales / catálogo; precio confirmado por el servidor. |
| POS02 | Carrito y medios de pago | Cumple | Cantidades, eliminación y efectivo/Yape/Plin/transferencia/tarjeta. |
| POS03 | Comprobante PDF descargable | Adaptado | PDF interno generado con ReportLab; sin validez SUNAT. |
| POS04 | Venta conectada al inventario | Cumple | Transacción, bloqueos y clave de reintento. |
| POS05 | Cierre diario por medio de pago | Cumple | Caja separa efectivo físico de medios digitales. |
| POS06 | Anulación trazable | Acotado | Solo día actual, caja abierta y sin abonos; documento original conservado. |

## Inventario y compras

| ID | Requisito | Estado | Evidencia |
|---|---|---|---|
| INV01 | Ficha con marca, foto y unidad | Cumple | Productos con imagen pequeña y referencia de equivalencia escrita. |
| INV02 | Stock transaccional y movimientos | Cumple | Venta, compra, ajuste, preparación y anulación con responsable. |
| INV03 | Mínimo, objetivo y alertas | Cumple | Alerta de stock y reposición considerando pendientes. |
| INV04 | Fracciones para insumos | Cumple | Hasta 3 decimales; enteros para unidades discretas. |
| COM01 | Proveedor y condiciones de pago | Cumple | Datos de contacto/documento y condiciones informativas. |
| COM02 | Borrador y emisión de pedido | Adaptado | Borrador → pendiente emitida → parcial/recibida/cancelada. Emitir no envía correo. |
| COM03 | Recepción actualiza inventario | Cumple | Cantidad recibida, saldo pendiente y reintentos sin duplicar. |

## Matizado

| ID | Requisito | Estado | Evidencia |
|---|---|---|---|
| MAT01 | Fórmula con código y referencia comercial | Cumple | Una base, colorantes, cantidades, unidades y notas. |
| MAT02 | Muestra y búsqueda | Cumple | Imagen opcional; búsqueda por código, tono, referencia o cliente. |
| MAT03 | Historial por cliente | Cumple | Fórmulas y preparaciones asociadas al cliente. |
| MAT04 | Costo conservado de la mezcla | Acotado | Costo de adquisición de insumos; excluye gastos no registrados. |
| MAT05 | Precio sugerido configurable | Adaptado | Recargo sobre costo; no margen porcentual sobre ventas. |
| MAT06 | Consumo automático de componentes | Cumple | Una transacción descuenta insumos y crea stock preparado. |
| MAT07 | Registro de reprocesos | Cumple | Preparación previa y motivo; nuevo consumo registrado. |
| MAT08 | Bases, marcas y equivalencias | Acotado | Tipos de insumo, marcas y referencia escrita; sin conversión automática de tonos. |

## Clientes y catálogo

| ID | Requisito | Estado | Evidencia |
|---|---|---|---|
| CLI01 | Ficha y segmento de cliente | Cumple | Nombre, documento, contacto, dirección y segmento. |
| CLI02 | Saldo de crédito y pagos | Cumple | Venta a crédito y abonos; saldo calculado sin editar deuda a mano. |
| CLI03 | Autorización de límites | Cumple | Gerencia fija límite; venta excedida se rechaza. |
| CAT01 | Catálogo público por categoría | Cumple | Ruta /catalogo sin inicio de sesión. |
| CAT02 | Foto, precio y disponibilidad | Cumple | Consulta de inventario; no expone costos ni datos privados. |
| CAT03 | WhatsApp y móvil | Cumple | Enlace directo y diseño responsive; sin API de mensajería. |

## Reportes y seguridad

| ID | Requisito | Estado | Evidencia |
|---|---|---|---|
| REP01 | Ventas diarias y mensuales | Cumple | Indicadores existentes y comprobantes vigentes. |
| REP02 | Ticket promedio y comprobantes | Cumple | Análisis por período; excluye anuladas. |
| REP03 | Alertas y top 10 por período | Cumple | Supervisión y análisis con fechas. |
| REP04 | Ventas por día de semana | Cumple | Gráfico del período seleccionado. |
| REP05 | Filtros y exportación | Cumple | Reportes paginados y CSV de todos los resultados filtrados. |
| SEG01 | Autenticación y recuperación | Histórico y actual | 4 logins reales actuales; recuperación Gmail validada antes, no repetida en este cierre. |
| SEG02 | Gerente Vendedor Almacenero Cajero | Cumple | Perfiles activos, permisos API y RLS. |
| SEG03 | Acciones sensibles auditadas | Cumple | Precios/clientes/proveedores/fórmulas/preparaciones/abonos/anulaciones. |
| SEG04 | Seguridad del catálogo público | Cumple | Rol SQL separado con proyección solo comercial. |
| INF01 | Respaldo automático y recuperación | Cumple | Actualización 28/11/2026: cron diario habilitado. Ejecución remota 46159712945 correcta; artefacto cifrado descargado y 22 tablas restauradas localmente con conteos, existencias y secuencias conciliados. Origen sin cambios. La ejecución verificada fue manual sobre el mismo flujo. No incluye contraseñas Auth. |

