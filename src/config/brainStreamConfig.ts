import type { BrainDataSource } from '@/types/brain'
import type { RealtimeUrlSource } from '@/services/brain/realtimeUrl'

export interface BrainDataSourceOptions {
  configuredSource?: string | null
  realtimeUrlSource: RealtimeUrlSource | null
  isDevelopment: boolean
}

export function resolveBrainDataSource(
  options: BrainDataSourceOptions,
): BrainDataSource {
  if (options.configuredSource === 'mock') return 'mock'
  if (options.configuredSource === 'websocket') return 'websocket'

  if (
    options.realtimeUrlSource !== null
    && options.realtimeUrlSource !== 'development-fallback'
  ) {
    return 'websocket'
  }

  return options.isDevelopment ? 'mock' : 'websocket'
}
