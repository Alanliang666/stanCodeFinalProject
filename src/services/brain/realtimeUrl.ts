export const REALTIME_URL_STORAGE_KEY = 'brain-realtime-websocket-url'

export type RealtimeUrlSource =
  | 'query'
  | 'local-storage'
  | 'environment'
  | 'development-fallback'

export interface RealtimeUrlResolution {
  url: string | null
  source: RealtimeUrlSource | null
  error: string | null
}

export interface RealtimeUrlOptions {
  querySearch: string
  storedUrl?: string | null
  environmentUrl?: string | null
  developmentFallbackUrl?: string | null
  pageProtocol: string
  isDevelopment: boolean
}

function validateRealtimeUrl(
  candidate: string | null | undefined,
  pageProtocol: string,
): string | null {
  const trimmed = candidate?.trim()
  if (!trimmed) return null

  try {
    const parsed = new URL(trimmed)
    if (parsed.protocol !== 'ws:' && parsed.protocol !== 'wss:') return null
    if (pageProtocol === 'https:' && parsed.protocol !== 'wss:') return null
    return parsed.toString()
  } catch {
    return null
  }
}

export function resolveRealtimeUrl(
  options: RealtimeUrlOptions,
): RealtimeUrlResolution {
  const queryCandidate = new URLSearchParams(options.querySearch).get('ws')
  const candidates: Array<{
    value: string | null | undefined
    source: RealtimeUrlSource
  }> = [
    { value: queryCandidate, source: 'query' },
    { value: options.storedUrl, source: 'local-storage' },
    { value: options.environmentUrl, source: 'environment' },
  ]

  for (const candidate of candidates) {
    const url = validateRealtimeUrl(candidate.value, options.pageProtocol)
    if (url) return { url, source: candidate.source, error: null }
  }

  if (options.isDevelopment && options.pageProtocol !== 'https:') {
    const developmentUrl = validateRealtimeUrl(
      options.developmentFallbackUrl,
      options.pageProtocol,
    )
    if (!developmentUrl) {
      return {
        url: null,
        source: null,
        error: 'Realtime endpoint not configured',
      }
    }
    return {
      url: developmentUrl,
      source: 'development-fallback',
      error: null,
    }
  }

  return {
    url: null,
    source: null,
    error: 'Realtime endpoint not configured',
  }
}

export function resolveBrowserRealtimeUrl(): RealtimeUrlResolution {
  if (typeof window === 'undefined') {
    return {
      url: null,
      source: null,
      error: 'Realtime endpoint not configured',
    }
  }

  let storedUrl: string | null = null
  try {
    storedUrl = window.localStorage.getItem(REALTIME_URL_STORAGE_KEY)
  } catch {
    // Storage can be unavailable in privacy-restricted browsing contexts.
  }

  const resolution = resolveRealtimeUrl({
    querySearch: window.location.search,
    storedUrl,
    environmentUrl: import.meta.env.VITE_REALTIME_WS_URL,
    developmentFallbackUrl: import.meta.env.DEV
      ? `ws://${window.location.hostname}:8000/ws`
      : null,
    pageProtocol: window.location.protocol,
    isDevelopment: import.meta.env.DEV,
  })

  if (resolution.url && resolution.source === 'query') {
    try {
      window.localStorage.setItem(REALTIME_URL_STORAGE_KEY, resolution.url)
    } catch {
      // A valid query override still works when persistence is unavailable.
    }
  }

  return resolution
}
