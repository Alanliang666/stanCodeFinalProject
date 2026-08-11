<script setup lang="ts">
import { computed, toRef, watchEffect } from 'vue'
import { useLoader } from '@tresjs/core'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import bundledAvatarUrl from '@/models/avatar.glb?url'
import { useExpressionController } from '@/composables/useExpressionController'
import type { AvatarLoadState, FacialMorphState } from '@/types/avatar'
import type { EmotionState } from '@/types/brain'

const props = withDefaults(
  defineProps<{
    modelUrl?: string
    emotion?: EmotionState
    emotionConfidence?: number
  }>(),
  {
    modelUrl: bundledAvatarUrl,
    emotion: 'neutral',
    emotionConfidence: 0,
  },
)

const emit = defineEmits<{
  loadState: [state: AvatarLoadState]
  morphState: [state: FacialMorphState]
}>()

const modelUrl = toRef(props, 'modelUrl')
const { state: model, isLoading, error, progress } = useLoader(
  GLTFLoader,
  modelUrl,
)

const avatarScene = computed(() => model.value?.scene ?? null)
const emotion = toRef(props, 'emotion')
const emotionConfidence = toRef(props, 'emotionConfidence')
const { morphState } = useExpressionController(
  avatarScene,
  emotion,
  emotionConfidence,
)

watchEffect(() => {
  emit('morphState', morphState.value)
})

watchEffect(() => {
  if (error.value) {
    emit('loadState', {
      status: 'error',
      progress: progress.percentage,
      message: error.value instanceof Error
        ? error.value.message
        : 'Unable to load avatar model',
    })
    return
  }

  if (avatarScene.value) {
    avatarScene.value.name = 'brain-avatar-model'
    emit('loadState', { status: 'loaded', progress: 100 })
    return
  }

  emit('loadState', {
    status: 'loading',
    progress: isLoading.value ? progress.percentage : 0,
  })
})
</script>

<template>
  <primitive
    v-if="avatarScene"
    :object="avatarScene"
    :dispose="true"
  />

  <TresMesh v-else-if="error" name="avatar-load-error">
    <TresOctahedronGeometry :args="[0.24, 0]" />
    <TresMeshStandardMaterial
      color="#fb7185"
      emissive="#fb7185"
      :emissive-intensity="0.8"
      :wireframe="true"
    />
  </TresMesh>

  <TresMesh v-else name="avatar-loading-placeholder">
    <TresCapsuleGeometry :args="[0.25, 0.8, 6, 12]" />
    <TresMeshStandardMaterial
      color="#334155"
      emissive="#51e6c4"
      :emissive-intensity="0.3"
      :transparent="true"
      :opacity="0.42"
      :wireframe="true"
    />
  </TresMesh>
</template>
