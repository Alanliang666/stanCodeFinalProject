import type { CognitiveVisualState } from '@/types/avatar'

const COGNITIVE_FACE_MORPH_TARGETS = [
  'browInnerUp',
  'browDown_L',
  'browDown_R',
  'browOuterUp_L',
  'browOuterUp_R',
  'eyeLookUp_L',
  'eyeLookUp_R',
  'eyeWide_L',
  'eyeWide_R',
  'eyeSquint_L',
  'eyeSquint_R',
  'eyeBlink_L',
  'eyeBlink_R',
  'noseSneer_L',
  'noseSneer_R',
  'jawOpen',
  'jawForward',
  'mouthPress_L',
  'mouthPress_R',
  'mouthFrown_L',
  'mouthFrown_R',
  'mouthShrugLower',
  'mouthShrugUpper',
  'mouthRollLower',
] as const

export type CognitiveFaceMorphTarget =
  (typeof COGNITIVE_FACE_MORPH_TARGETS)[number]

export type CognitiveFacePreset = Readonly<
  Partial<Record<CognitiveFaceMorphTarget, number>>
>

export const COGNITIVE_FACE_PRESETS = {
  idle: {},
  relaxedOpenEye: {
    browOuterUp_L: 0.18,
    browOuterUp_R: 0.18,
    eyeLookUp_L: 1.0,
    eyeLookUp_R: 1.0,
    eyeWide_L: 0.34,
    eyeWide_R: 0.34,
    jawOpen: 0.20,
    mouthShrugLower: 0.22,
    mouthRollLower: 0.12,
  },
  focused: {
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
  },
  relaxedCloseEye: {
    eyeBlink_L: 0.98,
    eyeBlink_R: 0.98,
    jawOpen: 0.035,
  },
} as const satisfies Record<CognitiveVisualState, CognitiveFacePreset>

export function getCognitiveFacePreset(
  state: CognitiveVisualState,
): CognitiveFacePreset {
  return COGNITIVE_FACE_PRESETS[state]
}
