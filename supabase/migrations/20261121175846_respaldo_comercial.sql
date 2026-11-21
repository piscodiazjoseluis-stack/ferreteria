-- Dedicated read-only identity for encrypted business backups. No password in history.
CREATE ROLE ferreteria_backup NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA ferreteria TO ferreteria_backup;
DO $$ DECLARE t text; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='ferreteria' LOOP
  EXECUTE format('GRANT SELECT ON ferreteria.%I TO ferreteria_backup',t);
  EXECUTE format('CREATE POLICY respaldo_lectura ON ferreteria.%I FOR SELECT TO ferreteria_backup USING (true)',t);
 END LOOP;
END $$;
