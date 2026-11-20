import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { tokenStore } from '../services/api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!tokenStore.get()) { setLoading(false); return }
    api.get('/api/auth/me').then((r) => setUser(r.data)).catch(() => tokenStore.clear()).finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password, role) => {
    const { data } = await api.post('/api/auth/login', { email, password, role })
    tokenStore.set(data.access_token); setUser(data.user)
    return data.user
  }, [])
  const logout = useCallback(() => { tokenStore.clear(); setUser(null) }, [])

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}
