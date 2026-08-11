export const EMOTION_STATES = [
  'neutral',
  'happy',
  'sad',
  'angry',
  'surprise',
] as const

export const COGNITIVE_STATES = [
  'neutral',
  'thinking',
  'focused',
  'mindWandering',
  'uncertain',
  'relaxed',
] as const

export const EEG_CHANNEL_NAMES = [
  'Fp1',
  'Fp2',
  'F3',
  'F4',
  'C3',
  'C4',
  'P3',
  'P4',
  'O1',
  'O2',
] as const

export type EmotionState = (typeof EMOTION_STATES)[number]
export type CognitiveState = (typeof COGNITIVE_STATES)[number]
export type EEGChannelName = (typeof EEG_CHANNEL_NAMES)[number]

export interface EEGChannel {
  name: EEGChannelName
  value: number
}

export interface BrainPrediction {
  timestamp: number

  eeg: {
    channels: EEGChannel[]
  }

  emotion: {
    state: EmotionState
    confidence: number
  }

  cognition: {
    state: CognitiveState
    confidence: number
  }

  metrics: {
    attention: number
    cognitiveLoad: number
    arousal: number
    mindWandering: number
  }
}

export type BrainConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error'
