# Primer avance: Ferretería y Matizados Miguel

**Fecha de presentación:** domingo 27 de septiembre de 2026

**Integrantes:** José Luis Pisco Díaz y Jesús

**Curso:** Evolución y Configuración de Software
**Idea central:** una venta que antes exigía consultar listas y actualizar el cuaderno o Excel después, ahora usa un precio único y registra la venta, el comprobante y la salida de inventario en el mismo sistema.

## ¿Está listo este primer avance?

Sí, para mostrar la evolución del **proceso de venta de mostrador e inventario**. El vendedor puede consultar precios y stock, registrar una venta al contado y revisar sus comprobantes. La venta descuenta existencias y deja un movimiento. El gerente administra productos y precios, registra entradas o ajustes con motivo, atiende alertas de stock y supervisa todas las ventas. El acceso distingue ambos roles. José Luis confirmó que probó el correo real de recuperación del gerente, cambió la contraseña mediante el enlace y volvió a ingresar.

El alcance demostrado es un **primer avance funcional**, no todos los módulos descritos como propuesta en el informe. El matizado digital, las órdenes de compra, créditos, catálogo público, facturación electrónica y reportes avanzados quedan para iteraciones posteriores. Tampoco se han medido todavía las metas del informe de reducir quiebres de stock o aumentar ventas; son objetivos, no resultados alcanzados.

La comparación proviene del informe: **P1**, stock en cuaderno y parcialmente en Excel sin actualización por venta; **P5**, varias listas de precios; **P7**, falta de información confiable para decidir. La tabla AS-IS/TO-BE también describe datos dispersos en Excel, cuadernos y chats. El flujo “antes” de la PPT resume esas evidencias; no pretende documentar cada paso operativo de una venta real.

## PPT antes del video: 2 minutos y 20 segundos

La PPT tiene cinco láminas, incluida la carátula. Hablen sobre las ideas, no lean cada palabra de la pantalla. El video comienza inmediatamente después de la lámina 5.

| Tiempo | Lámina y voz | Texto sugerido |
| --- | --- | --- |
| 0:00–0:15 | **1. Carátula — José Luis** | “Somos José Luis Pisco Díaz y Jesús. Presentamos el primer avance del sistema para Ferretería y Matizados Miguel. Nos enfocamos en cómo cambia el proceso de venta e inventario.” |
| 0:15–0:50 | **2. Problemática — Jesús** | “El informe identifica que el stock se llevaba en un cuaderno y parcialmente en Excel, sin actualizarse con cada venta. También había varias listas de precios. Eso podía generar consultas lentas, diferencias al cotizar y poca claridad sobre las existencias reales.” |
| 0:50–1:20 | **3. Proceso anterior — José Luis** | “Antes, para atender una venta había que buscar el producto, comprobar el stock en registros separados, revisar el precio y luego anotar la salida. Como la actualización dependía de otro paso manual, el cuaderno y Excel podían quedar desfasados.” |
| 1:20–1:55 | **4. Propuesta de mejora — Jesús** | “La propuesta es reunir catálogo, precios, ventas e inventario en una aplicación web con accesos distintos. En este avance ya funcionan los perfiles de gerente y vendedor, la venta al contado, el descuento automático del stock y el historial de movimientos. Nos concentramos en estas piezas porque atacan los problemas de stock y precio descritos en el informe.” |
| 1:55–2:20 | **5. Nuevo proceso — José Luis** | “Ahora el vendedor consulta un precio único y la disponibilidad actual. Al confirmar la venta, el sistema guarda el comprobante y descuenta las unidades. El gerente ve la operación y una alerta si queda poco stock. En el video veremos ese mismo recorrido funcionando.” |

## Video de demostración: aproximadamente 7 minutos

El guion alterna las voces y asigna a **José Luis el recorrido del vendedor** y a **Jesús el control gerencial**. La recuperación se muestra en un fragmento breve grabado aparte. No graben contraseñas, el enlace completo de recuperación ni tokens visibles en la barra del navegador.

| Tiempo | Voz y pantalla | Acción visible y texto sugerido |
| --- | --- | --- |
| 0:00–0:50 | **José Luis.** Portada breve y pantalla de acceso. | “El punto de partida era un negocio que creció, pero cuya información operativa quedó repartida. El stock se anotaba en cuaderno y parte en Excel. Nuestro primer avance se concentra en algo cotidiano: atender una venta y saber qué queda disponible después. Mostraremos el mismo recorrido desde dos perfiles, porque cada trabajador necesita acciones distintas.” |
| 0:50–1:30 | **Jesús.** Lámina comparativa “antes” o pantalla de acceso. | “El informe señala dos fallas concretas: el inventario no se actualizaba con cada venta y los precios estaban en varias listas. Si vendemos una pintura, no debería quedar pendiente descontarla en otra hoja. Tampoco debería depender de que cada vendedor recuerde qué precio está vigente. Esa relación entre problemas y solución es lo que vamos a comprobar.” |
| 1:30–2:45 | **Jesús.** Inicia sesión como gerente. Abre Supervisión, Productos e Inventario. | “Entro como gerente. Aquí veo los productos, las unidades disponibles y las alertas. En Productos se administra una ficha única con código, precio y stock mínimo. La pintura PIN-001 cuesta S/ 25; ese precio es el que consultará el vendedor. Puedo abrir ‘Editar’ porque mi perfil administra el catálogo. En Inventario, cada entrada o ajuste solicita un motivo y queda en el historial. No registraré todavía la reposición: primero veremos cómo una venta crea la necesidad.” Cierra sesión. |
| 2:45–4:25 | **José Luis.** Inicia sesión como vendedor. Recorre Consultar precios, Disponibilidad y Nueva venta. | “Mi pantalla es distinta: entro directamente al punto de venta. Puedo consultar el precio y el stock, pero no aparece la opción para editar productos ni ajustar existencias. Busco ‘Pintura látex blanca 1 galón’. Antes de cobrar, confirmo el precio oficial y la cantidad disponible. Agrego **una** unidad, elijo **Yape** y confirmo. El sistema calcula S/ 25 y genera el comprobante. Ahora entro a Disponibilidad: hay una unidad menos y aparece un movimiento de tipo ‘Venta’. En Mis ventas veo mi operación; no veo las ventas de otros usuarios. Este es el cambio clave frente al cuaderno: el descuento del stock ocurre al registrar la venta.” Cierra sesión. |
| 4:25–5:30 | **Jesús.** Vuelve como gerente; abre Supervisión, Ventas e Inventario. | “Regreso como gerente. La venta del vendedor aparece en ‘Ventas del negocio’, donde puedo abrir su comprobante. Si el stock de pintura bajó por debajo del mínimo, Supervisión muestra la alerta. Pulso ‘Reponer’, ingreso **3 unidades** con el motivo ‘Reposición recibida para demostración’ y confirmo. La alerta desaparece cuando vuelve a haber stock suficiente. En el historial se distinguen la salida por venta y la entrada por reposición, con fecha, usuario y motivo. Así puedo revisar por qué cambió la existencia.” |
| 5:30–6:15 | **José Luis.** Fragmento de recuperación grabado aparte: acceso → “¿Olvidaste tu contraseña?” → Gmail → formulario de nueva contraseña → acceso. | “El acceso también está protegido. Si el gerente olvida su contraseña, solicita un enlace desde esta pantalla. Probamos con su Gmail real: llegó el mensaje, abrimos el enlace, establecimos una contraseña nueva y pudimos volver a ingresar. En la grabación ocultamos la contraseña y el enlace completo. El vendedor no adquiere permisos de gerente por recuperar su propia clave; los permisos dependen del perfil de cada usuario.” |
| 6:15–6:40 | **Jesús.** Comparación visual antes/ahora. | “Lo que antes requería revisar listas y actualizar registros separados, ahora queda conectado: precio oficial, venta, comprobante y stock. El gerente puede supervisar y reponer con trazabilidad. Es un primer avance funcional centrado en los problemas P1 y P5 del informe.” |
| 6:40–7:00 | **José Luis.** Pantalla final de Supervisión o lámina 5. | “Todavía faltan módulos del proyecto completo, como matizado y compras. Pero ya podemos demostrar una mejora real del proceso de mostrador. No estamos mostrando solo pantallas: acabamos de registrar una venta y vimos sus efectos en el inventario y en cada rol.” |

## Preparación de las tomas

1. En el computador de grabación, inicia **FastAPI** y **Vite** con los comandos del `README.md`. Comprueba `http://127.0.0.1:5173/` y que Supabase esté disponible.
2. Ten a mano las credenciales de ambos perfiles **fuera de cámara**. La contraseña del gerente cambió durante la prueba de recuperación. El archivo local `.artifacts/demo-accounts.json` puede conservar la clave anterior; no la uses sin comprobarla ni muestres ese archivo en el video.
3. Antes de grabar la venta, comprueba en Disponibilidad el stock real de **PIN-001**. El 25 de septiembre figuraba con **8 unidades, mínimo 8 y precio S/ 25**. Si cambió, adapta en voz alta los números; no prometas que después habrá exactamente 7 unidades salvo que partas de 8.
4. Graba primero el fragmento de recuperación, si no conservas el de la prueba ya realizada. Haz un solo restablecimiento para la grabación; después usa la nueva clave en las tomas del gerente. En edición, el fragmento puede aparecer al final del recorrido. Oculta la contraseña, la URL del enlace y cualquier código de acceso.
5. Graba después el recorrido del gerente, la venta del vendedor y la reposición. La venta y la entrada **cambian datos reales**; si repites una toma, revisa de nuevo el stock antes de decir cantidades.
6. En el video llama a la pantalla “**comprobante interno de venta**”. El sistema de este avance no emite boletas o facturas electrónicas SUNAT. Tampoco afirmes que ya alcanzó las metas porcentuales del informe.

## Fuentes de contenido

- `Proyecto_Ferreteria_MF_MVP.docx`: sección 10 (P1, P5, P7), secciones 11.1–11.3 y tabla AS-IS/TO-BE.
- Código y validación del proyecto: `docs/paso-9.md`, `docs/validacion-final.md`, `frontend/src/Workspace.tsx`, `frontend/src/Sales.tsx` y API FastAPI.
- La prueba del correo real y el acceso con la nueva contraseña fue comunicada por José Luis el 25 de septiembre de 2026; no se presenta como una observación directa hecha por el equipo de desarrollo en esta revisión.
