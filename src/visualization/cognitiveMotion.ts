import type { CognitiveState } from '@/types/brain'

export interface CognitiveMotionPreset {
  label: string
  rotationSpeed: number
  floatAmplitude: number
  floatSpeed: number
  tiltAmplitude: number
  gazeX: number
  gazeY: number
  gazeDrift: number
  gazeSpeed: number
  headTilt: number
  headSway: number
  headSpeed: number
  particleDensity: number
  particleSpread: number
  particleSpeed: number
  particleColor: string
  haloOpacity: number
  haloScale: number
  haloPulseSpeed: number
  haloColor: string
}

const COGNITIVE_MOTION_PRESETS = {
  neutral: {
    label: 'Idle',
    rotationSpeed: 0.04,
    floatAmplitude: 0.02,
    floatSpeed: 0.8,
    tiltAmplitude: 0.01,
    gazeX: 0,
    gazeY: 0,
    gazeDrift: 0.015,
    gazeSpeed: 0.7,
    headTilt: 0,
    headSway: 0.025,
    headSpeed: 0.7,
    particleDensity: 0.3,
    particleSpread: 1,
    particleSpeed: 0.18,
    particleColor: '#64748b',
    haloOpacity: 0.12,
    haloScale: 1,
    haloPulseSpeed: 0.65,
    haloColor: '#51e6c4',
  },
  concentrating: {
    label: 'Stable',
    rotationSpeed: 0,
    floatAmplitude: 0,
    floatSpeed: 0.8,
    tiltAmplitude: 0,
    gazeX: 0,
    gazeY: 0,
    gazeDrift: 0,
    gazeSpeed: 0.5,
    headTilt: 0,
    headSway: 0.008,
    headSpeed: 0.45,
    particleDensity: 0.2,
    particleSpread: 0.72,
    particleSpeed: 0.08,
    particleColor: '#8aa4ff',
    haloOpacity: 0.46,
    haloScale: 0.92,
    haloPulseSpeed: 0.35,
    haloColor: '#7f91ff',
  },
} satisfies Record<CognitiveState, CognitiveMotionPreset>

export function mapCognitiveStateToMotion(
  state: CognitiveState,
): CognitiveMotionPreset {
  return COGNITIVE_MOTION_PRESETS[state]
}
