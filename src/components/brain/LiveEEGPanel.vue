<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import type {
  BrainDataSource,
  RealtimeConnectionStatus,
} from '@/types/brain'
import {
  LIVE_EEG_CHANNEL_ORDER,
  type EEGChunkMessage,
  type MuseEEGChannel,
} from '@/types/eeg'

const props = withDefaults(
  defineProps<{
    chunk?: EEGChunkMessage | null
    bufferSeconds?: number
    dataSource?: BrainDataSource
    connectionStatus?: RealtimeConnectionStatus
    deviceConnected?: boolean
    deviceName?: string
  }>(),
  {
    chunk: null,
    bufferSeconds: 3,
    dataSource: 'mock',
    connectionStatus: 'idle',
    deviceConnected: false,
    deviceName: 'Muse 2',
  },
)

const VIEWBOX_WIDTH = 1_000
const VIEWBOX_HEIGHT = 64
const WAVEFORM_PADDING = 5

const channelColors: Record<MuseEEGChannel, string> = {
  TP9: '#66dcc5',
  AF7: '#70d2e8',
  AF8: '#8ea5ff',
  TP10: '#a58cf2',
}

function createEmptyBuffers(): Record<MuseEEGChannel, number[]> {
  return {
    TP9: [],
    AF7: [],
    AF8: [],
    TP10: [],
  }
}

const samplingRateHz = ref(256)
const buffers = shallowRef(createEmptyBuffers())
const timestamps = shallowRef<number[]>([])
const discontinuityCount = ref(0)
const bufferCapacity = computed(() =>
  Math.max(1, Math.round(samplingRateHz.value * props.bufferSeconds)),
)

function trimToCapacity(values: number[]): number[] {
  return values.length > bufferCapacity.value
    ? values.slice(values.length - bufferCapacity.value)
    : values
}

function appendChunk(message: EEGChunkMessage | null | undefined): void {
  if (!message || message.type !== 'eeg_chunk') return

  const { data } = message
  if (data.sampling_rate_hz <= 0) return

  samplingRateHz.value = data.sampling_rate_hz
  const expectedInterval = 1 / data.sampling_rate_hz
  const previousTimestamp = timestamps.value.at(-1)
  const incomingTimestamps = data.timestamps.slice(0, data.samples.length)
  const timestampsToCheck = previousTimestamp === undefined
    ? incomingTimestamps
    : [previousTimestamp, ...incomingTimestamps]

  for (let index = 1; index < timestampsToCheck.length; index += 1) {
    const previous = timestampsToCheck[index - 1]
    const current = timestampsToCheck[index]
    if (
      previous !== undefined
      && current !== undefined
      && current - previous > expectedInterval * 1.5
    ) {
      discontinuityCount.value += 1
      if (import.meta.env.DEV) {
        console.debug('[LiveEEG] Timestamp discontinuity', {
          gapSeconds: current - previous,
          expectedInterval,
        })
      }
    }
  }
  const channelIndexes = new Map(
    data.channel_order.map((channel, index) => [channel, index]),
  )
  const nextBuffers = Object.fromEntries(
    LIVE_EEG_CHANNEL_ORDER.map((channel) => [
      channel,
      [...buffers.value[channel]],
    ]),
  ) as Record<MuseEEGChannel, number[]>

  for (const row of data.samples) {
    for (const channel of LIVE_EEG_CHANNEL_ORDER) {
      const channelIndex = channelIndexes.get(channel)
      if (channelIndex === undefined) continue

      const value = row[channelIndex]
      if (value !== undefined && Number.isFinite(value)) {
        nextBuffers[channel].push(value)
      }
    }
  }

  for (const channel of LIVE_EEG_CHANNEL_ORDER) {
    nextBuffers[channel] = trimToCapacity(nextBuffers[channel])
  }

  buffers.value = nextBuffers
  timestamps.value = trimToCapacity([
    ...timestamps.value,
    ...incomingTimestamps,
  ])
}

function createWaveformPath(samples: readonly number[]): string {
  if (samples.length < 2) return ''

  const mean = samples.reduce((total, value) => total + value, 0)
    / samples.length
  const peak = Math.max(
    0.25,
    ...samples.map((value) => Math.abs(value - mean)),
  )
  const drawableHeight = VIEWBOX_HEIGHT - WAVEFORM_PADDING * 2
  const xOffset = bufferCapacity.value - samples.length

  return samples.map((value, index) => {
    const x = ((xOffset + index) / (bufferCapacity.value - 1))
      * VIEWBOX_WIDTH
    const normalized = (value - mean) / peak
    const y = VIEWBOX_HEIGHT / 2
      - normalized * drawableHeight * 0.45

    const previousTimestamp = timestamps.value[index - 1]
    const currentTimestamp = timestamps.value[index]
    const hasGap = index > 0
      && previousTimestamp !== undefined
      && currentTimestamp !== undefined
      && currentTimestamp - previousTimestamp
        > (1 / samplingRateHz.value) * 1.5

    return `${index === 0 || hasGap ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
  }).join(' ')
}

const waveformPaths = computed(() =>
  Object.fromEntries(
    LIVE_EEG_CHANNEL_ORDER.map((channel) => [
      channel,
      createWaveformPath(buffers.value[channel]),
    ]),
  ) as Record<MuseEEGChannel, string>,
)

watch(() => props.chunk, appendChunk, { immediate: true })
watch(() => props.dataSource, () => {
  buffers.value = createEmptyBuffers()
  timestamps.value = []
  discontinuityCount.value = 0
})

const sourceLabel = computed(() =>
  props.dataSource === 'mock' ? 'Mock source' : 'Live / WebSocket',
)
const streamLabel = computed(() => {
  if (props.connectionStatus !== 'connected') return props.connectionStatus
  return props.deviceConnected
    ? `${props.deviceName} connected`
    : `${props.deviceName} disconnected`
})
</script>

<template>
  <section class="live-eeg" aria-labelledby="live-eeg-title">
    <header class="live-eeg__header">
      <div>
        <p class="live-eeg__eyebrow">
          <span aria-hidden="true" />
          Realtime input visualization
        </p>
        <h2 id="live-eeg-title">Live EEG</h2>
      </div>
      <div class="live-eeg__source">
        <span>{{ sourceLabel }}</span>
        <strong>{{ streamLabel }}</strong>
      </div>
    </header>

    <div class="live-eeg__channels">
      <article
        v-for="channel in LIVE_EEG_CHANNEL_ORDER"
        :key="channel"
        class="waveform-row"
        :data-channel="channel"
        :data-sample-count="buffers[channel].length"
      >
        <strong>{{ channel }}</strong>
        <svg
          class="waveform-row__plot"
          :viewBox="`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`"
          preserveAspectRatio="none"
          role="img"
          :aria-label="`${channel} rolling EEG waveform`"
        >
          <line
            x1="0"
            :y1="VIEWBOX_HEIGHT / 2"
            :x2="VIEWBOX_WIDTH"
            :y2="VIEWBOX_HEIGHT / 2"
            class="waveform-row__baseline"
          />
          <path
            :d="waveformPaths[channel]"
            :stroke="channelColors[channel]"
            class="waveform-row__line"
          />
        </svg>
      </article>
    </div>

    <footer class="live-eeg__footer">
      <span>{{ samplingRateHz }} Hz · 4 Channels</span>
      <span>{{ bufferSeconds }} s rolling UI buffer</span>
      <span v-if="discontinuityCount > 0">{{ discontinuityCount }} timestamp gap{{ discontinuityCount === 1 ? '' : 's' }}</span>
      <span>Signal unit pending backend contract</span>
    </footer>
  </section>
</template>

<style scoped>
.live-eeg {
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 22px;
  background: rgba(8, 17, 31, 0.78);
  box-shadow: 0 20px 65px rgba(2, 8, 23, 0.22);
}

.live-eeg__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  padding: 1rem 1.25rem 0.85rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.live-eeg__eyebrow {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0 0 0.25rem;
  color: #51e6c4;
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

.live-eeg__eyebrow span {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 50%;
  background: #51e6c4;
  box-shadow: 0 0 9px rgba(81, 230, 196, 0.75);
  animation: live-pulse 1.5s ease-in-out infinite;
}

.live-eeg h2 {
  margin: 0;
  color: #f1f5f9;
  font-size: 1rem;
  font-weight: 620;
  letter-spacing: -0.02em;
}

.live-eeg__source {
  text-align: right;
}

.live-eeg__source span,
.live-eeg__source strong {
  display: block;
}

.live-eeg__source span {
  color: #64748b;
  font-size: 0.58rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.live-eeg__source strong {
  margin-top: 0.2rem;
  color: #94a3b8;
  font-size: 0.67rem;
  font-weight: 550;
}

.live-eeg__channels {
  display: grid;
  gap: 0.35rem;
  padding: 0.75rem 1.25rem;
}

.waveform-row {
  display: grid;
  grid-template-columns: 3.25rem minmax(0, 1fr);
  align-items: center;
  min-height: 2.65rem;
}

.waveform-row strong {
  color: #94a3b8;
  font-size: 0.68rem;
  font-weight: 650;
  letter-spacing: 0.05em;
}

.waveform-row__plot {
  width: 100%;
  height: 2.65rem;
  overflow: visible;
  border-radius: 8px;
  background:
    linear-gradient(rgba(148, 163, 184, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.035) 1px, transparent 1px);
  background-size: 100% 50%, 6.25% 100%;
}

.waveform-row__baseline {
  stroke: rgba(148, 163, 184, 0.09);
  stroke-width: 1;
}

.waveform-row__line {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}

.live-eeg__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem 1.4rem;
  padding: 0.7rem 1.25rem;
  color: #536277;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  font-size: 0.58rem;
  letter-spacing: 0.04em;
}

@keyframes live-pulse {
  50% { opacity: 0.38; }
}

@media (max-width: 560px) {
  .live-eeg__header {
    align-items: flex-start;
    padding: 0.9rem 1rem 0.75rem;
  }

  .live-eeg__channels {
    padding: 0.65rem 1rem;
  }

  .live-eeg__source strong {
    max-width: 8rem;
  }

  .live-eeg__footer {
    padding: 0.65rem 1rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-eeg__eyebrow span {
    animation: none;
  }
}
</style>
