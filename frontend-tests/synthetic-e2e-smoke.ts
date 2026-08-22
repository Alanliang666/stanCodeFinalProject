import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import { WebSocketBrainService } from '../src/services/brain/websocketBrainService'
import { useBrainStore } from '../src/stores/brainStore'
import type { RealtimeMessage } from '../src/types/realtime'

const endpoint = process.argv[2] ?? 'ws://localhost:8000/ws'
const timeoutMs = 12_000

setActivePinia(createPinia())
const store = useBrainStore()
const service = new WebSocketBrainService()
const receivedTypes = new Set<RealtimeMessage['type']>()

store.beginStream('websocket', endpoint)

function updateApplicationState(message: RealtimeMessage): void {
  receivedTypes.add(message.type)
  if (message.type === 'device_status') {
    store.updateDeviceStatus(message.data)
  } else if (message.type === 'eeg_chunk') {
    store.updateEEGChunk(message)
  } else {
    store.updateRealtimePrediction(message)
  }
}

await new Promise<void>((resolve, reject) => {
  const timeout = setTimeout(() => {
    reject(new Error(
      `Timed out waiting for backend messages; received: ${[
        ...receivedTypes,
      ].join(', ')}`,
    ))
  }, timeoutMs)

  service.subscribe({
    onStatus: (status) => store.setConnectionStatus(status),
    onError: reject,
    onMessage: (message) => {
      updateApplicationState(message)
      if (receivedTypes.size === 3) {
        clearTimeout(timeout)
        resolve()
      }
    },
  })
  service.connect(endpoint)
}).finally(() => service.disconnect())

assert.equal(store.connectionStatus, 'disconnected')
assert.equal(store.deviceStatus.connected, true)
assert.equal(store.deviceStatus.device, 'Synthetic Muse 2')
assert.equal(store.eegChunk?.data.channel_order.join(','), 'TP9,AF7,AF8,TP10')
assert.ok((store.eegChunk?.data.samples.length ?? 0) > 0)
const receivedState = store.prediction?.cognition.state
assert.ok([
  'relaxed_openeye',
  'concentration',
  'relaxed_closeeye',
].includes(receivedState ?? ''))
assert.deepEqual(
  Object.keys(store.prediction?.cognition.probabilities ?? {}),
  ['relaxed_openeye', 'concentration', 'relaxed_closeeye'],
)

console.log('=== Frontend Synthetic Realtime Smoke ===')
console.log(`Endpoint: ${endpoint}`)
console.log(`Device: ${store.deviceStatus.device}`)
console.log(`EEG chunk samples: ${store.eegChunk?.data.samples.length}`)
console.log(
  `Prediction: ${store.prediction?.cognition.state} ${
    (store.prediction?.cognition.confidence ?? 0) * 100
  }%`,
)
console.log('Result: PASS')
