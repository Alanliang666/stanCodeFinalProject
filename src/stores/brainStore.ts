import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  mockBrainService,
  type BrainPredictionListener,
} from '@/services/brain/mockBrainService'
import type {
  BrainConnectionStatus,
  BrainPrediction,
} from '@/types/brain'

export const useBrainStore = defineStore('brain', () => {
  const prediction = ref<BrainPrediction | null>(null)
  const connectionStatus = ref<BrainConnectionStatus>('disconnected')
  const selectedDevice = ref('Mock EEG Device')
  const errorMessage = ref<string | null>(null)

  let unsubscribe: (() => void) | null = null

  const lastUpdated = computed(() => prediction.value?.timestamp ?? null)
  const isConnected = computed(() => connectionStatus.value === 'connected')

  function updatePrediction(nextPrediction: BrainPrediction): void {
    prediction.value = nextPrediction
    connectionStatus.value = 'connected'
    errorMessage.value = null
  }

  function startMockStream(): void {
    if (unsubscribe !== null) return

    connectionStatus.value = 'connecting'
    errorMessage.value = null

    const listener: BrainPredictionListener = (nextPrediction) => {
      updatePrediction(nextPrediction)
    }

    unsubscribe = mockBrainService.subscribe(listener)
    mockBrainService.start()
  }

  function stopMockStream(): void {
    mockBrainService.stop()
    unsubscribe?.()
    unsubscribe = null
    connectionStatus.value = 'disconnected'
  }

  function selectDevice(deviceName: string): void {
    selectedDevice.value = deviceName
  }

  return {
    prediction,
    connectionStatus,
    selectedDevice,
    errorMessage,
    lastUpdated,
    isConnected,
    updatePrediction,
    startMockStream,
    stopMockStream,
    selectDevice,
  }
})
