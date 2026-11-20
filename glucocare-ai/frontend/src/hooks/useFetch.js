import { useCallback, useEffect, useState } from 'react'
import { errMsg } from '../services/api'

export default function useFetch(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try { setState({ data: await fn(), loading: false, error: null }) }
    catch (e) { setState({ data: null, loading: false, error: errMsg(e) }) }
  }, deps)
  useEffect(() => { run() }, [run])
  return { ...state, reload: run }
}
