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
export const MOCK_COGNITIVE_STATE_DURATION_MS = 3_000

function randomWalk(value: number, volatility: number): number {
  return clamp(value + (Math.random() - 0.5) * volatility)
}

function createProbabilities(
  state: CognitiveState,
  confidence: number,
): Record<CognitiveState, number> {
  const remainingProbability = 1 - confidence
  return Object.fromEntries(
    COGNITIVE_STATES.map((candidate) => [
      candidate,
      candidate === state ? confidence : remainingProbability,
    ]),
  ) as Record<CognitiveState, number>
}

export function getMockCognitiveState(elapsedMs: number): CognitiveState {
  const phase = Math.floor(
    Math.max(0, elapsedMs) / MOCK_COGNITIVE_STATE_DURATION_MS,
  ) % 2
  return phase === 0 ? 'neutral' : 'concentrating'
}

function getMockConfidence(state: CognitiveState): number {
  return state === 'neutral' ? 0.82 : 0.90
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
      state: 'neutral',
      confidence: 0.82,
      probabilities: createProbabilities('neutral', 0.82),
    },
  }
}

export class MockBrainService {
  private timer: ReturnType<typeof setInterval> | null = null
  private listeners = new Set<BrainPredictionListener>()
  private currentPrediction = createInitialPrediction()
  private startedAt = 0

  subscribe(listener: BrainPredictionListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  start(updateInterval = DEFAULT_UPDATE_INTERVAL): void {
    if (this.timer !== null) return

    this.startedAt = Date.now()
    this.currentPrediction = createInitialPrediction()
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
    const state = getMockCognitiveState(Date.now() - this.startedAt)
    const confidence = getMockConfidence(state)
    return {
      timestamp: Date.now(),
      eeg: {
        channels: (previous.eeg?.channels ?? []).map(
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
        state,
        confidence,
        probabilities: createProbabilities(state, confidence),
      },
    }
  }
}

export const mockBrainService = new MockBrainService()
