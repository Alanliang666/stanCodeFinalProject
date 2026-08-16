<script setup lang="ts">
import { computed, onBeforeUnmount, toRef, watchEffect } from 'vue'
import { useLoader, useTresContext } from '@tresjs/core'
import type { WebGLRenderer } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import bundledAvatarUrl from '@/models/facecap.glb?url'
import { useExpressionController } from '@/composables/useExpressionController'
import type {
  AvatarLoadState,
  CognitiveVisualState,
  FacialMorphState,
} from '@/types/avatar'

const props = withDefaults(
  defineProps<{
    modelUrl?: string
    cognitiveVisualState?: CognitiveVisualState
  }>(),
  {
    modelUrl: bundledAvatarUrl,
    cognitiveVisualState: 'neutral',
  },
)

const emit = defineEmits<{
  loadState: [state: AvatarLoadState]
  morphState: [state: FacialMorphState]
}>()

const { renderer } = useTresContext()
const ktx2Loader = new KTX2Loader().detectSupport(
  renderer.instance as WebGLRenderer,
)
const modelUrl = toRef(props, 'modelUrl')
const { state: model, isLoading, error, progress } = useLoader(
  GLTFLoader,
  modelUrl,
  {
    extensions: (loader) => {
      loader.setKTX2Loader?.(ktx2Loader)
      loader.setMeshoptDecoder?.(MeshoptDecoder)
    },
  },
)

onBeforeUnmount(() => ktx2Loader.dispose())

const avatarScene = computed(() => model.value?.scene ?? null)
const cognitiveVisualState = toRef(props, 'cognitiveVisualState')
const { morphState } = useExpressionController(
  avatarScene,
  cognitiveVisualState,
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
