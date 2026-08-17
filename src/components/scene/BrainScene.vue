<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { TresCanvas } from '@tresjs/core'
import { Vector3 } from 'three'
import BrainAvatar from '@/components/scene/BrainAvatar.vue'
import { useBrainStore } from '@/stores/brainStore'
import type {
  AvatarLoadState,
  FacialMorphState,
} from '@/types/avatar'
import { mapCognitivePredictionToVisualState } from '@/visualization/cognitiveVisualStateAdapter'

const brainStore = useBrainStore()
const { prediction } = storeToRefs(brainStore)
const showDevelopmentStatus = import.meta.env.DEV
const avatarLoadState = ref<AvatarLoadState>({
  status: 'loading',
  progress: 0,
})
const facialMorphState = ref<FacialMorphState>({
  mode: 'unavailable',
  meshCount: 0,
  targetCount: 0,
})

const cognitivePrediction = computed(
  () => prediction.value?.cognition ?? null,
)
const cognitiveVisualState = computed(() =>
  mapCognitivePredictionToVisualState(cognitivePrediction.value),
)
const cognitiveVisualStateLabel = computed(() =>
  cognitiveVisualState.value.replace('_', ' '),
)
const sceneOrigin = new Vector3(0, 0, 0)
const cameraPosition = new Vector3(0, 0.95, 6.1)
const keyLightPosition = new Vector3(3, 4, 5)
const fillLightPosition = new Vector3(-3, -1, 2)
const avatarPosition = new Vector3(0, -0.12, 0.12)
const avatarScale = new Vector3(1.45, 1.45, 1.45)

function updateAvatarLoadState(state: AvatarLoadState): void {
  avatarLoadState.value = state
}

function updateFacialMorphState(state: FacialMorphState): void {
  facialMorphState.value = state
}
</script>

<template>
  <section
    class="brain-scene"
    aria-label="FaceCap cognitive avatar visualization"
  >
    <TresCanvas clear-color="#08111f" :antialias="true">
      <TresPerspectiveCamera
        :position="cameraPosition"
        :look-at="sceneOrigin"
      />

      <TresAmbientLight :intensity="1.25" />
      <TresDirectionalLight
        :position="keyLightPosition"
        :intensity="3.2"
        color="#d9fff6"
      />
      <TresPointLight
        :position="fillLightPosition"
        :intensity="12"
        color="#756cff"
      />

      <TresGroup :position="avatarPosition" :scale="avatarScale">
        <BrainAvatar
          :cognitive-visual-state="cognitiveVisualState"
          @load-state="updateAvatarLoadState"
          @morph-state="updateFacialMorphState"
        />
      </TresGroup>
    </TresCanvas>
    <div
      v-if="showDevelopmentStatus"
      class="brain-scene__diagnostics"
      aria-live="polite"
    >
      <span :class="`brain-scene__avatar--${avatarLoadState.status}`">
        Avatar: {{ avatarLoadState.status }}
      </span>
      <span
        :class="`brain-scene__face--${facialMorphState.mode}`"
        :title="`${facialMorphState.targetCount} facial morph targets`"
      >
        Face: {{ cognitiveVisualState }} · {{ facialMorphState.mode }}
      </span>
    </div>
    <div class="brain-scene__status" aria-hidden="true">
      <span />
      WebGL scene active
    </div>
    <div
      v-if="showDevelopmentStatus"
      class="brain-scene__state"
      aria-live="polite"
    >
      <span>Cognitive face</span>
      <strong>{{ cognitiveVisualStateLabel }}</strong>
    </div>
  </section>
</template>

<style scoped>
.brain-scene {
  position: relative;
  width: 100%;
  min-height: 23rem;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 24px;
  background: #08111f;
  box-shadow:
    0 24px 80px rgba(2, 8, 23, 0.3),
    inset 0 1px rgba(255, 255, 255, 0.035);
}

.brain-scene::after {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(rgba(81, 230, 196, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(81, 230, 196, 0.025) 1px, transparent 1px);
  background-size: 2rem 2rem;
  mask-image: linear-gradient(to bottom, transparent, black 45%, transparent);
  content: '';
}

.brain-scene__status,
.brain-scene__state {
  position: absolute;
  z-index: 1;
  bottom: 1rem;
  color: #64748b;
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.brain-scene__diagnostics {
  position: absolute;
  z-index: 1;
  bottom: 0.85rem;
  left: 50%;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.25rem;
  max-width: 14rem;
  opacity: 0.55;
  transform: translateX(-50%);
}

.brain-scene__diagnostics span {
  padding: 0.2rem 0.34rem;
  border: 1px solid rgba(117, 108, 255, 0.12);
  border-radius: 999px;
  color: #64748b;
  background: rgba(8, 17, 31, 0.52);
  font-size: 0.46rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.brain-scene__diagnostics .brain-scene__avatar--loaded,
.brain-scene__diagnostics .brain-scene__face--native,
.brain-scene__diagnostics .brain-scene__face--procedural {
  color: #8debd5;
  border-color: rgba(81, 230, 196, 0.14);
}

.brain-scene__diagnostics .brain-scene__avatar--error,
.brain-scene__diagnostics .brain-scene__face--unavailable {
  color: #fb8ca0;
  border-color: rgba(251, 113, 133, 0.14);
}

.brain-scene__status {
  left: 1rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.brain-scene__status span {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: #51e6c4;
  box-shadow: 0 0 10px #51e6c4;
}

.brain-scene__state {
  right: 1rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.brain-scene__state span {
  text-transform: capitalize;
}

.brain-scene__state strong {
  color: #cbd5e1;
  font-weight: 700;
}

.brain-scene__state strong::before {
  margin-right: 0.45rem;
  color: #334155;
  content: '→';
}

@media (max-width: 560px) {
  .brain-scene {
    min-height: 20rem;
  }

  .brain-scene__diagnostics {
    display: none;
  }
}
</style>
