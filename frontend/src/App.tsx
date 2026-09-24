import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { Auth } from './Auth'
import { Brand } from './Brand'
import { Workspace } from './Workspace'
import { api } from './lib/appData'
import type { Profile } from './lib/appData'
import { supabase } from './lib/supabase'
import './App.css'

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(Boolean(supabase))
  const [error, setError] = useState('')

  useEffect(() => {
    if (!supabase) return
    let active = true
    supabase.auth.getSession().then(({ data }) => {
      if (active) { if (!window.location.search.includes('recuperar=1')) setSession(data.session); setLoading(false) }
    })
    const { data } = supabase.auth.onAuthStateChange((event, next) => {
      if (!active) return
      if (event === 'SIGNED_OUT') { setSession(null); setProfile(null) }
      if (event === 'TOKEN_REFRESHED') setSession(next)
    })
    return () => { active = false; data.subscription.unsubscribe() }
  }, [])

  useEffect(() => {
    if (!session) return
    let active = true
    api<Profile>('/auth/me', session).then(data => { if (active) { setProfile(data); setError('') } })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'No se pudo comprobar el acceso.') })
    return () => { active = false }
  }, [session])

  async function logout() { await supabase?.auth.signOut({ scope: 'local' }); setSession(null); setProfile(null) }
  if (loading) return <div className="loading-screen"><Brand /><p>Comprobando acceso…</p></div>
  if (!session) return <Auth onSession={next => { setSession(next); setProfile(null); setError('') }} />
  if (!profile) return <div className="loading-screen"><Brand /><p>{error || 'Validando tu perfil…'}</p>{error && <button onClick={logout}>Cerrar sesión</button>}</div>
  return <Workspace session={session} profile={profile} onLogout={logout} />
}
