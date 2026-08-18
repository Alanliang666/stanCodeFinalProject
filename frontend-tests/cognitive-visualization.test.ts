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
    eyeWide_L: 0.025,
    eyeWide_R: 0.025,
    browOuterUp_L: 0.015,
    browOuterUp_R: 0.015,
  })
  assert.equal(COGNITIVE_FACE_PRESETS.focused.browDown_L, 0.42)
  assert.equal(COGNITIVE_FACE_PRESETS.focused.eyeSquint_R, 0.32)
  assert.equal(COGNITIVE_FACE_PRESETS.focused.mouthPress_L, 0.30)
  assert.equal(COGNITIVE_FACE_PRESETS.focused.mouthFrown_R, 0.08)
})

test('blink composes over focused without clearing cognitive weights', () => {
  const blink = getBlinkLayer(4.2 - 0.18 / 2)
  const composed = composeMorphLayers(
    COGNITIVE_FACE_PRESETS.focused,
    blink,
  )

  assert.equal(composed.browDown_L, 0.42)
  assert.equal(composed.mouthPress_R, 0.30)
  assert.ok((composed.eyeBlink_L ?? 0) > 0.99)
  assert.ok((composed.eyeBlink_R ?? 0) > 0.99)
})
