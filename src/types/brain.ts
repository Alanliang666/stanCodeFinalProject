import type { MockEEGVisualization } from '@/types/eeg'

export const COGNITIVE_STATES = [
  'relaxed_openeye',
  'concentration',
  'relaxed_closeeye',
] as const

export type CognitiveState = (typeof COGNITIVE_STATES)[number]

export interface CognitivePrediction {
  state: CognitiveState
  confidence: number
  probabilities: Record<CognitiveState, number>
}

export interface BrainPrediction {
  timestamp: number

  eeg?: MockEEGVisualization

  cognition: CognitivePrediction
}

export type BrainDataSource = 'mock' | 'websocket'

export type RealtimeConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
  | 'error'
