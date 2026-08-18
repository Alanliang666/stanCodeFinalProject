import type { CognitiveVisualState } from '@/types/avatar'

const COGNITIVE_FACE_MORPH_TARGETS = [
  'browInnerUp',
  'browDown_L',
  'browDown_R',
  'eyeLookUp_L',
  'eyeLookUp_R',
  'eyeWide_L',
  'eyeWide_R',
  'eyeSquint_L',
  'eyeSquint_R',
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
  neutral: {
    eyeLookUp_L: 0.78,
    eyeLookUp_R: 0.78,
    eyeWide_L: 0.36,
    eyeWide_R: 0.36,
    jawOpen: 0.22,
    mouthShrugLower: 0.28,
    mouthRollLower: 0.18,
  },
  focused: {
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
  },
} as const satisfies Record<CognitiveVisualState, CognitiveFacePreset>

export function getCognitiveFacePreset(
  state: CognitiveVisualState,
): CognitiveFacePreset {
  return COGNITIVE_FACE_PRESETS[state]
}
