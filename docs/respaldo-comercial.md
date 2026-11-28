# Respaldo comercial cifrado

El flujo `backup-business.yml` exporta exclusivamente el esquema comercial ferreteria con una identidad SQL dedicada de solo lectura. No copia contraseñas ni sesiones de Supabase Auth. La copia usa una transacción de lectura repetible para que las tablas correspondan a un mismo estado.

Los datos se comprimen en memoria, se cifran con AES-256-GCM y la clave de esa copia se envuelve con RSA-OAEP SHA-256. Solo la clave pública se guarda en GitHub. La clave privada de recuperación queda con el titular, fuera del repositorio y de los ZIP académicos.

La programación está habilitada diariamente a las 08:17 UTC (03:17 en Lima/Bogotá). GitHub puede retrasar tareas programadas. Los archivos cifrados tienen retención de 7 días; cada copia está limitada a 10 MB para controlar almacenamiento. Los runners estándar son gratuitos para este repositorio público; los artefactos usan la cuota de almacenamiento compartida de la cuenta. No se contrataron planes ni se modificó facturación. El proyecto Supabase debe estar activo para aceptar la conexión.

El flujo exige la variable de repositorio `FERRETERIA_BACKUP_ENABLED=true`. Sin ella, el trabajo se omite. La conexión de solo lectura se mantiene como secreto cifrado `BACKUP_DATABASE_URL`. Ninguna clave privada de recuperación se envía al runner.

## Verificación

La exportación con el rol real de respaldo funcionó y se comprobó que no puede escribir. El cifrado y el descifrado locales funcionaron. Se restauraron 22 tablas en una base PostgreSQL local nueva con todas las migraciones; se verificaron conteos, ledger y secuencias. Los usuarios Auth se representaron por UUID, no por contraseñas.

El bloqueo inicial de revisión automática quedó superado tras la autorización del titular el 28/11/2026. Se reactivó exclusivamente el proyecto Ferretería, que estaba pausado, y se habilitó `FERRETERIA_BACKUP_ENABLED=true`. La primera ejecución generó el cifrado, pero no pudo subirlo porque `upload-artifact` omite carpetas ocultas de forma predeterminada. Se corrigió `include-hidden-files: true` conservando el patrón limitado a `.backup-output/*.enc`.

La [ejecución 46159712945](https://github.com/piscodiazjoseluis-stack/ferreteria/actions/runs/46159712945), sobre el commit `967ac02`, finalizó correctamente el 28/11/2026. Se descargó el artefacto real, se descifró localmente con la clave privada y se restauraron sus 22 tablas en una base nueva `ferreteria_restore_remote_20261128`. Coincidieron todos los conteos, las existencias y las secuencias. Una segunda lectura del origen confirmó que no cambiaron sus datos. El rol de respaldo no dispone de permisos de escritura comercial ni de acceso a Auth. La clave privada nunca se envió a GitHub.

La ejecución verificada fue manual sobre el mismo flujo que utiliza el cron. La programación diaria está habilitada; no se atribuye a esta prueba la ejecución de un evento programado futuro. El respaldo comercial remoto queda validado dentro de este alcance.

## Recuperación

Descargar el archivo `.enc` desde la ejecución de Actions y conservar la clave privada en otra ubicación segura. Instalar `backend/scripts/backup_requirements.txt`. Para un ensayo exclusivamente local con PostgreSQL en 127.0.0.1:55432:

```powershell
python backend/scripts/restore_encrypted_local.py ruta/copia.enc ruta/clave_privada.pem
```

Para repetir un ensayo sin tocar una base anterior, añade `--database ferreteria_restore_nuevo_ensayo`. El nombre debe comenzar por `ferreteria_restore_`. La conexión del ensayo continúa limitada a `127.0.0.1:55432` y tiene un tiempo máximo de conexión de 10 segundos.

El script crea una base nueva y se niega a sobrescribir otra existente. Deshabilita disparadores de usuario solo durante la importación en esa base nueva, conserva datos históricos, vuelve a habilitarlos y ajusta secuencias. La operación real de recuperación también necesita administrar las identidades Auth con el proveedor; el respaldo comercial no sustituye la gestión de Auth ni un plan de continuidad completo.
