import {
  onBeforeUnmount,
  shallowRef,
  watch,
  type Ref,
} from 'vue'
import { useLoop } from '@tresjs/core'
import type { Object3D } from 'three'
import type { CognitiveVisualState, FacialMorphState } from '@/types/avatar'
import { clamp } from '@/utils/clamp'
import { getCognitiveFacePreset } from '@/visualization/cognitiveFacePresets'
import {
  resolveAvailableMorphWeights,
  setupFacialMorphTargets,
  smoothMorphTargetInfluences,
  type FacialMorphBinding,
  type MorphWeightMap,
} from '@/visualization/facialExpressions'

const EXPRESSION_SMOOTHING_SPEED = 7
const MAX_FRAME_DELTA = 0.1
const COGNITIVE_DEBUG_STEP_SECONDS = 3
const BLINK_INTERVAL_SECONDS = 4.2
const BLINK_DURATION_SECONDS = 0.18
const COGNITIVE_DEBUG_STATES = [
  'neutral',
  'focused',
  'distracted',
  'high_load',
] as const satisfies readonly CognitiveVisualState[]

const isCognitiveDebugEnabled = import.meta.env.DEV
  && typeof window !== 'undefined'
  && new URLSearchParams(window.location.search).get('cognitiveDebug') === '1'

function getBlinkLayer(elapsed: number): MorphWeightMap {
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

function composeMorphLayers(...layers: readonly MorphWeightMap[]): MorphWeightMap {
  const composed: Record<string, number> = {}

  for (const layer of layers) {
    for (const [name, weight] of Object.entries(layer)) {
      if (weight === undefined) continue
      composed[name] = clamp((composed[name] ?? 0) + weight)
    }
  }

  return composed
}

export function useExpressionController(
  scene: Readonly<Ref<Object3D | null>>,
  cognitiveVisualState: Readonly<Ref<CognitiveVisualState>>,
) {
  const bindings = shallowRef<FacialMorphBinding[]>([])
  const morphState = shallowRef<FacialMorphState>({
    mode: 'unavailable',
    meshCount: 0,
    targetCount: 0,
  })
  let activeDebugState: CognitiveVisualState | null = null

  watch(
    scene,
    (nextScene) => {
      for (const binding of bindings.value) {
        binding.influences.fill(0)
      }

      if (!nextScene) {
        bindings.value = []
        morphState.value = {
          mode: 'unavailable',
          meshCount: 0,
          targetCount: 0,
        }
        return
      }

      const setup = setupFacialMorphTargets(nextScene)
      bindings.value = setup.bindings
      morphState.value = {
        mode: setup.mode,
        meshCount: setup.meshCount,
        targetCount: setup.targetCount,
      }
    },
    { immediate: true, flush: 'sync' },
  )

  const { onBeforeRender } = useLoop()
  const { off } = onBeforeRender(({ delta, elapsed }) => {
    const frameDelta = Math.min(delta, MAX_FRAME_DELTA)
    const smoothing = 1 - Math.exp(-EXPRESSION_SMOOTHING_SPEED * frameDelta)
    const debugStateIndex = isCognitiveDebugEnabled
      ? Math.floor(elapsed / COGNITIVE_DEBUG_STEP_SECONDS)
        % COGNITIVE_DEBUG_STATES.length
      : -1
    const effectiveState = debugStateIndex >= 0
      ? COGNITIVE_DEBUG_STATES[debugStateIndex]
      : cognitiveVisualState.value
    const cognitiveLayer = getCognitiveFacePreset(effectiveState)
    const blinkLayer = getBlinkLayer(elapsed)
    const composedWeights = composeMorphLayers(cognitiveLayer, blinkLayer)

    if (isCognitiveDebugEnabled && effectiveState !== activeDebugState) {
      activeDebugState = effectiveState
      console.info(
        '[CognitiveFace]',
        `state: ${effectiveState}`,
        'targets:',
        resolveAvailableMorphWeights(bindings.value, cognitiveLayer),
      )
    }

    for (const binding of bindings.value) {
      smoothMorphTargetInfluences(binding, composedWeights, smoothing)
    }
  })

  onBeforeUnmount(off)

  return { morphState }
}
