import type { CognitiveState } from '@/types/brain'
import type { EEGChunkMessage } from '@/types/eeg'
import type {
  CognitivePredictionMessage,
  DeviceStatusMessage,
  RealtimeMessage,
} from '@/types/realtime'

const REQUIRED_CHANNEL_ORDER = ['TP9', 'AF7', 'AF8', 'TP10'] as const
const REQUIRED_COGNITIVE_STATES = [
  'neutral',
  'concentrating',
] as const satisfies readonly CognitiveState[]
const PROBABILITY_TOLERANCE = 1e-6

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isFiniteUnitValue(value: unknown): value is number {
  return typeof value === 'number'
    && Number.isFinite(value)
    && value >= 0
    && value <= 1
}

function hasRequiredChannelOrder(value: unknown): boolean {
  return Array.isArray(value)
    && value.length === REQUIRED_CHANNEL_ORDER.length
    && REQUIRED_CHANNEL_ORDER.every((channel, index) => value[index] === channel)
}

function hasOnlyFiniteNumbers(value: unknown): value is number[] {
  return Array.isArray(value)
    && value.every((entry) => typeof entry === 'number' && Number.isFinite(entry))
}

export function isDeviceStatusMessage(
  value: unknown,
): value is DeviceStatusMessage {
  if (!isRecord(value) || value.type !== 'device_status' || !isRecord(value.data)) {
    return false
  }

  const data = value.data
  return typeof data.connected === 'boolean'
    && typeof data.device === 'string'
    && data.device.trim().length > 0
    && data.sampling_rate_hz === 256
    && hasRequiredChannelOrder(data.channel_order)
}

export function isEEGChunkMessage(value: unknown): value is EEGChunkMessage {
  if (!isRecord(value) || value.type !== 'eeg_chunk' || !isRecord(value.data)) {
    return false
  }

  const data = value.data
  if (
    data.sampling_rate_hz !== 256
    || !hasRequiredChannelOrder(data.channel_order)
    || !hasOnlyFiniteNumbers(data.timestamps)
    || !Array.isArray(data.samples)
    || data.samples.length === 0
    || data.samples.length !== data.timestamps.length
  ) {
    return false
  }

  return data.samples.every((row) =>
    hasOnlyFiniteNumbers(row) && row.length === REQUIRED_CHANNEL_ORDER.length,
  )
}

export function isCognitivePredictionMessage(
  value: unknown,
): value is CognitivePredictionMessage {
  if (
    !isRecord(value)
    || value.type !== 'cognitive_prediction'
    || !isRecord(value.data)
  ) {
    return false
  }

  const data = value.data
  if (
    typeof data.timestamp !== 'number'
    || !Number.isFinite(data.timestamp)
    || typeof data.state !== 'string'
    || !REQUIRED_COGNITIVE_STATES.includes(data.state as CognitiveState)
    || !isFiniteUnitValue(data.confidence)
    || !isRecord(data.probabilities)
  ) {
    return false
  }

  const probabilityPayload = data.probabilities
  const probabilityKeys = Object.keys(probabilityPayload)
  if (
    probabilityKeys.length !== REQUIRED_COGNITIVE_STATES.length
    || !REQUIRED_COGNITIVE_STATES.every((state) =>
      probabilityKeys.includes(state)
      && isFiniteUnitValue(probabilityPayload[state]),
    )
  ) {
    return false
  }

  const probabilities = probabilityPayload as Record<CognitiveState, number>
  const probabilitySum = REQUIRED_COGNITIVE_STATES.reduce(
    (total, state) => total + probabilities[state],
    0,
  )
  const state = data.state as CognitiveState
  const stateProbability = probabilities[state]
  const highestProbability = Math.max(
    ...REQUIRED_COGNITIVE_STATES.map((candidate) => probabilities[candidate]),
  )

  return Math.abs(probabilitySum - 1) <= PROBABILITY_TOLERANCE
    && Math.abs(stateProbability - highestProbability) <= PROBABILITY_TOLERANCE
    && Math.abs(data.confidence - stateProbability) <= PROBABILITY_TOLERANCE
}

export function parseRealtimeMessage(input: string | unknown): RealtimeMessage | null {
  let value: unknown = input
  if (typeof input === 'string') {
    try {
      value = JSON.parse(input) as unknown
    } catch {
      return null
    }
  }

  if (isDeviceStatusMessage(value)) return value
  if (isEEGChunkMessage(value)) return value
  if (isCognitivePredictionMessage(value)) return value
  return null
}
