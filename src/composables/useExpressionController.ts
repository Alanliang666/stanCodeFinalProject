import {
  onBeforeUnmount,
  shallowRef,
  watch,
  type Ref,
} from 'vue'
import { useLoop } from '@tresjs/core'
import type { Object3D } from 'three'
import type { FacialMorphState } from '@/types/avatar'
import type { EmotionState } from '@/types/brain'
import { clamp } from '@/utils/clamp'
import {
  setupFacialMorphTargets,
  type FacialMorphBinding,
} from '@/visualization/facialExpressions'

const EXPRESSION_SMOOTHING_SPEED = 7
const MAX_FRAME_DELTA = 0.1

export function useExpressionController(
  scene: Readonly<Ref<Object3D | null>>,
  emotion: Readonly<Ref<EmotionState>>,
  confidence: Readonly<Ref<number>>,
) {
  const bindings = shallowRef<FacialMorphBinding[]>([])
  const morphState = shallowRef<FacialMorphState>({
    mode: 'unavailable',
    meshCount: 0,
    targetCount: 0,
  })

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
  const { off } = onBeforeRender(({ delta }) => {
    const frameDelta = Math.min(delta, MAX_FRAME_DELTA)
    const smoothing = 1 - Math.exp(-EXPRESSION_SMOOTHING_SPEED * frameDelta)
    const expressionStrength = clamp(confidence.value)

    for (const binding of bindings.value) {
      const activeTargets = binding.targets[emotion.value]

      for (let index = 0; index < binding.influences.length; index += 1) {
        const currentWeight = binding.influences[index] ?? 0
        const targetWeight = activeTargets.includes(index)
          ? expressionStrength
          : 0

        binding.influences[index] = currentWeight
          + (targetWeight - currentWeight) * smoothing
      }
    }
  })

  onBeforeUnmount(off)

  return { morphState }
}
