import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'

const [cdpUrl, applicationUrl, screenshotPath] = process.argv.slice(2)
if (!cdpUrl || !applicationUrl || !screenshotPath) {
  throw new Error('Expected CDP URL, application URL, and screenshot path')
}

const socket = new WebSocket(cdpUrl)
const pending = new Map()
const debugTargets = new Map()
const runtimeExceptions = []
let nextId = 1

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
  if (state && targetsObjectId) debugTargets.set(state, targetsObjectId)
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
let neutralScreenshot = null
let focusedStateSince = null
const deadline = Date.now() + 14_000

while (Date.now() < deadline) {
  await new Promise((resolve) => setTimeout(resolve, 250))
  currentView = await evaluate(`(() => ({
    productState: document.querySelector('.insight-card--state strong')?.textContent?.trim() ?? '',
    visualState: document.querySelector('.brain-scene__state strong')?.textContent?.trim() ?? '',
    faceStatus: document.querySelector('.brain-scene__diagnostics span:nth-child(2)')?.textContent?.trim() ?? '',
    avatarStatus: document.querySelector('.brain-scene__diagnostics span:first-child')?.textContent?.trim() ?? ''
  }))()`)
  if (
    currentView.productState === 'Neutral'
    || currentView.productState === 'Concentration'
  ) {
    observedProductStates.add(currentView.productState)
  }
  if (
    neutralScreenshot === null
    && currentView.productState === 'Neutral'
    && currentView.visualState === 'neutral'
    && currentView.faceStatus.toLowerCase().includes('native')
  ) {
    neutralScreenshot = await call('Page.captureScreenshot', {
      format: 'png',
      captureBeyondViewport: true,
    })
  }
  const isFocusedView = currentView.productState === 'Concentration'
    && currentView.visualState === 'focused'
  if (isFocusedView) {
    focusedStateSince ??= Date.now()
  } else {
    focusedStateSince = null
  }
  if (
    observedProductStates.has('Neutral')
    && observedProductStates.has('Concentration')
    && debugTargets.has('neutral')
    && debugTargets.has('focused')
    && isFocusedView
    && focusedStateSince !== null
    && Date.now() - focusedStateSince >= 800
    && currentView.faceStatus.toLowerCase().includes('native')
    && currentView.avatarStatus.toLowerCase().includes('loaded')
  ) {
    break
  }
}

assert.deepEqual([...observedProductStates].sort(), [
  'Concentration',
  'Neutral',
])
assert.ok(debugTargets.has('neutral'))
assert.ok(debugTargets.has('focused'))
assert.equal(currentView.productState, 'Concentration')
assert.equal(currentView.visualState, 'focused')
assert.match(currentView.faceStatus, /native/i)
assert.match(currentView.avatarStatus, /loaded/i)
assert.deepEqual(runtimeExceptions, [])
assert.ok(neutralScreenshot)

const neutralWeights = await readTargetWeights(debugTargets.get('neutral'))
const focusedWeights = await readTargetWeights(debugTargets.get('focused'))
assert.deepEqual(Object.keys(neutralWeights).sort(), [
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

const screenshot = await call('Page.captureScreenshot', {
  format: 'png',
  captureBeyondViewport: true,
})
writeFileSync(screenshotPath, Buffer.from(screenshot.data, 'base64'))
const neutralScreenshotPath = screenshotPath.replace(/\.png$/i, '-neutral.png')
writeFileSync(
  neutralScreenshotPath,
  Buffer.from(neutralScreenshot.data, 'base64'),
)

console.log('=== Browser Binary Cognitive Visual Smoke ===')
console.log(`Product states: ${[...observedProductStates].join(' -> ')}`)
console.log(`Current product state: ${currentView.productState}`)
console.log(`Current FaceCap visual state: ${currentView.visualState}`)
console.log(`FaceCap status: ${currentView.faceStatus}`)
console.log(`Neutral morph targets: ${Object.keys(neutralWeights).join(', ')}`)
console.log(`Focused morph targets: ${Object.keys(focusedWeights).join(', ')}`)
console.log(`Neutral screenshot: ${neutralScreenshotPath}`)
console.log('Result: PASS')

socket.close()
