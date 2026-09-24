import type { Session } from '@supabase/supabase-js'

export type Profile = { id: string; nombre: string; rol: 'gerente' | 'vendedor'; activo: boolean }
export type Category = { id: string; nombre: string }
export type Product = { id: string; codigo: string; nombre: string; categoria_id: string; categoria: string; unidad_venta: string; precio_venta: number; stock_minimo: number; stock: number; activo: boolean; creado_en: string; actualizado_en: string }
export type Movement = { id: string; producto_id: string; codigo: string; producto: string; tipo: string; variacion: number; stock_anterior: number; stock_resultante: number; motivo: string; fecha: string; usuario: string }
export type SaleLine = { producto_id: string; codigo_producto: string; nombre_producto: string; unidad_venta: string; cantidad: number; precio_unitario: number; subtotal: number }
export type SaleSummary = { id: string; numero: number; usuario_id: string; usuario: string; fecha: string; metodo_pago: string; total: number; lineas: number; unidades: number }
export type SaleReceipt = Omit<SaleSummary, 'lineas' | 'unidades'> & { clave_idempotencia: string; items: SaleLine[] }
export type SalesSummaryStats = { total_ventas: number; ventas_hoy: number; importe_hoy: number }

export const money = (value: number) => new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(value)
export const dateTime = (value: string) => new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value))
export const stockState = (p: Product) => !p.activo ? 'inactivo' : p.stock === 0 ? 'agotado' : p.stock < p.stock_minimo ? 'bajo' : 'disponible'
export const stateLabel: Record<string, string> = { inactivo: 'Inactivo', agotado: 'Agotado', bajo: 'Stock bajo', disponible: 'Disponible' }

export async function api<T>(path: string, session: Session, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}`, ...init?.headers } })
  const data: unknown = await response.json()
  if (!response.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : null
    throw new Error(typeof detail === 'string' ? detail : response.status === 422 ? 'Revisa los datos ingresados.' : 'No se pudo completar la operación.')
  }
  return data as T
}
