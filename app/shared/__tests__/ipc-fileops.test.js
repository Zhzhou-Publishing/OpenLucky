const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const h = require('./harness')
const mainWindow = require('../main-window') // shared instance with the handlers

function tmpDir(prefix = 'olk-fo-') {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix))
}

test.beforeEach(() => {
  h.resetMocks()
  mainWindow.setWin(null)
})

// ── read-preset-json ─────────────────────────────────────────────────────────

test('read-preset-json: emits parsed presets', () => {
  h.loadHandler('../../ipc/read-preset-json')
  const dir = tmpDir()
  fs.writeFileSync(path.join(dir, '.preset.json'), JSON.stringify({ 'a.jpg': { gamma: 2 } }))
  const ev = h.makeEvent()
  h.ipc.on['read-preset-json'](ev, dir)
  assert.deepEqual(ev.find('preset-json-loaded'), { presets: { 'a.jpg': { gamma: 2 } } })
})

// ── reset-image ──────────────────────────────────────────────────────────────

test('reset-image: removes the preset entry and deletes the output file', async () => {
  h.loadHandler('../../ipc/reset-image')
  const work = tmpDir('olk-work-')
  const out = tmpDir('olk-out-')
  fs.writeFileSync(path.join(work, '.preset.json'), JSON.stringify({ 'a.jpg': { gamma: 2 }, 'b.jpg': {} }))
  fs.writeFileSync(path.join(out, 'a.jpg'), 'img')
  const ev = h.makeEvent()
  await h.ipc.on['reset-image'](ev, { workingDirectory: work, outputDirectory: out, filename: 'a.jpg' })

  assert.deepEqual(ev.find('image-reset'), { filename: 'a.jpg', success: true })
  const remaining = JSON.parse(fs.readFileSync(path.join(work, '.preset.json'), 'utf-8'))
  assert.deepEqual(Object.keys(remaining), ['b.jpg'])
  assert.equal(fs.existsSync(path.join(out, 'a.jpg')), false)
})

// ── copy-preset-json ─────────────────────────────────────────────────────────

test('copy-preset-json: errors when source .preset.json is absent', () => {
  h.loadHandler('../../ipc/copy-preset-json')
  const ev = h.makeEvent()
  h.ipc.on['copy-preset-json'](ev, { workingDirectory: tmpDir(), originalDirectory: tmpDir() })
  assert.match(ev.find('copy-preset-json-error').message, /Source \.preset\.json not found/)
})

test('copy-preset-json: copies the file to the original directory on success', () => {
  h.loadHandler('../../ipc/copy-preset-json')
  const work = tmpDir(); const orig = tmpDir()
  fs.writeFileSync(path.join(work, '.preset.json'), '{"a.jpg":{}}')
  const ev = h.makeEvent()
  h.ipc.on['copy-preset-json'](ev, { workingDirectory: work, originalDirectory: orig })
  assert.equal(ev.channels().includes('copy-preset-json-success'), true)
  assert.equal(fs.readFileSync(path.join(orig, '.preset.json'), 'utf-8'), '{"a.jpg":{}}')
})

// ── get-full-res-image ───────────────────────────────────────────────────────

test('get-full-res-image: non-TIFF returns a direct file:// url', async () => {
  h.loadHandler('../../ipc/get-full-res-image')
  const dir = tmpDir()
  const ev = h.makeEvent()
  await h.ipc.on['get-full-res-image'](ev, { directoryPath: dir, filename: 'a.jpg' })
  assert.equal(ev.find('full-res-image-loaded').url, `file://${path.join(dir, 'a.jpg')}`)
  assert.equal(h.sharpCalls.length, 0)
})

test('get-full-res-image: TIFF is transcoded to a jpg via sharp', async () => {
  h.loadHandler('../../ipc/get-full-res-image')
  const dir = tmpDir()
  const ev = h.makeEvent()
  await h.ipc.on['get-full-res-image'](ev, { directoryPath: dir, filename: 'scan.tif' })
  assert.equal(h.sharpCalls.length, 1)
  assert.match(ev.find('full-res-image-loaded').url, /scan\.jpg$/)
})

// ── refresh-image ────────────────────────────────────────────────────────────

test('refresh-image: emits image-refreshed with a thumbnail entry', async () => {
  h.loadHandler('../../ipc/refresh-image')
  const dir = tmpDir()
  const ev = h.makeEvent()
  await h.ipc.on['refresh-image'](ev, { directoryPath: dir, filename: 'a.jpg' })
  const payload = ev.find('image-refreshed')
  assert.equal(payload.filename, 'a.jpg')
  assert.equal(payload.entry.name, 'a.jpg')
  assert.match(payload.entry.url, /^file:\/\//)
})

// ── get-images (event.sender) ────────────────────────────────────────────────

test('get-images: sends images-loaded to the calling window for image files only', async () => {
  h.loadHandler('../../ipc/get-images')
  const dir = tmpDir()
  fs.writeFileSync(path.join(dir, 'a.jpg'), 'x')
  fs.writeFileSync(path.join(dir, 'b.arw'), 'x')
  fs.writeFileSync(path.join(dir, 'notes.txt'), 'x') // ignored
  const ev = h.makeEvent()
  await h.ipc.on['get-images'](ev, dir)
  const { images } = ev.find('images-loaded')
  const names = images.map(i => i.name).sort()
  assert.deepEqual(names, ['a.jpg', 'b.arw'])
})

// ── select-directory (dialog + event.sender) ─────────────────────────────────

test('select-directory: cancelled dialog sends directory-cancelled', async () => {
  h.loadHandler('../../ipc/select-directory')
  const ev = h.makeEvent()
  h.electronMock.dialog.showOpenDialog = async () => ({ canceled: true, filePaths: [] })
  await h.ipc.on['select-directory'](ev)
  assert.equal(ev.channels().includes('directory-cancelled'), true)
})

test('select-directory: selection sends directory-selected with file list', async () => {
  h.loadHandler('../../ipc/select-directory')
  const dir = tmpDir()
  fs.writeFileSync(path.join(dir, 'a.jpg'), 'x')
  const ev = h.makeEvent()
  h.electronMock.dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [dir] })
  await h.ipc.on['select-directory'](ev)
  const payload = ev.find('directory-selected')
  assert.equal(payload.path, dir)
  assert.deepEqual(payload.files, ['a.jpg'])
})

// ── open-external (url allow-listing) ────────────────────────────────────────

test('open-external: opens only http(s) urls', () => {
  h.loadHandler('../../ipc/open-external')
  const opened = []
  h.electronMock.shell.openExternal = (u) => opened.push(u)
  h.ipc.on['open-external'](null, 'https://example.com')
  h.ipc.on['open-external'](null, 'http://example.com')
  h.ipc.on['open-external'](null, 'javascript:alert(1)')
  h.ipc.on['open-external'](null, 'file:///etc/passwd')
  assert.deepEqual(opened, ['https://example.com', 'http://example.com'])
})

// ── set-theme ────────────────────────────────────────────────────────────────

test('set-theme: maps to dark/light only', () => {
  h.loadHandler('../../ipc/set-theme')
  h.ipc.on['set-theme'](null, 'dark')
  assert.equal(h.electronMock.nativeTheme.themeSource, 'dark')
  h.ipc.on['set-theme'](null, 'light')
  assert.equal(h.electronMock.nativeTheme.themeSource, 'light')
  h.ipc.on['set-theme'](null, 'system') // anything else → light
  assert.equal(h.electronMock.nativeTheme.themeSource, 'light')
})

// ── confirm-close ────────────────────────────────────────────────────────────

test('confirm-close: a true response closes the window', () => {
  h.loadHandler('../../ipc/confirm-close')
  let closed = false
  const win = h.makeWin(); win.close = () => { closed = true }
  mainWindow.setWin(win)
  h.ipc.on['confirm-close-response'](null, true)
  assert.equal(closed, true)
})

test('confirm-close: a false response leaves the window open', () => {
  h.loadHandler('../../ipc/confirm-close')
  let closed = false
  const win = h.makeWin(); win.close = () => { closed = true }
  mainWindow.setWin(win)
  h.ipc.on['confirm-close-response'](null, false)
  assert.equal(closed, false)
})
