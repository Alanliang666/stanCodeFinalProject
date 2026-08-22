export type AvatarLoadStatus = 'loading' | 'loaded' | 'error'

export interface AvatarLoadState {
  status: AvatarLoadStatus
  progress: number
  message?: string
}

export type FacialMorphMode = 'native' | 'procedural' | 'unavailable'

export interface FacialMorphState {
  mode: FacialMorphMode
  meshCount: number
  targetCount: number
}

export type CognitiveVisualState =
  | 'idle'
  | 'relaxedOpenEye'
  | 'focused'
  | 'relaxedCloseEye'
