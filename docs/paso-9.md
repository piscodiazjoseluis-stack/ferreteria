# Paso 9: venta al contado y perfiles diferenciados

## Qué puede hacer cada perfil

| Acción | Gerente | Vendedor |
| --- | --- | --- |
| Inicio | Supervisión del negocio | Punto de venta |
| Productos y precios | Crear y editar | Consultar |
| Inventario | Registrar entradas y ajustes físicos con motivo | Consultar disponibilidad e historial |
| Ventas | Registrar y consultar todas las ventas | Registrar y consultar sus propias ventas |
| Comprobante | Consultar cualquier venta | Consultar las propias |

La interfaz oculta las acciones ajenas al perfil y FastAPI exige el rol de gerente para modificar productos e inventario. Las ventas toman el precio actual del servidor; el usuario no puede alterar el precio en el formulario.

## Qué ocurre al confirmar una venta

FastAPI comprueba producto activo y stock suficiente, bloquea las filas de existencias, calcula el importe, guarda la venta y sus líneas, descuenta el stock y escribe un movimiento de tipo **Venta**. Todo ocurre en una transacción: si una parte falla, no queda una venta a medias. Una clave de idempotencia evita duplicar una venta al reintentar la misma confirmación. El comprobante conserva código, nombre y precio de cada producto tal como eran al vender.

**Saldo inicial** es la cantidad con la que se registró un producto. **Entrada** suma unidades recibidas, por ejemplo una reposición. **Ajuste** corrige el saldo para que coincida con un conteo físico y exige un motivo; puede subir o bajar. **Venta** resta las unidades vendidas automáticamente y queda vinculada al comprobante.

## Prueba de integración

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe scripts\verify_access.py
.\.venv\Scripts\python.exe scripts\verify_catalog.py
.\.venv\Scripts\python.exe scripts\verify_sales.py
```

La prueba de ventas usa una clave fija para que repetirla no vuelva a descontar stock. También confirma el rechazo de una cantidad superior a las existencias y que el movimiento de venta se registra una vez. Para verificar visualmente, acceder en `http://127.0.0.1:5173/` con las cuentas de `.artifacts/demo-accounts.json`. Ese archivo es local y no se sube a Git.

## Guion de presentación (3–5 minutos)

1. Explicar el proceso anterior: precios y existencias repartidos entre papel y Excel; una venta requería consultar precios y descontar stock manualmente.
2. Ingresar como **gerente**. Mostrar supervisión, editar el precio o crear un producto de prueba, y registrar una entrada de stock con motivo. Señalar la tabla de movimientos.
3. Cerrar sesión e ingresar como **vendedor**. Mostrar que su menú abre en **Punto de venta** y que puede consultar, pero no editar, precios o inventario.
4. Vender una unidad de un producto con existencias. Antes de confirmar, mostrar precio y total. Después, mostrar comprobante y número de venta.
5. Abrir **Disponibilidad**: el stock bajó una unidad y apareció el movimiento **Venta**. Abrir **Mis ventas**: solo aparece el historial propio.
6. Volver a gerente y abrir **Ventas del negocio**: puede revisar la operación del vendedor y su comprobante. Esta es la mejora concreta frente a Excel: una operación registra simultáneamente cobro, historial y existencias, con permisos distintos.

Las cuentas ficticias son para demostración. El 25 de septiembre de 2026, José Luis confirmó que recibió el enlace de recuperación en el Gmail real del gerente, cambió la contraseña mediante ese enlace y volvió a iniciar sesión. Es una prueba de extremo a extremo realizada por el usuario; no se registra ni comparte la nueva contraseña.
