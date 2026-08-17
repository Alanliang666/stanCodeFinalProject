import type { RealtimeConnectionStatus } from '@/types/brain'
import type { RealtimeMessage } from '@/types/realtime'
import { parseRealtimeMessage } from '@/services/brain/realtimeMessageValidators'

const RECONNECT_DELAYS_MS = [1_000, 2_000, 4_000, 8_000] as const
const SOCKET_CONNECTING = 0
const SOCKET_OPEN = 1

export interface WebSocketLike {
  readonly readyState: number
  onopen: (() => void) | null
  onmessage: ((event: { data: unknown }) => void) | null
  onerror: (() => void) | null
  onclose: (() => void) | null
  close: () => void
}

export type WebSocketFactory = (url: string) => WebSocketLike

export interface WebSocketBrainSubscriber {
  onMessage?: (message: RealtimeMessage) => void
  onStatus?: (status: RealtimeConnectionStatus) => void
  onError?: (message: string) => void
  onInvalidMessage?: () => void
}

export interface WebSocketBrainServiceOptions {
  webSocketFactory?: WebSocketFactory
  reconnectDelaysMs?: readonly number[]
  setTimer?: typeof setTimeout
  clearTimer?: typeof clearTimeout
}

class BrowserWebSocketAdapter implements WebSocketLike {
  private readonly socket: WebSocket
  onopen: (() => void) | null = null
  onmessage: ((event: { data: unknown }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(socket: WebSocket) {
    this.socket = socket
    socket.addEventListener('open', () => this.onopen?.())
    socket.addEventListener('message', (event) => {
      this.onmessage?.({ data: event.data })
    })
    socket.addEventListener('error', () => this.onerror?.())
    socket.addEventListener('close', () => this.onclose?.())
  }

  get readyState(): number {
    return this.socket.readyState
  }

  close(): void {
    this.socket.close()
  }
}

export class WebSocketBrainService {
  private readonly subscribers = new Set<WebSocketBrainSubscriber>()
  private readonly webSocketFactory: WebSocketFactory
  private readonly reconnectDelaysMs: readonly number[]
  private readonly setTimer: typeof setTimeout
  private readonly clearTimer: typeof clearTimeout
  private socket: WebSocketLike | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempt = 0
  private targetUrl: string | null = null
  private manuallyDisconnected = true
  private generation = 0
  private currentStatus: RealtimeConnectionStatus = 'idle'

  constructor(options: WebSocketBrainServiceOptions = {}) {
    this.webSocketFactory = options.webSocketFactory
      ?? ((url) => new BrowserWebSocketAdapter(new WebSocket(url)))
    this.reconnectDelaysMs = options.reconnectDelaysMs
      ?? RECONNECT_DELAYS_MS
    this.setTimer = options.setTimer ?? setTimeout
    this.clearTimer = options.clearTimer ?? clearTimeout
  }

  subscribe(subscriber: WebSocketBrainSubscriber): () => void {
    this.subscribers.add(subscriber)
    subscriber.onStatus?.(this.currentStatus)
    return () => this.subscribers.delete(subscriber)
  }

  connect(url: string): void {
    if (
      this.targetUrl === url
      && this.socket !== null
      && (this.socket.readyState === SOCKET_CONNECTING
        || this.socket.readyState === SOCKET_OPEN)
    ) {
      return
    }

    this.manuallyDisconnected = false
    this.targetUrl = url
    this.reconnectAttempt = 0
    this.clearReconnectTimer()
    this.closeCurrentSocket()
    this.openSocket(false)
  }

  disconnect(): void {
    this.manuallyDisconnected = true
    this.targetUrl = null
    this.reconnectAttempt = 0
    this.clearReconnectTimer()
    this.generation += 1
    this.closeCurrentSocket()
    this.emitStatus('disconnected')
  }

  reconnect(url?: string): void {
    const nextUrl = url ?? this.targetUrl
    if (!nextUrl) return
    this.disconnect()
    this.connect(nextUrl)
  }

  private openSocket(isReconnect: boolean): void {
    if (!this.targetUrl || this.manuallyDisconnected) return
    if (
      this.socket !== null
      && (this.socket.readyState === SOCKET_CONNECTING
        || this.socket.readyState === SOCKET_OPEN)
    ) {
      return
    }

    this.emitStatus(isReconnect ? 'reconnecting' : 'connecting')
    const generation = ++this.generation
    let socket: WebSocketLike
    try {
      socket = this.webSocketFactory(this.targetUrl)
    } catch {
      this.emitError('Unable to create realtime WebSocket')
      this.scheduleReconnect()
      return
    }
    this.socket = socket

    socket.onopen = () => {
      if (!this.isCurrentSocket(socket, generation)) return
      this.reconnectAttempt = 0
      this.emitStatus('connected')
    }
    socket.onmessage = (event) => {
      if (!this.isCurrentSocket(socket, generation)) return
      const message = parseRealtimeMessage(event.data)
      if (!message) {
        this.subscribers.forEach((subscriber) =>
          subscriber.onInvalidMessage?.(),
        )
        return
      }
      this.subscribers.forEach((subscriber) =>
        subscriber.onMessage?.(message),
      )
    }
    socket.onerror = () => {
      if (!this.isCurrentSocket(socket, generation)) return
      this.emitStatus('error')
      this.emitError('Realtime WebSocket error')
    }
    socket.onclose = () => {
      if (!this.isCurrentSocket(socket, generation)) return
      this.socket = null
      if (this.manuallyDisconnected) {
        this.emitStatus('disconnected')
        return
      }
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (
      this.manuallyDisconnected
      || !this.targetUrl
      || this.reconnectTimer !== null
    ) {
      return
    }

    const delayIndex = Math.min(
      this.reconnectAttempt,
      this.reconnectDelaysMs.length - 1,
    )
    const delay = this.reconnectDelaysMs[delayIndex] ?? 8_000
    this.reconnectAttempt += 1
    this.emitStatus('reconnecting')
    this.reconnectTimer = this.setTimer(() => {
      this.reconnectTimer = null
      this.openSocket(true)
    }, delay)
  }

  private isCurrentSocket(socket: WebSocketLike, generation: number): boolean {
    return this.socket === socket && this.generation === generation
  }

  private closeCurrentSocket(): void {
    const socket = this.socket
    this.socket = null
    if (socket !== null) socket.close()
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer === null) return
    this.clearTimer(this.reconnectTimer)
    this.reconnectTimer = null
  }

  private emitStatus(status: RealtimeConnectionStatus): void {
    this.currentStatus = status
    this.subscribers.forEach((subscriber) => subscriber.onStatus?.(status))
  }

  private emitError(message: string): void {
    this.subscribers.forEach((subscriber) => subscriber.onError?.(message))
  }
}

export const websocketBrainService = new WebSocketBrainService()
