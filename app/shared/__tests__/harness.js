// Zero-dependency test harness for the Electron main-process code.
//
// The IPC handlers and shared/utils.js require `electron`, `electron-log`,
// `sharp`, `image-size` and `p-limit` — none of which load (or should run) under
// plain `node`. This harness installs a Module._load interceptor that swaps those
// for controllable in-memory stubs, plus helpers to drive handlers and capture
// the messages they emit. Requiring this file MUST happen before any handler /
// shared/utils require, so put it at the top of every integration test file.

const Module = require('node:module')
const EventEmitter = require('node:events')
const os = require('node:os')

// ── Mutable mock state (tests reach in to configure / inspect) ───────────────

// Drives child_process.spawn. Tests set `spawnImpl` to return a fake child and
// every spawn() call is recorded in `spawnCalls`.
const spawnCalls = []
let spawnImpl = () => { throw new Error('spawnImpl not set for this test') }

// Drives image-size's default export.
let imageSizeImpl = () => ({ width: 1000, height: 800 })

// Records sharp() invocations; terminal ops resolve with configurable values.
const sharpCalls = []
let sharpToBufferImpl = async () => Buffer.from('jpeg-bytes')
let sharpToFileImpl = async () => ({})

function sharpFactory(input) {
  sharpCalls.push(input)
  const chain = {
    removeAlpha: () => chain,
    resize: () => chain,
    jpeg: () => chain,
    png: () => chain,
    toFile: (...a) => sharpToFileImpl(...a),
    toBuffer: (...a) => sharpToBufferImpl(...a)
  }
  return chain
}

// Captured IPC registrations.
const ipc = { on: {}, handle: {}, once: {} }

// Electron stub. Mutable so tests can override dialog/shell/nativeTheme.
const electronMock = {
  ipcMain: {
    on: (ch, fn) => { ipc.on[ch] = fn },
    handle: (ch, fn) => { ipc.handle[ch] = fn },
    once: (ch, fn) => { ipc.once[ch] = fn },
    removeListener: () => {},
    removeAllListeners: () => {}
  },
  app: {
    isPackaged: false,
    getPath: () => os.tmpdir(),
    getVersion: () => '1.4.3',
    getLocale: () => 'en'
  },
  dialog: { showOpenDialog: async () => ({ canceled: true, filePaths: [] }) },
  shell: { openExternal: () => {} },
  nativeTheme: { themeSource: 'system' },
  BrowserWindow: class {}
}

// No-op electron-log replacement.
const noop = () => {}
const logStub = {
  transports: { console: {}, file: {} },
  debug: noop, info: noop, warn: noop, error: noop, initialize: noop
}

// Passthrough p-limit: run each task immediately, no concurrency gating.
const pLimitStub = { default: () => (fn) => fn() }

// ── Module interception ──────────────────────────────────────────────────────

const realCp = require('node:child_process')
const cpMock = new Proxy(realCp, {
  get(target, prop) {
    if (prop === 'spawn') {
      return (...args) => { spawnCalls.push(args); return spawnImpl(...args) }
    }
    return target[prop]
  }
})

const imageSizeMock = (...args) => imageSizeImpl(...args)

const origLoad = Module._load
Module._load = function (request, parent, isMain) {
  switch (request) {
    case 'electron': return electronMock
    case 'electron-log': return logStub
    case 'sharp': return sharpFactory
    case 'image-size': return imageSizeMock
    case 'child_process':
    case 'node:child_process': return cpMock
    case 'p-limit': return pLimitStub
    default: return origLoad.apply(this, arguments)
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

// Re-require a module fresh (clears its cache entry first) so per-module state
// (e.g. confirm-close's allowClose) resets between tests.
function freshRequire(relPath) {
  const resolved = require.resolve(relPath)
  delete require.cache[resolved]
  return require(resolved)
}

// Register a handler module and return its registration maps.
function loadHandler(relPath) {
  const mod = freshRequire(relPath)
  mod.register()
  return mod
}

// A fake `event` whose sender records every send().
function makeEvent() {
  const sent = []
  return {
    sent,
    sender: {
      send: (channel, payload) => sent.push({ channel, payload }),
      isDestroyed: () => false
    },
    // convenience: first payload sent on `channel`
    find: (channel) => (sent.find(m => m.channel === channel) || {}).payload,
    channels: () => sent.map(m => m.channel)
  }
}

// A fake BrowserWindow for getWin()-based handlers.
function makeWin() {
  const sent = []
  return {
    sent,
    isDestroyed: () => false,
    close: () => {},
    on: () => {},
    webContents: {
      send: (channel, payload) => sent.push({ channel, payload })
    },
    find: (channel) => (sent.find(m => m.channel === channel) || {}).payload,
    channels: () => sent.map(m => m.channel)
  }
}

// A fake child process. Drive it with .emitStdout/.emitStderr/.close/.fail.
function makeChild() {
  const child = new EventEmitter()
  child.stdout = new EventEmitter()
  child.stderr = new EventEmitter()
  child.emitStdout = (s) => child.stdout.emit('data', Buffer.from(s))
  child.emitStderr = (s) => child.stderr.emit('data', Buffer.from(s))
  child.close = (code) => child.emit('close', code)
  child.fail = (err) => child.emit('error', err instanceof Error ? err : new Error(err))
  return child
}

// Set the spawn behavior for a test: every spawn returns the given child.
function setSpawn(child) {
  spawnImpl = () => child
}

// The (command, args, options) of the most recent spawn() call.
function lastSpawn() {
  const args = spawnCalls[spawnCalls.length - 1]
  return args ? { command: args[0], args: args[1], options: args[2] } : null
}

function resetMocks() {
  spawnCalls.length = 0
  sharpCalls.length = 0
  spawnImpl = () => { throw new Error('spawnImpl not set for this test') }
  imageSizeImpl = () => ({ width: 1000, height: 800 })
  sharpToBufferImpl = async () => Buffer.from('jpeg-bytes')
  sharpToFileImpl = async () => ({})
  electronMock.app.isPackaged = false
  electronMock.dialog.showOpenDialog = async () => ({ canceled: true, filePaths: [] })
  electronMock.shell.openExternal = () => {}
  electronMock.nativeTheme.themeSource = 'system'
}

module.exports = {
  ipc,
  electronMock,
  spawnCalls,
  sharpCalls,
  freshRequire,
  loadHandler,
  makeEvent,
  makeWin,
  makeChild,
  setSpawn,
  lastSpawn,
  resetMocks,
  // setters for the mutable mock impls
  setImageSize: (fn) => { imageSizeImpl = fn },
  setSharpToBuffer: (fn) => { sharpToBufferImpl = fn },
  setSharpToFile: (fn) => { sharpToFileImpl = fn },
  setSpawnImpl: (fn) => { spawnImpl = fn }
}
