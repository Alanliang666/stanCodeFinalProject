export function lerp(current: number, target: number, amount: number): number {
  return current + (target - current) * amount
}
