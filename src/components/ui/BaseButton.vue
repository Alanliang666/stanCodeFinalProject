<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: 'button' | 'submit' | 'reset'
    variant?: 'primary' | 'ghost'
    disabled?: boolean
  }>(),
  {
    type: 'button',
    variant: 'primary',
    disabled: false,
  },
)

defineEmits<{
  click: [event: MouseEvent]
}>()
</script>

<template>
  <button
    class="base-button"
    :class="`base-button--${variant}`"
    :type="type"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.base-button {
  min-height: 2.35rem;
  padding: 0.55rem 0.9rem;
  border: 0;
  border-radius: 999px;
  color: #06261f;
  background: #51e6c4;
  font: inherit;
  font-size: 0.77rem;
  font-weight: 750;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    opacity 160ms ease;
}

.base-button:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #79f2d6;
}

.base-button:focus-visible {
  outline: 2px solid #f8fafc;
  outline-offset: 3px;
}

.base-button--ghost {
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(148, 163, 184, 0.08);
}

.base-button--ghost:hover:not(:disabled) {
  background: rgba(148, 163, 184, 0.14);
}

.base-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
