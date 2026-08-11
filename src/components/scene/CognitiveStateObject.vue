<script setup lang="ts">
import { shallowRef, toRef } from 'vue'
import { Group, Vector3 } from 'three'
import CognitiveHalo from '@/components/scene/CognitiveHalo.vue'
import CognitiveParticles from '@/components/scene/CognitiveParticles.vue'
import { useCognitiveAnimation } from '@/composables/useCognitiveAnimation'
import type { CognitiveState } from '@/types/brain'

const props = defineProps<{
  state: CognitiveState
}>()

const root = shallowRef<Group | null>(null)
const head = shallowRef<Group | null>(null)
const gaze = shallowRef<Group | null>(null)
const cognitiveState = toRef(props, 'state')

const rootPosition = new Vector3(-1.85, 0, 0)
const rootScale = new Vector3(0.62, 0.62, 0.62)
const headScale = new Vector3(0.82, 1.02, 0.78)
const leftEyePosition = new Vector3(-0.3, 0.17, 0.7)
const rightEyePosition = new Vector3(0.3, 0.17, 0.7)
const eyeScale = new Vector3(0.17, 0.12, 0.075)
const leftPupilPosition = new Vector3(-0.3, 0.17, 0.77)
const rightPupilPosition = new Vector3(0.3, 0.17, 0.77)
const pupilScale = new Vector3(0.065, 0.065, 0.04)

useCognitiveAnimation({ root, head, gaze }, cognitiveState)
</script>

<template>
  <TresGroup
    ref="root"
    name="cognitive-visualization"
    :position="rootPosition"
    :scale="rootScale"
  >
    <CognitiveParticles :state="state" />
    <CognitiveHalo :state="state" />

    <TresGroup ref="head" name="cognitive-head">
      <TresMesh :scale="headScale">
        <TresSphereGeometry :args="[1, 36, 28]" />
        <TresMeshStandardMaterial
          color="#1d2a45"
          emissive="#17273f"
          :emissive-intensity="0.55"
          :roughness="0.38"
          :metalness="0.28"
          :transparent="true"
          :opacity="0.94"
        />
      </TresMesh>

      <TresMesh :position="leftEyePosition" :scale="eyeScale">
        <TresSphereGeometry :args="[1, 20, 16]" />
        <TresMeshBasicMaterial color="#d9fff7" />
      </TresMesh>
      <TresMesh :position="rightEyePosition" :scale="eyeScale">
        <TresSphereGeometry :args="[1, 20, 16]" />
        <TresMeshBasicMaterial color="#d9fff7" />
      </TresMesh>

      <TresGroup ref="gaze" name="gaze-controller">
        <TresMesh :position="leftPupilPosition" :scale="pupilScale">
          <TresSphereGeometry :args="[1, 16, 12]" />
          <TresMeshBasicMaterial color="#07101d" :tone-mapped="false" />
        </TresMesh>
        <TresMesh :position="rightPupilPosition" :scale="pupilScale">
          <TresSphereGeometry :args="[1, 16, 12]" />
          <TresMeshBasicMaterial color="#07101d" :tone-mapped="false" />
        </TresMesh>
      </TresGroup>
    </TresGroup>
  </TresGroup>
</template>
