export const MUSE_EEG_CHANNELS = [
  'AF7',
  'AF8',
  'TP9',
  'TP10',
] as const

export type MuseEEGChannel = (typeof MUSE_EEG_CHANNELS)[number]

export const LIVE_EEG_CHANNEL_ORDER = [
  'TP9',
  'AF7',
  'AF8',
  'TP10',
] as const satisfies readonly MuseEEGChannel[]

export interface EEGChunkData {
  sampling_rate_hz: number
  channel_order: readonly MuseEEGChannel[]
  timestamps: readonly number[]
  samples: readonly (readonly number[])[]
}

export interface EEGChunkMessage {
  type: 'eeg_chunk'
  data: EEGChunkData
}

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
