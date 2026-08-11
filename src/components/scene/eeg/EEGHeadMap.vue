<script setup lang="ts">
import { computed } from 'vue'
import { Euler, Vector3 } from 'three'
import ElectrodePoint from '@/components/scene/eeg/ElectrodePoint.vue'
import type { EEGChannel } from '@/types/brain'
import { EEG_ELECTRODE_LAYOUT } from '@/visualization/eegElectrodes'

const props = defineProps<{
  channels: EEGChannel[]
}>()

const channelValues = computed(
  () => new Map(props.channels.map((channel) => [channel.name, channel.value])),
)

const headMapPosition = new Vector3(1.85, -0.05, 0)
const headMapRotation = new Euler(-0.08, -0.18, 0)
const headScale = new Vector3(0.86, 1, 0.9)
</script>

<template>
  <TresGroup
    name="eeg-head-map"
    :position="headMapPosition"
    :rotation="headMapRotation"
  >
    <TresMesh :scale="headScale">
      <TresSphereGeometry :args="[1.18, 32, 24]" />
      <TresMeshBasicMaterial
        color="#7394ad"
        :wireframe="true"
        :transparent="true"
        :opacity="0.09"
        :depth-write="false"
      />
    </TresMesh>

    <ElectrodePoint
      v-for="electrode in EEG_ELECTRODE_LAYOUT"
      :key="electrode.name"
      :name="electrode.name"
      :position="electrode.position"
      :value="channelValues.get(electrode.name) ?? 0"
    />
  </TresGroup>
</template>
