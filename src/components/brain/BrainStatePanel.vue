<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import BaseCard from '@/components/ui/BaseCard.vue'
import { useBrainStore } from '@/stores/brainStore'
import type {
  CognitiveState,
  RealtimeConnectionStatus,
} from '@/types/brain'
import { LIVE_EEG_CHANNEL_ORDER } from '@/types/eeg'

const brainStore = useBrainStore()
const {
  prediction,
  connectionStatus,
  deviceStatus,
  dataSource,
  dataSourceLabel,
  errorMessage,
  lastUpdated,
} = storeToRefs(brainStore)

const statusLabels: Record<RealtimeConnectionStatus, string> = {
  idle: 'Idle',
  disconnected: 'Disconnected',
  connecting: 'Connecting',
  connected: 'Connected',
  reconnecting: 'Reconnecting',
  error: 'Connection error',
}

const lastUpdatedLabel = computed(() => {
  if (lastUpdated.value === null) return 'Prediction unavailable'
  return new Intl.DateTimeFormat('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(lastUpdated.value)
})

function toPercentage(value: number): number {
  return Math.round(value * 100)
}

const cognitiveStateLabels: Record<CognitiveState, string> = {
  relaxed_openeye: 'Relaxed · Eyes Open',
  concentration: 'Concentration',
  relaxed_closeeye: 'Relaxed · Eyes Closed',
}
</script>

<template>
  <BaseCard eyebrow="Cognitive prediction" title="EEG Insights">
    <div class="panel-meta">
      <div class="connection">
        <span
          class="connection__dot"
          :class="`connection__dot--${connectionStatus}`"
          aria-hidden="true"
        />
        <span>Realtime: {{ statusLabels[connectionStatus] }}</span>
      </div>
      <span class="panel-meta__device">
        Muse: {{ deviceStatus.connected ? 'Connected' : 'Disconnected' }}
      </span>
      <time v-if="lastUpdated" :datetime="new Date(lastUpdated).toISOString()">
        Updated {{ lastUpdatedLabel }}
      </time>
      <span v-else>{{ lastUpdatedLabel }}</span>
    </div>

    <div class="panel-content">
      <div class="insight-grid">
        <article class="insight-card insight-card--state">
          <span>Current Cognitive State</span>
          <strong>{{ prediction ? cognitiveStateLabels[prediction.cognition.state] : 'Unavailable' }}</strong>
        </article>

        <article class="insight-card">
          <span>Model Confidence</span>
          <strong>{{ prediction ? `${toPercentage(prediction.cognition.confidence)}%` : '—' }}</strong>
        </article>

        <article class="insight-card">
          <span>Data Source</span>
          <strong>{{ dataSourceLabel }}</strong>
          <small>{{ dataSource === 'mock' ? 'Frontend development generator' : 'Backend realtime stream' }}</small>
        </article>
      </div>

      <section
        class="muse-section"
        aria-label="EEG device information"
      >
        <div class="muse-section__heading">
          <div>
            <span>{{ deviceStatus.device }}</span>
            <strong>{{ deviceStatus.connected ? 'Connected' : 'Disconnected' }}</strong>
          </div>
          <span class="muse-section__badge">{{ dataSource === 'mock' ? 'Mock' : 'Realtime' }}</span>
        </div>

        <div class="muse-section__details">
          <div>
            <span>Channels</span>
            <strong>{{ LIVE_EEG_CHANNEL_ORDER.join(' · ') }}</strong>
          </div>
          <div>
            <span>Sampling Rate</span>
            <strong>{{ deviceStatus.sampling_rate_hz }} Hz</strong>
          </div>
        </div>
      </section>

      <p v-if="!prediction" class="prediction-status" aria-live="polite">
        {{ errorMessage ?? 'Prediction unavailable / waiting' }}
      </p>
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

.prediction-status {
  margin: 1rem 0 0;
  padding: 0.75rem 0.9rem;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  background: rgba(148, 163, 184, 0.035);
  color: #64748b;
  font-size: 0.7rem;
}

@keyframes pulse {
  50% { opacity: 0.4; }
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

}

@media (prefers-reduced-motion: reduce) {
  .connection__dot,
  .prediction-status {
    animation: none;
    transition: none;
  }
}
</style>
