import { Vector3 } from 'three'
import type {
  ElectrodeVisualState,
  MuseEEGChannel,
} from '@/types/eeg'
import { clamp } from '@/utils/clamp'
import { lerp } from '@/utils/lerp'

export interface EEGElectrodeLayout {
  name: MuseEEGChannel
  position: Vector3
}

export const EEG_ELECTRODE_LAYOUT: readonly EEGElectrodeLayout[] = [
  { name: 'AF7', position: new Vector3(-0.52, 0.78, 0.88) },
  { name: 'AF8', position: new Vector3(0.52, 0.78, 0.88) },
  { name: 'TP9', position: new Vector3(-1.08, 0.05, -0.3) },
  { name: 'TP10', position: new Vector3(1.08, 0.05, -0.3) },
]

export function mapEEGValueToVisual(
  normalizedValue: number,
): ElectrodeVisualState {
  const activity = clamp(normalizedValue)

  return {
    size: lerp(0.065, 0.135, activity),
    opacity: lerp(0.3, 0.78, activity),
    emissiveIntensity: lerp(0.2, 1.7, activity),
    glowSize: lerp(0.13, 0.24, activity),
    glowOpacity: lerp(0.025, 0.13, activity),
  }
}
