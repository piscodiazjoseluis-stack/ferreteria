# Ferretería y Matizados Miguel

Primer avance universitario: evolución del catálogo e inventario en Excel/cuaderno hacia una aplicación web con acceso por roles, datos persistentes e historial verificable. La venta transaccional es la siguiente etapa.

## Estado

Pasos 7 y 8: acceso por perfiles, productos e inventario conectados a Supabase. El gerente mantiene el catálogo, registra entradas y ajustes físicos; el vendedor consulta. La pantalla de ventas identifica claramente que esa operación aún no está disponible.

Proyecto Supabase confirmado: `Ferreteria`, referencia `lapzymfujekspcssruvn`.
Las tablas antiguas se eliminaron con autorización y copia local previa. Las siete tablas nuevas están en el esquema privado `ferreteria`. LifeTrack queda fuera del alcance.

## Herramientas

Configurado con Node.js 24.13.0 y Python 3.13. Dependencias frontend en package-lock.json y backend en requirements.txt.

## Iniciar en Windows PowerShell

Terminal 1, desde la carpeta del proyecto:

```powershell
Set-Location 'C:\Users\USUARIO\Documents\ChatGPT\Software_ferreteria 2\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
Set-Location 'C:\Users\USUARIO\Documents\ChatGPT\Software_ferreteria 2\frontend'
npm.cmd run dev
```

Abrir http://127.0.0.1:5173. Debe aparecer la pantalla de acceso. Las cuentas de prueba están en `.artifacts/demo-accounts.json`, fuera de Git.
Documentación de la API: http://127.0.0.1:8000/docs.
Detener cada proceso con Ctrl+C en su terminal.

El proxy de Vite reenvía `/api` a FastAPI. El estado comprueba comunicación local, no conexión con PostgreSQL. La configuración de producción se resolverá en la etapa de entrega.

## Reinstalar dependencias si fuera necesario

En frontend: `npm.cmd ci`.
En backend: `py -3.13 -m venv .venv` y después `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Verificar

En frontend: `npm.cmd run build` y `npm.cmd run lint`.
En backend: `.\.venv\Scripts\python.exe -m pip check`.

La instalación actual tiene `backend/.env` y `frontend/.env` configurados. `.env.example` documenta las variables necesarias para otra instalación; nunca subir `.env` ni credenciales a Git.

Consultar [base de datos y acceso](docs/paso-7.md) para migraciones, permisos y pruebas de integración.

Consultar [productos e inventario](docs/paso-8.md) para las funciones disponibles y la prueba comercial.

Consultar [decisiones y etapas](docs/decisiones.md) antes de avanzar.
