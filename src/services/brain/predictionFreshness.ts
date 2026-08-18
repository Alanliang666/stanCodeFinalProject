export function isPredictionStale(
  receivedAt: number | null,
  now: number,
  staleTimeoutMs: number,
): boolean {
  return receivedAt !== null && now - receivedAt > staleTimeoutMs
}
