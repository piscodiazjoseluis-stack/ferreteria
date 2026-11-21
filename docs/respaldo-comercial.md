# Respaldo comercial cifrado

El flujo `backup-business.yml` exporta exclusivamente el esquema comercial ferreteria con una identidad SQL dedicada de solo lectura. No copia contraseñas ni sesiones de Supabase Auth. La copia usa una transacción de lectura repetible para que las tablas correspondan a un mismo estado.

Los datos se comprimen en memoria, se cifran con AES-256-GCM y la clave de esa copia se envuelve con RSA-OAEP SHA-256. Solo la clave pública se guarda en GitHub. La clave privada de recuperación queda con el titular, fuera del repositorio y de los ZIP académicos.

La programación propuesta es diaria a las 08:17 UTC (03:17 en Lima/Bogotá). GitHub puede retrasar tareas programadas. Los archivos cifrados tienen retención de 7 días; cada copia está limitada a 10 MB para controlar almacenamiento. Los runners estándar son gratuitos para este repositorio público; los artefactos usan la cuota de almacenamiento compartida de la cuenta. No se contrataron planes ni se modificó facturación.

El flujo exige la variable de repositorio `FERRETERIA_BACKUP_ENABLED=true`. Sin ella, el trabajo se omite. La conexión de solo lectura se mantiene como secreto cifrado `BACKUP_DATABASE_URL`. Ninguna clave privada de recuperación se envía al runner.

## Verificación

La exportación con el rol real de respaldo funcionó y se comprobó que no puede escribir. El cifrado y el descifrado locales funcionaron. Se restauraron 22 tablas en una base PostgreSQL local nueva con todas las migraciones; se verificaron conteos, ledger y secuencias. Los usuarios Auth se representaron por UUID, no por contraseñas.

La primera ejecución manual del flujo remoto fue bloqueada por la revisión automática con el mensaje `blocked by policy`, sin razón detallada. No se considera aprobada su ejecución en GitHub hasta contar con el resultado del flujo. La variable de habilitación evita ejecutar la programación mientras esa autorización esté pendiente.

## Recuperación

Descargar el archivo `.enc` desde la ejecución de Actions y conservar la clave privada en otra ubicación segura. Instalar `backend/scripts/backup_requirements.txt`. Para un ensayo exclusivamente local con PostgreSQL en 127.0.0.1:55432:

```powershell
python backend/scripts/restore_encrypted_local.py ruta/copia.enc ruta/clave_privada.pem
```

El script crea una base nueva y se niega a sobrescribir otra existente. Deshabilita disparadores de usuario solo durante la importación en esa base nueva, conserva datos históricos, vuelve a habilitarlos y ajusta secuencias. La operación real de recuperación también necesita administrar las identidades Auth con el proveedor; el respaldo comercial no sustituye la gestión de Auth ni un plan de continuidad completo.
