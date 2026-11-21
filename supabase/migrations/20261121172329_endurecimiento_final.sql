ALTER TABLE ferreteria.productos ADD COLUMN equivalencia text NOT NULL DEFAULT '' CHECK(length(equivalencia)<=160);
CREATE INDEX movimientos_compra_idx ON ferreteria.movimientos_inventario(detalle_compra_id);
-- Preserve the exact OR semantics while evaluating one policy per API action.
DO $$ DECLARE r record;p record;us text;ck text; BEGIN
 FOR r IN SELECT tablename,cmd FROM pg_policies WHERE schemaname='ferreteria' AND roles=ARRAY['ferreteria_api']::name[]
 GROUP BY tablename,cmd HAVING count(*)>1 LOOP
  SELECT string_agg('('||coalesce(qual,'true')||')',' OR '), string_agg('('||coalesce(with_check,qual,'true')||')',' OR ')
  INTO us,ck FROM pg_policies WHERE schemaname='ferreteria' AND tablename=r.tablename AND cmd=r.cmd AND roles=ARRAY['ferreteria_api']::name[];
  FOR p IN SELECT policyname FROM pg_policies WHERE schemaname='ferreteria' AND tablename=r.tablename AND cmd=r.cmd AND roles=ARRAY['ferreteria_api']::name[] LOOP
   EXECUTE format('DROP POLICY %I ON ferreteria.%I',p.policyname,r.tablename); END LOOP;
  EXECUTE format('CREATE POLICY %I ON ferreteria.%I FOR %s TO ferreteria_api %s %s','acceso_final_'||lower(r.cmd),r.tablename,r.cmd,
   CASE WHEN r.cmd IN ('SELECT','UPDATE','DELETE','ALL') THEN 'USING ('||us||')' ELSE '' END,
   CASE WHEN r.cmd IN ('INSERT','UPDATE','ALL') THEN 'WITH CHECK ('||ck||')' ELSE '' END);
 END LOOP;
END $$;
