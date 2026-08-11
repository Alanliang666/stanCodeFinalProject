<script setup lang="ts">
import { computed } from 'vue'
import { clamp } from '@/utils/clamp'

const props = defineProps<{
  value: number
}>()

const percentage = computed(() => Math.round(clamp(props.value) * 100))
</script>

<template>
  <div class="meter">
    <div class="meter__header">
      <span>Attention</span>
      <strong>{{ percentage }}%</strong>
    </div>
    <div
      class="meter__track"
      role="progressbar"
      aria-label="Attention"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="percentage"
    >
      <span class="meter__fill" :style="{ width: `${percentage}%` }" />
    </div>
  </div>
</template>

<style scoped>
.meter__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.7rem;
  color: #94a3b8;
  font-size: 0.78rem;
}

.meter__header strong {
  color: #f8fafc;
  font-variant-numeric: tabular-nums;
}

.meter__track {
  height: 0.45rem;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
}

.meter__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1bc9a5, #6ff1d3);
  box-shadow: 0 0 16px rgba(81, 230, 196, 0.45);
  transition: width 600ms ease;
}
</style>
