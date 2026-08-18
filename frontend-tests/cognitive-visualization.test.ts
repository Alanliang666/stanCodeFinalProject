import assert from 'node:assert/strict'
import test from 'node:test'
import {
  composeMorphLayers,
  getBlinkLayer,
} from '../src/visualization/expressionLayers'
import {
  COGNITIVE_FACE_PRESETS,
} from '../src/visualization/cognitiveFacePresets'
import {
  mapCognitivePredictionToVisualState,
} from '../src/visualization/cognitiveVisualStateAdapter'

test('formal prediction maps only to binary FaceCap visual states', () => {
  assert.equal(mapCognitivePredictionToVisualState(null), 'neutral')
  assert.equal(mapCognitivePredictionToVisualState({
    state: 'neutral',
    confidence: 0.82,
    probabilities: { neutral: 0.82, concentrating: 0.18 },
  }), 'neutral')
  assert.equal(mapCognitivePredictionToVisualState({
    state: 'concentrating',
    confidence: 0.90,
    probabilities: { neutral: 0.10, concentrating: 0.90 },
  }), 'focused')
})

test('FaceCap presets contain only neutral and focused', () => {
  assert.deepEqual(Object.keys(COGNITIVE_FACE_PRESETS), [
    'neutral',
    'focused',
  ])
  assert.deepEqual(COGNITIVE_FACE_PRESETS.neutral, {
    eyeLookUp_L: 0.78,
    eyeLookUp_R: 0.78,
    eyeWide_L: 0.36,
    eyeWide_R: 0.36,
    jawOpen: 0.22,
    mouthShrugLower: 0.28,
    mouthRollLower: 0.18,
  })
  assert.deepEqual(COGNITIVE_FACE_PRESETS.focused, {
    browInnerUp: 0.38,
    browDown_L: 1.0,
    browDown_R: 1.0,
    eyeSquint_L: 0.90,
    eyeSquint_R: 0.90,
    noseSneer_L: 0.65,
    noseSneer_R: 0.65,
    mouthPress_L: 0.78,
    mouthPress_R: 0.78,
    mouthFrown_L: 0.42,
    mouthFrown_R: 0.42,
    mouthShrugUpper: 0.55,
    jawForward: 0.48,
  })
})

test('blink composes over focused without clearing cognitive weights', () => {
  const blink = getBlinkLayer(4.2 - 0.18 / 2)
  const composed = composeMorphLayers(
    COGNITIVE_FACE_PRESETS.focused,
    blink,
  )

  assert.equal(composed.browDown_L, 1.0)
  assert.equal(composed.mouthPress_R, 0.78)
  assert.ok((composed.eyeBlink_L ?? 0) > 0.99)
  assert.ok((composed.eyeBlink_R ?? 0) > 0.99)
})
