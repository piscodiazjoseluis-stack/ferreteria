import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { ChartNoAxesCombined, ShoppingCart, Truck } from 'lucide-react'
import { api, money } from './lib/appData'
import type { ManagementOverview } from './lib/appData'
import './ManagementInsights.css'

export function ManagementInsights({ session, refreshKey }: { session: Session; refreshKey: number }) {
  const [data, setData] = useState<ManagementOverview | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    api<ManagementOverview>('/management/overview', session).then(result => { if (active) { setData(result); setError('') } })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'No se pudieron cargar los indicadores.') })
    return () => { active = false }
  }, [session, refreshKey])
  if (error) return <div className="alert error" role="alert">{error}</div>
  if (!data) return <div className="management-loading" role="status">Cargando indicadores de gerencia…</div>
  return <section className="management-insights" aria-label="Indicadores de gerencia">
    <div className="management-section-heading"><div><span className="eyebrow">ACTIVIDAD DEL NEGOCIO</span><h2>Decisiones con datos reales</h2><p>Ventas registradas y compras pendientes en la base de datos.</p></div></div>
    <div className="management-metrics"><div><ShoppingCart size={20} /><small>Ventas de hoy</small><strong>{data.ventas_hoy}</strong><span>{money(Number(data.importe_hoy))} · hora de Lima</span></div><div><ChartNoAxesCombined size={20} /><small>Ventas del mes</small><strong>{money(Number(data.importe_mes))}</strong><span>{data.ventas_mes} operaciones confirmadas</span></div><div><Truck size={20} /><small>Pedidos por recibir</small><strong>{data.pedidos_pendientes}</strong><span>En espera de almacén</span></div></div>
    <div className="panel management-top"><div className="panel-heading"><h2>Productos más vendidos este mes</h2><p>Ordenados por unidades confirmadas.</p></div>{data.productos_mas_vendidos.length ? data.productos_mas_vendidos.map((item, index) => <div className="management-rank" key={item.codigo_producto}><span>{index + 1}</span><div><strong>{item.nombre_producto}</strong><small>{item.codigo_producto}</small></div><b>{item.unidades} u.</b><em>{money(Number(item.importe))}</em></div>) : <p className="management-no-sales">Aún no hay ventas registradas este mes.</p>}</div>
  </section>
}
