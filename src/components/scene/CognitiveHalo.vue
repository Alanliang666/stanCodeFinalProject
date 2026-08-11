<script setup lang="ts">
import { computed, onBeforeUnmount, shallowRef } from 'vue'
import { useLoop } from '@tresjs/core'
import { AdditiveBlending, Euler, Group, Vector3 } from 'three'
import type { CognitiveState } from '@/types/brain'
import { lerp } from '@/utils/lerp'
import { mapCognitiveStateToMotion } from '@/visualization/cognitiveMotion'

const props = defineProps<{
  state: CognitiveState
}>()

const halo = shallowRef<Group | null>(null)
const preset = computed(() => mapCognitiveStateToMotion(props.state))

const secondaryRingRotation = new Euler(0.72, 0.18, 0)
const initialScale = new Vector3(1, 1, 1)
let currentScale = 1

const { onBeforeRender } = useLoop()
const { off } = onBeforeRender(({ delta, elapsed }) => {
  const group = halo.value
  if (!group) return

  const frameDelta = Math.min(delta, 0.1)
  const smoothing = 1 - Math.exp(-3.5 * frameDelta)
  currentScale = lerp(currentScale, preset.value.haloScale, smoothing)

  const pulse = 1 + Math.sin(elapsed * preset.value.haloPulseSpeed)
    * preset.value.haloOpacity * 0.09
  group.scale.setScalar(currentScale * pulse)
  group.rotation.z += frameDelta * 0.035
})

onBeforeUnmount(off)
</script>

<template>
  <TresGroup ref="halo" name="cognitive-halo" :scale="initialScale">
    <TresMesh>
      <TresTorusGeometry :args="[1.14, 0.025, 10, 72]" />
      <TresMeshBasicMaterial
        :color="preset.haloColor"
        :transparent="true"
        :opacity="preset.haloOpacity"
        :depth-write="false"
        :tone-mapped="false"
        :blending="AdditiveBlending"
      />
    </TresMesh>

    <TresMesh :rotation="secondaryRingRotation">
      <TresTorusGeometry :args="[1.32, 0.012, 8, 72]" />
      <TresMeshBasicMaterial
        :color="preset.haloColor"
        :transparent="true"
        :opacity="preset.haloOpacity * 0.55"
        :depth-write="false"
        :tone-mapped="false"
        :blending="AdditiveBlending"
      />
    </TresMesh>
  </TresGroup>
</template>
