# Base de datos y acceso

## Estado implementado

Proyecto Supabase `Ferreteria`, referencia `lapzymfujekspcssruvn`.
Siete tablas comerciales en el esquema privado `ferreteria`, más la tabla técnica `alembic_version`.
Seleccionar ese esquema en Table Editor; `public` está vacío tras la limpieza autorizada.

El rol de conexión `ferreteria_api` no es propietario ni tiene BYPASSRLS. La contraseña está en `backend/.env`, excluido de Git.
La conexión usa el session pooler del proyecto, compatible con IPv4 y SSL.

La interfaz inicia sesión con Supabase Auth y envía el token a FastAPI. FastAPI consulta `/auth/v1/user`, obtiene la identidad verificada y establece `app.user_id` únicamente durante la transacción. Consulta un perfil activo en PostgreSQL; no usa metadatos editables del usuario para decidir su rol.

Las tablas comerciales no están expuestas a la Data API. Las políticas RLS distinguen lectura de personal activo, mantenimiento del gerente y registros del usuario responsable. La API sigue siendo responsable del flujo de negocio completo que se implementará en los Pasos 8 y 9.

## Cuentas de demostración

Se crearon `gerente@ferreteria.example.com` y `vendedor@ferreteria.example.com`, sin enviar correos. Son cuentas ficticias con contraseñas aleatorias, guardadas en `.artifacts/demo-accounts.json` (archivo privado excluido de Git).
No usar estas cuentas como cuentas de producción. Las 11 cuentas antiguas de Auth se conservaron, sin perfiles ni acceso automático al nuevo sistema.

## Migraciones

La migración inicial fue aplicada mediante el conector Supabase y está conservada en `backend/migrations/sql/0001_initial.sql`. La limpieza de objetos antiguos fue una operación única: no repetirla.
Alembic reconoce el estado inicial como revisión `0001`. El entorno de migración requiere `MIGRATION_DATABASE_URL` administrativa, separada de la conexión limitada de la API. No es necesaria para ejecutar la aplicación.
Desde backend: `.\.venv\Scripts\python.exe -m alembic history` consulta las revisiones locales. Para migraciones futuras configurar la conexión administrativa de forma privada y ejecutar `alembic upgrade head` mediante el mismo Python.
El archivo de revisión inicial omite la limpieza antigua para instalaciones nuevas. No se ofrece un downgrade destructivo; usar migraciones correctivas o restauración planificada.

## Verificación

Desde la raíz del proyecto:

```powershell
.\backend\.venv\Scripts\python.exe backend/scripts/verify_access.py
```

Prueba Auth real, API y PostgreSQL para los dos roles; tokens inválidos, ausencia de perfil, acceso del vendedor, restricciones de stock/precio y aislamiento del contexto de usuario. Las inserciones comerciales de prueba se revierten con rollback.

Frontend: `npm.cmd run lint` y `npm.cmd run build` desde frontend.

## Observaciones

La tabla técnica `alembic_version` tiene RLS sin políticas deliberadamente: ningún usuario operativo debe acceder a ella. El rol administrativo maneja migraciones.
El asesor de Supabase señala protección contra contraseñas filtradas desactivada; no se modificó la configuración global ni el plan. Las cuentas de prueba usan contraseñas aleatorias fuertes.
La pantalla actual permite acceso y cierre de sesión. Los módulos comerciales y su diseño final pertenecen a las próximas etapas.
