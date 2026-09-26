# Decisiones y etapas

Entrega: domingo 27 de septiembre de 2026. Un desarrollador.

## Aprobado

1. Alcance: ventas al contado conectadas al inventario; un almacén, cantidades enteras, soles y un método de pago por venta.
2. Requisitos: gerente y vendedor; catálogo centralizado; entradas y ajustes justificados; venta transaccional; historial permanente; evitar stock negativo y confirmaciones duplicadas.
3. Arquitectura: React, Vite y TypeScript; FastAPI; PostgreSQL y Auth en Supabase; SQLAlchemy y Alembic. Las operaciones de negocio pasan por FastAPI.
4. Modelo: perfiles, categorias, productos, existencias, ventas, detalle_venta y movimientos_inventario. Precios y descripciones históricos; idempotencia; bloqueo de existencias durante ventas; importes decimales.
5. Pantallas: acceso, nueva venta, productos e inventario, ventas y movimientos. Identidad visual definitiva pendiente.

## Paso actual

Paso 6 completado: estructura, dependencias, API de estado e interfaz de comprobación verificadas.

Paso 7 verificado de nuevo: modelo remoto, conexión local mediante session pooler, autenticación, dos cuentas ficticias con perfiles, políticas de acceso y pruebas de integración. El usuario autorizó continuar directamente al Paso 8.

Paso 8 implementado: API e interfaz de productos e inventario, saldo inicial, entradas, ajustes físicos justificados e historial.

Paso 9 implementado: ventas reales con precio del catálogo, bloqueo y descuento transaccional de existencias, comprobante, movimiento automático e idempotencia. Navegación y acciones diferenciadas: gerente supervisa todas las ventas, administra productos/precios y registra entradas/ajustes; vendedor abre en el punto de venta, consulta precios/stock y ve sus propias ventas. El 25 de septiembre, José Luis comunicó que probó con el Gmail real del gerente la recepción del enlace de recuperación, el cambio de contraseña y un nuevo inicio de sesión. Esta validación de extremo a extremo fue realizada y reportada por el usuario; la nueva clave no se guarda en el proyecto.

## Destino Supabase

- Proyecto autorizado: **Ferretería**.
- Enlace: https://supabase.com/dashboard/project/lapzymfujekspcssruvn
- Referencia verificada mediante el conector: `lapzymfujekspcssruvn`, nombre `Ferreteria`, estado `ACTIVE_HEALTHY`.
- El usuario reconectó Supabase y se confirmó el acceso correcto. LifeTrack es un proyecto separado.
- No usar LifeTrack ni los otros proyectos.
- El usuario autorizó eliminar las tablas del proyecto anterior dentro de Ferretería. Se verificó la identidad y se inventariaron dependencias antes de la limpieza. No se eliminaron esquemas internos de Supabase ni las cuentas Auth antiguas.
- El conteo exacto corrigió el resumen inicial: 3 equipos, 11 perfiles y 27 solicitudes. Copia previa en `.artifacts/legacy-backup.json`, excluida de Git.
- Limpieza autorizada ya ejecutada: tablas `teams`, `profiles`, `early_requests`; sus dos vistas, disparador de alta de usuarios, función y enums. Usuarios Auth anteriores preservados, sin perfiles en el nuevo sistema.
- Migración remota `20260922033553` / `ferreteria_initial_schema` aplicada. Siete tablas en el esquema privado `ferreteria`, RLS habilitado y forzado, categorías iniciales y rol limitado `ferreteria_api` con login y sin BYPASSRLS.
- SQL conservado en `backend/migrations/sql/0001_initial.sql`. No repetir la limpieza.
- La conexión directa requiere IPv6 no disponible en esta máquina; se configuró el session pooler IPv4 del proyecto. La contraseña local permanece en `backend/.env`, fuera de Git.
- Dos cuentas ficticias de demostración (gerente y vendedor) creadas en Auth y perfiles del nuevo sistema; credenciales en `.artifacts/demo-accounts.json`, fuera de Git.
- Revisiones locales Alembic y prueba Auth → FastAPI → PostgreSQL aprobadas. Interfaz de inicio/cierre de sesión comprobada en navegador.

## Siguientes etapas

7. Base de datos, migraciones, autenticación y permisos: implementado y verificado.
8. Productos e inventario conectados: implementado y comprobado en navegador.
9. Venta transaccional e historiales: implementado y comprobado en navegador y API.
10. Pruebas de permisos, concurrencia, idempotencia y persistencia.
11. Entrega reproducible.
12. Ensayo de demostración.

El usuario autorizó avanzar hasta una demostración clara para el domingo. Consultar `docs/paso-9.md` para el guion.
