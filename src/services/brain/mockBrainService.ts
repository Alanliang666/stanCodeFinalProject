import { clamp } from '@/utils/clamp'
import {
  COGNITIVE_STATES,
  EEG_CHANNEL_NAMES,
  EMOTION_STATES,
  type BrainPrediction,
  type CognitiveState,
  type EEGChannel,
  type EmotionState,
} from '@/types/brain'

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
      channels: EEG_CHANNEL_NAMES.map((name) => ({
        name,
        value: 0.25 + Math.random() * 0.5,
      })),
    },
    emotion: {
      state: 'neutral',
      confidence: 0.72,
    },
    cognition: {
      state: 'focused',
      confidence: 0.78,
    },
    metrics: {
      attention: 0.74,
      cognitiveLoad: 0.52,
      arousal: 0.46,
      mindWandering: 0.21,
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
          (channel): EEGChannel => ({
            ...channel,
            value: randomWalk(channel.value, 0.24),
          }),
        ),
      },
      emotion: {
        state: nextState<EmotionState>(
          previous.emotion.state,
          EMOTION_STATES,
        ),
        confidence: randomWalk(previous.emotion.confidence, 0.15),
      },
      cognition: {
        state: nextState<CognitiveState>(
          previous.cognition.state,
          COGNITIVE_STATES,
        ),
        confidence: randomWalk(previous.cognition.confidence, 0.15),
      },
      metrics: {
        attention: randomWalk(previous.metrics.attention, 0.16),
        cognitiveLoad: randomWalk(previous.metrics.cognitiveLoad, 0.16),
        arousal: randomWalk(previous.metrics.arousal, 0.16),
        mindWandering: randomWalk(previous.metrics.mindWandering, 0.16),
      },
    }
  }
}

export const mockBrainService = new MockBrainService()
