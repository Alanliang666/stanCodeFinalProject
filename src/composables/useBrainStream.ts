import {
  onBeforeUnmount,
  onMounted,
  watch,
} from 'vue'
import { storeToRefs } from 'pinia'
import { resolveBrainDataSource } from '@/config/brainStreamConfig'
import { useMockLiveEEG } from '@/composables/useMockLiveEEG'
import {
  mockBrainService,
  type BrainPredictionListener,
} from '@/services/brain/mockBrainService'
import { BrainStreamModeController } from '@/services/brain/brainStreamModeController'
import {
  resolveBrowserRealtimeUrl,
  type RealtimeUrlResolution,
} from '@/services/brain/realtimeUrl'
import {
  websocketBrainService,
  type WebSocketBrainSubscriber,
} from '@/services/brain/websocketBrainService'
import { useBrainStore } from '@/stores/brainStore'
import type { RealtimeMessage } from '@/types/realtime'

export const PREDICTION_STALE_TIMEOUT_MS = 5_000
const STALE_CHECK_INTERVAL_MS = 1_000

export function useBrainStream() {
  const brainStore = useBrainStore()
  const storeRefs = storeToRefs(brainStore)
  const realtimeUrlResolution: RealtimeUrlResolution =
    resolveBrowserRealtimeUrl()
  const selectedDataSource = resolveBrainDataSource({
    configuredSource: import.meta.env.VITE_BRAIN_DATA_SOURCE,
    realtimeUrlSource: realtimeUrlResolution.source,
    isDevelopment: import.meta.env.DEV,
  })
  const mockEEG = useMockLiveEEG({ autoStart: false })

  let unsubscribeMockPrediction: (() => void) | null = null
  let unsubscribeWebSocket: (() => void) | null = null
  let staleTimer: ReturnType<typeof setInterval> | null = null
  let started = false

  watch(mockEEG.chunk, (chunk) => {
    if (chunk && brainStore.dataSource === 'mock') {
      brainStore.updateEEGChunk(chunk)
    }
  })

  function handleRealtimeMessage(message: RealtimeMessage): void {
    if (brainStore.dataSource !== 'websocket') return
    if (message.type === 'device_status') {
      brainStore.updateDeviceStatus(message.data)
      return
    }
    if (message.type === 'eeg_chunk') {
      brainStore.updateEEGChunk(message)
      return
    }
    brainStore.updateRealtimePrediction(message)
  }

  function startMock(): void {
    brainStore.beginStream('mock')
    brainStore.setConnectionStatus('connecting')
    const listener: BrainPredictionListener = (prediction) => {
      if (brainStore.dataSource === 'mock') {
        brainStore.updatePrediction(prediction)
      }
    }
    unsubscribeMockPrediction = mockBrainService.subscribe(listener)
    mockBrainService.start()
    mockEEG.start()
    brainStore.setConnectionStatus('connected')
  }

  function stopMock(): void {
    mockBrainService.stop()
    unsubscribeMockPrediction?.()
    unsubscribeMockPrediction = null
    mockEEG.stop()
  }

  function startWebSocket(): void {
    const realtimeUrl = realtimeUrlResolution.url
    brainStore.beginStream('websocket', realtimeUrl)
    if (!realtimeUrl) {
      brainStore.setConnectionStatus('error')
      brainStore.setError(
        realtimeUrlResolution.error ?? 'Realtime endpoint not configured',
      )
      return
    }

    const subscriber: WebSocketBrainSubscriber = {
      onMessage: handleRealtimeMessage,
      onStatus: (status) => {
        if (brainStore.dataSource !== 'websocket') return
        brainStore.setConnectionStatus(status)
        if (status !== 'connected') brainStore.markPredictionUnavailable()
      },
      onError: (message) => brainStore.setError(message),
      onInvalidMessage: () => {
        if (import.meta.env.DEV) {
          console.debug('[Realtime] Ignored invalid backend message')
        }
      },
    }
    unsubscribeWebSocket = websocketBrainService.subscribe(subscriber)
    websocketBrainService.connect(realtimeUrl)
  }

  function stopWebSocket(): void {
    websocketBrainService.disconnect()
    unsubscribeWebSocket?.()
    unsubscribeWebSocket = null
  }

  const modeController = new BrainStreamModeController({
    startMock,
    stopMock,
    startWebSocket,
    stopWebSocket,
  })

  function start(): void {
    if (started) return
    started = true
    modeController.start(selectedDataSource)
    staleTimer = setInterval(() => {
      brainStore.expireStalePrediction(
        Date.now(),
        PREDICTION_STALE_TIMEOUT_MS,
      )
    }, STALE_CHECK_INTERVAL_MS)
  }

  function stop(): void {
    if (!started) return
    started = false
    modeController.stop()
    if (staleTimer !== null) {
      clearInterval(staleTimer)
      staleTimer = null
    }
    brainStore.markPredictionUnavailable()
    brainStore.setConnectionStatus('disconnected')
  }

  function reconnect(): void {
    if (
      brainStore.dataSource === 'websocket'
      && realtimeUrlResolution.url
    ) {
      websocketBrainService.reconnect(realtimeUrlResolution.url)
    }
  }

  onMounted(start)
  onBeforeUnmount(stop)

  return {
    ...storeRefs,
    realtimeUrlResolution,
    start,
    stop,
    reconnect,
  }
}
