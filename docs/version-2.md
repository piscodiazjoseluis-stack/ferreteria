# Segunda versión: compras, recepción y supervisión

## Flujo que se demuestra

1. El Vendedor registra una venta al contado. La operación descuenta stock y deja comprobante y movimiento.
2. El Gerente ve los productos bajo mínimo, registra un proveedor y crea un pedido. Crear el pedido **no** aumenta el stock.
3. El Almacenero abre el pedido pendiente, cuenta cada producto y registra una recepción completa. La transacción cambia el estado del pedido, aumenta las existencias y crea un movimiento vinculado a cada línea. Un segundo intento recibe HTTP 409 y no vuelve a sumar stock.
4. Gerencia consulta pedidos pendientes, ventas del día y mes, productos más vendidos y movimientos. Los números provienen de las tablas reales.

## Permisos

| Acción | Gerente | Almacenero | Vendedor |
| --- | --- | --- | --- |
| Registrar y editar proveedores | Sí | No | No |
| Crear y cancelar pedidos pendientes | Sí | No | No |
| Consultar pedidos y proveedores | Sí | Sí | No |
| Confirmar recepción física | No | Sí | No |
| Ver costos estimados de compra | Sí | No | No |
| Crear y editar productos y precios | Sí | No | No |
| Registrar ventas | Sí | No | Sí |
| Consultar inventario | Sí | Sí | Sí |
| Ver indicadores gerenciales | Sí | No | No |

Las restricciones están en FastAPI y, para las tablas nuevas, también en políticas RLS del esquema privado. `ferreteria_api` usa una identidad de usuario por transacción. El navegador no recibe la cadena privada de PostgreSQL. La cuenta de Almacenero debe existir en Supabase Auth y tener un perfil activo `almacenero` en `ferreteria.perfiles`.

## Modelo y límites de esta versión

La migración `0002_compras_almacen` agrega `proveedores`, `compras`, `detalle_compra` y el origen de compra a `movimientos_inventario`. El pedido es inmutable después de crearse salvo la transición controlada a `recibida` o `cancelada`. Esta versión solo acepta **recepción completa**: si el conteo físico no coincide, se informa la diferencia y no se modifica el stock. Las entregas parciales, devoluciones y cuentas por pagar requieren otra iteración. El costo del pedido es estimado y no sustituye la contabilidad ni la facturación electrónica.

La entrada manual de inventario del Gerente permanece disponible para casos excepcionales; la reposición ordinaria se documenta mediante un pedido y una recepción. Matizados, crédito, catálogo público y compras con entregas parciales continúan fuera de esta versión.

## Validación

- `npm.cmd run build` y `npm.cmd run lint` en `frontend`.
- `python -m compileall -q backend/app` y `python -m pip check` en el entorno del backend.
- API con datos reales: confirmar que gerente crea proveedor y pedido, que vendedor recibe 403 en compras y que crear un pedido no cambia existencias.
- Almacenero: iniciar sesión, verificar menú propio, contar un pedido real y confirmar; comprobar orden `recibida`, stock incrementado una vez, movimiento ligado a cada línea y 409 en repetición. Probar 403 al intentar registrar venta o alterar precios.
- Revisar escritorio y móvil en navegador, mensajes de carga, error y confirmación.

Las migraciones de Supabase y la revisión `0003` de Alembic ya están alineadas. Antes de grabar la demostración, comprobar el estado publicado de GitHub/Vercel por separado y repetir el flujo con las cuentas reales del proyecto. No presentar una prueba técnica con identidad sustituida como si fuera un inicio de sesión real.

## Verificación del 24 de octubre de 2026

La cuenta real de prueba de Almacén ingresó en el navegador local y en la [versión 2 pública](https://ferreteria-miguel-v2.vercel.app/). El pedido #1 se recibió tras rechazar primero un conteo incorrecto. El stock del Foco LED 12 W pasó de 3 a 8 y quedó exactamente un movimiento de compra vinculado. Una repetición del POST de recepción devolvió 409 y no sumó stock de nuevo. Con un token real de Almacén, la API devolvió 403 al intentar consultar ventas o indicadores gerenciales y al intentar crear producto, proveedor o pedido; la respuesta del detalle no expuso costos. El acceso anónimo y un token inválido devolvieron 401.

En producción, el Vendedor inició sesión y registró la venta de prueba #13 por S/ 19.00, con comprobante. La URL pública respondió 200 en `/api/health`. El titular confirmó que pudo restablecer la contraseña del Gerente mediante un correo recibido en Gmail e iniciar sesión en V2; Supabase Auth registró un último inicio de sesión coincidente el 24 de octubre de 2026 a las 06:11, hora mostrada por el panel. Después se repitió la prueba en navegador con la cuenta real de Gerente: cargaron ventas de hoy y del mes (una operación por S/ 19.00), dos productos bajo mínimo y cero pedidos pendientes. Gerencia creó el pedido #2 por seis Martillos de carpintero a S/ 15.00 cada uno. El pedido quedó pendiente y el indicador subió a uno, mientras el stock del Martillo permaneció en cuatro. Gerencia canceló el pedido de prueba; quedó en estado `cancelada` y el indicador volvió a cero sin cambiar existencias. La publicación V2 está lista en Vercel y el código se verificó en `main` de GitHub. El enlace Git nativo sigue pendiente: el proyecto Vercel solo ofrece la cuenta `funal123jose-create`, mientras el repositorio pertenece a `piscodiazjoseluis-stack`. Se configuraron los secretos del repositorio para un flujo de GitHub Actions con token limitado al proyecto V2; la publicación automática del primer commit aún debe comprobarse.
