import type { CognitivePrediction } from '@/types/brain'
import type {
  EEGChunkMessage,
  MuseEEGChannel,
} from '@/types/eeg'

export interface DeviceStatusData {
  connected: boolean
  device: string
  sampling_rate_hz: number
  channel_order: readonly MuseEEGChannel[]
}

export interface DeviceStatusMessage {
  type: 'device_status'
  data: DeviceStatusData
}

export interface CognitivePredictionData extends CognitivePrediction {
  timestamp: number
}

export interface CognitivePredictionMessage {
  type: 'cognitive_prediction'
  data: CognitivePredictionData
}

export type RealtimeMessage =
  | DeviceStatusMessage
  | EEGChunkMessage
  | CognitivePredictionMessage
