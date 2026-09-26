# Validación final antes de la exposición

Fecha de revisión: 24 de septiembre de 2026. Proyecto Supabase: `Ferreteria` (`lapzymfujekspcssruvn`).

## Comprobado

- Se actualizó solo el correo del usuario Auth existente con rol Gerente a `gerente.ferreteria3@gmail.com`. Conserva el mismo identificador y la misma contraseña: el inicio de sesión con la clave anterior funcionó usando el correo nuevo; el correo antiguo fue rechazado. La cuenta Vendedor conservó su identificador, correo y contraseña, y pudo iniciar sesión.
- Una contraseña incorrecta mostró «Correo o contraseña incorrectos». El acceso sin token, con token inválido y las operaciones ajenas al rol fueron rechazados por la API y la base de datos.
- Desde la interfaz del Gerente se creó y editó un producto, se registraron una entrada y un ajuste con motivo, y los saldos e historial reflejaron cada cambio. El acceso directo «Reponer» desde una alerta de stock bajo abrió el formulario correspondiente; tras registrar la entrada, la alerta desapareció.
- Se confirmó una venta desde la interfaz: se creó el comprobante, se actualizó el total de ventas y se descontó una unidad del inventario. Las pruebas de integración verificaron la venta atómica, el rechazo por stock insuficiente y precio obsoleto, y que un reintento con la misma clave de idempotencia no duplica la operación.
- El Gerente pudo consultar los comprobantes del equipo. El Vendedor vio un menú y panel propios, pudo consultar precios y disponibilidad, y en «Mis ventas» solo aparecieron sus operaciones. Las pruebas de API confirmaron que no puede modificar productos o existencias ni consultar comprobantes ajenos.
- Se revisó la interfaz de escritorio y móvil (390 × 844): navegación, tabla desplazable y formulario de producto. La consola del navegador no registró errores. Durante la carga inicial del catálogo y de ventas ahora se muestra un estado de espera, evitando métricas transitorias en cero.

## Recuperación con correo real

El 25 de septiembre de 2026, José Luis comunicó que completó la prueba con `gerente.ferreteria3@gmail.com`: recibió el correo real, abrió el enlace, estableció una contraseña nueva y volvió a iniciar sesión. Por tanto, el flujo se puede presentar como **validado por el usuario de extremo a extremo**. La comprobación anterior de esta sección corresponde al 24 de septiembre; las observaciones de configuración pendientes de esa fecha quedaron superadas por la prueba del usuario. En esta revisión no se accedió al buzón ni se revalidó directamente la configuración SMTP.

La contraseña nueva reemplaza la anterior del Gerente. No se guarda en este repositorio ni se envía por chat. Antes de grabar la exposición, conviene probar en privado el acceso actual de Gerente y Vendedor y ocultar contraseñas y enlaces de recuperación de la grabación.
