import type { CognitiveVisualState } from '@/types/avatar'
import type {
  CognitivePrediction,
  CognitiveState,
} from '@/types/brain'

const COGNITIVE_VISUAL_STATE_BY_PREDICTION = {
  neutral: 'neutral',
  concentrating: 'focused',
} as const satisfies Record<CognitiveState, CognitiveVisualState>

export function mapCognitivePredictionToVisualState(
  prediction: CognitivePrediction | null | undefined,
): CognitiveVisualState {
  if (!prediction) return 'neutral'

  return COGNITIVE_VISUAL_STATE_BY_PREDICTION[prediction.state]
}
