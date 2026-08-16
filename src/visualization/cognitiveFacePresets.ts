import type { CognitiveVisualState } from '@/types/avatar'

const COGNITIVE_FACE_MORPH_TARGETS = [
  'browInnerUp',
  'browDown_L',
  'browDown_R',
  'browOuterUp_L',
  'browOuterUp_R',
  'eyeLookOut_L',
  'eyeLookIn_R',
  'eyeSquint_L',
  'eyeSquint_R',
  'noseSneer_L',
  'noseSneer_R',
  'mouthLeft',
  'mouthPress_L',
  'mouthPress_R',
] as const

export type CognitiveFaceMorphTarget =
  (typeof COGNITIVE_FACE_MORPH_TARGETS)[number]

export type CognitiveFacePreset = Readonly<
  Partial<Record<CognitiveFaceMorphTarget, number>>
>

export const COGNITIVE_FACE_PRESETS = {
  neutral: {},
  focused: {
    browDown_L: 0.08,
    browDown_R: 0.08,
    eyeSquint_L: 0.055,
    eyeSquint_R: 0.055,
    mouthPress_L: 0.025,
    mouthPress_R: 0.025,
  },
  distracted: {
    browOuterUp_L: 0.055,
    browOuterUp_R: 0.055,
    eyeLookOut_L: 0.1,
    eyeLookIn_R: 0.1,
    mouthLeft: 0.035,
  },
  high_load: {
    browInnerUp: 0.09,
    browDown_L: 0.055,
    browDown_R: 0.055,
    eyeSquint_L: 0.09,
    eyeSquint_R: 0.09,
    noseSneer_L: 0.025,
    noseSneer_R: 0.025,
    mouthPress_L: 0.07,
    mouthPress_R: 0.07,
  },
} as const satisfies Record<CognitiveVisualState, CognitiveFacePreset>

export function getCognitiveFacePreset(
  state: CognitiveVisualState,
): CognitiveFacePreset {
  return COGNITIVE_FACE_PRESETS[state]
}
