# Despliegue de la demostración

El repositorio usa Vercel Services para servir Vite en `/` y FastAPI en `/api` desde un mismo dominio. La base de datos y la autenticación siguen en el proyecto Supabase `Ferreteria` (`lapzymfujekspcssruvn`). Ninguna contraseña ni URL de conexión privada se guarda en Git.

**Dominio de producción:** https://ferreteria-gold.vercel.app/

**Repositorio:** https://github.com/piscodiazjoseluis-stack/ferreteria

El 25 de septiembre de 2026 se confirmó HTTP 200 en la portada, respuesta correcta de `/api/health`, autenticación del Vendedor mediante la API pública y carga de cuatro productos. También se abrió la interfaz pública con la sesión del Vendedor y se comprobó su menú de trabajo. El Gerente conserva la contraseña nueva establecida por el usuario mediante recuperación; esa clave no está disponible para las pruebas automatizadas de esta revisión. Las URL de retorno para el dominio público y la instalación local quedaron incluidas en Supabase Auth.

## Variables de Vercel

Configurar en Production y Preview:

| Variable | Uso |
| --- | --- |
| `VITE_SUPABASE_URL` | URL pública del proyecto Supabase; Vite la incluye en el navegador. |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Clave publicable de Supabase; Vite la incluye en el navegador. |
| `SUPABASE_URL` | Misma URL para la validación de sesiones en FastAPI. |
| `SUPABASE_PUBLISHABLE_KEY` | Misma clave publicable para FastAPI. |
| `DATABASE_URL` | URL PostgreSQL del usuario limitado `ferreteria_api`, con SSL y el pooler de sesión. Es un secreto solo de servidor. |

No configurar `MIGRATION_DATABASE_URL` en Vercel: el despliegue no ejecuta migraciones. No usar el rol `postgres`, la clave `service_role` ni la cadena de conexión de migración para atender peticiones.

## Autenticación en el dominio público

Supabase Auth tiene como Site URL `https://ferreteria-gold.vercel.app` y permite `https://ferreteria-gold.vercel.app/?recuperar=1` y `http://127.0.0.1:5173/?recuperar=1`. El formulario genera la URL de retorno desde el origen del navegador. José Luis ya confirmó el flujo completo con Gmail desde la instalación local; antes de grabar la recuperación en el dominio público, debe abrir el nuevo enlace recibido en ese mismo dominio y establecer personalmente la nueva contraseña.

## Comprobaciones

1. Abrir el dominio: debe aparecer el inicio de sesión.
2. Consultar `/api/health`: debe responder `{"status":"ok","service":"ferreteria-api"}`.
3. Iniciar sesión con Vendedor y confirmar que aparecen sus módulos.
4. Consultar productos, registrar una venta de prueba y comprobar comprobante, stock y movimiento.
5. Iniciar sesión con Gerente, confirmar supervisión y reposición.
6. Verificar recuperación de contraseña en el dominio público si se utilizará en la grabación.

Las ventas y reposiciones cambian la base de datos compartida con la aplicación local. Comprobar existencias antes de cada toma.

## Segunda versión (24 de octubre de 2026)

La URL pública de la versión 2 es https://ferreteria-miguel-v2.vercel.app/. Se desplegó desde el checkout local al proyecto `ferreteria-miguel-v2` de Vercel. FastAPI y Vite usan el mismo dominio. Se configuraron en Production las variables del backend y las dos variables públicas `VITE_SUPABASE_*`; `DATABASE_URL` quedó como Secret. La URL de producción responde `/api/health` y se comprobó en navegador el acceso real de Almacén y Vendedor, una recepción y una venta. La URL de despliegue única exige autenticación de Vercel, pero el alias de producción se comprobó accesible sin esa protección.

El repositorio GitHub citado arriba ya contiene el código V2 en `main` (`3fac258`). El proyecto Vercel todavía no quedó enlazado para despliegues automáticos: la integración GitHub de Vercel informó que carece de acceso de escritura a ese repositorio. El despliegue manual comprobado permanece activo. Antes de usar la recuperación de contraseña desde la nueva URL, añadir `https://ferreteria-miguel-v2.vercel.app/?recuperar=1` a las URL de redirección permitidas en Supabase Auth y comprobar el enlace recibido. Mantener la URL anterior para que la primera versión siga funcionando.
