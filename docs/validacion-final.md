# Validación final antes de la exposición

Fecha de revisión: 24 de septiembre de 2026. Proyecto Supabase: `Ferreteria` (`lapzymfujekspcssruvn`).

## Comprobado

- Se actualizó solo el correo del usuario Auth existente con rol Gerente a `gerente.ferreteria3@gmail.com`. Conserva el mismo identificador y la misma contraseña: el inicio de sesión con la clave anterior funcionó usando el correo nuevo; el correo antiguo fue rechazado. La cuenta Vendedor conservó su identificador, correo y contraseña, y pudo iniciar sesión.
- Una contraseña incorrecta mostró «Correo o contraseña incorrectos». El acceso sin token, con token inválido y las operaciones ajenas al rol fueron rechazados por la API y la base de datos.
- Desde la interfaz del Gerente se creó y editó un producto, se registraron una entrada y un ajuste con motivo, y los saldos e historial reflejaron cada cambio. El acceso directo «Reponer» desde una alerta de stock bajo abrió el formulario correspondiente; tras registrar la entrada, la alerta desapareció.
- Se confirmó una venta desde la interfaz: se creó el comprobante, se actualizó el total de ventas y se descontó una unidad del inventario. Las pruebas de integración verificaron la venta atómica, el rechazo por stock insuficiente y precio obsoleto, y que un reintento con la misma clave de idempotencia no duplica la operación.
- El Gerente pudo consultar los comprobantes del equipo. El Vendedor vio un menú y panel propios, pudo consultar precios y disponibilidad, y en «Mis ventas» solo aparecieron sus operaciones. Las pruebas de API confirmaron que no puede modificar productos o existencias ni consultar comprobantes ajenos.
- Se revisó la interfaz de escritorio y móvil (390 × 844): navegación, tabla desplazable y formulario de producto. La consola del navegador no registró errores. Durante la carga inicial ahora se muestra un estado de espera, evitando métricas transitorias en cero.

## Pendiente para cerrar esta etapa

- **Correo real de recuperación:** el SMTP personalizado está desactivado en Supabase. El servicio integrado solo entrega correos a integrantes del proyecto; `gerente.ferreteria3@gmail.com` no está confirmado como tal. Se necesita configurar un proveedor SMTP con credenciales introducidas por el propietario en Supabase. No incorporar la cuenta Gmail al equipo de Supabase solo para recibir correos, pues eso ampliaría el acceso administrativo.
- **Retorno del enlace:** la URL de retorno de la app local `http://127.0.0.1:5173/?recuperar=1` debe figurar en la lista permitida de Supabase Auth. La URL del sitio todavía apunta a `http://localhost:3000`.
- **Prueba de extremo a extremo:** solicitar el enlace desde la app, verificar su llegada en Gmail, abrirlo, fijar personalmente una nueva contraseña y volver a iniciar sesión con ella. La nueva contraseña sustituirá a la que se conservó al cambiar el correo. No registrar la nueva clave en este repositorio ni enviarla por chat.

La etapa y el guion de exposición se cierran después de esa prueba con la cuenta real.
