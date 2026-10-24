-- Segunda versión: pedidos, proveedores y recepción completa en una transacción.
ALTER TABLE ferreteria.perfiles DROP CONSTRAINT perfiles_rol_check;
ALTER TABLE ferreteria.perfiles ADD CONSTRAINT perfiles_rol_check
  CHECK (rol IN ('gerente','vendedor','almacenero'));

CREATE TABLE ferreteria.proveedores (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 nombre text NOT NULL CHECK (length(btrim(nombre)) BETWEEN 2 AND 160),
 documento text CHECK (documento IS NULL OR length(btrim(documento)) BETWEEN 8 AND 20),
 telefono text CHECK (telefono IS NULL OR length(btrim(telefono)) BETWEEN 6 AND 30),
 correo text CHECK (correo IS NULL OR length(btrim(correo)) BETWEEN 5 AND 160),
 activo boolean NOT NULL DEFAULT true,
 creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX proveedores_documento_unico ON ferreteria.proveedores(documento) WHERE documento IS NOT NULL;

CREATE TABLE ferreteria.compras (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 numero bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
 proveedor_id uuid NOT NULL REFERENCES ferreteria.proveedores(id),
 creado_por uuid NOT NULL REFERENCES ferreteria.perfiles(id),
 creado_nombre text NOT NULL,
 creado_en timestamptz NOT NULL DEFAULT now(),
 estado text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','recibida','cancelada')),
 total_estimado numeric(12,2) NOT NULL CHECK (total_estimado > 0 AND total_estimado <> 'NaN'::numeric),
 observacion text NOT NULL DEFAULT '' CHECK (length(observacion) <= 500),
 recibido_por uuid REFERENCES ferreteria.perfiles(id),
 recibido_nombre text,
 recibido_en timestamptz,
 CHECK ((estado='recibida' AND recibido_por IS NOT NULL AND recibido_nombre IS NOT NULL AND recibido_en IS NOT NULL)
     OR (estado<>'recibida' AND recibido_por IS NULL AND recibido_nombre IS NULL AND recibido_en IS NULL))
);
CREATE INDEX compras_estado_fecha_idx ON ferreteria.compras(estado,creado_en DESC);

CREATE TABLE ferreteria.detalle_compra (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 compra_id uuid NOT NULL REFERENCES ferreteria.compras(id),
 producto_id uuid NOT NULL REFERENCES ferreteria.productos(id),
 codigo_producto text NOT NULL,
 nombre_producto text NOT NULL,
 cantidad integer NOT NULL CHECK (cantidad > 0),
 costo_unitario numeric(12,2) NOT NULL CHECK (costo_unitario > 0 AND costo_unitario <> 'NaN'::numeric),
 subtotal numeric(12,2) GENERATED ALWAYS AS (cantidad*costo_unitario) STORED,
 UNIQUE(compra_id,producto_id)
);
CREATE INDEX detalle_compra_producto_idx ON ferreteria.detalle_compra(producto_id);

ALTER TABLE ferreteria.movimientos_inventario
 ADD COLUMN detalle_compra_id uuid UNIQUE REFERENCES ferreteria.detalle_compra(id);
ALTER TABLE ferreteria.movimientos_inventario DROP CONSTRAINT movimientos_inventario_tipo_check;
ALTER TABLE ferreteria.movimientos_inventario ADD CONSTRAINT movimientos_inventario_tipo_check
 CHECK (tipo IN ('saldo_inicial','entrada','ajuste','venta','compra'));
ALTER TABLE ferreteria.movimientos_inventario DROP CONSTRAINT movimientos_inventario_check1;
ALTER TABLE ferreteria.movimientos_inventario ADD CONSTRAINT movimientos_inventario_origen_check CHECK (
  (tipo IN ('saldo_inicial','entrada') AND variacion>0 AND detalle_venta_id IS NULL AND detalle_compra_id IS NULL)
  OR (tipo='ajuste' AND detalle_venta_id IS NULL AND detalle_compra_id IS NULL)
  OR (tipo='venta' AND variacion<0 AND detalle_venta_id IS NOT NULL AND detalle_compra_id IS NULL)
  OR (tipo='compra' AND variacion>0 AND detalle_venta_id IS NULL AND detalle_compra_id IS NOT NULL)
);

CREATE FUNCTION ferreteria.validar_estado_compra() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF OLD.estado<>'pendiente' OR NEW.id<>OLD.id OR NEW.numero<>OLD.numero OR
    NEW.proveedor_id<>OLD.proveedor_id OR NEW.creado_por<>OLD.creado_por OR
    NEW.creado_en<>OLD.creado_en OR NEW.creado_nombre<>OLD.creado_nombre OR
    NEW.total_estimado<>OLD.total_estimado OR
    NEW.observacion<>OLD.observacion THEN
   RAISE EXCEPTION 'El pedido confirmado no se puede editar';
 END IF;
 IF NEW.estado='recibida' THEN
   IF ferreteria.rol_actual()<>'almacenero' OR
      NEW.recibido_por<>ferreteria.usuario_actual() OR
      NEW.recibido_nombre IS DISTINCT FROM (SELECT nombre FROM ferreteria.perfiles WHERE id=ferreteria.usuario_actual()) OR
      NEW.recibido_en IS NULL THEN
     RAISE EXCEPTION 'Recepción no autorizada';
   END IF;
 ELSIF NEW.estado='cancelada' THEN
   IF ferreteria.rol_actual()<>'gerente' OR NEW.recibido_por IS NOT NULL OR NEW.recibido_nombre IS NOT NULL OR NEW.recibido_en IS NOT NULL THEN
     RAISE EXCEPTION 'Cancelación no autorizada';
   END IF;
 ELSE
   RAISE EXCEPTION 'Transición de pedido no permitida';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER compras_estado_controlado BEFORE UPDATE ON ferreteria.compras
 FOR EACH ROW EXECUTE FUNCTION ferreteria.validar_estado_compra();
CREATE TRIGGER detalle_compra_inmutable BEFORE UPDATE OR DELETE ON ferreteria.detalle_compra
 FOR EACH ROW EXECUTE FUNCTION ferreteria.proteger_historial();

ALTER TABLE ferreteria.proveedores ENABLE ROW LEVEL SECURITY;
ALTER TABLE ferreteria.proveedores FORCE ROW LEVEL SECURITY;
ALTER TABLE ferreteria.compras ENABLE ROW LEVEL SECURITY;
ALTER TABLE ferreteria.compras FORCE ROW LEVEL SECURITY;
ALTER TABLE ferreteria.detalle_compra ENABLE ROW LEVEL SECURITY;
ALTER TABLE ferreteria.detalle_compra FORCE ROW LEVEL SECURITY;
CREATE POLICY proveedores_lectura ON ferreteria.proveedores FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'));
CREATE POLICY proveedores_alta ON ferreteria.proveedores FOR INSERT TO ferreteria_api
 WITH CHECK ((SELECT ferreteria.rol_actual())='gerente');
CREATE POLICY proveedores_cambio ON ferreteria.proveedores FOR UPDATE TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual())='gerente') WITH CHECK ((SELECT ferreteria.rol_actual())='gerente');
CREATE POLICY compras_lectura ON ferreteria.compras FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'));
CREATE POLICY compras_alta ON ferreteria.compras FOR INSERT TO ferreteria_api
 WITH CHECK ((SELECT ferreteria.rol_actual())='gerente' AND creado_por=(SELECT ferreteria.usuario_actual()) AND estado='pendiente');
CREATE POLICY compras_cambio ON ferreteria.compras FOR UPDATE TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'))
 WITH CHECK ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'));
CREATE POLICY detalle_compra_lectura ON ferreteria.detalle_compra FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','almacenero'));
CREATE POLICY detalle_compra_alta ON ferreteria.detalle_compra FOR INSERT TO ferreteria_api
 WITH CHECK ((SELECT ferreteria.rol_actual())='gerente' AND EXISTS (
   SELECT 1 FROM ferreteria.compras c WHERE c.id=compra_id AND c.creado_por=(SELECT ferreteria.usuario_actual()) AND c.estado='pendiente'));
GRANT SELECT,INSERT,UPDATE ON ferreteria.proveedores,ferreteria.compras TO ferreteria_api;
GRANT SELECT,INSERT ON ferreteria.detalle_compra TO ferreteria_api;
GRANT USAGE ON SEQUENCE ferreteria.compras_numero_seq TO ferreteria_api;

DROP POLICY lectura_personal ON ferreteria.productos;
CREATE POLICY lectura_personal ON ferreteria.productos FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor','almacenero'));
DROP POLICY lectura_personal ON ferreteria.categorias;
CREATE POLICY lectura_personal ON ferreteria.categorias FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor','almacenero'));
DROP POLICY lectura_personal ON ferreteria.existencias;
CREATE POLICY lectura_personal ON ferreteria.existencias FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor','almacenero'));
DROP POLICY lectura_personal ON ferreteria.movimientos_inventario;
CREATE POLICY lectura_personal ON ferreteria.movimientos_inventario FOR SELECT TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor','almacenero'));
DROP POLICY cambio_existencias ON ferreteria.existencias;
CREATE POLICY cambio_existencias ON ferreteria.existencias FOR UPDATE TO ferreteria_api
 USING ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor','almacenero'))
 WITH CHECK ((SELECT ferreteria.rol_actual()) IN ('gerente','vendedor','almacenero'));
DROP POLICY alta_movimiento ON ferreteria.movimientos_inventario;
CREATE POLICY alta_movimiento ON ferreteria.movimientos_inventario FOR INSERT TO ferreteria_api
 WITH CHECK (usuario_id=(SELECT ferreteria.usuario_actual()) AND (
   ((SELECT ferreteria.rol_actual())='gerente' AND tipo<>'compra')
   OR ((SELECT ferreteria.rol_actual())='vendedor' AND tipo='venta' AND EXISTS (
      SELECT 1 FROM ferreteria.detalle_venta d JOIN ferreteria.ventas v ON v.id=d.venta_id
      WHERE d.id=detalle_venta_id AND v.usuario_id=(SELECT ferreteria.usuario_actual())))
   OR ((SELECT ferreteria.rol_actual())='almacenero' AND tipo='compra' AND EXISTS (
      SELECT 1 FROM ferreteria.detalle_compra d JOIN ferreteria.compras c ON c.id=d.compra_id
      WHERE d.id=detalle_compra_id AND c.estado='recibida' AND c.recibido_por=(SELECT ferreteria.usuario_actual())))
 ));
REVOKE ALL ON FUNCTION ferreteria.validar_estado_compra() FROM PUBLIC,anon,authenticated;
