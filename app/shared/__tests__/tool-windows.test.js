// Tests for the tool-window manager (app/main/tool-windows.js) and its three
// IPC delegators (open-tool-window / get-tool-context / tool-result).
//
// The manager talks to electron's BrowserWindow directly, so these tests swap
// in a controllable fake window class (freshRequired per test so the module
// binds to the current mock) and drive the handlers through the harness IPC.
const test = require('node:test')
const assert = require('node:assert/strict')

const h = require('./harness')

// A controllable BrowserWindow fake: keeps an id registry for fromId(),
// records loadFile/show/emits, and lets a test route fromWebContents() to any
// window (used by the open-tool-window delegator to find the owner).
function installFakeWindows() {
  let nextId = 1
  const byId = new Map()
  const created = []
  class FakeBrowserWindow {
    constructor(opts) {
      this.id = nextId++
      this.opts = opts
      this.destroyed = false
      this.sent = []
      this.loaded = null
      this._on = {}
      this._once = {}
      this.webContents = {
        send: (ch, payload) => this.sent.push({ channel: ch, payload }),
        isDestroyed: () => this.destroyed
      }
      byId.set(this.id, this)
      created.push(this)
    }
    loadFile(file, opts) { this.loaded = { file, opts } }
    once(event, fn) { this._once[event] = fn }
    on(event, fn) { this._on[event] = fn }
    show() { this.shown = true }
    isDestroyed() { return this.destroyed }
    emit(event) { (this._once[event] || this._on[event] || (() => {}))() }
    find(channel) { return (this.sent.find(m => m.channel === channel) || {}).payload }
    channels() { return this.sent.map(m => m.channel) }
    static fromId(id) { return byId.get(id) || null }
    static fromWebContents() {
      return FakeBrowserWindow._fromSender ? FakeBrowserWindow._fromSender() : null
    }
  }
  FakeBrowserWindow._fromSender = null
  return { FakeBrowserWindow, byId, created }
}

const DEFAULT_BROWSER_WINDOW = class {
  static fromWebContents() { return null }
}

test.afterEach(() => {
  h.electronMock.BrowserWindow = DEFAULT_BROWSER_WINDOW
})

test('tool-windows: opens a child window, loads ?tool=, and serves its context', () => {
  const { FakeBrowserWindow, created } = installFakeWindows()
  h.electronMock.BrowserWindow = FakeBrowserWindow
  const tw = h.freshRequire('../../main/tool-windows')

  const owner = new FakeBrowserWindow({})
  const id = tw.openToolWindow('dust', { photo: 'a.jpg', workingDir: '/w' }, owner)

  assert.equal(typeof id, 'number')
  const child = created[1]                       // created[0] is the owner
  assert.equal(child.opts.parent, owner)         // child of the main window
  assert.deepEqual(child.loaded.opts, { query: { tool: 'dust' } })
  assert.equal(child.opts.width, 1000)           // sized from shared/tools.js
  assert.equal(tw.getToolContext(child.webContents).photo, 'a.jpg')
})

test('tool-windows: singleton — a second open returns null and creates no window', () => {
  const { FakeBrowserWindow, created } = installFakeWindows()
  h.electronMock.BrowserWindow = FakeBrowserWindow
  const tw = h.freshRequire('../../main/tool-windows')

  const owner = new FakeBrowserWindow({})
  const first = tw.openToolWindow('dust', { photo: 'a.jpg' }, owner)
  const again = tw.openToolWindow('dust', { photo: 'b.jpg' }, owner)

  assert.equal(typeof first, 'number')
  assert.equal(again, null)
  assert.equal(created.length, 2)                // owner + one child only
})

test('tool-windows: forwardToolResult sends {tool, result} to the owner window', () => {
  const { FakeBrowserWindow } = installFakeWindows()
  h.electronMock.BrowserWindow = FakeBrowserWindow
  const tw = h.freshRequire('../../main/tool-windows')

  const owner = new FakeBrowserWindow({})
  tw.openToolWindow('dust', { photo: 'a.jpg' }, owner)
  tw.forwardToolResult('dust', { grain_level: 0.3 })

  assert.deepEqual(owner.find('tool-result'), { tool: 'dust', result: { grain_level: 0.3 } })
})

test('tool-windows: unknown tool or missing owner throws', () => {
  const { FakeBrowserWindow } = installFakeWindows()
  h.electronMock.BrowserWindow = FakeBrowserWindow
  const tw = h.freshRequire('../../main/tool-windows')

  assert.throws(() => tw.openToolWindow('nope', {}, { id: 1, isDestroyed: () => false }), /unknown tool/)
  assert.throws(() => tw.openToolWindow('dust', {}, null), /owner window/)
})

test('ipc: open-tool-window / get-tool-context / tool-result wire to the manager', () => {
  const { FakeBrowserWindow, created } = installFakeWindows()
  h.electronMock.BrowserWindow = FakeBrowserWindow
  h.freshRequire('../../main/tool-windows')

  const owner = new FakeBrowserWindow({})
  FakeBrowserWindow._fromSender = () => owner

  h.loadHandler('../../ipc/open-tool-window')
  h.loadHandler('../../ipc/get-tool-context')
  h.loadHandler('../../ipc/tool-result')

  const ev = h.makeEvent()
  const id = h.ipc.handle['open-tool-window'](ev, { tool: 'dust', payload: { photo: 'a.jpg' } })
  assert.equal(typeof id, 'number')

  const child = created[1]
  const ctx = h.ipc.handle['get-tool-context']({ sender: child.webContents })
  assert.equal(ctx.photo, 'a.jpg')

  h.ipc.on['tool-result'](child.webContents, { tool: 'dust', result: { grain_level: 0.3 } })
  assert.deepEqual(owner.find('tool-result'), { tool: 'dust', result: { grain_level: 0.3 } })
})
