<script setup lang="ts">
import { computed } from 'vue'
import { AdditiveBlending, Vector3 } from 'three'
import type { MuseEEGChannel } from '@/types/eeg'
import { mapEEGValueToVisual } from '@/visualization/eegElectrodes'

const props = defineProps<{
  name: MuseEEGChannel
  position: Vector3
  value: number
}>()

const visualState = computed(() => mapEEGValueToVisual(props.value))
const pointScale = computed(() => {
  const size = visualState.value.size
  return new Vector3(size, size, size)
})
const glowScale = computed(() => {
  const size = visualState.value.glowSize
  return new Vector3(size, size, size)
})
</script>

<template>
  <TresGroup :name="`electrode-${name}`" :position="position">
    <TresMesh :scale="glowScale">
      <TresSphereGeometry :args="[1, 16, 16]" />
      <TresMeshBasicMaterial
        color="#51e6c4"
        :transparent="true"
        :opacity="visualState.glowOpacity"
        :depth-write="false"
        :tone-mapped="false"
        :blending="AdditiveBlending"
      />
    </TresMesh>

    <TresMesh :scale="pointScale">
      <TresSphereGeometry :args="[1, 20, 20]" />
      <TresMeshStandardMaterial
        color="#b8fff0"
        emissive="#31e6bd"
        :emissive-intensity="visualState.emissiveIntensity"
        :transparent="true"
        :opacity="visualState.opacity"
        :roughness="0.22"
        :metalness="0.08"
      />
    </TresMesh>
  </TresGroup>
</template>
