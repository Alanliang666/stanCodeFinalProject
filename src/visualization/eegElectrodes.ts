import { Vector3 } from 'three'
import type { EEGChannelName } from '@/types/brain'
import type { ElectrodeVisualState } from '@/types/eeg'
import { clamp } from '@/utils/clamp'
import { lerp } from '@/utils/lerp'

export interface EEGElectrodeLayout {
  name: EEGChannelName
  position: Vector3
}

export const EEG_ELECTRODE_LAYOUT: readonly EEGElectrodeLayout[] = [
  { name: 'Fp1', position: new Vector3(-0.45, 0.92, 0.84) },
  { name: 'Fp2', position: new Vector3(0.45, 0.92, 0.84) },
  { name: 'F3', position: new Vector3(-0.72, 0.58, 0.78) },
  { name: 'F4', position: new Vector3(0.72, 0.58, 0.78) },
  { name: 'C3', position: new Vector3(-1.16, 0.12, 0.18) },
  { name: 'C4', position: new Vector3(1.16, 0.12, 0.18) },
  { name: 'P3', position: new Vector3(-0.76, 0.5, -0.82) },
  { name: 'P4', position: new Vector3(0.76, 0.5, -0.82) },
  { name: 'O1', position: new Vector3(-0.46, 0.3, -1.1) },
  { name: 'O2', position: new Vector3(0.46, 0.3, -1.1) },
]

export function mapEEGValueToVisual(value: number): ElectrodeVisualState {
  const activity = clamp(value)

  return {
    size: lerp(0.075, 0.17, activity),
    opacity: lerp(0.38, 1, activity),
    emissiveIntensity: lerp(0.35, 3.4, activity),
    glowSize: lerp(0.16, 0.34, activity),
    glowOpacity: lerp(0.04, 0.28, activity),
  }
}
