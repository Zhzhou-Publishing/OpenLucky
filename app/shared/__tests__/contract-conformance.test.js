const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const h = require('./harness')
const CONTRACT = require('../backend-contract')
const cliArgs = require('../cli-args')

const IPC_DIR = path.resolve(__dirname, '..', '..', 'ipc')

// ── Contract table integrity ─────────────────────────────────────────────────

test('contract: is JSON-serializable (serde-ready round-trip)', () => {
  const roundTripped = JSON.parse(JSON.stringify(CONTRACT))
  assert.deepEqual(roundTripped, CONTRACT)
})

test('contract: ids are unique and every id maps to an ipc/<id>.js file', () => {
  const seen = new Set()
  for (const entry of CONTRACT) {
    assert.equal(typeof entry.id, 'string', 'every entry needs an id')
    assert.ok(!seen.has(entry.id), `duplicate contract id: ${entry.id}`)
    seen.add(entry.id)
    const file = path.join(IPC_DIR, `${entry.id}.js`)
    assert.ok(fs.existsSync(file), `contract id "${entry.id}" must map to ipc/${entry.id}.js`)
    const mod = h.freshRequire(`../../ipc/${entry.id}`)
    assert.equal(typeof mod.register, 'function', `ipc/${entry.id}.js must export register()`)
  }
})

test('contract: registration is one of handle/on/once and channel is a string', () => {
  for (const entry of CONTRACT) {
    assert.ok(['handle', 'on', 'once'].includes(entry.registration),
      `${entry.id}: registration must be handle/on/once`)
    assert.equal(typeof entry.channel, 'string', `${entry.id}: channel must be a string`)
  }
})

test('contract: kind and implementation are from the allowed sets', () => {
  for (const entry of CONTRACT) {
    assert.ok(['spawn-json', 'spawn-stream', 'custom'].includes(entry.kind),
      `${entry.id}: bad kind "${entry.kind}"`)
    assert.ok(['engine-driver', 'custom-handler'].includes(entry.implementation),
      `${entry.id}: bad implementation "${entry.implementation}"`)
  }
})

test('contract: every spawn.cliBuilder name exists in cli-args (Rust argv spec)', () => {
  for (const entry of CONTRACT) {
    if (!entry.spawn || !entry.spawn.cliBuilder) continue
    assert.equal(typeof cliArgs[entry.spawn.cliBuilder], 'function',
      `${entry.id}: spawn.cliBuilder "${entry.spawn.cliBuilder}" not found in cli-args.js`)
  }
})

test('contract: spawn-stream driver entries declare started/progress/success/error or finalize', () => {
  for (const entry of CONTRACT) {
    if (entry.implementation !== 'engine-driver') continue
    if (entry.kind === 'spawn-json') {
      assert.ok(entry.return && entry.return.type, `${entry.id}: spawn-json needs return spec`)
      continue
    }
    if (entry.kind === 'spawn-stream') {
      const hasStream = entry.emit && (entry.emit.started || entry.emit.finalize)
      assert.ok(hasStream, `${entry.id}: spawn-stream needs emit.started or emit.finalize`)
    }
  }
})

test('contract: custom-handler entries do not declare engine spawn drivers', () => {
  for (const entry of CONTRACT) {
    if (entry.implementation !== 'custom-handler') continue
    assert.notEqual(entry.kind, 'spawn-json', `${entry.id}: custom handler cannot be spawn-json`)
  }
})

// ── Contract <-> delegator sync (after A2/A3, every entry registers its channel) ──

test('contract: loadHandler registers the declared channel on ipcMain', () => {
  for (const entry of CONTRACT) {
    const mod = h.loadHandler(`../../ipc/${entry.id}`)
    const map = h.ipc[entry.registration]
    assert.equal(typeof map[entry.channel], 'function',
      `${entry.id}: after register(), h.ipc.${entry.registration}['${entry.channel}'] should be set`)
    if (entry.setupWindow) {
      assert.equal(typeof mod.setupWindow, 'function',
        `${entry.id}: contract flags setupWindow but the delegator does not export it`)
    }
  }
})

test('contract: prepare-working-directory-from-selected registers once(cancel-processing)', () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  const ev = h.makeEvent()
  const p = h.ipc.on['prepare-working-directory-from-selected'](ev, 'nonexistent-dir')
  assert.equal(typeof h.ipc.once['cancel-processing'], 'function',
    'handler must register once(cancel-processing)')
  // handler throws on ENOENT; swallow the rejection (p-limit passthrough)
  if (p && typeof p.then === 'function') p.catch(() => {})
})
