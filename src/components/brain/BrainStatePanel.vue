<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import { useBrainStore } from '@/stores/brainStore'
import type { BrainConnectionStatus } from '@/types/brain'
import { MUSE_EEG_CHANNELS } from '@/types/eeg'

const brainStore = useBrainStore()
const { prediction, connectionStatus, lastUpdated } = storeToRefs(brainStore)

const statusLabels: Record<BrainConnectionStatus, string> = {
  disconnected: 'Mock stream paused',
  connecting: 'Starting mock stream',
  connected: 'Mock stream active',
  error: 'Mock stream error',
}

const lastUpdatedLabel = computed(() => {
  if (lastUpdated.value === null) return 'Waiting for mock data'
  return new Intl.DateTimeFormat('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(lastUpdated.value)
})

function formatState(state: string): string {
  return state.replace(/([a-z])([A-Z])/g, '$1 $2')
}

function toPercentage(value: number): number {
  return Math.round(value * 100)
}

function toggleStream(): void {
  if (connectionStatus.value === 'connected') {
    brainStore.stopMockStream()
    return
  }
  brainStore.startMockStream()
}
</script>

<template>
  <BaseCard eyebrow="Frontend simulation" title="EEG Insights">
    <template #action>
      <BaseButton
        :variant="connectionStatus === 'connected' ? 'ghost' : 'primary'"
        :disabled="connectionStatus === 'connecting'"
        @click="toggleStream"
      >
        {{ connectionStatus === 'connected' ? 'Pause mock' : 'Start mock' }}
      </BaseButton>
    </template>

    <div class="panel-meta">
      <div class="connection">
        <span
          class="connection__dot"
          :class="`connection__dot--${connectionStatus}`"
          aria-hidden="true"
        />
        <span>{{ statusLabels[connectionStatus] }}</span>
      </div>
      <span class="panel-meta__device">Muse: Waiting for device</span>
      <time v-if="lastUpdated" :datetime="new Date(lastUpdated).toISOString()">
        Updated {{ lastUpdatedLabel }}
      </time>
      <span v-else>{{ lastUpdatedLabel }}</span>
    </div>

    <div v-if="prediction" class="panel-content">
      <div class="insight-grid">
        <article class="insight-card insight-card--state">
          <span>Current Cognitive State</span>
          <strong>{{ formatState(prediction.cognition.state) }}</strong>
        </article>

        <article class="insight-card">
          <span>Model Confidence</span>
          <strong>{{ toPercentage(prediction.cognition.confidence) }}%</strong>
        </article>

        <article class="insight-card">
          <span>Data Source</span>
          <strong>Mock Data</strong>
          <small>No physical Muse connected</small>
        </article>
      </div>

      <section
        class="muse-section"
        aria-label="Muse 2 mock device information"
      >
        <div class="muse-section__heading">
          <div>
            <span>Muse 2 EEG</span>
            <strong>Waiting for device</strong>
          </div>
          <span class="muse-section__badge">Mock</span>
        </div>

        <div class="muse-section__details">
          <div>
            <span>Channels</span>
            <strong>{{ MUSE_EEG_CHANNELS.join(' · ') }}</strong>
          </div>
          <div>
            <span>Sampling Rate</span>
            <strong>256 Hz</strong>
          </div>
        </div>
      </section>

      <div class="eeg-section">
        <div class="section-heading">
          <div>
            <span class="section-heading__eyebrow">
              {{ prediction.eeg.channels.length }} mock channels
            </span>
            <h3>EEG activity</h3>
          </div>
          <span>Mock normalized value</span>
        </div>

        <div class="channel-grid">
          <div
            v-for="channel in prediction.eeg.channels"
            :key="channel.name"
            class="channel"
          >
            <div class="channel__header">
              <span>{{ channel.name }}</span>
              <strong>{{ channel.normalizedValue.toFixed(2) }}</strong>
            </div>
            <div class="channel__track" aria-hidden="true">
              <span
                :style="{
                  width: `${toPercentage(channel.normalizedValue)}%`,
                }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state" aria-live="polite">
      <span class="empty-state__pulse" />
      <p>Initializing mock prediction...</p>
    </div>
  </BaseCard>
</template>

<style scoped>
.panel-meta {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  min-height: 2.9rem;
  padding: 0 1.5rem;
  color: #64748b;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
  font-size: 0.7rem;
}

.panel-meta time,
.panel-meta > span:last-child {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.connection {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: #cbd5e1;
  font-weight: 650;
}

.connection__dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: #64748b;
}

.connection__dot--connected {
  background: #51e6c4;
  box-shadow: 0 0 0 4px rgba(81, 230, 196, 0.09), 0 0 12px #51e6c4;
}

.connection__dot--connecting {
  background: #fbbf24;
  animation: pulse 1s ease-in-out infinite;
}

.connection__dot--error {
  background: #fb7185;
}

.panel-meta__device {
  padding-left: 0.9rem;
  border-left: 1px solid rgba(148, 163, 184, 0.16);
}

.panel-content {
  padding: 1.5rem;
}

.insight-grid {
  display: grid;
  grid-template-columns: 1.25fr repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.insight-card {
  position: relative;
  min-height: 7.2rem;
  overflow: hidden;
  padding: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 17px;
  background: rgba(148, 163, 184, 0.045);
}

.insight-card::after {
  position: absolute;
  right: -2rem;
  bottom: -3.5rem;
  width: 8rem;
  height: 8rem;
  border-radius: 50%;
  background: rgba(110, 114, 238, 0.09);
  filter: blur(8px);
  content: '';
}

.insight-card--state::after {
  background: rgba(81, 230, 196, 0.11);
}

.insight-card > span,
.insight-card small {
  position: relative;
  z-index: 1;
  display: block;
  color: #64748b;
  font-size: 0.66rem;
}

.insight-card strong {
  position: relative;
  z-index: 1;
  display: block;
  margin: 0.65rem 0 0.5rem;
  color: #f8fafc;
  font-size: clamp(1.05rem, 2.4vw, 1.55rem);
  font-weight: 600;
  letter-spacing: -0.035em;
  text-transform: capitalize;
}

.muse-section {
  margin-top: 1.25rem;
  padding: 1rem;
  border: 1px solid rgba(81, 230, 196, 0.13);
  border-radius: 16px;
  background: rgba(81, 230, 196, 0.035);
}

.muse-section__heading,
.muse-section__details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.muse-section__heading > div > span,
.muse-section__details span {
  display: block;
  color: #64748b;
  font-size: 0.64rem;
}

.muse-section__heading strong {
  display: block;
  margin-top: 0.25rem;
  color: #cbd5e1;
  font-size: 0.82rem;
  font-weight: 600;
}

.muse-section__badge {
  padding: 0.3rem 0.55rem;
  border: 1px solid rgba(81, 230, 196, 0.2);
  border-radius: 999px;
  color: #8debd5;
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.muse-section__details {
  margin-top: 0.9rem;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
}

.muse-section__details > div:last-child {
  text-align: right;
}

.muse-section__details strong {
  display: block;
  margin-top: 0.3rem;
  color: #e2e8f0;
  font-size: 0.74rem;
  font-weight: 600;
}

.eeg-section {
  margin-top: 1.5rem;
  padding-top: 1.4rem;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 1.15rem;
  color: #64748b;
  font-size: 0.68rem;
}

.section-heading__eyebrow {
  display: block;
  margin-bottom: 0.25rem;
  color: #51e6c4;
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.section-heading h3 {
  margin: 0;
  color: #e2e8f0;
  font-size: 0.9rem;
  font-weight: 600;
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.8rem 0.65rem;
}

.channel__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.4rem;
  color: #94a3b8;
  font-size: 0.63rem;
}

.channel__header strong {
  color: #64748b;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.channel__track {
  height: 0.25rem;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.1);
}

.channel__track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #29bd9e, #6e72ee);
  transition: width 600ms ease;
}

.empty-state {
  display: grid;
  min-height: 23rem;
  place-content: center;
  justify-items: center;
  color: #64748b;
  font-size: 0.8rem;
}

.empty-state__pulse {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid rgba(81, 230, 196, 0.18);
  border-top-color: #51e6c4;
  border-radius: 50%;
  animation: spin 900ms linear infinite;
}

@keyframes pulse {
  50% { opacity: 0.4; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 660px) {
  .panel-meta__device {
    display: none;
  }

  .panel-content {
    padding: 1rem;
  }

  .insight-grid {
    grid-template-columns: 1fr;
  }

  .channel-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .channel__track span,
  .connection__dot,
  .empty-state__pulse {
    animation: none;
    transition: none;
  }
}
</style>
