import type { BrainDataSource } from '@/types/brain'

export interface BrainStreamModeActions {
  startMock: () => void
  stopMock: () => void
  startWebSocket: () => void
  stopWebSocket: () => void
}

export class BrainStreamModeController {
  private activeSource: BrainDataSource | null = null
  private readonly actions: BrainStreamModeActions

  constructor(actions: BrainStreamModeActions) {
    this.actions = actions
  }

  start(source: BrainDataSource): void {
    if (this.activeSource === source) return
    this.stop()
    this.activeSource = source
    if (source === 'mock') {
      this.actions.startMock()
      return
    }
    this.actions.startWebSocket()
  }

  stop(): void {
    if (this.activeSource === 'mock') this.actions.stopMock()
    if (this.activeSource === 'websocket') this.actions.stopWebSocket()
    this.activeSource = null
  }

  get currentSource(): BrainDataSource | null {
    return this.activeSource
  }
}
