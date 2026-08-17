import type { CognitiveVisualState } from '@/types/avatar'

const COGNITIVE_FACE_MORPH_TARGETS = [
  'browInnerUp',
  'browDown_L',
  'browDown_R',
  'browOuterUp_L',
  'browOuterUp_R',
  'eyeWide_L',
  'eyeWide_R',
  'eyeSquint_L',
  'eyeSquint_R',
  'noseSneer_L',
  'noseSneer_R',
  'mouthPress_L',
  'mouthPress_R',
  'mouthFrown_L',
  'mouthFrown_R',
] as const

export type CognitiveFaceMorphTarget =
  (typeof COGNITIVE_FACE_MORPH_TARGETS)[number]

export type CognitiveFacePreset = Readonly<
  Partial<Record<CognitiveFaceMorphTarget, number>>
>

export const COGNITIVE_FACE_PRESETS = {
  neutral: {
    eyeWide_L: 0.025,
    eyeWide_R: 0.025,
    browOuterUp_L: 0.015,
    browOuterUp_R: 0.015,
  },
  focused: {
    browDown_L: 0.42,
    browDown_R: 0.42,
    browInnerUp: 0.10,
    eyeSquint_L: 0.32,
    eyeSquint_R: 0.32,
    noseSneer_L: 0.10,
    noseSneer_R: 0.10,
    mouthPress_L: 0.30,
    mouthPress_R: 0.30,
    mouthFrown_L: 0.08,
    mouthFrown_R: 0.08,
  },
} as const satisfies Record<CognitiveVisualState, CognitiveFacePreset>

export function getCognitiveFacePreset(
  state: CognitiveVisualState,
): CognitiveFacePreset {
  return COGNITIVE_FACE_PRESETS[state]
}
