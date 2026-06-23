const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const h = require('./harness') // installs mocks — must come before utils
const utils = h.freshRequire('../utils')

function tmpDir(prefix = 'olk-utils-') {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix))
}

test.beforeEach(() => h.resetMocks())

// ── readPresetJson ───────────────────────────────────────────────────────────

test('readPresetJson returns {} when .preset.json is missing', () => {
  const dir = tmpDir()
  assert.deepEqual(utils.readPresetJson(dir), {})
})

test('readPresetJson parses a valid .preset.json', () => {
  const dir = tmpDir()
  fs.writeFileSync(path.join(dir, '.preset.json'), JSON.stringify({ 'a.jpg': { gamma: 2 } }))
  assert.deepEqual(utils.readPresetJson(dir), { 'a.jpg': { gamma: 2 } })
})

test('readPresetJson returns {} on malformed JSON instead of throwing', () => {
  const dir = tmpDir()
  fs.writeFileSync(path.join(dir, '.preset.json'), '{ not valid json')
  assert.deepEqual(utils.readPresetJson(dir), {})
})

// ── resolveImagePath ─────────────────────────────────────────────────────────

test('resolveImagePath prefers an existing preset output_dir', () => {
  const dir = tmpDir()
  const out = path.join(dir, 'edited.tif')
  fs.writeFileSync(out, 'x')
  const presets = { 'a.jpg': { output_dir: out } }
  assert.equal(utils.resolveImagePath(dir, 'a.jpg', presets), out)
})

test('resolveImagePath falls back to the original when output_dir is absent or missing', () => {
  const dir = tmpDir()
  // no preset entry
  assert.equal(utils.resolveImagePath(dir, 'a.jpg', {}), path.join(dir, 'a.jpg'))
  // entry points at a non-existent file
  const presets = { 'a.jpg': { output_dir: path.join(dir, 'nope.tif') } }
  assert.equal(utils.resolveImagePath(dir, 'a.jpg', presets), path.join(dir, 'a.jpg'))
})

// ── needsResize ──────────────────────────────────────────────────────────────

test('needsResize is always true for RAW (no dimension read needed)', async () => {
  h.setImageSize(() => { throw new Error('should not be called for RAW') })
  assert.equal(await utils.needsResize('/x/IMG.ARW'), true)
})

test('needsResize thresholds the long edge at 800 for non-RAW', async () => {
  h.setImageSize(() => ({ width: 1000, height: 600 }))
  assert.equal(await utils.needsResize('/x/big.jpg'), true)
  h.setImageSize(() => ({ width: 640, height: 480 }))
  assert.equal(await utils.needsResize('/x/small.jpg'), false)
})

test('needsResize returns false when dimensions cannot be read', async () => {
  h.setImageSize(() => { throw new Error('corrupt') })
  assert.equal(await utils.needsResize('/x/broken.jpg'), false)
})

// ── buildThumbnailEntry ──────────────────────────────────────────────────────

test('buildThumbnailEntry: non-TIFF returns a file:// url and isRaw flag', async () => {
  const entry = await utils.buildThumbnailEntry('/dir', 'IMG.ARW', {}, '/tmpdir', 42)
  assert.equal(entry.name, 'IMG.ARW')
  assert.equal(entry.isRaw, true)
  assert.match(entry.url, /^file:\/\/.*IMG\.ARW\?t=42$/)
  assert.equal(h.sharpCalls.length, 0) // no transcode for non-TIFF
})

test('buildThumbnailEntry: TIFF is transcoded via sharp to a jpg thumbnail', async () => {
  const entry = await utils.buildThumbnailEntry('/dir', 'scan.tif', {}, '/tmpdir', 7)
  assert.equal(entry.isRaw, false)
  assert.equal(h.sharpCalls.length, 1)
  assert.match(entry.url, /scan\.jpg\?t=7$/)
})

// ── resizeImage (spawn wiring) ───────────────────────────────────────────────

test('resizeImage spawns `tool resize` with -v and resolves success on exit 0', async () => {
  const child = h.makeChild()
  h.setSpawn(child)
  const p = utils.resizeImage('/in.arw', '/out.tif', { value: 1920 })
  const { args } = h.lastSpawn()
  assert.deepEqual(args.slice(-8), ['tool', 'resize', '-i', '/in.arw', '-o', '/out.tif', '-v', '1920'])
  child.close(0)
  assert.deepEqual(await p, { success: true })
})

test('resizeImage resolves {success:false} with stderr on non-zero exit', async () => {
  const child = h.makeChild()
  h.setSpawn(child)
  const p = utils.resizeImage('/in.arw', '/out.tif', {})
  // no -v when value omitted
  const { args } = h.lastSpawn()
  assert.equal(args.includes('-v'), false)
  child.emitStderr('boom')
  child.close(3)
  assert.deepEqual(await p, { success: false, error: 'boom' })
})
