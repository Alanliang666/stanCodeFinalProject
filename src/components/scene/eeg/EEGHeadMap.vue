<script setup lang="ts">
import { computed } from 'vue'
import { Euler, Vector3 } from 'three'
import ElectrodePoint from '@/components/scene/eeg/ElectrodePoint.vue'
import type { MockEEGVisualizationChannel } from '@/types/eeg'
import { EEG_ELECTRODE_LAYOUT } from '@/visualization/eegElectrodes'

const props = defineProps<{
  channels: MockEEGVisualizationChannel[]
}>()

const channelValues = computed(
  () => new Map(
    props.channels.map((channel) => [
      channel.name,
      channel.normalizedValue,
    ]),
  ),
)

const headMapPosition = new Vector3(2.45, -0.82, -0.12)
const headMapRotation = new Euler(-0.08, -0.28, 0)
const headMapScale = new Vector3(0.5, 0.5, 0.5)
const headScale = new Vector3(0.86, 1, 0.9)
</script>

<template>
  <TresGroup
    name="muse-2-mock-eeg-head-map"
    :position="headMapPosition"
    :rotation="headMapRotation"
    :scale="headMapScale"
  >
    <TresMesh :scale="headScale">
      <TresSphereGeometry :args="[1.18, 32, 24]" />
      <TresMeshBasicMaterial
        color="#607b91"
        :wireframe="true"
        :transparent="true"
        :opacity="0.045"
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
