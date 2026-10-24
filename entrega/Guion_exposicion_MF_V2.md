# Demostración de la segunda versión — Ferretería y Matizados Miguel

Duración sugerida: 6–8 minutos. Abrir antes de empezar [la versión 2 publicada](https://ferreteria-miguel-v2.vercel.app/) y tener a mano las cuentas de Vendedor, Gerente y Almacenero. Registrar el stock visible al inicio; los números pueden cambiar porque la demostración usa una base de datos real.

## Idea central para explicar

«Antes, ventas y existencias se apuntaban en cuaderno o Excel. Eso obligaba a actualizar varias veces el mismo dato y hacía difícil saber quién cambió el stock o si un pedido realmente llegó. En esta versión, Vendedor, Gerente y Almacenero tienen tareas diferentes sobre una misma información. Una venta descuenta existencias y una compra solo las aumenta cuando Almacén confirma la recepción física».

## Recorrido recomendado

1. **Vendedor — Punto de venta.** Iniciar sesión y señalar que solo aparecen Nueva venta, Consultar precios y Disponibilidad. Buscar un producto de bajo stock, por ejemplo Martillo de carpintero. Anotar el stock, añadir una unidad y confirmar el cobro en efectivo. Mostrar el comprobante y comprobar que el stock bajó una unidad. Explicar que el vendedor usa el precio oficial del catálogo y no puede modificarlo.
2. **Gerente — Supervisión.** Cerrar sesión, entrar como Gerente y mostrar el menú de control: Supervisión, Ventas, Productos, Inventario y Compras. Señalar la alerta de stock bajo y los indicadores de ventas del día y del mes. En Ventas, enseñar que Gerencia ve las operaciones del negocio, mientras el Vendedor ve solo las propias.
3. **Gerente — Proveedor y pedido.** En Compras, registrar un proveedor de demostración o elegir uno activo. Crear un pedido del producto con stock bajo; para la exposición se pueden usar 6 unidades de Martillo a un costo estimado de S/ 15 por unidad. Mostrar el número del pedido y su estado *Pendiente*. Volver a Inventario y comprobar que crear el pedido **no** aumentó el stock. Explicar que el pedido es una intención de compra, no mercancía recibida.
4. **Almacenero — Recepción.** Entrar con el perfil Almacenero. Mostrar que su menú contiene Recepciones, Inventario y Catálogo; no dispone de Ventas, creación de productos ni indicadores gerenciales. Abrir el pedido pendiente y contar las unidades físicas. Si se desea demostrar el control, introducir primero una cantidad distinta: el sistema rechaza la recepción y no modifica el inventario. Introducir luego la cantidad exacta y confirmar. Mostrar el mensaje, el estado *Recibida* y el nuevo stock.
5. **Trazabilidad y cierre.** En Inventario, enseñar el movimiento «Compra recibida», con unidades antes y después, fecha y responsable. Volver como Gerente a Supervisión y Compras: el pedido ya no está pendiente y el stock se actualizó. Explicar que se puede reconstruir quién vendió, quién pidió y quién recibió.

## Qué destacar frente a la profesora

- La diferencia de perfiles es funcional y está protegida en la API: el Vendedor no puede crear pedidos; Almacén no puede registrar ventas ni ver costos; el Gerente no puede simular la recepción física.
- Los datos viven en Supabase y se consultan desde la aplicación. El navegador no contiene la conexión privada de PostgreSQL.
- Venta y recepción crean movimientos vinculados. Una recepción repetida se rechaza para evitar duplicar existencias.
- Los indicadores gerenciales se calculan con ventas y pedidos reales. No son tarjetas estáticas.
- La recepción es completa en esta versión; si faltan unidades, se detiene la operación. Entregas parciales, cuentas por pagar y matizados quedan como evolución futura.

## Antes de grabar

Comprobar conexión a Internet, iniciar sesión con cada perfil, elegir un producto activo y revisar su stock. Tener preparado el proveedor que se usará. No enseñar contraseñas en pantalla ni borrar datos de pruebas anteriores: crear un pedido nuevo permite demostrar todo el ciclo. Si se presenta recuperación por correo desde el dominio V2, verificar antes que la URL de retorno de V2 esté autorizada en Supabase y que el enlace llega al buzón; el cambio de contraseña debe hacerlo el titular de la cuenta.
