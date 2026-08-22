import type { CognitiveVisualState } from '@/types/avatar'
import type {
  CognitivePrediction,
  CognitiveState,
} from '@/types/brain'

const COGNITIVE_VISUAL_STATE_BY_PREDICTION = {
  relaxed_openeye: 'relaxedOpenEye',
  concentration: 'focused',
  relaxed_closeeye: 'relaxedCloseEye',
} as const satisfies Record<CognitiveState, CognitiveVisualState>

export function mapCognitivePredictionToVisualState(
  prediction: CognitivePrediction | null | undefined,
): CognitiveVisualState {
  if (!prediction) return 'idle'

  return COGNITIVE_VISUAL_STATE_BY_PREDICTION[prediction.state]
}
