# Versión final de Ferretería Miguel

La entrega integra clientes y crédito, cobros, matizado con cantidades decimales, catálogo público, comprobante PDF y auditoría. Conserva ventas, compras, recepción parcial, reposición y caja de V3. La aprobación de V3 correspondía a su alcance de exposición; esta entrega amplía el cumplimiento del informe inicial.

## Reglas que se deben explicar

- Crédito: Gerencia autoriza el límite. La venta descuenta stock y genera deuda, pero no efectivo. Gerencia o Cajero registra abonos contra una venta; solo los abonos en efectivo aumentan el efectivo esperado. Un abono no vuelve a contabilizar la venta.
- Caja: una jornada global de Lima; abrir antes de vender o cobrar. El cierre es definitivo y conserva una instantánea. No se reabre. La revisión permite cancelar antes de confirmar. Los cobros digitales se registran; no se procesan pagos bancarios.
- Anulación: solo Gerencia, venta del día, caja abierta y sin abonos. Conserva la venta original, restituye existencias y excluye la venta de indicadores y cobros vigentes. No hay devoluciones de períodos cerrados ni reembolsos de crédito con abonos.
- Matizado: una fórmula inmutable identifica base, colorantes, cantidades, unidades, producto de salida, rendimiento, cliente, referencia, muestra y notas. Para cambiarla se crea otro código. El Vendedor puede actuar como operario, como en el organigrama original; Caja solo consulta.
- Los insumos utilizan su unidad registrada (ml, g, litro o kg). No se convierten unidades ni densidades. Las unidades discretas solo aceptan enteros. Se admiten tres decimales de cantidad y cuatro de costo unitario; el dinero se redondea a dos decimales por línea.
- Confirmar preparación consume insumos y crea stock del producto preparado en una transacción. La venta posterior descuenta ese producto, sin consumir insumos otra vez. El historial conserva cantidades y costos usados; el reproceso requiere motivo y consume insumos de nuevo.
- Valoración: costo inicial declarado por Gerencia y promedio ponderado de adquisición tras una recepción. Una preparación usa el costo vigente conservado en sus componentes. No incluye mano de obra, impuestos ni gastos indirectos no registrados. El precio sugerido aplica un recargo sobre costo, no un margen sobre ventas.
- Catálogo `/catalogo`: consulta anónima, fotos, marca, precio y disponibilidad. PostgreSQL usa un rol sin acceso a clientes, costos o caja. WhatsApp es un enlace directo, no una integración API.
- Fotografías: PNG, JPEG o WebP de hasta 200 KB, guardadas en PostgreSQL con sus registros. No se implementó Supabase Storage; evitar afirmarlo en documentos. El límite protege el volumen de respuestas.
- Compra: guardar como borrador no compromete reposición; emitir cambia a pendiente de recepción. No envía correos al proveedor. Las condiciones de pago son informativas, no cuentas por pagar.

## Arquitectura realmente utilizada

React/Vite/TypeScript y FastAPI comparten dominio en Vercel Services. PostgreSQL y Auth en Supabase; esquema comercial privado con RLS forzado. SQLAlchemy y Alembic gestionan acceso y migraciones. ReportLab genera comprobantes internos, sin validez SUNAT. CSV es exportación operativa, no respaldo. GitHub Actions verifica frontend y API con PostgreSQL 17 aislado antes de desplegar.

Docker/Compose y Oracle/Render estaban propuestos, pero no son necesarios en la implementación publicada. Se sustituyeron por instalación local con Python/Node y frontend/API juntos en Vercel. Las identidades JWT se verifican contra Supabase; el rol se consulta en perfiles, no en metadatos editables del usuario.

## Migración y pruebas

`20261121165018_cierre_final.sql` / Alembic `0005`: conversión exacta de cantidades, tablas nuevas y permisos. La limpieza antigua se retiró del instalador inicial: nunca debe repetirse. Copia privada V3 y prueba de restauración local antes de migrar; usuarios Auth se representan por ID en el ensayo, sin respaldar contraseñas.

Las revisiones `0006` y `0007` completan el endurecimiento de políticas e índices y la identidad SQL de respaldo de solo lectura. El 28/11/2026 se habilitó el respaldo diario y se verificó la ejecución remota 46159712945, descargando su copia cifrada y restaurando 22 tablas en una base local nueva. Véase `docs/respaldo-comercial.md` para la evidencia, la custodia de la clave y los límites de Auth.

`verify_final.py` prueba la API y RLS contra PostgreSQL real local con identidades sustituidas, sin presentarlas como un login Supabase. Prueba reglas, errores, idempotencia, compras decimales, crédito, abonos, PDF, anulaciones, caja y conciliación del ledger. `verify_restore.py` restaura la copia privada en una base nueva local. El arnés `final_test_app.py` nunca se importa desde `app.main`, ni se publica como entrada de Vercel.

## Límites de cierre

No se garantizan tonos físicos por software, emisión SUNAT, WhatsApp API, modo offline, procesamiento bancario o contabilidad tributaria. Los porcentajes del informe original son metas, no resultados medidos. Se mantienen autenticación por correo y recuperación ya implementadas; el envío de recuperación real requiere una prueba específica, no se deduce de build o health.

Las evidencias finales y la matriz deben distinguir pruebas locales, navegador y producción, junto con las restricciones de cada flujo. Los datos demostrativos se etiquetan como tales.
