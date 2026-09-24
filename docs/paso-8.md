# Paso 8 · Productos e inventario

## Qué se puede demostrar

El gerente inicia sesión, registra un producto con código, categoría, unidad, precio, mínimo y saldo inicial. El sistema crea la ficha y sus existencias en Supabase. Cada entrada y ajuste por cantidad física exige motivo y produce un movimiento con fecha, usuario, saldo anterior, variación y saldo nuevo. El vendedor consulta catálogo, existencias e historial, pero no puede modificar nada: FastAPI devuelve 403 aunque intente llamar directamente a los endpoints.

El producto de muestra `PIN-001` es Pintura látex blanca 1 galón, precio **S/ 25**, mínimo **8** y stock actual **10**. Deja preparado el recorrido aprobado para la próxima etapa: vender 3 deberá cobrar S/ 75 y dejar stock 7, marcado como bajo. La venta aún no está implementada; la pantalla Ventas lo indica explícitamente.

## Ejecutar localmente

En dos terminales PowerShell desde la carpeta del proyecto:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm.cmd run dev
```

Abrir http://127.0.0.1:5173/. Las configuraciones privadas permanecen en `backend/.env`, `frontend/.env` y `.artifacts/`; esos archivos están fuera de Git. La API necesita conexión a Internet para validar Supabase Auth y consultar PostgreSQL.

## Verificación

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\verify_access.py
.\backend\.venv\Scripts\python.exe backend\scripts\verify_catalog.py
cd frontend
npm.cmd run build
npm.cmd run lint
```

`verify_catalog.py` es idempotente: crea el producto de muestra si falta, prueba permisos y restricciones, y comprueba el historial y el stock final. La primera ejecución crea movimientos de saldo inicial, entrada y ajuste. Las siguientes no los duplican.

En navegador se verificaron: contraseña incorrecta, login gerente, entrada 10→11, ajuste físico 11→10, historial persistente y login vendedor con inventario de solo lectura. La recuperación de contraseña usa Supabase Auth y depende de que la URL local esté permitida en Auth y de una cuenta con correo real. El proyecto usa SMTP predeterminado de Supabase, que solo entrega a correos miembros de la organización; el correo propuesto para la prueba no es miembro. Por eso la recepción final del correo queda pendiente de elegir un correo miembro o configurar SMTP propio. No confundir una respuesta de envío aceptada con la llegada efectiva a la bandeja.
