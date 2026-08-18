import { onBeforeUnmount, onMounted, shallowRef } from 'vue'
import {
  LIVE_EEG_CHANNEL_ORDER,
  type EEGChunkMessage,
  type MuseEEGChannel,
} from '@/types/eeg'

const MOCK_SAMPLING_RATE_HZ = 256
const MOCK_CHUNK_SAMPLE_COUNT = 16
const MOCK_CHUNK_INTERVAL_MS =
  (MOCK_CHUNK_SAMPLE_COUNT / MOCK_SAMPLING_RATE_HZ) * 1_000

const CHANNEL_FREQUENCIES: Record<MuseEEGChannel, number> = {
  TP9: 8.6,
  AF7: 10.4,
  AF8: 10.8,
  TP10: 9.1,
}

const CHANNEL_PHASES: Record<MuseEEGChannel, number> = {
  TP9: 0.2,
  AF7: 1.1,
  AF8: 2.4,
  TP10: 3.2,
}

function createMockSample(channel: MuseEEGChannel, time: number): number {
  const carrier = Math.sin(
    2 * Math.PI * CHANNEL_FREQUENCIES[channel] * time
      + CHANNEL_PHASES[channel],
  )
  const drift = Math.sin(2 * Math.PI * 1.7 * time) * 0.18
  const noise = (Math.random() - 0.5) * 0.24

  return carrier * 0.68 + drift + noise
}

export interface MockLiveEEGOptions {
  autoStart?: boolean
}

export function useMockLiveEEG(options: MockLiveEEGOptions = {}) {
  const chunk = shallowRef<EEGChunkMessage | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null
  let sampleIndex = 0

  function generateChunk(): EEGChunkMessage {
    const chunkStartedAt = Date.now() / 1_000
      - (MOCK_CHUNK_SAMPLE_COUNT - 1) / MOCK_SAMPLING_RATE_HZ
    const timestamps: number[] = []
    const samples: number[][] = []

    for (let rowIndex = 0; rowIndex < MOCK_CHUNK_SAMPLE_COUNT; rowIndex += 1) {
      const time = sampleIndex / MOCK_SAMPLING_RATE_HZ
      timestamps.push(
        chunkStartedAt + rowIndex / MOCK_SAMPLING_RATE_HZ,
      )
      samples.push(
        LIVE_EEG_CHANNEL_ORDER.map((channel) =>
          createMockSample(channel, time),
        ),
      )
      sampleIndex += 1
    }

    return {
      type: 'eeg_chunk',
      data: {
        sampling_rate_hz: MOCK_SAMPLING_RATE_HZ,
        channel_order: LIVE_EEG_CHANNEL_ORDER,
        timestamps,
        samples,
      },
    }
  }

  function start(): void {
    if (timer !== null) return
    chunk.value = generateChunk()
    timer = setInterval(() => {
      chunk.value = generateChunk()
    }, MOCK_CHUNK_INTERVAL_MS)
  }

  function stop(): void {
    if (timer === null) return
    clearInterval(timer)
    timer = null
  }

  if (options.autoStart ?? true) onMounted(start)
  onBeforeUnmount(stop)

  return { chunk, start, stop }
}
