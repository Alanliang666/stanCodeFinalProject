import { onBeforeUnmount, type DeepReadonly, type Ref, type ShallowRef } from 'vue'
import { useLoop } from '@tresjs/core'
import type { Group } from 'three'
import type { CognitiveState } from '@/types/brain'
import { lerp } from '@/utils/lerp'
import { mapCognitiveStateToMotion } from '@/visualization/cognitiveMotion'

const TRANSITION_SPEED = 4
const MAX_FRAME_DELTA = 0.1

export interface CognitiveAnimationTargets {
  root: ShallowRef<Group | null>
  head: ShallowRef<Group | null>
  gaze: ShallowRef<Group | null>
}

export function useCognitiveAnimation(
  targets: CognitiveAnimationTargets,
  cognitiveState: DeepReadonly<Ref<CognitiveState>>,
): void {
  const currentMotion = {
    rotationSpeed: 0,
    floatAmplitude: 0,
    floatSpeed: 0.8,
    tiltAmplitude: 0,
    gazeX: 0,
    gazeY: 0,
    gazeDrift: 0,
    gazeSpeed: 0.7,
    headTilt: 0,
    headSway: 0,
    headSpeed: 0.7,
  }

  const { onBeforeRender } = useLoop()

  const { off } = onBeforeRender(({ delta, elapsed }) => {
    const root = targets.root.value
    const head = targets.head.value
    const gaze = targets.gaze.value
    if (!root || !head || !gaze) return

    const targetMotion = mapCognitiveStateToMotion(cognitiveState.value)
    const frameDelta = Math.min(delta, MAX_FRAME_DELTA)
    const smoothing = 1 - Math.exp(-TRANSITION_SPEED * frameDelta)

    currentMotion.rotationSpeed = lerp(
      currentMotion.rotationSpeed,
      targetMotion.rotationSpeed,
      smoothing,
    )
    currentMotion.floatAmplitude = lerp(
      currentMotion.floatAmplitude,
      targetMotion.floatAmplitude,
      smoothing,
    )
    currentMotion.floatSpeed = lerp(
      currentMotion.floatSpeed,
      targetMotion.floatSpeed,
      smoothing,
    )
    currentMotion.tiltAmplitude = lerp(
      currentMotion.tiltAmplitude,
      targetMotion.tiltAmplitude,
      smoothing,
    )
    currentMotion.gazeX = lerp(currentMotion.gazeX, targetMotion.gazeX, smoothing)
    currentMotion.gazeY = lerp(currentMotion.gazeY, targetMotion.gazeY, smoothing)
    currentMotion.gazeDrift = lerp(
      currentMotion.gazeDrift,
      targetMotion.gazeDrift,
      smoothing,
    )
    currentMotion.gazeSpeed = lerp(
      currentMotion.gazeSpeed,
      targetMotion.gazeSpeed,
      smoothing,
    )
    currentMotion.headTilt = lerp(
      currentMotion.headTilt,
      targetMotion.headTilt,
      smoothing,
    )
    currentMotion.headSway = lerp(
      currentMotion.headSway,
      targetMotion.headSway,
      smoothing,
    )
    currentMotion.headSpeed = lerp(
      currentMotion.headSpeed,
      targetMotion.headSpeed,
      smoothing,
    )

    root.rotation.y += currentMotion.rotationSpeed * frameDelta
    root.position.y = Math.sin(elapsed * currentMotion.floatSpeed)
      * currentMotion.floatAmplitude
    root.rotation.z = Math.sin(elapsed * currentMotion.floatSpeed * 0.75)
      * currentMotion.tiltAmplitude

    head.rotation.z = currentMotion.headTilt
      + Math.sin(elapsed * currentMotion.headSpeed) * currentMotion.headSway
    head.rotation.y = Math.sin(elapsed * currentMotion.headSpeed * 0.73)
      * currentMotion.headSway * 0.65
    head.position.y = Math.cos(elapsed * currentMotion.headSpeed)
      * currentMotion.headSway * 0.08

    gaze.position.x = currentMotion.gazeX
      + Math.sin(elapsed * currentMotion.gazeSpeed) * currentMotion.gazeDrift
    gaze.position.y = currentMotion.gazeY
      + Math.cos(elapsed * currentMotion.gazeSpeed * 0.81)
      * currentMotion.gazeDrift * 0.65
  })

  onBeforeUnmount(off)
}
