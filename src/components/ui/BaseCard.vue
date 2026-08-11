<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    eyebrow?: string
  }>(),
  {
    title: '',
    eyebrow: '',
  },
)
</script>

<template>
  <section class="base-card">
    <header v-if="title || eyebrow || $slots.action" class="base-card__header">
      <div>
        <p v-if="eyebrow" class="base-card__eyebrow">{{ eyebrow }}</p>
        <h2 v-if="title" class="base-card__title">{{ title }}</h2>
      </div>
      <slot name="action" />
    </header>
    <slot />
  </section>
</template>

<style scoped>
.base-card {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 24px;
  background: rgba(12, 21, 36, 0.82);
  box-shadow:
    0 24px 80px rgba(2, 8, 23, 0.3),
    inset 0 1px rgba(255, 255, 255, 0.035);
  backdrop-filter: blur(18px);
}

.base-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.4rem 1.5rem 1.1rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.base-card__eyebrow {
  margin: 0 0 0.3rem;
  color: #51e6c4;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.base-card__title {
  margin: 0;
  color: #f8fafc;
  font-size: 1.1rem;
  font-weight: 650;
  letter-spacing: -0.02em;
}
</style>
