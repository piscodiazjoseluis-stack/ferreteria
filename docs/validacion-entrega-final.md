# Validación de la entrega final del 21 de noviembre de 2026

## Evidencia independiente

- PostgreSQL 17 local: migraciones nuevas desde cero y 53 peticiones API con el rol SQL limitado, sin conexión a datos comerciales reales. La identidad de esos casos se sustituye en el arnés de pruebas.
- GitHub Actions repite build, lint y pruebas de API con PostgreSQL efímero antes de desplegar. Se corrigió la creación de la carpeta privada de evidencias en una descarga limpia.
- Supabase Ferreteria: copia comercial V3 previa y restauración de prueba en una base local nueva. Coincidieron 16 ventas, 6 compras y 49 movimientos; el stock concilió con el ledger. La migración remota conservó los datos previos y quedó en revisión 0007, incluido el rol de respaldo de solo lectura.
- API pública: 30 comprobaciones con cuatro inicios de sesión reales. Preparación: 250.5 ml de base y 2.125 g de colorante; venta a crédito S/ 25; abono en efectivo S/ 10; saldo S/ 15. Datos ficticios FINAL-; no se cerró la caja.
- Navegador público: Gerente, Vendedor, Almacenero y Cajero iniciaron sesión; navegación y cuenta de cliente verificadas; catálogo anónimo a 390 px con WhatsApp sin enviar mensajes y sin desplazamiento horizontal del documento.
- Navegador local: alta de cliente, alta de fórmula, preparación confirmada, consulta gerencial y revisión de caja cancelada. Sin errores JavaScript en esos recorridos.
- Dependencias: se corrigieron avisos conocidos de Vite y source-map-js mediante actualizaciones compatibles (Vite 8.3.8 y source-map-js 1.2.4), y se actualizó certifi a 2026.11.20. npm audit y pip-audit de los requisitos fijados terminaron sin vulnerabilidades conocidas. Esto no equivale a una certificación de seguridad total.

## Restricciones explícitas

La recuperación Gmail completa conserva la validación previa del titular y no se repitió leyendo el buzón durante este cierre. No se hizo una auditoría externa ni carga masiva. El asesor de seguridad mantiene un aviso de protección de contraseñas filtradas deshabilitada y Alembic cerrada sin políticas de aplicación intencionalmente.

Se implementó un flujo de respaldo comercial cifrado con programación diaria, retención de siete días y una identidad SQL de solo lectura. La exportación, el cifrado, el descifrado y la restauración de sus 22 tablas pasaron localmente. Su ejecución en GitHub sigue pendiente de autorización tras el rechazo de revisión automática «blocked by policy», sin causa detallada. La variable de habilitación permanece sin activar; no se atribuye al sistema un respaldo automático ya operativo. No se contrataron capacidades de pago. El procedimiento y la custodia de la clave privada se describen en respaldo-comercial.md.

El token de CI documentado vence el 23 de noviembre; revisar vigencia antes de otro despliegue. Su caducidad no apaga el sistema publicado. No se implementaron SUNAT, procesamiento bancario, conversiones automáticas de tonos o modo offline. Las reglas acotadas están en la matriz y el manual técnico.

La entrega incluye manuales PDF, informe Word/PDF, matriz PDF y Markdown, diagramas PDF, comparativo, guion, evidencias y presentación editable exportable a PowerPoint. El archivo de código y el paquete académico se distribuyen sin credenciales.

## Actualización del respaldo del 28 de noviembre de 2026

El estado pendiente descrito arriba corresponde al cierre del 21/11/2026. El titular autorizó su verificación el 28/11/2026. Se reactivó Ferretería y se habilitó el flujo diario. Una primera ejecución detectó que la subida omitía la carpeta oculta de salida; se corrigió esa configuración, manteniendo la selección exclusiva de archivos cifrados `.enc`.

La [ejecución 46159712945](https://github.com/piscodiazjoseluis-stack/ferreteria/actions/runs/46159712945) terminó correctamente. Se descargó y descifró el artefacto y se restauraron 22 tablas en una base local nueva. Coincidieron todos los conteos y se validaron existencias y secuencias. La comparación posterior del origen confirmó que los datos comerciales no cambiaron. Se mantiene la exclusión de credenciales Auth y la clave privada fuera de GitHub. El cron está habilitado; la ejecución comprobada fue manual sobre ese mismo flujo.
