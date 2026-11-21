DROP POLICY alta_movimiento ON ferreteria.movimientos_inventario;
-- Additive final release. Apply as administrator in a single transaction after backup.
ALTER TABLE ferreteria.perfiles DROP CONSTRAINT perfiles_rol_check;
ALTER TABLE ferreteria.perfiles ADD CHECK (rol IN ('gerente','vendedor','almacenero','cajero'));
ALTER TABLE ferreteria.productos DROP CONSTRAINT productos_unidad_venta_check;
ALTER TABLE ferreteria.productos ADD CHECK (unidad_venta IN ('unidad','caja','bolsa','paquete','galon','balde','ml','g','litro','kg'));
ALTER TABLE ferreteria.productos ADD COLUMN marca text NOT NULL DEFAULT '' CHECK(length(marca)<=100),
 ADD COLUMN foto text NOT NULL DEFAULT '' CHECK(length(foto)<=280000),
 ADD COLUMN costo_unitario numeric(16,4) NOT NULL DEFAULT 0 CHECK(costo_unitario>=0 AND costo_unitario<>'NaN'::numeric),
 ADD COLUMN tipo text NOT NULL DEFAULT 'mercaderia' CHECK(tipo IN ('mercaderia','insumo','preparado'));
ALTER TABLE ferreteria.productos ALTER COLUMN stock_minimo TYPE numeric(16,3), ALTER COLUMN stock_objetivo TYPE numeric(16,3);
ALTER TABLE ferreteria.existencias ALTER COLUMN cantidad TYPE numeric(16,3);
-- Remove integer truncation from the ledger equation before supporting fractional input.
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT conname FROM pg_constraint WHERE conrelid='ferreteria.movimientos_inventario'::regclass AND contype='c'
 AND (pg_get_constraintdef(oid) LIKE '%bigint%' OR conname IN ('movimientos_inventario_tipo_check','movimientos_inventario_origen_check')) LOOP
 EXECUTE format('ALTER TABLE ferreteria.movimientos_inventario DROP CONSTRAINT %I',r.conname); END LOOP;
END $$;
ALTER TABLE ferreteria.movimientos_inventario ALTER COLUMN variacion TYPE numeric(16,3),
 ALTER COLUMN stock_anterior TYPE numeric(16,3), ALTER COLUMN stock_resultante TYPE numeric(16,3);
ALTER TABLE ferreteria.movimientos_inventario ADD CHECK(stock_resultante=stock_anterior+variacion),
 ADD CHECK(tipo IN ('saldo_inicial','entrada','ajuste','venta','compra','matizado','preparacion','anulacion'));
ALTER TABLE ferreteria.detalle_venta DROP COLUMN subtotal;
ALTER TABLE ferreteria.detalle_venta ALTER COLUMN cantidad TYPE numeric(16,3);
ALTER TABLE ferreteria.detalle_venta ADD COLUMN subtotal numeric(12,2) GENERATED ALWAYS AS (round(cantidad*precio_unitario,2)) STORED;
ALTER TABLE ferreteria.detalle_compra DROP COLUMN subtotal;
ALTER TABLE ferreteria.detalle_compra ALTER COLUMN cantidad TYPE numeric(16,3);
ALTER TABLE ferreteria.detalle_compra ADD COLUMN subtotal numeric(12,2) GENERATED ALWAYS AS (round(cantidad*costo_unitario,2)) STORED;
ALTER TABLE ferreteria.detalle_recepcion ALTER COLUMN cantidad TYPE numeric(16,3);
ALTER TABLE ferreteria.proveedores ADD COLUMN condiciones_pago text NOT NULL DEFAULT '' CHECK(length(condiciones_pago)<=250);

CREATE TABLE ferreteria.clientes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),nombre text NOT NULL CHECK(length(btrim(nombre)) BETWEEN 2 AND 160),
 documento text NOT NULL UNIQUE CHECK(length(documento) BETWEEN 5 AND 20),
 segmento text NOT NULL CHECK(segmento IN ('publico','maestro','empresa')),
 contacto text NOT NULL DEFAULT '' CHECK(length(contacto)<=160), direccion text NOT NULL DEFAULT '' CHECK(length(direccion)<=250),
 limite_credito numeric(12,2) NOT NULL DEFAULT 0 CHECK(limite_credito>=0 AND limite_credito<>'NaN'::numeric),
 activo boolean NOT NULL DEFAULT true, creado_en timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE ferreteria.ventas ADD COLUMN cliente_id uuid REFERENCES ferreteria.clientes(id),
 ADD COLUMN cliente_nombre text NOT NULL DEFAULT '', ADD COLUMN condicion text NOT NULL DEFAULT 'contado' CHECK(condicion IN ('contado','credito'));
ALTER TABLE ferreteria.ventas DROP CONSTRAINT ventas_metodo_pago_check;
ALTER TABLE ferreteria.ventas ADD CHECK(metodo_pago IN ('efectivo','yape','plin','transferencia','tarjeta','credito')),
 ADD CHECK((condicion='credito' AND cliente_id IS NOT NULL AND metodo_pago='credito') OR (condicion='contado' AND metodo_pago<>'credito'));
CREATE TABLE ferreteria.abonos (
 id uuid PRIMARY KEY,venta_id uuid NOT NULL REFERENCES ferreteria.ventas(id),importe numeric(12,2) NOT NULL CHECK(importe>0 AND importe<>'NaN'::numeric),
 metodo_pago text NOT NULL CHECK(metodo_pago IN ('efectivo','yape','plin','transferencia','tarjeta')),
 usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),usuario_nombre text NOT NULL,fecha timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ferreteria.anulaciones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),venta_id uuid NOT NULL UNIQUE REFERENCES ferreteria.ventas(id),
 motivo text NOT NULL CHECK(length(btrim(motivo)) BETWEEN 3 AND 500),usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 usuario_nombre text NOT NULL,fecha timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ferreteria.formulas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),codigo text NOT NULL UNIQUE CHECK(length(codigo) BETWEEN 1 AND 40),
 tono text NOT NULL CHECK(length(btrim(tono)) BETWEEN 2 AND 160),referencia text NOT NULL DEFAULT '' CHECK(length(referencia)<=120),
 cliente_id uuid REFERENCES ferreteria.clientes(id),salida_id uuid NOT NULL REFERENCES ferreteria.productos(id),
 rendimiento numeric(16,3) NOT NULL CHECK(rendimiento>0 AND rendimiento<>'NaN'::numeric),
 margen numeric(6,2) NOT NULL DEFAULT 30 CHECK(margen BETWEEN 0 AND 500),
 foto text NOT NULL DEFAULT '' CHECK(length(foto)<=280000),notas text NOT NULL DEFAULT '' CHECK(length(notas)<=1000),
 usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ferreteria.componentes_formula (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),formula_id uuid NOT NULL REFERENCES ferreteria.formulas(id),
 producto_id uuid NOT NULL REFERENCES ferreteria.productos(id),cantidad numeric(16,3) NOT NULL CHECK(cantidad>0 AND cantidad<>'NaN'::numeric),
 funcion text NOT NULL CHECK(funcion IN ('base','colorante')), UNIQUE(formula_id,producto_id)
);
CREATE TABLE ferreteria.preparaciones (
 id uuid PRIMARY KEY,formula_id uuid NOT NULL REFERENCES ferreteria.formulas(id),
 cliente_id uuid REFERENCES ferreteria.clientes(id),salida_id uuid NOT NULL REFERENCES ferreteria.productos(id),
 cantidad numeric(16,3) NOT NULL CHECK(cantidad>0 AND cantidad<>'NaN'::numeric),
 costo numeric(12,2) NOT NULL CHECK(costo>=0),precio_sugerido numeric(12,2) NOT NULL CHECK(precio_sugerido>=0),
 detalle jsonb NOT NULL,huella text NOT NULL,usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),usuario_nombre text NOT NULL,
 reproceso_de uuid REFERENCES ferreteria.preparaciones(id),motivo text NOT NULL DEFAULT '' CHECK(length(motivo)<=500),
 fecha timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE ferreteria.movimientos_inventario ADD COLUMN preparacion_id uuid REFERENCES ferreteria.preparaciones(id),
 ADD COLUMN anulacion_id uuid REFERENCES ferreteria.anulaciones(id);
CREATE UNIQUE INDEX movimiento_preparacion_producto ON ferreteria.movimientos_inventario(preparacion_id,producto_id) WHERE preparacion_id IS NOT NULL;
CREATE UNIQUE INDEX movimiento_anulacion_producto ON ferreteria.movimientos_inventario(anulacion_id,producto_id) WHERE anulacion_id IS NOT NULL;
ALTER TABLE ferreteria.movimientos_inventario ADD CHECK(
 (tipo IN ('saldo_inicial','entrada','ajuste') AND detalle_venta_id IS NULL AND detalle_compra_id IS NULL AND preparacion_id IS NULL AND anulacion_id IS NULL) OR
 (tipo='venta' AND variacion<0 AND detalle_venta_id IS NOT NULL AND detalle_compra_id IS NULL AND preparacion_id IS NULL AND anulacion_id IS NULL) OR
 (tipo='compra' AND variacion>0 AND detalle_compra_id IS NOT NULL AND detalle_venta_id IS NULL AND preparacion_id IS NULL AND anulacion_id IS NULL) OR
 (tipo IN ('matizado','preparacion') AND preparacion_id IS NOT NULL AND detalle_venta_id IS NULL AND detalle_compra_id IS NULL AND anulacion_id IS NULL AND ((tipo='matizado' AND variacion<0) OR (tipo='preparacion' AND variacion>0))) OR
 (tipo='anulacion' AND variacion>0 AND anulacion_id IS NOT NULL AND detalle_venta_id IS NULL AND detalle_compra_id IS NULL AND preparacion_id IS NULL));
CREATE TABLE ferreteria.auditoria (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,tabla text NOT NULL,registro text NOT NULL,accion text NOT NULL,
 anterior jsonb,nuevo jsonb,usuario_id uuid,fecha timestamptz NOT NULL DEFAULT now()
);
-- Trigger has only INSERT privileges; actor comes from the API transaction, not input data.
CREATE FUNCTION ferreteria.auditar() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$ BEGIN
 INSERT INTO ferreteria.auditoria(tabla,registro,accion,anterior,nuevo,usuario_id)
 VALUES(TG_TABLE_NAME,NEW.id::text,TG_OP,CASE WHEN TG_OP='UPDATE' THEN to_jsonb(OLD)-'foto' ELSE NULL END,to_jsonb(NEW)-'foto',ferreteria.usuario_actual()); RETURN NEW;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['productos','clientes','proveedores','formulas'] LOOP
 EXECUTE format('CREATE TRIGGER auditoria_cambios AFTER INSERT OR UPDATE ON ferreteria.%I FOR EACH ROW EXECUTE FUNCTION ferreteria.auditar()',t); END LOOP;
 FOREACH t IN ARRAY ARRAY['abonos','anulaciones','preparaciones'] LOOP
 EXECUTE format('CREATE TRIGGER auditoria_operacion AFTER INSERT ON ferreteria.%I FOR EACH ROW EXECUTE FUNCTION ferreteria.auditar()',t); END LOOP;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['clientes','abonos','anulaciones','formulas','componentes_formula','preparaciones','auditoria'] LOOP
 EXECUTE format('ALTER TABLE ferreteria.%I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE ferreteria.%I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('REVOKE ALL ON ferreteria.%I FROM PUBLIC,anon,authenticated',t);
 EXECUTE format('GRANT SELECT,INSERT ON ferreteria.%I TO ferreteria_api',t);
 EXECUTE format('CREATE POLICY lectura_final ON ferreteria.%I FOR SELECT TO ferreteria_api USING ((SELECT ferreteria.rol_actual()) IN (''gerente'',''vendedor'',''cajero''))',t);
 EXECUTE format('CREATE POLICY alta_final ON ferreteria.%I FOR INSERT TO ferreteria_api WITH CHECK ((SELECT ferreteria.rol_actual()) IN (''gerente'',''vendedor'',''cajero''))',t);
 IF t NOT IN ('clientes') THEN
 EXECUTE format('CREATE TRIGGER inmutable_final BEFORE UPDATE OR DELETE ON ferreteria.%I FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial()',t); END IF;
 END LOOP;
END $$;
DROP POLICY lectura_final ON ferreteria.auditoria;
CREATE POLICY auditoria_gerente ON ferreteria.auditoria FOR SELECT TO ferreteria_api USING((SELECT ferreteria.rol_actual())='gerente');
DROP POLICY alta_final ON ferreteria.anulaciones;
CREATE POLICY anular_gerente ON ferreteria.anulaciones FOR INSERT TO ferreteria_api WITH CHECK((SELECT ferreteria.rol_actual())='gerente' AND usuario_id=ferreteria.usuario_actual());
DROP POLICY alta_final ON ferreteria.abonos;
CREATE POLICY cobrar_caja ON ferreteria.abonos FOR INSERT TO ferreteria_api WITH CHECK((SELECT ferreteria.rol_actual()) IN ('gerente','cajero') AND usuario_id=ferreteria.usuario_actual());
GRANT UPDATE ON ferreteria.clientes TO ferreteria_api;
CREATE POLICY cliente_editar ON ferreteria.clientes FOR UPDATE TO ferreteria_api USING((SELECT ferreteria.rol_actual())='gerente') WITH CHECK((SELECT ferreteria.rol_actual())='gerente');
GRANT USAGE ON SEQUENCE ferreteria.auditoria_id_seq TO ferreteria_api;
REVOKE ALL ON FUNCTION ferreteria.auditar() FROM PUBLIC,anon,authenticated;
-- Cashier follows the same business rules as management for cash; API still limits other modules.
CREATE OR REPLACE FUNCTION ferreteria.proteger_caja() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$ BEGIN
 IF OLD.estado<>'abierta' OR NEW.estado<>'cerrada' OR
 (to_jsonb(NEW)-ARRAY['estado','contado','esperado','diferencia','resumen','motivo','cerrado_por','cerrado_nombre','cerrado_en']) IS DISTINCT FROM
 (to_jsonb(OLD)-ARRAY['estado','contado','esperado','diferencia','resumen','motivo','cerrado_por','cerrado_nombre','cerrado_en']) OR
 ferreteria.rol_actual() NOT IN ('gerente','cajero') OR NEW.cerrado_por IS DISTINCT FROM ferreteria.usuario_actual() THEN
 RAISE EXCEPTION 'Cierre no autorizado'; END IF; RETURN NEW; END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['productos','categorias','existencias','ventas','detalle_venta','movimientos_inventario'] LOOP
 EXECUTE format('CREATE POLICY cajero_lectura ON ferreteria.%I FOR SELECT TO ferreteria_api USING (ferreteria.rol_actual()=''cajero'')',t); END LOOP;
END $$;
CREATE POLICY cajero_stock ON ferreteria.existencias FOR UPDATE TO ferreteria_api USING(ferreteria.rol_actual()='cajero') WITH CHECK(ferreteria.rol_actual()='cajero');
CREATE POLICY cajero_venta ON ferreteria.ventas FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual()='cajero' AND usuario_id=ferreteria.usuario_actual());
CREATE POLICY cajero_movimiento ON ferreteria.movimientos_inventario FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual()='cajero' AND tipo='venta' AND usuario_id=ferreteria.usuario_actual());
-- Explicit policies for cash operations and ledger consumption by matizado.
CREATE POLICY cajero_caja_select ON ferreteria.cajas FOR SELECT TO ferreteria_api USING(ferreteria.rol_actual()='cajero');
CREATE POLICY cajero_caja_insert ON ferreteria.cajas FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual()='cajero' AND abierto_por=ferreteria.usuario_actual());
CREATE POLICY cajero_caja_update ON ferreteria.cajas FOR UPDATE TO ferreteria_api USING(ferreteria.rol_actual()='cajero') WITH CHECK(ferreteria.rol_actual()='cajero');
CREATE POLICY cajero_movimiento_select ON ferreteria.movimientos_caja FOR SELECT TO ferreteria_api USING(ferreteria.rol_actual()='cajero');
CREATE POLICY cajero_movimiento_insert ON ferreteria.movimientos_caja FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual()='cajero' AND usuario_id=ferreteria.usuario_actual() AND EXISTS(SELECT 1 FROM ferreteria.cajas WHERE id=caja_id AND estado='abierta'));
CREATE POLICY matizado_movimiento ON ferreteria.movimientos_inventario FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual() IN ('gerente','vendedor') AND usuario_id=ferreteria.usuario_actual() AND tipo IN ('matizado','preparacion') AND EXISTS(SELECT 1 FROM ferreteria.preparaciones WHERE id=preparacion_id AND usuario_id=ferreteria.usuario_actual()));
CREATE ROLE ferreteria_public NOLOGIN NOINHERIT NOBYPASSRLS;
GRANT ferreteria_public TO ferreteria_api;
GRANT USAGE ON SCHEMA ferreteria TO ferreteria_public;
GRANT SELECT(id,codigo,nombre,categoria_id,unidad_venta,precio_venta,marca,foto,activo,tipo) ON ferreteria.productos TO ferreteria_public;
GRANT SELECT ON ferreteria.categorias,ferreteria.existencias TO ferreteria_public;
CREATE POLICY catalogo_publico ON ferreteria.productos FOR SELECT TO ferreteria_public USING(activo AND tipo<>'insumo');
CREATE POLICY categorias_publicas ON ferreteria.categorias FOR SELECT TO ferreteria_public USING(activo);
CREATE POLICY stock_publico ON ferreteria.existencias FOR SELECT TO ferreteria_public USING(EXISTS(SELECT 1 FROM ferreteria.productos WHERE id=producto_id AND activo AND tipo<>'insumo'));
CREATE INDEX ventas_cliente_idx ON ferreteria.ventas(cliente_id);
CREATE INDEX abonos_venta_idx ON ferreteria.abonos(venta_id);
CREATE INDEX formulas_cliente_idx ON ferreteria.formulas(cliente_id);
CREATE INDEX formulas_salida_idx ON ferreteria.formulas(salida_id);
CREATE INDEX componentes_formula_idx ON ferreteria.componentes_formula(formula_id);
CREATE INDEX componentes_producto_idx ON ferreteria.componentes_formula(producto_id);
CREATE INDEX preparaciones_formula_idx ON ferreteria.preparaciones(formula_id);
CREATE INDEX auditoria_fecha_idx ON ferreteria.auditoria(fecha DESC);

CREATE POLICY alta_movimiento ON ferreteria.movimientos_inventario FOR INSERT TO ferreteria_api WITH CHECK (
 usuario_id=(SELECT ferreteria.usuario_actual()) AND (
   ((SELECT ferreteria.rol_actual())='gerente' AND tipo<>'compra') OR
   ((SELECT ferreteria.rol_actual())='vendedor' AND tipo='venta' AND EXISTS(SELECT 1 FROM ferreteria.detalle_venta d JOIN ferreteria.ventas v ON v.id=d.venta_id WHERE d.id=detalle_venta_id AND v.usuario_id=(SELECT ferreteria.usuario_actual()))) OR
   ((SELECT ferreteria.rol_actual())='almacenero' AND tipo='compra' AND EXISTS(
     SELECT 1 FROM ferreteria.detalle_recepcion dr JOIN ferreteria.recepciones r ON r.id=dr.recepcion_id
     JOIN ferreteria.detalle_compra d ON d.id=dr.detalle_compra_id
     WHERE dr.id=movimientos_inventario.detalle_recepcion_id AND d.id=movimientos_inventario.detalle_compra_id
       AND d.producto_id=movimientos_inventario.producto_id AND dr.cantidad=movimientos_inventario.variacion
       AND r.usuario_id=(SELECT ferreteria.usuario_actual())))));

-- Average acquisition cost after each delivery, preserving the valuation of existing stock.
-- SECURITY DEFINER is narrowly scoped to this trigger, not callable by application users.
CREATE FUNCTION ferreteria.valorar_recepcion() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE prod uuid; unit_cost numeric; stock numeric; old_cost numeric;
BEGIN
 IF ferreteria.rol_actual()<>'almacenero' THEN RAISE EXCEPTION 'Valoración no autorizada'; END IF;
 SELECT producto_id,costo_unitario INTO prod,unit_cost FROM ferreteria.detalle_compra WHERE id=NEW.detalle_compra_id;
 SELECT e.cantidad,p.costo_unitario INTO stock,old_cost FROM ferreteria.existencias e JOIN ferreteria.productos p ON p.id=e.producto_id WHERE p.id=prod FOR UPDATE OF p;
 IF stock<NEW.cantidad OR stock<=0 THEN RAISE EXCEPTION 'La recepción debe actualizar primero el stock'; END IF;
 UPDATE ferreteria.productos SET costo_unitario=round(((stock-NEW.cantidad)*old_cost+NEW.cantidad*unit_cost)/stock,4) WHERE id=prod;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION ferreteria.valorar_recepcion() FROM PUBLIC,anon,authenticated,ferreteria_api;
CREATE TRIGGER valorar_entrega AFTER INSERT ON ferreteria.detalle_recepcion FOR EACH ROW EXECUTE FUNCTION ferreteria.valorar_recepcion();

ALTER TABLE ferreteria.compras DROP CONSTRAINT compras_estado_check;
ALTER TABLE ferreteria.compras ADD CONSTRAINT compras_estado_check CHECK(estado IN ('borrador','pendiente','parcial','recibida','cancelada'));
DROP POLICY compras_alta ON ferreteria.compras;
CREATE POLICY compras_alta ON ferreteria.compras FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual()='gerente' AND creado_por=ferreteria.usuario_actual() AND estado IN ('borrador','pendiente'));
DROP POLICY detalle_compra_alta ON ferreteria.detalle_compra;
CREATE POLICY detalle_compra_alta ON ferreteria.detalle_compra FOR INSERT TO ferreteria_api WITH CHECK(ferreteria.rol_actual()='gerente' AND EXISTS(SELECT 1 FROM ferreteria.compras WHERE id=compra_id AND creado_por=ferreteria.usuario_actual() AND estado IN ('borrador','pendiente')));
CREATE OR REPLACE FUNCTION ferreteria.validar_estado_compra() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF OLD.estado NOT IN ('borrador','pendiente','parcial') OR
 (to_jsonb(OLD)-ARRAY['estado','recibido_por','recibido_nombre','recibido_en']) IS DISTINCT FROM
 (to_jsonb(NEW)-ARRAY['estado','recibido_por','recibido_nombre','recibido_en']) THEN RAISE EXCEPTION 'Pedido inmutable'; END IF;
 IF NEW.estado='pendiente' AND OLD.estado='borrador' AND ferreteria.rol_actual()='gerente' THEN RETURN NEW; END IF;
 IF NEW.estado IN ('parcial','recibida') AND OLD.estado<>'borrador' THEN
  IF ferreteria.rol_actual()<>'almacenero' THEN RAISE EXCEPTION 'Recepción no autorizada'; END IF;
  IF NEW.estado='recibida' AND (NEW.recibido_por IS DISTINCT FROM ferreteria.usuario_actual() OR NEW.recibido_nombre IS DISTINCT FROM (SELECT nombre FROM ferreteria.perfiles WHERE id=ferreteria.usuario_actual()) OR NEW.recibido_en IS NULL) THEN RAISE EXCEPTION 'Responsable no válido'; END IF;
 ELSIF NEW.estado='cancelada' AND OLD.estado IN ('borrador','pendiente') AND ferreteria.rol_actual()='gerente' AND NOT EXISTS(SELECT 1 FROM ferreteria.recepciones WHERE compra_id=OLD.id) THEN NULL;
 ELSE RAISE EXCEPTION 'Transición no permitida'; END IF;
 RETURN NEW;
END $$;
-- Index every new foreign key used for history and ownership checks.
CREATE INDEX abonos_usuario_idx ON ferreteria.abonos(usuario_id);
CREATE INDEX anulaciones_usuario_idx ON ferreteria.anulaciones(usuario_id);
CREATE INDEX formulas_usuario_idx ON ferreteria.formulas(usuario_id);
CREATE INDEX preparaciones_cliente_idx ON ferreteria.preparaciones(cliente_id);
CREATE INDEX preparaciones_salida_idx ON ferreteria.preparaciones(salida_id);
CREATE INDEX preparaciones_usuario_idx ON ferreteria.preparaciones(usuario_id);
CREATE INDEX preparaciones_reproceso_idx ON ferreteria.preparaciones(reproceso_de);
CREATE INDEX movimientos_preparacion_idx ON ferreteria.movimientos_inventario(preparacion_id);
CREATE INDEX movimientos_anulacion_idx ON ferreteria.movimientos_inventario(anulacion_id);
