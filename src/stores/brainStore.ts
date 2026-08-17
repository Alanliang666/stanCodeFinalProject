import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import type {
  BrainDataSource,
  BrainPrediction,
  RealtimeConnectionStatus,
} from '@/types/brain'
import type { EEGChunkMessage } from '@/types/eeg'
import type {
  CognitivePredictionMessage,
  DeviceStatusData,
} from '@/types/realtime'
import { isPredictionStale } from '@/services/brain/predictionFreshness'

const DEFAULT_DEVICE_STATUS: DeviceStatusData = {
  connected: false,
  device: 'Muse 2',
  sampling_rate_hz: 256,
  channel_order: ['TP9', 'AF7', 'AF8', 'TP10'],
}

function backendTimestampToMilliseconds(timestamp: number): number {
  return timestamp < 10_000_000_000 ? timestamp * 1_000 : timestamp
}

export const useBrainStore = defineStore('brain', () => {
  const prediction = ref<BrainPrediction | null>(null)
  const eegChunk = shallowRef<EEGChunkMessage | null>(null)
  const dataSource = ref<BrainDataSource>('mock')
  const connectionStatus = ref<RealtimeConnectionStatus>('idle')
  const deviceStatus = ref<DeviceStatusData>({ ...DEFAULT_DEVICE_STATUS })
  const realtimeUrl = ref<string | null>(null)
  const errorMessage = ref<string | null>(null)
  const lastPredictionReceivedAt = ref<number | null>(null)

  const lastUpdated = computed(() => prediction.value?.timestamp ?? null)
  const isConnected = computed(() => connectionStatus.value === 'connected')
  const dataSourceLabel = computed(() =>
    dataSource.value === 'mock' ? 'Mock Data' : 'Live / WebSocket',
  )

  function beginStream(
    source: BrainDataSource,
    endpoint: string | null = null,
  ): void {
    dataSource.value = source
    realtimeUrl.value = endpoint
    prediction.value = null
    eegChunk.value = null
    lastPredictionReceivedAt.value = null
    errorMessage.value = null
    deviceStatus.value = source === 'mock'
      ? {
          connected: false,
          device: 'Mock EEG Generator',
          sampling_rate_hz: 256,
          channel_order: ['TP9', 'AF7', 'AF8', 'TP10'],
        }
      : { ...DEFAULT_DEVICE_STATUS }
  }

  function updatePrediction(nextPrediction: BrainPrediction): void {
    prediction.value = nextPrediction
    lastPredictionReceivedAt.value = Date.now()
    errorMessage.value = null
  }

  function updateRealtimePrediction(
    message: CognitivePredictionMessage,
  ): void {
    updatePrediction({
      timestamp: backendTimestampToMilliseconds(message.data.timestamp),
      cognition: {
        state: message.data.state,
        confidence: message.data.confidence,
        probabilities: { ...message.data.probabilities },
      },
    })
  }

  function updateEEGChunk(message: EEGChunkMessage): void {
    eegChunk.value = message
  }

  function updateDeviceStatus(status: DeviceStatusData): void {
    deviceStatus.value = {
      ...status,
      channel_order: [...status.channel_order],
    }
  }

  function setConnectionStatus(status: RealtimeConnectionStatus): void {
    connectionStatus.value = status
  }

  function setError(message: string | null): void {
    errorMessage.value = message
  }

  function markPredictionUnavailable(): void {
    prediction.value = null
    lastPredictionReceivedAt.value = null
  }

  function expireStalePrediction(
    now: number,
    staleTimeoutMs: number,
  ): boolean {
    const receivedAt = lastPredictionReceivedAt.value
    if (!isPredictionStale(receivedAt, now, staleTimeoutMs)) return false
    markPredictionUnavailable()
    return true
  }

  return {
    prediction,
    eegChunk,
    dataSource,
    connectionStatus,
    deviceStatus,
    realtimeUrl,
    errorMessage,
    lastPredictionReceivedAt,
    lastUpdated,
    isConnected,
    dataSourceLabel,
    beginStream,
    updatePrediction,
    updateRealtimePrediction,
    updateEEGChunk,
    updateDeviceStatus,
    setConnectionStatus,
    setError,
    markPredictionUnavailable,
    expireStalePrediction,
  }
})
