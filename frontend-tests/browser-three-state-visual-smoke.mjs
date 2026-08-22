import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'

const [cdpUrl, applicationUrl, screenshotPath] = process.argv.slice(2)
if (!cdpUrl || !applicationUrl || !screenshotPath) {
  throw new Error('Expected CDP URL, application URL, and screenshot path')
}

const socket = new WebSocket(cdpUrl)
const pending = new Map()
const debugTargets = new Map()
const debugScreenshots = new Map()
const runtimeExceptions = []
let nextId = 1
let activeDebugState = null
let debugStateSince = null

socket.onmessage = (event) => {
  const message = JSON.parse(event.data)
  if (message.id) {
    const handler = pending.get(message.id)
    if (handler) {
      pending.delete(message.id)
      if (message.error) handler.reject(new Error(message.error.message))
      else handler.resolve(message.result)
    }
    return
  }

  if (message.method === 'Runtime.exceptionThrown') {
    runtimeExceptions.push(message.params.exceptionDetails.text)
    return
  }
  if (message.method !== 'Runtime.consoleAPICalled') return
  const args = message.params.args
  if (args[0]?.value !== '[CognitiveFace]') return
  const state = String(args[1]?.value ?? '').replace('state: ', '')
  const targetsObjectId = args[3]?.objectId
  if (state && targetsObjectId) {
    debugTargets.set(state, targetsObjectId)
    activeDebugState = state
    debugStateSince = Date.now()
  }
}

await new Promise((resolve, reject) => {
  socket.onopen = resolve
  socket.onerror = reject
})

function call(method, params = {}) {
  const id = nextId
  nextId += 1
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    socket.send(JSON.stringify({ id, method, params }))
  })
}

async function evaluate(expression) {
  const result = await call('Runtime.evaluate', {
    expression,
    returnByValue: true,
  })
  return result.result.value
}

async function readTargetWeights(objectId) {
  const result = await call('Runtime.callFunctionOn', {
    objectId,
    functionDeclaration: 'function () { return this }',
    returnByValue: true,
  })
  return result.result.value
}

await call('Runtime.enable')
await call('Page.enable')
await call('Page.navigate', { url: applicationUrl })

const observedProductStates = new Set()
let currentView = null
const deadline = Date.now() + 18_000

while (Date.now() < deadline) {
  await new Promise((resolve) => setTimeout(resolve, 250))
  currentView = await evaluate(`(() => ({
    productState: document.querySelector('.insight-card--state strong')?.textContent?.trim() ?? '',
    visualState: document.querySelector('.brain-scene__state strong')?.textContent?.trim() ?? '',
    faceStatus: document.querySelector('.brain-scene__diagnostics span:nth-child(2)')?.textContent?.trim() ?? '',
    avatarStatus: document.querySelector('.brain-scene__diagnostics span:first-child')?.textContent?.trim() ?? ''
  }))()`)
  if (['Relaxed · Eyes Open', 'Concentration', 'Relaxed · Eyes Closed'].includes(
    currentView.productState,
  )) {
    observedProductStates.add(currentView.productState)
  }
  if (
    activeDebugState
    && debugStateSince !== null
    && Date.now() - debugStateSince >= 800
    && !debugScreenshots.has(activeDebugState)
    && currentView.faceStatus.toLowerCase().includes('native')
    && currentView.avatarStatus.toLowerCase().includes('loaded')
  ) {
    debugScreenshots.set(activeDebugState, await call('Page.captureScreenshot', {
      format: 'png',
      captureBeyondViewport: true,
    }))
  }
  if (
    observedProductStates.has('Relaxed · Eyes Open')
    && observedProductStates.has('Concentration')
    && observedProductStates.has('Relaxed · Eyes Closed')
    && debugTargets.has('relaxedOpenEye')
    && debugTargets.has('focused')
    && debugTargets.has('relaxedCloseEye')
    && debugScreenshots.size === 3
    && currentView.faceStatus.toLowerCase().includes('native')
    && currentView.avatarStatus.toLowerCase().includes('loaded')
  ) {
    break
  }
}

console.log('Observed diagnostics before assertions:', {
  currentView,
  debugStates: [...debugTargets.keys()],
  screenshotStates: [...debugScreenshots.keys()],
  runtimeExceptions,
})

assert.deepEqual([...observedProductStates].sort(), [
  'Concentration',
  'Relaxed · Eyes Closed',
  'Relaxed · Eyes Open',
])
assert.ok(debugTargets.has('relaxedOpenEye'))
assert.ok(debugTargets.has('focused'))
assert.ok(debugTargets.has('relaxedCloseEye'))
assert.match(currentView.faceStatus, /native/i)
assert.match(currentView.avatarStatus, /loaded/i)
assert.deepEqual(runtimeExceptions, [])
assert.equal(debugScreenshots.size, 3)

const relaxedOpenEyeWeights = await readTargetWeights(
  debugTargets.get('relaxedOpenEye'),
)
const focusedWeights = await readTargetWeights(debugTargets.get('focused'))
const relaxedCloseEyeWeights = await readTargetWeights(
  debugTargets.get('relaxedCloseEye'),
)
assert.deepEqual(Object.keys(relaxedOpenEyeWeights).sort(), [
  'browOuterUp_L',
  'browOuterUp_R',
  'eyeLookUp_L',
  'eyeLookUp_R',
  'eyeWide_L',
  'eyeWide_R',
  'jawOpen',
  'mouthRollLower',
  'mouthShrugLower',
].sort())
assert.deepEqual(Object.keys(focusedWeights).sort(), [
  'browDown_L',
  'browDown_R',
  'browInnerUp',
  'eyeSquint_L',
  'eyeSquint_R',
  'jawForward',
  'mouthFrown_L',
  'mouthFrown_R',
  'mouthPress_L',
  'mouthPress_R',
  'mouthShrugUpper',
  'noseSneer_L',
  'noseSneer_R',
].sort())
assert.deepEqual(Object.keys(relaxedCloseEyeWeights).sort(), [
  'eyeBlink_L',
  'eyeBlink_R',
  'jawOpen',
].sort())

for (const [state, screenshot] of debugScreenshots) {
  const statePath = screenshotPath.replace(/\.png$/i, `-${state}.png`)
  writeFileSync(statePath, Buffer.from(screenshot.data, 'base64'))
}

console.log('=== Browser Three-State Cognitive Visual Smoke ===')
console.log(`Product states: ${[...observedProductStates].join(' -> ')}`)
console.log(`FaceCap status: ${currentView.faceStatus}`)
console.log(`Relaxed open-eye targets: ${Object.keys(relaxedOpenEyeWeights).join(', ')}`)
console.log(`Focused morph targets: ${Object.keys(focusedWeights).join(', ')}`)
console.log(`Relaxed closed-eye targets: ${Object.keys(relaxedCloseEyeWeights).join(', ')}`)
console.log('Result: PASS')

socket.close()
