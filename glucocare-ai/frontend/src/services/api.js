import axios from 'axios'

const TOKEN_KEY = 'glucocare_token'
export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t) => { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ } },
}

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '' })
api.interceptors.request.use((cfg) => {
  const t = tokenStore.get()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})
api.interceptors.response.use((r) => r, (err) => {
  if (err.response?.status === 401 && !String(err.config?.url).includes('/auth/login')) {
    tokenStore.clear()
    if (!location.pathname.startsWith('/login')) location.href = '/login?expired=1'
  }
  return Promise.reject(err)
})

export const errMsg = (e) => {
  const d = e?.response?.data?.detail
  if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(1).join('.')}: ${x.msg}`).join('; ')
  if (typeof d === 'string') return d
  if (e?.response?.status === 403) return 'You do not have permission to view this.'
  if (e?.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the backend running on port 8000?'
  return e?.message || 'Something went wrong'
}

const saveBlob = (blob, filename) => {
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href; a.download = filename; document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 2000)
}

export async function downloadFile(url, filename) {
  const res = await api.get(url, { responseType: 'blob' })
  saveBlob(res.data, filename)
}

/** Opens a report in a new browser tab (PDF / images). Other file types are downloaded instead. */
export async function openFile(url, filename) {
  const w = window.open('', '_blank')
  try {
    const res = await api.get(url, { responseType: 'blob' })
    const t = res.data.type || ''
    if (w && (t.includes('pdf') || t.startsWith('image/'))) { w.location.href = URL.createObjectURL(res.data) }
    else { if (w) w.close(); saveBlob(res.data, filename) }
  } catch (e) { if (w) w.close(); throw e }
}

export default api
