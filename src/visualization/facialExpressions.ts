import {
  Float32BufferAttribute,
  type BufferAttribute,
  type InterleavedBufferAttribute,
  type Mesh,
  type Object3D,
} from 'three'
import type { FacialMorphMode } from '@/types/avatar'
import type { EmotionState } from '@/types/brain'

const FACIAL_EMOTIONS = ['happy', 'sad', 'angry', 'surprise'] as const

const MORPH_ALIASES: Record<(typeof FACIAL_EMOTIONS)[number], readonly string[]> = {
  happy: ['happy', 'happiness', 'joy', 'smile', 'mouthsmile'],
  sad: ['sad', 'sadness', 'sorrow', 'frown', 'mouthfrown'],
  angry: ['angry', 'anger', 'mad', 'browdown'],
  surprise: ['surprise', 'surprised', 'astonished', 'mouthopen', 'jawopen'],
}

export type EmotionMorphTargets = Record<EmotionState, number[]>

export interface FacialMorphBinding {
  influences: number[]
  targets: EmotionMorphTargets
}

export interface FacialMorphSetup {
  bindings: FacialMorphBinding[]
  mode: FacialMorphMode
  meshCount: number
  targetCount: number
}

function createEmptyTargetMap(): EmotionMorphTargets {
  return {
    neutral: [],
    happy: [],
    sad: [],
    angry: [],
    surprise: [],
  }
}

function normalizeMorphName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, '')
}

function collectNativeBindings(scene: Object3D): FacialMorphBinding[] {
  const bindings: FacialMorphBinding[] = []

  scene.traverse((object) => {
    const mesh = object as Mesh
    if (!mesh.isMesh || !mesh.morphTargetDictionary || !mesh.morphTargetInfluences) {
      return
    }

    const targets = createEmptyTargetMap()
    const dictionaryEntries = Object.entries(mesh.morphTargetDictionary)

    for (const emotion of FACIAL_EMOTIONS) {
      const aliases = MORPH_ALIASES[emotion]
      targets[emotion] = dictionaryEntries
        .filter(([name]) => {
          const normalizedName = normalizeMorphName(name)
          return aliases.some((alias) => normalizedName.includes(alias))
        })
        .map(([, index]) => index)
    }

    if (FACIAL_EMOTIONS.some((emotion) => targets[emotion].length > 0)) {
      bindings.push({ influences: mesh.morphTargetInfluences, targets })
    }
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

  const attributes = FACIAL_EMOTIONS.map((emotion) => {
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

  const targets = createEmptyTargetMap()
  for (const emotion of FACIAL_EMOTIONS) {
    const targetIndex = mesh.morphTargetDictionary[emotion]
    if (targetIndex !== undefined) targets[emotion] = [targetIndex]
  }

  return { influences: mesh.morphTargetInfluences, targets }
}

export function setupFacialMorphTargets(scene: Object3D): FacialMorphSetup {
  const nativeBindings = collectNativeBindings(scene)
  if (nativeBindings.length > 0) {
    return {
      bindings: nativeBindings,
      mode: 'native',
      meshCount: nativeBindings.length,
      targetCount: nativeBindings.reduce(
        (total, binding) => total + FACIAL_EMOTIONS.reduce(
          (count, emotion) => count + binding.targets[emotion].length,
          0,
        ),
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
    targetCount: proceduralBindings.length * FACIAL_EMOTIONS.length,
  }
}
