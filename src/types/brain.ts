import type { MockEEGVisualization } from '@/types/eeg'

export const COGNITIVE_STATES = [
  'neutral',
  'thinking',
  'focused',
  'mindWandering',
  'uncertain',
  'relaxed',
] as const

export type CognitiveState = (typeof COGNITIVE_STATES)[number]

export interface CognitivePrediction {
  state: CognitiveState
  confidence: number
}

export interface BrainPrediction {
  timestamp: number

  eeg: MockEEGVisualization

  cognition: CognitivePrediction
}

export type BrainConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error'
