import { clamp } from '@/utils/clamp'
import type { MorphWeightMap } from '@/visualization/facialExpressions'

const BLINK_INTERVAL_SECONDS = 4.2
const BLINK_DURATION_SECONDS = 0.18

export function getBlinkLayer(elapsed: number): MorphWeightMap {
  const phase = elapsed % BLINK_INTERVAL_SECONDS
  const blinkStart = BLINK_INTERVAL_SECONDS - BLINK_DURATION_SECONDS
  if (phase < blinkStart) return {}

  const progress = (phase - blinkStart) / BLINK_DURATION_SECONDS
  const weight = Math.sin(progress * Math.PI)
  return {
    eyeBlink_L: weight,
    eyeBlink_R: weight,
  }
}

export function composeMorphLayers(
  ...layers: readonly MorphWeightMap[]
): MorphWeightMap {
  const composed: Record<string, number> = {}

  for (const layer of layers) {
    for (const [name, weight] of Object.entries(layer)) {
      if (weight === undefined) continue
      composed[name] = clamp((composed[name] ?? 0) + weight)
    }
  }

  return composed
}
