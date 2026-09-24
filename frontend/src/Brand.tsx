export function Brand({ light = false }: { light?: boolean }) {
  return <div className={`brand ${light ? 'light' : ''}`}><div className="brand-logo">M<span>&</span>F</div><div><strong>Ferretería Miguel</strong><small>GESTIÓN COMERCIAL</small></div></div>
}
