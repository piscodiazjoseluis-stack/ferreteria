# Despliegue de la demostración

El repositorio usa Vercel Services para servir Vite en `/` y FastAPI en `/api` desde un mismo dominio. La base de datos y la autenticación siguen en el proyecto Supabase `Ferreteria` (`lapzymfujekspcssruvn`). Ninguna contraseña ni URL de conexión privada se guarda en Git.

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

Después de obtener el dominio definitivo de Vercel, añadir `https://DOMINIO/?recuperar=1` a las URL de redirección permitidas de Supabase Auth. El formulario genera esta URL desde el origen del navegador. Probar el enlace de recuperación en ese mismo dominio antes de grabar el video. Mantener también la URL local autorizada si se seguirá usando la instalación local.

## Comprobaciones

1. Abrir el dominio: debe aparecer el inicio de sesión.
2. Consultar `/api/health`: debe responder `{"status":"ok","service":"ferreteria-api"}`.
3. Iniciar sesión con Vendedor y confirmar que aparecen sus módulos.
4. Consultar productos, registrar una venta de prueba y comprobar comprobante, stock y movimiento.
5. Iniciar sesión con Gerente, confirmar supervisión y reposición.
6. Verificar recuperación de contraseña en el dominio público si se utilizará en la grabación.

Las ventas y reposiciones cambian la base de datos compartida con la aplicación local. Comprobar existencias antes de cada toma.
