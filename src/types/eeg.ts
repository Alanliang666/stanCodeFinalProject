export const MUSE_EEG_CHANNELS = [
  'AF7',
  'AF8',
  'TP9',
  'TP10',
] as const

export type MuseEEGChannel = (typeof MUSE_EEG_CHANNELS)[number]

export interface MockEEGVisualizationChannel {
  name: MuseEEGChannel
  normalizedValue: number
}

export interface MockEEGVisualization {
  kind: 'mock-normalized'
  channels: MockEEGVisualizationChannel[]
}

export interface ElectrodeVisualState {
  size: number
  opacity: number
  emissiveIntensity: number
  glowSize: number
  glowOpacity: number
}
