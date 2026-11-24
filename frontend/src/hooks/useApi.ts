import { useCallback, useEffect, useRef, useState } from 'react'
import { toErrorMessage } from '../api/client'

export interface ApiState<T> {
  data: T | undefined
  error: string | null
  loading: boolean
  reload: () => void
}

/**
 * Runs `fetcher` whenever `deps` change. Stale responses (from an older set of
 * deps) are ignored so fast filter changes never show out-of-date results.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [data, setData] = useState<T>()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const requestId = useRef(0)
  const fetchRef = useRef(fetcher)
  // Keep the latest fetcher without re-running the request effect (runs before it).
  useEffect(() => {
    fetchRef.current = fetcher
  })

  useEffect(() => {
    const id = ++requestId.current
    fetchRef
      .current()
      .then((result) => {
        if (id !== requestId.current) return
        setData(result)
        setError(null)
      })
      .catch((err: unknown) => {
        if (id !== requestId.current) return
        setError(toErrorMessage(err))
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => {
    setLoading(true)
    setTick((t) => t + 1)
  }, [])

  // Show the loading state as soon as inputs change, without a synchronous setState in the effect.
  const depsKey = JSON.stringify(deps)
  const [lastKey, setLastKey] = useState(depsKey)
  if (depsKey !== lastKey) {
    setLastKey(depsKey)
    setLoading(true)
  }

  return { data, error, loading, reload }
}
