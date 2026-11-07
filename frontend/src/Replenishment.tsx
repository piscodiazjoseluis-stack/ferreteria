import { useCallback, useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { RefreshCw } from 'lucide-react'
import { api } from './lib/appData'
import './Operations.css'

type Suggestion = { id: string; codigo: string; nombre: string; stock: number; stock_minimo: number; stock_objetivo: number; pendiente: number; sugerida: number }
export function Replenishment({ session, onOrder }: { session: Session; onOrder: (product: string, quantity: number) => void }) {
  const [rows, setRows] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setLoading(true)
    try { setRows(await api<Suggestion[]>('/management/replenishment', session)); setError('') }
    catch (r) { setError(r instanceof Error ? r.message : 'No se pudo calcular la reposición.') }
    finally { setLoading(false) }
  }, [session])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  return <section className="panel table-panel"><div className="table-toolbar"><div><h2>Reposición sugerida</h2><p>Gerencia revisa la cantidad antes de emitir el pedido.</p></div><button className="secondary-button" disabled={loading} onClick={() => void load()}><RefreshCw size={16} /> Recalcular</button></div>
    <p className="replenishment-explanation"><strong>Cálculo:</strong> objetivo − existencias − unidades pendientes de recibir. Si el resultado es negativo, sugerimos cero. Define el objetivo en Productos → Editar. El cálculo usa los registros actuales y no predice ventas futuras.</p>
    {error && <div className="alert error" role="alert">{error}</div>}{loading ? <p className="operations-empty" role="status">Calculando reposición…</p> : <div className="table-scroll"><table><thead><tr><th>PRODUCTO</th><th>DISPONIBLE</th><th>MÍNIMO</th><th>OBJETIVO</th><th>POR RECIBIR</th><th>SUGERIDO</th><th>ACCIÓN</th></tr></thead><tbody>{rows.map(r => <tr key={r.id}><td><strong>{r.nombre}</strong><small className="sub">{r.codigo}</small></td><td>{r.stock}</td><td>{r.stock_minimo}</td><td>{r.stock_objetivo}</td><td>{r.pendiente}</td><td><strong>{r.sugerida}</strong></td><td><button className="row-link" disabled={!r.sugerida} onClick={() => onOrder(r.id, r.sugerida)}>{r.sugerida ? 'Preparar pedido' : 'Cubierto'}</button></td></tr>)}</tbody></table></div>}
  </section>
}
