import assert from 'node:assert/strict'
import test from 'node:test'
import {
  isCognitivePredictionMessage,
  isDeviceStatusMessage,
  isEEGChunkMessage,
  parseRealtimeMessage,
} from '../src/services/brain/realtimeMessageValidators'
import {
  getMockCognitiveState,
  MOCK_COGNITIVE_STATE_DURATION_MS,
} from '../src/services/brain/mockBrainService'

const channelOrder = ['TP9', 'AF7', 'AF8', 'TP10']

test('accepts the backend device_status contract', () => {
  assert.equal(isDeviceStatusMessage({
    type: 'device_status',
    data: {
      connected: true,
      device: 'Synthetic Muse 2',
      sampling_rate_hz: 256,
      channel_order: channelOrder,
    },
  }), true)
})

test('accepts variable-size eeg_chunk data with shape (N, 4)', () => {
  assert.equal(isEEGChunkMessage({
    type: 'eeg_chunk',
    data: {
      sampling_rate_hz: 256,
      channel_order: channelOrder,
      timestamps: [1, 1 + 1 / 256],
      samples: [[1, 2, 3, 4], [5, 6, 7, 8]],
    },
  }), true)
})

test('accepts the formal cognitive_prediction contract', () => {
  assert.equal(isCognitivePredictionMessage({
    type: 'cognitive_prediction',
    data: {
      timestamp: 1_234_567_890.123,
      state: 'neutral',
      confidence: 0.82,
      probabilities: {
        neutral: 0.82,
        concentrating: 0.18,
      },
    },
  }), true)
})

test('ignores unknown or invalid JSON messages safely', () => {
  assert.equal(parseRealtimeMessage('{"type":"unknown"}'), null)
  assert.equal(parseRealtimeMessage('{not-json'), null)
})

test('rejects malformed samples and wrong channel order', () => {
  const base = {
    type: 'eeg_chunk',
    data: {
      sampling_rate_hz: 256,
      channel_order: channelOrder,
      timestamps: [1],
      samples: [[1, 2, 3]],
    },
  }
  assert.equal(isEEGChunkMessage(base), false)
  assert.equal(isEEGChunkMessage({
    ...base,
    data: {
      ...base.data,
      channel_order: ['AF7', 'AF8', 'TP9', 'TP10'],
      samples: [[1, 2, 3, 4]],
    },
  }), false)
})

test('rejects illegal cognitive states and malformed probabilities', () => {
  const base = {
    type: 'cognitive_prediction',
    data: {
      timestamp: 1,
      state: 'focused',
      confidence: 0.7,
      probabilities: {
        neutral: 0.7,
        concentrating: 0.3,
      },
    },
  }
  assert.equal(isCognitivePredictionMessage(base), false)
  assert.equal(isCognitivePredictionMessage({
    ...base,
    data: {
      ...base.data,
      state: 'neutral',
      probabilities: { neutral: 0.7 },
    },
  }), false)

  assert.equal(isCognitivePredictionMessage({
    ...base,
    data: {
      ...base.data,
      state: 'neutral',
      probabilities: {
        neutral: 0.7,
        concentrating: 0.3,
        relaxed: 0,
      },
    },
  }), false)

  assert.equal(isCognitivePredictionMessage({
    ...base,
    data: {
      ...base.data,
      state: 'relaxed',
    },
  }), false)
})

test('frontend mock uses a deterministic three-second binary cycle', () => {
  assert.equal(getMockCognitiveState(0), 'neutral')
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS - 1),
    'neutral',
  )
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS),
    'concentrating',
  )
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS * 2),
    'neutral',
  )
})
