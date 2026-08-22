import assert from 'node:assert/strict'
import test from 'node:test'
import {
  isCognitivePredictionMessage,
  isDeviceStatusMessage,
  isEEGChunkMessage,
  parseRealtimeMessage,
} from '../src/services/brain/realtimeMessageValidators'
import {
  createMockProbabilities,
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

test('accepts variable-size eeg_chunk data independent of model window', () => {
  for (const sampleCount of [1, 17, 32, 256, 512]) {
    const timestamps = Array.from(
      { length: sampleCount },
      (_, index) => 1 + index / 256,
    )
    const samples = Array.from(
      { length: sampleCount },
      (_, index) => [index, index + 1, index + 2, index + 3],
    )
    assert.equal(isEEGChunkMessage({
      type: 'eeg_chunk',
      data: {
        sampling_rate_hz: 256,
        channel_order: channelOrder,
        timestamps,
        samples,
      },
    }), true)
  }
})

test('accepts all three formal cognitive_prediction states', () => {
  const predictions = [
    {
      state: 'relaxed_openeye',
      confidence: 0.82,
      probabilities: {
        relaxed_openeye: 0.82,
        concentration: 0.10,
        relaxed_closeeye: 0.08,
      },
    },
    {
      state: 'concentration',
      confidence: 0.88,
      probabilities: {
        relaxed_openeye: 0.06,
        concentration: 0.88,
        relaxed_closeeye: 0.06,
      },
    },
    {
      state: 'relaxed_closeeye',
      confidence: 0.84,
      probabilities: {
        relaxed_openeye: 0.08,
        concentration: 0.08,
        relaxed_closeeye: 0.84,
      },
    },
  ]

  for (const prediction of predictions) {
    assert.equal(isCognitivePredictionMessage({
      type: 'cognitive_prediction',
      data: {
        timestamp: 1_234_567_890.123,
        ...prediction,
      },
    }), true)
  }
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

test('rejects legacy or unknown states, incomplete classes, and extras', () => {
  const base = {
    type: 'cognitive_prediction',
    data: {
      timestamp: 1,
      state: 'concentration',
      confidence: 0.88,
      probabilities: {
        relaxed_openeye: 0.06,
        concentration: 0.88,
        relaxed_closeeye: 0.06,
      },
    },
  }
  for (const legacyState of ['neutral', 'concentrating', 'focused', 'unknown']) {
    assert.equal(isCognitivePredictionMessage({
      ...base,
      data: { ...base.data, state: legacyState },
    }), false)
  }

  assert.equal(isCognitivePredictionMessage({
    ...base,
    data: {
      ...base.data,
      probabilities: {
        relaxed_openeye: 0.12,
        concentration: 0.88,
      },
    },
  }), false)

  for (const legacyClass of ['neutral', 'concentrating', 'unknown']) {
    assert.equal(isCognitivePredictionMessage({
      ...base,
      data: {
        ...base.data,
        probabilities: {
          ...base.data.probabilities,
          [legacyClass]: 0,
        },
      },
    }), false)
  }
})

test('rejects non-finite, sum, argmax, and confidence invariant violations', () => {
  const base = {
    type: 'cognitive_prediction',
    data: {
      timestamp: 1,
      state: 'concentration',
      confidence: 0.88,
      probabilities: {
        relaxed_openeye: 0.06,
        concentration: 0.88,
        relaxed_closeeye: 0.06,
      },
    },
  }
  const invalidData = [
    {
      ...base.data,
      probabilities: {
        ...base.data.probabilities,
        relaxed_openeye: Number.NaN,
      },
    },
    {
      ...base.data,
      probabilities: {
        relaxed_openeye: 0.10,
        concentration: 0.70,
        relaxed_closeeye: 0.10,
      },
      confidence: 0.70,
    },
    {
      ...base.data,
      state: 'relaxed_openeye',
      confidence: 0.06,
    },
    {
      ...base.data,
      confidence: 0.80,
    },
  ]

  for (const data of invalidData) {
    assert.equal(isCognitivePredictionMessage({ ...base, data }), false)
  }
})

test('frontend mock uses a deterministic three-state canonical cycle', () => {
  assert.equal(getMockCognitiveState(0), 'relaxed_openeye')
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS - 1),
    'relaxed_openeye',
  )
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS),
    'concentration',
  )
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS * 2),
    'relaxed_closeeye',
  )
  assert.equal(
    getMockCognitiveState(MOCK_COGNITIVE_STATE_DURATION_MS * 3),
    'relaxed_openeye',
  )

  const probabilities = createMockProbabilities('concentration', 0.88)
  assert.deepEqual(Object.keys(probabilities), [
    'relaxed_openeye',
    'concentration',
    'relaxed_closeeye',
  ])
  assert.ok(Math.abs(Object.values(probabilities).reduce(
    (sum, probability) => sum + probability,
    0,
  ) - 1) <= 1e-6)
})
