import assert from 'node:assert/strict'
import test from 'node:test'
import {
  composeMorphLayers,
  getBlinkLayer,
  getBlinkLayerForVisualState,
} from '../src/visualization/expressionLayers'
import {
  COGNITIVE_FACE_PRESETS,
} from '../src/visualization/cognitiveFacePresets'
import {
  mapCognitivePredictionToVisualState,
} from '../src/visualization/cognitiveVisualStateAdapter'

test('formal predictions map to separate three-state FaceCap visuals', () => {
  assert.equal(mapCognitivePredictionToVisualState(null), 'idle')
  assert.equal(mapCognitivePredictionToVisualState({
    state: 'relaxed_openeye',
    confidence: 0.82,
    probabilities: {
      relaxed_openeye: 0.82,
      concentration: 0.10,
      relaxed_closeeye: 0.08,
    },
  }), 'relaxedOpenEye')
  assert.equal(mapCognitivePredictionToVisualState({
    state: 'concentration',
    confidence: 0.88,
    probabilities: {
      relaxed_openeye: 0.06,
      concentration: 0.88,
      relaxed_closeeye: 0.06,
    },
  }), 'focused')
  assert.equal(mapCognitivePredictionToVisualState({
    state: 'relaxed_closeeye',
    confidence: 0.84,
    probabilities: {
      relaxed_openeye: 0.08,
      concentration: 0.08,
      relaxed_closeeye: 0.84,
    },
  }), 'relaxedCloseEye')
})

test('FaceCap presets include baseline and three distinct expressions', () => {
  assert.deepEqual(Object.keys(COGNITIVE_FACE_PRESETS), [
    'idle',
    'relaxedOpenEye',
    'focused',
    'relaxedCloseEye',
  ])
  assert.deepEqual(COGNITIVE_FACE_PRESETS.idle, {})
  assert.deepEqual(COGNITIVE_FACE_PRESETS.relaxedOpenEye, {
    browOuterUp_L: 0.18,
    browOuterUp_R: 0.18,
    eyeLookUp_L: 1.0,
    eyeLookUp_R: 1.0,
    eyeWide_L: 0.34,
    eyeWide_R: 0.34,
    jawOpen: 0.20,
    mouthShrugLower: 0.22,
    mouthRollLower: 0.12,
  })
  assert.deepEqual(COGNITIVE_FACE_PRESETS.focused, {
    browInnerUp: 0.32,
    browDown_L: 1.0,
    browDown_R: 1.0,
    eyeSquint_L: 0.86,
    eyeSquint_R: 0.86,
    noseSneer_L: 0.72,
    noseSneer_R: 0.72,
    mouthPress_L: 0.86,
    mouthPress_R: 0.86,
    mouthFrown_L: 0.36,
    mouthFrown_R: 0.36,
    mouthShrugUpper: 0.62,
    jawForward: 0.44,
  })
  assert.deepEqual(COGNITIVE_FACE_PRESETS.relaxedCloseEye, {
    eyeBlink_L: 0.98,
    eyeBlink_R: 0.98,
    jawOpen: 0.035,
  })
})

test('blink composes over focused without clearing cognitive weights', () => {
  const blink = getBlinkLayer(4.2 - 0.18 / 2)
  const composed = composeMorphLayers(
    COGNITIVE_FACE_PRESETS.focused,
    blink,
  )

  assert.equal(composed.browDown_L, 1.0)
  assert.equal(composed.mouthPress_R, 0.86)
  assert.ok((composed.eyeBlink_L ?? 0) > 0.99)
  assert.ok((composed.eyeBlink_R ?? 0) > 0.99)
})

test('relaxed closed-eye expression owns eyelids and suppresses auto blink', () => {
  const blinkPeak = 4.2 - 0.18 / 2

  assert.deepEqual(
    getBlinkLayerForVisualState('relaxedCloseEye', blinkPeak),
    {},
  )
  assert.ok(
    (getBlinkLayerForVisualState('relaxedOpenEye', blinkPeak).eyeBlink_L ?? 0)
      > 0.99,
  )
  const composed = composeMorphLayers(
    COGNITIVE_FACE_PRESETS.relaxedCloseEye,
    getBlinkLayerForVisualState('relaxedCloseEye', blinkPeak),
  )
  assert.equal(composed.eyeBlink_L, 0.98)
  assert.equal(composed.eyeBlink_R, 0.98)
})
