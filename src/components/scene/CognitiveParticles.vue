<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { useLoop } from '@tresjs/core'
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Points,
  PointsMaterial,
} from 'three'
import type { CognitiveState } from '@/types/brain'
import { lerp } from '@/utils/lerp'
import { mapCognitiveStateToMotion } from '@/visualization/cognitiveMotion'

const props = defineProps<{
  state: CognitiveState
}>()

const MAX_PARTICLES = 96
const positions = new Float32Array(MAX_PARTICLES * 3)
const goldenAngle = Math.PI * (3 - Math.sqrt(5))

for (let index = 0; index < MAX_PARTICLES; index += 1) {
  const normalizedIndex = (index + 0.5) / MAX_PARTICLES
  const y = 1 - normalizedIndex * 2
  const radiusAtY = Math.sqrt(1 - y * y)
  const angle = goldenAngle * index
  const shellRadius = 1.25 + (index % 7) * 0.075
  const offset = index * 3

  positions[offset] = Math.cos(angle) * radiusAtY * shellRadius
  positions[offset + 1] = y * shellRadius
  positions[offset + 2] = Math.sin(angle) * radiusAtY * shellRadius
}

const geometry = new BufferGeometry()
geometry.setAttribute('position', new BufferAttribute(positions, 3))

const material = new PointsMaterial({
  color: '#51e6c4',
  size: 0.055,
  sizeAttenuation: true,
  transparent: true,
  opacity: 0.45,
  depthWrite: false,
  blending: AdditiveBlending,
})

const particleCloud = new Points(geometry, material)
particleCloud.name = 'cognitive-particles'

let targetSpread = 1
let currentSpread = 1
let targetSpeed = 0.2
let currentSpeed = 0.2

watch(
  () => props.state,
  (state) => {
    const preset = mapCognitiveStateToMotion(state)
    geometry.setDrawRange(
      0,
      Math.max(1, Math.round(MAX_PARTICLES * preset.particleDensity)),
    )
    material.color.set(preset.particleColor)
    material.opacity = 0.18 + preset.particleDensity * 0.46
    material.size = 0.04 + preset.particleDensity * 0.025
    targetSpread = preset.particleSpread
    targetSpeed = preset.particleSpeed
  },
  { immediate: true },
)

const { onBeforeRender } = useLoop()
const { off } = onBeforeRender(({ delta }) => {
  const frameDelta = Math.min(delta, 0.1)
  const smoothing = 1 - Math.exp(-3.5 * frameDelta)

  currentSpread = lerp(currentSpread, targetSpread, smoothing)
  currentSpeed = lerp(currentSpeed, targetSpeed, smoothing)

  particleCloud.scale.setScalar(currentSpread)
  particleCloud.rotation.y += currentSpeed * frameDelta
  particleCloud.rotation.x += currentSpeed * frameDelta * 0.22
})

onBeforeUnmount(() => {
  off()
  geometry.dispose()
  material.dispose()
})
</script>

<template>
  <primitive :object="particleCloud" />
</template>
