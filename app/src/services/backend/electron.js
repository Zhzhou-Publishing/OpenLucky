// Electron backend adapter — talks to the main process via ipcRenderer.
//
// This is the renderer's single IPC entry point. Pages import from index.js
// (the facade swap point), never window.require('electron') directly.
//
// request() wraps "send + wait for matched response + auto-cleanup". Terminal
// progress channels passed via `terminal` settle the promise; per-chunk progress
// channels passed via `progress` are cleaned up on settle — fixing the
// pre-facade leaky listeners.
// applyFilmparam / refreshImage broadcast on GLOBAL channels and must be matched
// by filename, so they keep filename-matching semantics instead of naive
// one-shot promises.

import { path } from './path'

function transport() {
  if (typeof window === 'undefined' || !window.require) return null
  return window.require('electron').ipcRenderer
}

export const isAvailable = () => !!transport()

// ── low-level primitives ──────────────────────────────────────────────────────

export function subscribe(channel, handler) {
  const ipc = transport()
  if (!ipc) return () => {}
  ipc.on(channel, handler)
  return () => ipc.removeListener(channel, handler)
}

export function subscribeOnce(channel, handler) {
  const ipc = transport()
  if (!ipc) return () => {}
  ipc.once(channel, handler)
  return () => ipc.removeListener(channel, handler)
}

export function unsubscribe(channel, handler) {
  const ipc = transport()
  if (!ipc) return
  ipc.removeListener(channel, handler)
}

export function send(channel, ...args) {
  const ipc = transport()
  if (!ipc) return
  ipc.send(channel, ...args)
}

export function invoke(channel, payload) {
  const ipc = transport()
  if (!ipc) return Promise.reject(new Error('Electron IPC unavailable'))
  return ipc.invoke(channel, payload)
}

// ── request() helper: send + matched response + auto-cleanup ──────────────────

// options:
//   successCh   channel that resolves the promise (payload becomes the value)
//   errorCh     channel that rejects the promise (payload becomes the rejection)
//   match       optional predicate to ignore unrelated broadcasts
//   terminal    { channel: (payload) => result } — channels whose first firing
//               settles the promise; result may be a value or a Promise
//   progress    { channel: handler } — per-chunk listeners removed on settle
function request(sendCh, sendArgs, { successCh, errorCh, match, terminal = {}, progress = {} } = {}) {
  const ipc = transport()
  if (!ipc) return Promise.reject(new Error('Electron IPC unavailable'))
  return new Promise((resolve, reject) => {
    const onSuccess = (e, payload) => {
      if (match && !match(payload)) return
      cleanup()
      resolve(payload)
    }
    const onError = (e, payload) => {
      if (match && !match(payload)) return
      cleanup()
      reject(payload)
    }
    const terminalFns = {}
    const cleanup = () => {
      ipc.removeListener(successCh, onSuccess)
      if (errorCh) ipc.removeListener(errorCh, onError)
      for (const ch of Object.keys(terminal)) ipc.removeListener(ch, terminalFns[ch])
      for (const ch of Object.keys(progress)) ipc.removeListener(ch, progress[ch])
    }

    ipc.on(successCh, onSuccess)
    if (errorCh) ipc.on(errorCh, onError)
    for (const [ch, makeResult] of Object.entries(terminal)) {
      const fn = (e, payload) => {
        cleanup()
        const result = makeResult ? makeResult(payload) : payload
        if (result && typeof result.then === 'function') result.then(resolve, reject)
        else resolve(result)
      }
      terminalFns[ch] = fn
      ipc.on(ch, fn)
    }
    for (const [ch, fn] of Object.entries(progress)) {
      ipc.on(ch, fn)
    }
    ipc.send(...sendArgs)
  })
}

// ── invoke operations (promise) ───────────────────────────────────────────────

export function computeHistogram(payload) {
  return invoke('compute-histogram', payload)
}

export function pickColor(payload) {
  return invoke('pick-color', payload)
}

// ── send + matched response (promise) ─────────────────────────────────────────

export function getPresets() {
  return request('get-presets', ['get-presets'], { successCh: 'presets-loaded', errorCh: 'presets-error' })
}

export function checkOpenlucky() {
  return request('check-openlucky', ['check-openlucky'], { successCh: 'openlucky-checked' })
}

// resolve {path, files} | {canceled:true}; reject on directory-error (bare string)
export function selectDirectory() {
  return request('select-directory', ['select-directory'], {
    successCh: 'directory-selected',
    errorCh: 'directory-error',
    terminal: { 'directory-cancelled': () => ({ canceled: true }) }
  })
}

export function getImages(directoryPath) {
  return request('get-images', ['get-images', directoryPath], { successCh: 'images-loaded', errorCh: 'images-error' })
}

export function readPresetJson(directoryPath) {
  return request('read-preset-json', ['read-preset-json', directoryPath], { successCh: 'preset-json-loaded', errorCh: 'preset-json-error' })
}

export function resetImage({ workingDirectory, outputDirectory, filename }) {
  return request('reset-image', ['reset-image', { workingDirectory, outputDirectory, filename }], {
    successCh: 'image-reset',
    errorCh: 'image-reset-error',
    match: (p) => p.filename === filename
  })
}

export function getFullResImage({ directoryPath, filename }) {
  return request('get-full-res-image', ['get-full-res-image', { directoryPath, filename }], {
    successCh: 'full-res-image-loaded',
    errorCh: 'full-res-image-error'
  })
}

export function prepareWorkingDirectory(directoryPath, options, { progress = {} } = {}) {
  return request('prepare-working-directory', ['prepare-working-directory', directoryPath, options || {}], {
    successCh: 'working-directory-prepared',
    errorCh: 'working-directory-error',
    progress
  })
}

export function prepareWorkingDirectoryFromSelected(directoryPath, options, { progress = {} } = {}) {
  return request('prepare-working-directory-from-selected', ['prepare-working-directory-from-selected', directoryPath, options || {}], {
    successCh: 'working-directory-from-selected-prepared',
    errorCh: 'working-directory-from-selected-error',
    progress
  })
}

export function applyPreset({ inputPath, outputPath, preset }, { progress = {} } = {}) {
  return request('apply-preset', ['apply-preset', { inputPath, outputPath, preset }], {
    successCh: 'preset-apply-success',
    errorCh: 'preset-apply-error',
    progress
  })
}

export function applyFilmparambatch(payload, { progress = {} } = {}) {
  return request('apply-filmparambatch', ['apply-filmparambatch', payload], {
    successCh: 'filmparambatch-apply-success',
    errorCh: 'filmparambatch-apply-error',
    progress
  })
}

export function applyPresetToBatch({ presetFile, inputDir, outputDir }, { progress = {} } = {}) {
  return request('apply-preset-to-batch', ['apply-preset-to-batch', { presetFile, inputDir, outputDir }], {
    successCh: 'preset-to-batch-success',
    errorCh: 'preset-to-batch-error',
    progress
  })
}

// ── filename-matched operations (global channels, multiple requests overlap) ──

const applyFilmparamQueue = []

export function applyFilmparam(payload) {
  const ipc = transport()
  if (!ipc) return Promise.reject(new Error('Electron IPC unavailable'))
  return new Promise((resolve, reject) => {
    const req = { payload, settled: false }
    applyFilmparamQueue.push(req)

    let settledTimeout = null

    const cleanup = () => {
      if (settledTimeout) clearTimeout(settledTimeout)
      ipc.removeListener('filmparam-apply-success', onSuccess)
      ipc.removeListener('filmparam-apply-error', onError)
      const idx = applyFilmparamQueue.indexOf(req)
      if (idx !== -1) applyFilmparamQueue.splice(idx, 1)
    }

    const onSuccess = (e, result) => {
      const outputFile = result && result.outputFile
      const fname = outputFile ? path.basename(outputFile) : null
      const matches = fname === payload.filename || (outputFile && outputFile.includes(payload.filename))
      if (!matches) return
      req.settled = true
      cleanup()
      resolve(result)
    }

    const onError = (e, err) => {
      // filmparam-apply-error carries no filename; attribute only when this
      // request is the SOLE pending one.
      if (applyFilmparamQueue.length !== 1 || applyFilmparamQueue[0] !== req) return
      req.settled = true
      applyFilmparamQueue.length = 0
      cleanup()
      reject(err)
    }

    ipc.on('filmparam-apply-success', onSuccess)
    ipc.on('filmparam-apply-error', onError)

    // Backstop: if success/error never matches, settle instead of leaking.
    settledTimeout = setTimeout(() => {
      if (req.settled) return
      req.settled = true
      cleanup()
      reject(new Error('applyFilmparam timed out waiting for a matching response'))
    }, 120000)

    ipc.send('apply-filmparam', payload)
  })
}

export function refreshImage({ directoryPath, filename }) {
  return request('refresh-image', ['refresh-image', { directoryPath, filename }], {
    successCh: 'image-refreshed',
    errorCh: 'image-refresh-error',
    match: (p) => p.filename === filename
  })
}

// ── fire-and-forget ───────────────────────────────────────────────────────────

export function cancelProcessing() {
  send('cancel-processing')
}

export function confirmCloseResponse(allow) {
  send('confirm-close-response', allow)
}

export function setTheme(name) {
  send('set-theme', name)
}

export function openExternal(url) {
  send('open-external', url)
}

// ── tool windows (pr/025.tool_windows.md) ────────────────────────────────────

// Open a tool window from the main window; resolves to the window id, or null
// when the tool already has a window (singleton, no focus).
export function openToolWindow(tool, payload) {
  return invoke('open-tool-window', { tool, payload })
}

// Inside a tool window: return the payload it was opened with.
export function getToolContext() {
  return invoke('get-tool-context')
}

// Inside a tool window: fire-and-forget the finished result back to the main
// window, which merges it into the photo params and refreshes.
export function notifyToolResult(tool, result) {
  send('tool-result', { tool, result })
}

// On the main window: subscribe to results forwarded by finished tool windows.
export function onToolResult(handler) {
  return subscribe('tool-result', handler)
}

// ── main-push event ───────────────────────────────────────────────────────────

export function onConfirmClose(handler) {
  return subscribe('confirm-close', handler)
}

export function offConfirmClose(handler) {
  unsubscribe('confirm-close', handler)
}

export { path }
