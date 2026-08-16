import { clamp } from '@/utils/clamp'
import {
  COGNITIVE_STATES,
  type BrainPrediction,
  type CognitiveState,
} from '@/types/brain'
import {
  MUSE_EEG_CHANNELS,
  type MockEEGVisualizationChannel,
} from '@/types/eeg'

export type BrainPredictionListener = (prediction: BrainPrediction) => void

const DEFAULT_UPDATE_INTERVAL = 1_000
const STATE_CHANGE_PROBABILITY = 0.2

function randomItem<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)] as T
}

function randomWalk(value: number, volatility: number): number {
  return clamp(value + (Math.random() - 0.5) * volatility)
}

function createInitialPrediction(): BrainPrediction {
  return {
    timestamp: Date.now(),
    eeg: {
      kind: 'mock-normalized',
      channels: MUSE_EEG_CHANNELS.map((name) => ({
        name,
        normalizedValue: 0.25 + Math.random() * 0.5,
      })),
    },
    cognition: {
      state: 'focused',
      confidence: 0.78,
    },
  }
}

function nextState<T>(current: T, candidates: readonly T[]): T {
  return Math.random() < STATE_CHANGE_PROBABILITY
    ? randomItem(candidates)
    : current
}

export class MockBrainService {
  private timer: ReturnType<typeof setInterval> | null = null
  private listeners = new Set<BrainPredictionListener>()
  private currentPrediction = createInitialPrediction()

  subscribe(listener: BrainPredictionListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  start(updateInterval = DEFAULT_UPDATE_INTERVAL): void {
    if (this.timer !== null) return

    this.emit(this.currentPrediction)
    this.timer = setInterval(() => {
      this.currentPrediction = this.generatePrediction(this.currentPrediction)
      this.emit(this.currentPrediction)
    }, updateInterval)
  }

  stop(): void {
    if (this.timer === null) return
    clearInterval(this.timer)
    this.timer = null
  }

  private emit(prediction: BrainPrediction): void {
    this.listeners.forEach((listener) => listener(prediction))
  }

  private generatePrediction(previous: BrainPrediction): BrainPrediction {
    return {
      timestamp: Date.now(),
      eeg: {
        channels: previous.eeg.channels.map(
          (channel): MockEEGVisualizationChannel => ({
            ...channel,
            normalizedValue: randomWalk(
              channel.normalizedValue,
              0.24,
            ),
          }),
        ),
        kind: 'mock-normalized',
      },
      cognition: {
        state: nextState<CognitiveState>(
          previous.cognition.state,
          COGNITIVE_STATES,
        ),
        confidence: randomWalk(previous.cognition.confidence, 0.15),
      },
    }
  }
}

export const mockBrainService = new MockBrainService()
