-- V3: additive data structures; legacy sales and movements remain immutable.
ALTER TABLE ferreteria.ventas ADD COLUMN usuario_nombre text NOT NULL DEFAULT 'Personal autorizado';
ALTER TABLE ferreteria.movimientos_inventario ADD COLUMN usuario_nombre text NOT NULL DEFAULT 'Personal autorizado';
-- Only enrich historical attribution; do not change prices, quantities or totals.
ALTER TABLE ferreteria.ventas DISABLE TRIGGER ventas_inmutables;
UPDATE ferreteria.ventas v SET usuario_nombre=p.nombre FROM ferreteria.perfiles p WHERE p.id=v.usuario_id;
ALTER TABLE ferreteria.ventas ENABLE TRIGGER ventas_inmutables;
ALTER TABLE ferreteria.movimientos_inventario DISABLE TRIGGER movimientos_inmutables;
UPDATE ferreteria.movimientos_inventario m SET usuario_nombre=p.nombre FROM ferreteria.perfiles p WHERE p.id=m.usuario_id;
ALTER TABLE ferreteria.movimientos_inventario ENABLE TRIGGER movimientos_inmutables;
CREATE FUNCTION ferreteria.nombre_responsable() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 SELECT nombre INTO NEW.usuario_nombre FROM ferreteria.perfiles WHERE id=NEW.usuario_id;
 IF NEW.usuario_nombre IS NULL THEN RAISE EXCEPTION 'Responsable no encontrado'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER venta_responsable BEFORE INSERT ON ferreteria.ventas FOR EACH ROW EXECUTE FUNCTION ferreteria.nombre_responsable();
CREATE TRIGGER movimiento_responsable BEFORE INSERT ON ferreteria.movimientos_inventario FOR EACH ROW EXECUTE FUNCTION ferreteria.nombre_responsable();
REVOKE ALL ON FUNCTION ferreteria.nombre_responsable() FROM PUBLIC,anon,authenticated;
ALTER TABLE ferreteria.productos ADD COLUMN stock_objetivo integer;
UPDATE ferreteria.productos SET stock_objetivo=stock_minimo;
ALTER TABLE ferreteria.productos ALTER COLUMN stock_objetivo SET NOT NULL;
ALTER TABLE ferreteria.productos ADD CONSTRAINT objetivo_minimo CHECK (stock_objetivo>=stock_minimo);

ALTER TABLE ferreteria.compras DROP CONSTRAINT compras_estado_check;
ALTER TABLE ferreteria.compras ADD CONSTRAINT compras_estado_check CHECK (estado IN ('pendiente','parcial','recibida','cancelada'));
CREATE TABLE ferreteria.recepciones (
 id uuid PRIMARY KEY,
 compra_id uuid NOT NULL REFERENCES ferreteria.compras(id),
 usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 usuario_nombre text NOT NULL,
 fecha timestamptz NOT NULL DEFAULT now(),
 huella text NOT NULL
);
CREATE INDEX recepciones_compra_idx ON ferreteria.recepciones(compra_id);
CREATE INDEX recepciones_usuario_idx ON ferreteria.recepciones(usuario_id);
CREATE TABLE ferreteria.detalle_recepcion (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 recepcion_id uuid NOT NULL REFERENCES ferreteria.recepciones(id),
 detalle_compra_id uuid NOT NULL REFERENCES ferreteria.detalle_compra(id),
 cantidad integer NOT NULL CHECK (cantidad>0),
 UNIQUE(recepcion_id,detalle_compra_id)
);
CREATE INDEX detalle_recepcion_compra_idx ON ferreteria.detalle_recepcion(detalle_compra_id);
-- Represent already completed V2 deliveries without replaying stock changes.
INSERT INTO ferreteria.recepciones(id,compra_id,usuario_id,usuario_nombre,fecha,huella)
 SELECT gen_random_uuid(),id,recibido_por,recibido_nombre,recibido_en,'legacy-v2'
 FROM ferreteria.compras WHERE estado='recibida';
INSERT INTO ferreteria.detalle_recepcion(recepcion_id,detalle_compra_id,cantidad)
 SELECT r.id,d.id,d.cantidad FROM ferreteria.recepciones r
 JOIN ferreteria.detalle_compra d ON d.compra_id=r.compra_id;
ALTER TABLE ferreteria.movimientos_inventario DROP CONSTRAINT movimientos_inventario_detalle_compra_id_key;
ALTER TABLE ferreteria.movimientos_inventario ADD COLUMN detalle_recepcion_id uuid UNIQUE REFERENCES ferreteria.detalle_recepcion(id);

CREATE OR REPLACE FUNCTION ferreteria.validar_estado_compra() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF OLD.estado NOT IN ('pendiente','parcial') OR
   (to_jsonb(OLD)-ARRAY['estado','recibido_por','recibido_nombre','recibido_en']) IS DISTINCT FROM
   (to_jsonb(NEW)-ARRAY['estado','recibido_por','recibido_nombre','recibido_en']) THEN
   RAISE EXCEPTION 'El pedido confirmado no se puede editar';
 END IF;
 IF NEW.estado IN ('parcial','recibida') THEN
   IF ferreteria.rol_actual()<>'almacenero' THEN RAISE EXCEPTION 'Recepción no autorizada'; END IF;
   IF NEW.estado='recibida' AND (NEW.recibido_por IS DISTINCT FROM ferreteria.usuario_actual() OR
      NEW.recibido_nombre IS DISTINCT FROM (SELECT nombre FROM ferreteria.perfiles WHERE id=ferreteria.usuario_actual()) OR NEW.recibido_en IS NULL) THEN
     RAISE EXCEPTION 'Responsable de recepción no válido';
   END IF;
 ELSIF NEW.estado='cancelada' THEN
   IF OLD.estado<>'pendiente' OR ferreteria.rol_actual()<>'gerente' OR EXISTS(SELECT 1 FROM ferreteria.recepciones WHERE compra_id=OLD.id) THEN
     RAISE EXCEPTION 'Solo se cancela un pedido sin entregas';
   END IF;
 ELSE RAISE EXCEPTION 'Transición no permitida'; END IF;
 RETURN NEW;
END $$;

CREATE TABLE ferreteria.cajas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 fecha date NOT NULL UNIQUE,
 fondo numeric(12,2) NOT NULL CHECK(fondo>=0 AND fondo<>'NaN'::numeric),
 abierto_por uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 abierto_nombre text NOT NULL,
 abierto_en timestamptz NOT NULL DEFAULT now(),
 estado text NOT NULL DEFAULT 'abierta' CHECK(estado IN ('abierta','cerrada')),
 contado numeric(12,2),
 esperado numeric(12,2),
 diferencia numeric(12,2),
 resumen jsonb,
 motivo text NOT NULL DEFAULT '',
 cerrado_por uuid REFERENCES ferreteria.perfiles(id),
 cerrado_nombre text,
 cerrado_en timestamptz,
 CHECK ((estado='abierta' AND cerrado_en IS NULL AND contado IS NULL AND esperado IS NULL AND diferencia IS NULL AND resumen IS NULL)
   OR (estado='cerrada' AND cerrado_en IS NOT NULL AND cerrado_por IS NOT NULL AND contado>=0
       AND esperado>=0 AND diferencia=contado-esperado AND resumen IS NOT NULL))
);
CREATE INDEX cajas_abierto_por_idx ON ferreteria.cajas(abierto_por);
CREATE INDEX cajas_cerrado_por_idx ON ferreteria.cajas(cerrado_por) WHERE cerrado_por IS NOT NULL;
CREATE TABLE ferreteria.movimientos_caja (
 id uuid PRIMARY KEY,
 caja_id uuid NOT NULL REFERENCES ferreteria.cajas(id),
 tipo text NOT NULL CHECK(tipo IN ('ingreso','retiro')),
 importe numeric(12,2) NOT NULL CHECK(importe>0 AND importe<>'NaN'::numeric),
 motivo text NOT NULL CHECK(length(btrim(motivo)) BETWEEN 3 AND 500),
 usuario_id uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 usuario_nombre text NOT NULL,
 fecha timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX movimientos_caja_caja_idx ON ferreteria.movimientos_caja(caja_id);
CREATE INDEX movimientos_caja_usuario_idx ON ferreteria.movimientos_caja(usuario_id);
CREATE FUNCTION ferreteria.proteger_caja() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF OLD.estado<>'abierta' OR NEW.estado<>'cerrada' OR
    NEW.fecha<>OLD.fecha OR NEW.fondo<>OLD.fondo OR NEW.id<>OLD.id OR
    NEW.abierto_por<>OLD.abierto_por OR NEW.abierto_nombre<>OLD.abierto_nombre OR NEW.abierto_en<>OLD.abierto_en OR
    ferreteria.rol_actual()<>'gerente' OR NEW.cerrado_por IS DISTINCT FROM ferreteria.usuario_actual() THEN
   RAISE EXCEPTION 'El cierre de caja no se puede modificar';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER caja_cierre_controlado BEFORE UPDATE ON ferreteria.cajas FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_caja();
CREATE TRIGGER caja_sin_borrado BEFORE DELETE ON ferreteria.cajas FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial();

DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['recepciones','detalle_recepcion','cajas','movimientos_caja'] LOOP
   EXECUTE format('ALTER TABLE ferreteria.%I ENABLE ROW LEVEL SECURITY',t);
   EXECUTE format('ALTER TABLE ferreteria.%I FORCE ROW LEVEL SECURITY',t);
   EXECUTE format('REVOKE ALL ON ferreteria.%I FROM PUBLIC,anon,authenticated',t);
   EXECUTE format('GRANT SELECT,INSERT ON ferreteria.%I TO ferreteria_api',t);
   IF t<>'cajas' THEN
     EXECUTE format('CREATE TRIGGER historial_inmutable BEFORE UPDATE OR DELETE ON ferreteria.%I FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial()',t);
   END IF;
 END LOOP;
END $$;
CREATE POLICY recepciones_lectura ON ferreteria.recepciones FOR SELECT TO ferreteria_api USING ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'));
CREATE POLICY recepciones_alta ON ferreteria.recepciones FOR INSERT TO ferreteria_api WITH CHECK ((SELECT ferreteria.rol_actual())='almacenero' AND usuario_id=(SELECT ferreteria.usuario_actual()));
CREATE POLICY detalle_recepcion_lectura ON ferreteria.detalle_recepcion FOR SELECT TO ferreteria_api USING ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'));
CREATE POLICY detalle_recepcion_alta ON ferreteria.detalle_recepcion FOR INSERT TO ferreteria_api WITH CHECK (
 (SELECT ferreteria.rol_actual())='almacenero' AND EXISTS (SELECT 1 FROM ferreteria.recepciones r JOIN ferreteria.detalle_compra d ON d.compra_id=r.compra_id
 WHERE r.id=recepcion_id AND d.id=detalle_compra_id AND r.usuario_id=(SELECT ferreteria.usuario_actual())));
CREATE POLICY cajas_lectura ON ferreteria.cajas FOR SELECT TO ferreteria_api USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor'));
CREATE POLICY cajas_alta ON ferreteria.cajas FOR INSERT TO ferreteria_api WITH CHECK ((SELECT ferreteria.rol_actual())='gerente' AND abierto_por=(SELECT ferreteria.usuario_actual()) AND estado='abierta');
CREATE POLICY cajas_cierre ON ferreteria.cajas FOR UPDATE TO ferreteria_api USING ((SELECT ferreteria.rol_actual())='gerente') WITH CHECK ((SELECT ferreteria.rol_actual())='gerente');
GRANT UPDATE ON ferreteria.cajas TO ferreteria_api;
CREATE POLICY movimientos_caja_lectura ON ferreteria.movimientos_caja FOR SELECT TO ferreteria_api USING ((SELECT ferreteria.rol_actual())='gerente');
CREATE POLICY movimientos_caja_alta ON ferreteria.movimientos_caja FOR INSERT TO ferreteria_api WITH CHECK ((SELECT ferreteria.rol_actual())='gerente' AND usuario_id=(SELECT ferreteria.usuario_actual()) AND EXISTS(SELECT 1 FROM ferreteria.cajas c WHERE c.id=caja_id AND c.estado='abierta'));

DROP POLICY alta_movimiento ON ferreteria.movimientos_inventario;
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
REVOKE ALL ON FUNCTION ferreteria.proteger_caja() FROM PUBLIC,anon,authenticated;
