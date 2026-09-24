CREATE TABLE ferreteria.alembic_version (version_num varchar(32) NOT NULL PRIMARY KEY);
REVOKE ALL ON ferreteria.alembic_version FROM PUBLIC, anon, authenticated, ferreteria_api;
ALTER TABLE ferreteria.alembic_version ENABLE ROW LEVEL SECURITY;
INSERT INTO ferreteria.alembic_version VALUES ('0001');
