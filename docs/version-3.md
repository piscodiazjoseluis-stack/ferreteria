# Versión 3 de reposición reportes y caja

Alcance aprobado: reposición sugerida, recepciones parciales, reportes filtrados y exportables, caja diaria. Se conservan los tres perfiles y la identidad visual de V2.

## Reglas

- La sugerencia es `máximo(0, objetivo - stock - unidades pendientes)`. Objetivo configurable, nunca menor que el mínimo. No es una predicción de demanda. Gerencia revisa proveedor y costo antes de pedir.
- Cada recepción guarda cantidades, fecha y responsable. Solo entra lo recibido. No se permiten excesos, recepciones vacías ni duplicados. Pedidos parcialmente recibidos no se cancelan para ocultar entregas.
- Reportes con fechas de Lima, totales de todo el resultado, paginación y CSV del mismo filtro. Un CSV es un archivo de consulta, no una copia de seguridad.
- Caja global por día de Lima, gestionada por Gerencia. Fondo, ingresos y retiros justificados, ventas por medio de pago, conteo real y diferencia. Abrir caja antes de vender. El cierre impide registrar más ventas ese día. Los reintentos de ventas ya confirmadas siguen devolviendo el mismo comprobante.
- El cierre conserva una instantánea y requiere explicar diferencias. Yape, Plin, transferencia y tarjeta se muestran separados del efectivo físico.

## Referencia visual

Fuente dominante: Workspace, Purchasing y Sales de V2; DM Sans y Manrope, verde oscuro, paneles claros, botones y formularios existentes. Referencias complementarias: Refero Craft Details (foco visible, tipos de campos, estados de carga) y Copywriting (acciones y errores concretos). Nuevas vistas mediante las mismas tablas, formularios y pestañas; sin cambiar marca ni navegación existente.

## Accesos a los módulos

Gerencia: Compras → Reposición sugerida; Productos → Editar → Stock objetivo; Reportes; Caja diaria. Almacén: Recepciones → Recibir. Vendedor conserva sus tres apartados y consulta el estado de caja antes de confirmar ventas.

Los enlaces `/#reportes`, `/#caja` y `/#compras` abren directamente el módulo permitido para el perfil. Al recargar se conserva ese módulo. Un perfil sin permiso se dirige a su espacio de trabajo autorizado.

## Migración y conservación de datos

Supabase Ferretería fue reactivado el 7 de noviembre de 2026. Se guardó copia local privada de las tablas antes de migrar. `20261107164429_operaciones_v3.sql`, registrada también como revisión Alembic `0004`, agregó recepciones y caja con RLS. Los dos pedidos recibidos de V2 se representaron en el historial sin repetir movimientos: las 13 ventas, los 3 pedidos y las 25 unidades previas no cambiaron con la migración.

## Pruebas realizadas

- `backend/scripts/verify_v3.py`: inicio de sesión real de los tres perfiles, comprobación de `/auth/me`, permisos y consultas SQL con el rol limitado. Tras validar los tokens se reutilizan sus identidades solo durante la batería transaccional para evitar consultar Auth en cada petición. Todos los cambios de esa batería se revierten al terminar.
- Pedido de 10 unidades: entrega de 6, saldo 4, entrega de 4 y saldo cero. Stock 4 → 10 → 14. Rechazo de recepción vacía, exceso, cancelación posterior a entrega y reintento con contenido distinto. Una repetición con la misma clave no suma de nuevo.
- Objetivo 12, stock 4 y ningún pedido: sugerencia 8. Un pedido pendiente cubre la necesidad. La recepción parcial conserva únicamente el saldo pendiente en el cálculo.
- Reportes: fechas inválidas rechazadas, dos páginas distintas, filtros por código, totales completos y CSV reconciliado. Con 107 ventas temporales se obtuvieron 100 filas y luego 7, y 107 filas exportadas. Las filas de esta prueba no se conservaron.
- Caja: fondo, venta en efectivo, venta por Yape, ingreso, retiro, rechazo de retiro excesivo, explicación obligatoria para una diferencia, cierre inmutable y bloqueo de nuevas ventas. El reintento de una venta anterior sigue devolviendo su comprobante.
- `backend/scripts/verify_v3_concurrency.py`: con dos conexiones independientes, un cierre esperó la transacción de venta en curso y recalculó el efectivo tras liberarse el bloqueo. Ambas transacciones se revirtieron y la caja real quedó abierta.
- Dos peticiones simultáneas con la misma clave sobre el pedido de demostración #7 devolvieron 200 y crearon una sola entrada de tres unidades; stock 4 → 7. Una segunda entrega de dos unidades se confirmó desde el navegador de Almacén.
- Compilación TypeScript/Vite, lint sin advertencias, sintaxis Python y `pip check` aprobados. Revisión visual de recepción a 390 × 844 usando un marco de prueba local; sus cantidades e ingreso se presentan sin desplazamiento horizontal en el formulario.

## Datos de demostración

Producto `DEMO-V3-001`, Tornillos de demostración V3, mínimo 8 y objetivo 12. Pedido #7 de ocho unidades a S/ 3, con entregas de tres y dos. Son datos explícitos de demostración y pueden cambiar al utilizar el sistema. La caja del 7 de noviembre se abrió con un fondo de demostración de S/ 100 y un ingreso adicional de S/ 10. Consultar los importes actuales antes de exponer; el cierre del día no debe realizarse hasta terminar las ventas de la demostración.

## Límites y revisión de seguridad

Los medios de pago son registros internos; no hay conexión con bancos ni pasarelas. No se añadieron anulaciones, crédito, matizado ni facturación electrónica. La sugerencia no estima demanda ni margen. Los reportes de compras muestran importes estimados de pedidos, incluidos los cancelados si se elige Todos, y no equivalen a gasto pagado.

Las tablas nuevas tienen RLS habilitado y forzado, y permanecen en el esquema privado. Los asesores de Supabase mantuvieron dos avisos previos: la tabla administrativa Alembic está cerrada sin políticas de aplicación intencionalmente, y la protección de contraseñas filtradas de Auth sigue deshabilitada. Esta última es una configuración adicional a revisar, no una prueba de fallo de los permisos implementados.
