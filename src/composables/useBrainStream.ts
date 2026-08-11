import { onBeforeUnmount, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useBrainStore } from '@/stores/brainStore'

export function useBrainStream() {
  const brainStore = useBrainStore()
  const { connectionStatus, errorMessage } = storeToRefs(brainStore)

  onMounted(() => brainStore.startMockStream())
  onBeforeUnmount(() => brainStore.stopMockStream())

  return {
    connectionStatus,
    errorMessage,
    start: brainStore.startMockStream,
    stop: brainStore.stopMockStream,
  }
}
