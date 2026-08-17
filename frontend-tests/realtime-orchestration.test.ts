import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveBrainDataSource } from '../src/config/brainStreamConfig'
import { BrainStreamModeController } from '../src/services/brain/brainStreamModeController'
import { isPredictionStale } from '../src/services/brain/predictionFreshness'
import { resolveRealtimeUrl } from '../src/services/brain/realtimeUrl'
import {
  WebSocketBrainService,
  type WebSocketLike,
} from '../src/services/brain/websocketBrainService'

test('resolves runtime URL in query, storage, environment order', () => {
  const common = {
    pageProtocol: 'https:',
    isDevelopment: false,
  }
  assert.deepEqual(resolveRealtimeUrl({
    ...common,
    querySearch: '?ws=wss%3A%2F%2Fquery.example%2Fws',
    storedUrl: 'wss://stored.example/ws',
    environmentUrl: 'wss://env.example/ws',
  }), {
    url: 'wss://query.example/ws',
    source: 'query',
    error: null,
  })
  assert.equal(resolveRealtimeUrl({
    ...common,
    querySearch: '',
    storedUrl: 'wss://stored.example/ws',
    environmentUrl: 'wss://env.example/ws',
  }).source, 'local-storage')
  assert.equal(resolveRealtimeUrl({
    ...common,
    querySearch: '',
    environmentUrl: 'wss://env.example/ws',
  }).source, 'environment')
})

test('HTTPS pages reject ws and production has no localhost fallback', () => {
  const resolution = resolveRealtimeUrl({
    querySearch: '?ws=ws%3A%2F%2Flocalhost%3A8000%2Fws',
    pageProtocol: 'https:',
    isDevelopment: false,
  })
  assert.equal(resolution.url, null)
  assert.equal(resolution.error, 'Realtime endpoint not configured')
})

test('local HTTP development receives its explicit fallback', () => {
  const resolution = resolveRealtimeUrl({
    querySearch: '',
    pageProtocol: 'http:',
    isDevelopment: true,
    developmentFallbackUrl: 'ws://localhost:8000/ws',
  })
  assert.equal(resolution.url, 'ws://localhost:8000/ws')
  assert.equal(resolution.source, 'development-fallback')
})

test('source selection keeps mock and websocket mutually exclusive', () => {
  const calls: string[] = []
  const controller = new BrainStreamModeController({
    startMock: () => calls.push('start-mock'),
    stopMock: () => calls.push('stop-mock'),
    startWebSocket: () => calls.push('start-websocket'),
    stopWebSocket: () => calls.push('stop-websocket'),
  })
  controller.start('mock')
  controller.start('mock')
  controller.start('websocket')
  controller.stop()
  assert.deepEqual(calls, [
    'start-mock',
    'stop-mock',
    'start-websocket',
    'stop-websocket',
  ])
  assert.equal(resolveBrainDataSource({
    configuredSource: 'websocket',
    realtimeUrlSource: null,
    isDevelopment: true,
  }), 'websocket')
  assert.equal(resolveBrainDataSource({
    configuredSource: 'mock',
    realtimeUrlSource: 'query',
    isDevelopment: false,
  }), 'mock')
})

test('stale prediction threshold is deterministic', () => {
  assert.equal(isPredictionStale(null, 10_000, 5_000), false)
  assert.equal(isPredictionStale(5_000, 10_000, 5_000), false)
  assert.equal(isPredictionStale(4_999, 10_000, 5_000), true)
})

class FakeSocket implements WebSocketLike {
  readyState = 0
  onopen: (() => void) | null = null
  onmessage: ((event: { data: unknown }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  open(): void {
    this.readyState = 1
    this.onopen?.()
  }

  remoteClose(): void {
    this.readyState = 3
    this.onclose?.()
  }

  close(): void {
    this.readyState = 3
    this.onclose?.()
  }
}

test('disconnect state and reconnect never create concurrent sockets', () => {
  const sockets: FakeSocket[] = []
  const scheduled: Array<() => void> = []
  const statuses: string[] = []
  const service = new WebSocketBrainService({
    webSocketFactory: () => {
      const socket = new FakeSocket()
      sockets.push(socket)
      return socket
    },
    reconnectDelaysMs: [1, 2, 4, 8],
    setTimer: ((callback: () => void) => {
      scheduled.push(callback)
      return scheduled.length
    }) as typeof setTimeout,
    clearTimer: (() => undefined) as typeof clearTimeout,
  })
  service.subscribe({ onStatus: (status) => statuses.push(status) })

  service.connect('ws://example.test/ws')
  service.connect('ws://example.test/ws')
  assert.equal(sockets.length, 1)
  sockets[0]?.open()
  service.connect('ws://example.test/ws')
  assert.equal(sockets.length, 1)

  sockets[0]?.remoteClose()
  assert.equal(scheduled.length, 1)
  scheduled[0]?.()
  assert.equal(sockets.length, 2)

  service.disconnect()
  assert.equal(statuses.at(-1), 'disconnected')
})
