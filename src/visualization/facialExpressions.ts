import {
  Float32BufferAttribute,
  type BufferAttribute,
  type InterleavedBufferAttribute,
  type Mesh,
  type Object3D,
} from 'three'
import type { FacialMorphMode } from '@/types/avatar'
import { clamp } from '@/utils/clamp'

const PROCEDURAL_FALLBACK_TARGETS = ['happy', 'sad', 'angry', 'surprise'] as const

export type MorphWeightMap = Readonly<Record<string, number | undefined>>

export interface FacialMorphBinding {
  influences: number[]
  meshName: string
  morphTargetDictionary: Record<string, number>
}

export interface FacialMorphSetup {
  bindings: FacialMorphBinding[]
  mode: FacialMorphMode
  meshCount: number
  targetCount: number
}

function collectNativeBindings(scene: Object3D): FacialMorphBinding[] {
  const bindings: FacialMorphBinding[] = []

  scene.traverse((object) => {
    const mesh = object as Mesh
    if (!mesh.isMesh || !mesh.morphTargetDictionary || !mesh.morphTargetInfluences) {
      return
    }

    const dictionaryEntries = Object.entries(mesh.morphTargetDictionary)

    if (import.meta.env.DEV) {
      console.info('[BrainAvatar] Native morph targets discovered', {
        meshName: mesh.name,
        targetCount: dictionaryEntries.length,
        targetNames: dictionaryEntries.map(([name]) => name),
      })
    }

    bindings.push({
      influences: mesh.morphTargetInfluences,
      meshName: mesh.name,
      morphTargetDictionary: mesh.morphTargetDictionary,
    })
  })

  return bindings
}

function getAxisValue(
  attribute: BufferAttribute | InterleavedBufferAttribute,
  vertexIndex: number,
  axis: number,
): number {
  if (axis === 0) return attribute.getX(vertexIndex)
  if (axis === 1) return attribute.getY(vertexIndex)
  return attribute.getZ(vertexIndex)
}

function setAxisValue(
  positions: Float32Array,
  vertexIndex: number,
  axis: number,
  value: number,
): void {
  positions[vertexIndex * 3 + axis] = value
}

function createProceduralTargets(mesh: Mesh): FacialMorphBinding | null {
  const basePosition = mesh.geometry.getAttribute('position')
  if (!basePosition || basePosition.count < 20) return null

  mesh.geometry.computeBoundingBox()
  const bounds = mesh.geometry.boundingBox
  if (!bounds) return null

  const minimums = [bounds.min.x, bounds.min.y, bounds.min.z]
  const maximums = [bounds.max.x, bounds.max.y, bounds.max.z]
  const sizes = maximums.map((maximum, axis) => maximum - minimums[axis]!)
  const axes = [0, 1, 2].sort((left, right) => sizes[right]! - sizes[left]!)
  const verticalAxis = axes[0]!
  const horizontalAxis = axes[1]!
  const verticalSize = sizes[verticalAxis]!
  const horizontalSize = sizes[horizontalAxis]!
  const verticalMinimum = minimums[verticalAxis]!
  const horizontalCenter = (
    minimums[horizontalAxis]! + maximums[horizontalAxis]!
  ) * 0.5

  const basePositions = new Float32Array(basePosition.count * 3)
  for (let index = 0; index < basePosition.count; index += 1) {
    basePositions[index * 3] = basePosition.getX(index)
    basePositions[index * 3 + 1] = basePosition.getY(index)
    basePositions[index * 3 + 2] = basePosition.getZ(index)
  }

  const attributes = PROCEDURAL_FALLBACK_TARGETS.map((emotion) => {
    const positions = new Float32Array(basePositions)

    for (let index = 0; index < basePosition.count; index += 1) {
      const vertical = getAxisValue(basePosition, index, verticalAxis)
      const horizontal = getAxisValue(basePosition, index, horizontalAxis)
      const verticalRatio = (vertical - verticalMinimum) / verticalSize
      const horizontalRatio = Math.min(
        Math.abs(horizontal - horizontalCenter) / (horizontalSize * 0.5),
        1,
      )

      if (emotion === 'happy' && verticalRatio > 0.74 && verticalRatio < 0.88) {
        const lift = verticalSize * 0.026 * horizontalRatio
        setAxisValue(positions, index, verticalAxis, vertical + lift)
      }

      if (emotion === 'sad' && verticalRatio > 0.74 && verticalRatio < 0.88) {
        const drop = verticalSize * 0.023 * horizontalRatio
        setAxisValue(positions, index, verticalAxis, vertical - drop)
      }

      if (emotion === 'angry' && verticalRatio > 0.78 && verticalRatio < 0.99) {
        const browDrop = verticalSize * 0.016 * (1 - horizontalRatio * 0.65)
        setAxisValue(positions, index, verticalAxis, vertical - browDrop)
      }

      if (
        emotion === 'surprise'
        && verticalRatio > 0.72
        && verticalRatio < 0.87
        && horizontalRatio < 0.58
      ) {
        const jawDrop = verticalSize * 0.038 * (1 - horizontalRatio)
        const widenedHorizontal = horizontalCenter
          + (horizontal - horizontalCenter) * 1.07
        setAxisValue(positions, index, verticalAxis, vertical - jawDrop)
        setAxisValue(positions, index, horizontalAxis, widenedHorizontal)
      }
    }

    const attribute = new Float32BufferAttribute(positions, 3)
    attribute.name = emotion
    return attribute
  })

  mesh.geometry.morphTargetsRelative = false
  mesh.geometry.morphAttributes.position = attributes
  mesh.updateMorphTargets()

  if (!mesh.morphTargetInfluences || !mesh.morphTargetDictionary) return null

  return {
    influences: mesh.morphTargetInfluences,
    meshName: mesh.name,
    morphTargetDictionary: mesh.morphTargetDictionary,
  }
}

export function resolveAvailableMorphWeights(
  bindings: readonly FacialMorphBinding[],
  requestedWeights: MorphWeightMap,
): Record<string, number> {
  const resolvedWeights: Record<string, number> = {}

  for (const [name, weight] of Object.entries(requestedWeights)) {
    if (weight === undefined) continue
    const isAvailable = bindings.some(
      (binding) => binding.morphTargetDictionary[name] !== undefined,
    )
    if (isAvailable) resolvedWeights[name] = clamp(weight)
  }

  return resolvedWeights
}

export function smoothMorphTargetInfluences(
  binding: FacialMorphBinding,
  targetWeights: MorphWeightMap,
  smoothing: number,
): void {
  const weightsByIndex = new Map<number, number>()

  for (const [name, weight] of Object.entries(targetWeights)) {
    if (weight === undefined) continue
    const index = binding.morphTargetDictionary[name]
    if (index !== undefined) weightsByIndex.set(index, clamp(weight))
  }

  for (let index = 0; index < binding.influences.length; index += 1) {
    const currentWeight = binding.influences[index] ?? 0
    const targetWeight = weightsByIndex.get(index) ?? 0
    binding.influences[index] = currentWeight
      + (targetWeight - currentWeight) * smoothing
  }
}

export function setupFacialMorphTargets(scene: Object3D): FacialMorphSetup {
  const nativeBindings = collectNativeBindings(scene)
  if (nativeBindings.length > 0) {
    return {
      bindings: nativeBindings,
      mode: 'native',
      meshCount: nativeBindings.length,
      targetCount: nativeBindings.reduce(
        (total, binding) => total
          + Object.keys(binding.morphTargetDictionary ?? {}).length,
        0,
      ),
    }
  }

  const proceduralBindings: FacialMorphBinding[] = []
  scene.traverse((object) => {
    const mesh = object as Mesh
    if (!mesh.isMesh) return
    const binding = createProceduralTargets(mesh)
    if (binding) proceduralBindings.push(binding)
  })

  return {
    bindings: proceduralBindings,
    mode: proceduralBindings.length > 0 ? 'procedural' : 'unavailable',
    meshCount: proceduralBindings.length,
    targetCount: proceduralBindings.length * PROCEDURAL_FALLBACK_TARGETS.length,
  }
}
