-- Ferreteria only: legacy cleanup explicitly authorized by the owner.
-- Backup: .artifacts/legacy-backup.json. No CASCADE: unexpected dependencies abort.
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();
DROP VIEW IF EXISTS public.vw_rotation_check;
DROP VIEW IF EXISTS public.vw_dashboard_requests;
DROP TABLE public.early_requests;
DROP TABLE public.profiles;
DROP TABLE public.teams;
DROP TYPE public.request_status;
DROP TYPE public.user_role;

CREATE SCHEMA ferreteria;
REVOKE ALL ON SCHEMA ferreteria FROM PUBLIC, anon, authenticated;
CREATE ROLE ferreteria_api NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA ferreteria TO ferreteria_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA ferreteria REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA ferreteria REVOKE ALL ON TABLES FROM anon, authenticated;

CREATE TABLE ferreteria.perfiles (
 id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
 nombre text NOT NULL CHECK (length(btrim(nombre)) BETWEEN 1 AND 120),
 rol text NOT NULL CHECK (rol IN ('gerente','vendedor')),
 activo boolean NOT NULL DEFAULT true,
 creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ferreteria.categorias (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 nombre text NOT NULL CHECK (length(btrim(nombre)) BETWEEN 1 AND 100),
 activo boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX categorias_nombre_unique ON ferreteria.categorias (lower(btrim(nombre)));
CREATE TABLE ferreteria.productos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 codigo text NOT NULL UNIQUE CHECK (codigo = upper(btrim(codigo)) AND length(codigo) BETWEEN 1 AND 40),
 nombre text NOT NULL CHECK (length(btrim(nombre)) BETWEEN 1 AND 160),
 categoria_id uuid NOT NULL REFERENCES ferreteria.categorias(id),
 unidad_venta text NOT NULL CHECK (unidad_venta IN ('unidad','caja','bolsa','paquete','galon','balde')),
 precio_venta numeric(12,2) NOT NULL CHECK (precio_venta > 0 AND precio_venta <> 'NaN'::numeric),
 stock_minimo integer NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
 activo boolean NOT NULL DEFAULT true,
 creado_en timestamptz NOT NULL DEFAULT now(),
 actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX productos_categoria_idx ON ferreteria.productos(categoria_id);
CREATE TABLE ferreteria.existencias (
 producto_id uuid PRIMARY KEY REFERENCES ferreteria.productos(id),
 cantidad integer NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
 actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ferreteria.ventas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 numero bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
 usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 fecha timestamptz NOT NULL DEFAULT now(),
 metodo_pago text NOT NULL CHECK (metodo_pago IN ('efectivo','yape','plin','transferencia','tarjeta')),
 total numeric(12,2) NOT NULL CHECK (total > 0 AND total <> 'NaN'::numeric),
 clave_idempotencia uuid NOT NULL UNIQUE,
 huella_solicitud text NOT NULL CHECK (huella_solicitud ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ventas_fecha_idx ON ferreteria.ventas(fecha DESC);
CREATE INDEX ventas_usuario_idx ON ferreteria.ventas(usuario_id);
CREATE TABLE ferreteria.detalle_venta (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 venta_id uuid NOT NULL REFERENCES ferreteria.ventas(id),
 producto_id uuid NOT NULL REFERENCES ferreteria.productos(id),
 codigo_producto text NOT NULL CHECK (length(btrim(codigo_producto)) > 0),
 nombre_producto text NOT NULL CHECK (length(btrim(nombre_producto)) > 0),
 unidad_venta text NOT NULL,
 cantidad integer NOT NULL CHECK (cantidad > 0),
 precio_unitario numeric(12,2) NOT NULL CHECK (precio_unitario > 0 AND precio_unitario <> 'NaN'::numeric),
 subtotal numeric(12,2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
 UNIQUE (venta_id,producto_id)
);
CREATE INDEX detalle_producto_idx ON ferreteria.detalle_venta(producto_id);
CREATE TABLE ferreteria.movimientos_inventario (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 producto_id uuid NOT NULL REFERENCES ferreteria.productos(id),
 tipo text NOT NULL CHECK (tipo IN ('saldo_inicial','entrada','ajuste','venta')),
 variacion integer NOT NULL CHECK (variacion <> 0),
 stock_anterior integer NOT NULL CHECK (stock_anterior >= 0),
 stock_resultante integer NOT NULL CHECK (stock_resultante >= 0),
 motivo text NOT NULL CHECK (length(btrim(motivo)) BETWEEN 1 AND 500),
 usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 fecha timestamptz NOT NULL DEFAULT now(),
 detalle_venta_id uuid UNIQUE REFERENCES ferreteria.detalle_venta(id),
 CHECK (stock_resultante::bigint = stock_anterior::bigint + variacion::bigint),
 CHECK ((tipo IN ('saldo_inicial','entrada') AND variacion > 0 AND detalle_venta_id IS NULL)
     OR (tipo = 'ajuste' AND detalle_venta_id IS NULL)
     OR (tipo = 'venta' AND variacion < 0 AND detalle_venta_id IS NOT NULL)),
 CHECK (tipo <> 'saldo_inicial' OR stock_anterior=0)
);
CREATE INDEX movimientos_producto_fecha_idx ON ferreteria.movimientos_inventario(producto_id,fecha DESC);
CREATE INDEX movimientos_usuario_idx ON ferreteria.movimientos_inventario(usuario_id);
CREATE UNIQUE INDEX un_saldo_inicial_por_producto ON ferreteria.movimientos_inventario(producto_id) WHERE tipo='saldo_inicial';

-- Identity is set transaction-locally by FastAPI after Supabase verifies the token.
CREATE FUNCTION ferreteria.usuario_actual() RETURNS uuid LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path = '' AS $$ SELECT nullif(current_setting('app.user_id',true),'')::uuid $$;
CREATE FUNCTION ferreteria.rol_actual() RETURNS text LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path = '' AS $$
 SELECT rol FROM ferreteria.perfiles WHERE id=ferreteria.usuario_actual() AND activo
 $$;
REVOKE ALL ON FUNCTION ferreteria.usuario_actual(), ferreteria.rol_actual() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ferreteria.usuario_actual(), ferreteria.rol_actual() TO ferreteria_api;

ALTER TABLE ferreteria.perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ferreteria.perfiles FORCE ROW LEVEL SECURITY;
CREATE POLICY perfil_propio ON ferreteria.perfiles FOR SELECT TO ferreteria_api USING (id=(SELECT ferreteria.usuario_actual()));
GRANT SELECT ON ferreteria.perfiles TO ferreteria_api;

DO $$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY['categorias','productos','existencias','ventas','detalle_venta','movimientos_inventario'] LOOP
  EXECUTE format('ALTER TABLE ferreteria.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE ferreteria.%I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY lectura_personal ON ferreteria.%I FOR SELECT TO ferreteria_api USING ((SELECT ferreteria.rol_actual()) IN (''gerente'',''vendedor''))',t);
  EXECUTE format('GRANT SELECT ON ferreteria.%I TO ferreteria_api',t);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['categorias','productos'] LOOP
  EXECUTE format('CREATE POLICY alta_gerente ON ferreteria.%I FOR INSERT TO ferreteria_api WITH CHECK ((SELECT ferreteria.rol_actual())=''gerente'')',t);
  EXECUTE format('CREATE POLICY cambio_gerente ON ferreteria.%I FOR UPDATE TO ferreteria_api USING ((SELECT ferreteria.rol_actual())=''gerente'') WITH CHECK ((SELECT ferreteria.rol_actual())=''gerente'')',t);
  EXECUTE format('GRANT INSERT, UPDATE ON ferreteria.%I TO ferreteria_api',t);
 END LOOP;
END $$;
CREATE POLICY alta_existencias ON ferreteria.existencias FOR INSERT TO ferreteria_api WITH CHECK ((SELECT ferreteria.rol_actual())='gerente');
CREATE POLICY cambio_existencias ON ferreteria.existencias FOR UPDATE TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor'))
 WITH CHECK ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor'));
GRANT INSERT, UPDATE ON ferreteria.existencias TO ferreteria_api;
CREATE POLICY alta_venta ON ferreteria.ventas FOR INSERT TO ferreteria_api
 WITH CHECK (usuario_id=(SELECT ferreteria.usuario_actual()) AND (SELECT ferreteria.rol_actual()) IN ('gerente','vendedor'));
CREATE POLICY alta_detalle ON ferreteria.detalle_venta FOR INSERT TO ferreteria_api
 WITH CHECK (EXISTS (SELECT 1 FROM ferreteria.ventas v WHERE v.id=venta_id AND v.usuario_id=(SELECT ferreteria.usuario_actual())));
CREATE POLICY alta_movimiento ON ferreteria.movimientos_inventario FOR INSERT TO ferreteria_api
 WITH CHECK (usuario_id=(SELECT ferreteria.usuario_actual()) AND
 ((SELECT ferreteria.rol_actual())='gerente' OR
 ((SELECT ferreteria.rol_actual())='vendedor' AND tipo='venta' AND EXISTS
 (SELECT 1 FROM ferreteria.detalle_venta d JOIN ferreteria.ventas v ON v.id=d.venta_id WHERE d.id=detalle_venta_id AND v.usuario_id=(SELECT ferreteria.usuario_actual())))));
GRANT INSERT ON ferreteria.ventas,ferreteria.detalle_venta,ferreteria.movimientos_inventario TO ferreteria_api;
GRANT USAGE ON SEQUENCE ferreteria.ventas_numero_seq TO ferreteria_api;

CREATE FUNCTION ferreteria.proteger_historial() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN RAISE EXCEPTION 'El historial confirmado no se puede modificar ni eliminar'; END $$;
CREATE TRIGGER ventas_inmutables BEFORE UPDATE OR DELETE ON ferreteria.ventas FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial();
CREATE TRIGGER detalles_inmutables BEFORE UPDATE OR DELETE ON ferreteria.detalle_venta FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial();
CREATE TRIGGER movimientos_inmutables BEFORE UPDATE OR DELETE ON ferreteria.movimientos_inventario FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial();
CREATE FUNCTION ferreteria.actualizar_producto() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF OLD.unidad_venta<>NEW.unidad_venta AND EXISTS(SELECT 1 FROM ferreteria.movimientos_inventario WHERE producto_id=OLD.id) THEN
  RAISE EXCEPTION 'La unidad de un producto con movimientos no puede cambiar';
 END IF;
 NEW.actualizado_en=now(); RETURN NEW;
END $$;
CREATE TRIGGER producto_actualizado BEFORE UPDATE ON ferreteria.productos FOR EACH ROW EXECUTE FUNCTION ferreteria.actualizar_producto();

REVOKE ALL ON ALL TABLES IN SCHEMA ferreteria FROM PUBLIC,anon,authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA ferreteria FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION ferreteria.proteger_historial(), ferreteria.actualizar_producto() FROM PUBLIC,anon,authenticated;
INSERT INTO ferreteria.categorias(nombre) VALUES ('Herramientas'),('Pinturas'),('Electricidad'),('Gasfitería'),('Materiales de construcción');
