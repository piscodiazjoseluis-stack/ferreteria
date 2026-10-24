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
