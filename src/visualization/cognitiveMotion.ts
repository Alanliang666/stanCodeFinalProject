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
  thinking: {
    label: 'Rotate',
    rotationSpeed: 1.1,
    floatAmplitude: 0.04,
    floatSpeed: 1.2,
    tiltAmplitude: 0.06,
    gazeX: 0.1,
    gazeY: 0.08,
    gazeDrift: 0.02,
    gazeSpeed: 1.25,
    headTilt: -0.1,
    headSway: 0.07,
    headSpeed: 1.1,
    particleDensity: 0.68,
    particleSpread: 1.08,
    particleSpeed: 0.8,
    particleColor: '#51e6c4',
    haloOpacity: 0.3,
    haloScale: 1.08,
    haloPulseSpeed: 1.3,
    haloColor: '#51e6c4',
  },
  focused: {
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
  mindWandering: {
    label: 'Float',
    rotationSpeed: 0.12,
    floatAmplitude: 0.42,
    floatSpeed: 0.65,
    tiltAmplitude: 0.14,
    gazeX: 0.02,
    gazeY: -0.035,
    gazeDrift: 0.14,
    gazeSpeed: 0.42,
    headTilt: 0.08,
    headSway: 0.18,
    headSpeed: 0.55,
    particleDensity: 0.92,
    particleSpread: 1.55,
    particleSpeed: 0.22,
    particleColor: '#b68cff',
    haloOpacity: 0.18,
    haloScale: 1.28,
    haloPulseSpeed: 0.48,
    haloColor: '#9c7cff',
  },
  uncertain: {
    label: 'Waver',
    rotationSpeed: 0.35,
    floatAmplitude: 0.1,
    floatSpeed: 2.1,
    tiltAmplitude: 0.2,
    gazeX: -0.04,
    gazeY: 0.02,
    gazeDrift: 0.1,
    gazeSpeed: 2.2,
    headTilt: -0.04,
    headSway: 0.14,
    headSpeed: 1.8,
    particleDensity: 0.55,
    particleSpread: 1.18,
    particleSpeed: 0.55,
    particleColor: '#f4b76b',
    haloOpacity: 0.2,
    haloScale: 1.12,
    haloPulseSpeed: 1.8,
    haloColor: '#f4b76b',
  },
  relaxed: {
    label: 'Drift',
    rotationSpeed: 0.025,
    floatAmplitude: 0.1,
    floatSpeed: 0.5,
    tiltAmplitude: 0.04,
    gazeX: 0,
    gazeY: -0.02,
    gazeDrift: 0.025,
    gazeSpeed: 0.38,
    headTilt: 0.035,
    headSway: 0.045,
    headSpeed: 0.42,
    particleDensity: 0.38,
    particleSpread: 1.22,
    particleSpeed: 0.12,
    particleColor: '#79d8c4',
    haloOpacity: 0.16,
    haloScale: 1.16,
    haloPulseSpeed: 0.4,
    haloColor: '#79d8c4',
  },
} satisfies Record<CognitiveState, CognitiveMotionPreset>

export function mapCognitiveStateToMotion(
  state: CognitiveState,
): CognitiveMotionPreset {
  return COGNITIVE_MOTION_PRESETS[state]
}
