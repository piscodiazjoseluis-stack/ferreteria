# Instalación y configuración de la versión final

El ZIP de código no contiene cuentas, contraseñas ni bases copiadas. Para otra instalación se necesitan una cuenta Supabase propia, PostgreSQL y permisos administrativos para migrar. No usar las conexiones de otros proyectos de esta máquina.

1. Instalar Node.js 22 o superior y Python 3.13. Extraer el ZIP a una carpeta nueva.
2. En `backend`, crear el entorno con `py -3.13 -m venv .venv` e instalar `requirements.txt` con ese Python.
3. Copiar `backend/.env.example` a `backend/.env`. Configurar las variables de Auth y las conexiones. La conexión administrativa MIGRATION_DATABASE_URL solo es para migrar. La API debe usar DATABASE_URL con el rol limitado ferreteria_api, SSL y NOBYPASSRLS.
4. En una base Supabase vacía autorizada, ejecutar desde backend `.venv/Scripts/python.exe -m alembic upgrade head`. No ejecutar scripts antiguos de limpieza. En una base existente, comprobar primero la revisión de Alembic y respaldar los datos. No aplicar la cadena inicial sobre tablas ya instaladas.
5. El administrador habilita LOGIN y una contraseña nueva al rol ferreteria_api. No se proporciona una contraseña predeterminada ni se usa el rol postgres en la API.
6. Crear usuarios de correo en Supabase Authentication, mediante el panel o la API administrativa documentada del proveedor. Obtener su UUID y registrar un perfil coincidente, por ejemplo:

```sql
INSERT INTO ferreteria.perfiles(id,nombre,rol,activo)
VALUES ('UUID_DEL_USUARIO_AUTH','Nombre del colaborador','gerente',true);
```

   Roles válidos: gerente, vendedor, almacenero y cajero. El UUID debe existir en Auth. Solo administradores crean perfiles; no hay registro público de empleados ni asignación de roles desde metadatos editables del usuario.
7. En frontend, ejecutar `npm.cmd ci`, copiar `.env.example` a `.env` y configurar únicamente las variables públicas VITE_SUPABASE_URL y VITE_SUPABASE_PUBLISHABLE_KEY.
8. Iniciar FastAPI en 127.0.0.1:8000 y Vite en 127.0.0.1:5173 como indica README. Iniciar sesión y comprobar el perfil.
9. Registrar productos y costos, proveedor y cliente de prueba. Abrir caja antes de vender o cobrar. Probar una recepción, una venta y un abono antes de operar con datos reales.
10. Para otra publicación, crear un proyecto Vercel Services propio y configurar variables/secretos fuera del repositorio. GitHub Actions debe apuntar a ese proyecto y a un token vigente. Añadir el dominio de recuperación en Supabase Auth antes de probar correo.

Los usuarios no se restauran desde el CSV de reportes. Para recuperación operativa, respaldar PostgreSQL y gestionar las cuentas Auth mediante el proveedor. El ensayo de restauración incluido solo utiliza la copia comercial privada, con UUID de usuarios representados localmente para verificar relaciones.
