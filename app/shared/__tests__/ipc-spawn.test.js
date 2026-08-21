const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const h = require('./harness')

function tmpDir(prefix = 'olk-ipc-') {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix))
}

test.beforeEach(() => h.resetMocks())

// ── check-openlucky ──────────────────────────────────────────────────────────

test('check-openlucky: success on exit 0', () => {
  h.loadHandler('../../ipc/check-openlucky')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['check-openlucky'](ev)
  assert.deepEqual(h.lastSpawn().args.slice(-1), ['--help'])
  child.close(0)
  assert.deepEqual(ev.find('openlucky-checked'), { success: true, error: '' })
})

test('check-openlucky: failure on non-zero exit carries stderr', () => {
  h.loadHandler('../../ipc/check-openlucky')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['check-openlucky'](ev)
  child.emitStderr('not found')
  child.close(127)
  assert.deepEqual(ev.find('openlucky-checked'), { success: false, error: 'not found' })
})

test('check-openlucky: spawn error reports failure', () => {
  h.loadHandler('../../ipc/check-openlucky')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['check-openlucky'](ev)
  child.fail('ENOENT')
  assert.equal(ev.find('openlucky-checked').success, false)
})

// ── get-presets ──────────────────────────────────────────────────────────────

test('get-presets: parses config JSON into a preset list', () => {
  h.loadHandler('../../ipc/get-presets')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['get-presets'](ev)
  assert.deepEqual(h.lastSpawn().args.slice(-4), ['config', 'read', '-f', 'json'])
  child.emitStdout(JSON.stringify({ presets: { kodak: { label: 'Kodak Gold' }, fuji: {} } }))
  child.close(0)
  const { presets } = ev.find('presets-loaded')
  assert.deepEqual(presets, [
    { label: 'Kodak Gold', value: 'kodak' },
    { value: 'fuji', label: 'fuji' } // falls back to key as label
  ])
})

test('get-presets: malformed JSON yields presets-error', () => {
  h.loadHandler('../../ipc/get-presets')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['get-presets'](ev)
  child.emitStdout('{not json')
  child.close(0)
  assert.equal(ev.channels().includes('presets-error'), true)
})

// ── compute-histogram (ipcMain.handle) ───────────────────────────────────────

test('compute-histogram: resolves parsed JSON on success', async () => {
  h.loadHandler('../../ipc/compute-histogram')
  const child = h.makeChild(); h.setSpawn(child)
  const dir = tmpDir()
  const p = h.ipc.handle['compute-histogram']({}, { directoryPath: dir, filename: 'a.tif' })
  const { args } = h.lastSpawn()
  assert.equal(args.includes('histogram'), true)
  child.emitStdout('{"r":[1,2,3]}')
  child.close(0)
  assert.deepEqual(await p, { r: [1, 2, 3] })
})

test('compute-histogram: rejects on non-zero exit', async () => {
  h.loadHandler('../../ipc/compute-histogram')
  const child = h.makeChild(); h.setSpawn(child)
  const dir = tmpDir()
  const p = h.ipc.handle['compute-histogram']({}, { directoryPath: dir, filename: 'a.tif' })
  child.emitStderr('bad area')
  child.close(2)
  await assert.rejects(p, /bad area/)
})

// ── pick-color (ipcMain.handle) ──────────────────────────────────────────────

test('pick-color: spawns tool pick and resolves parsed JSON', async () => {
  h.loadHandler('../../ipc/pick-color')
  const child = h.makeChild(); h.setSpawn(child)
  const p = h.ipc.handle['pick-color']({}, { filePath: '/a.tif', x: 10, y: 20 })
  const { args } = h.lastSpawn()
  assert.deepEqual(args.slice(-10), ['tool', 'pick', '-i', '/a.tif', '-x', '10', '-y', '20', '-f', '8'])
  child.emitStdout('{"hex":"#aabbcc"}')
  child.close(0)
  assert.deepEqual(await p, { hex: '#aabbcc' })
})

// ── apply-preset (filmbatch) ─────────────────────────────────────────────────

test('apply-preset: emits started then success, spawning filmbatch', async () => {
  h.loadHandler('../../ipc/apply-preset')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['apply-preset'](ev, { inputPath: 'in', outputPath: 'out', preset: 'kodak' })
  const { args } = h.lastSpawn()
  assert.deepEqual(args.slice(-9), ['filmbatch', '--input', 'in', '--output', 'out', '--preset', 'kodak', '--algo', 'v2'])
  assert.equal(ev.channels()[0], 'preset-apply-started')
  child.close(0)
  assert.equal(ev.channels().includes('preset-apply-success'), true)
})

test('apply-preset: non-zero exit emits preset-apply-error with stderr', () => {
  h.loadHandler('../../ipc/apply-preset')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['apply-preset'](ev, { inputPath: 'in', outputPath: 'out', preset: 'kodak' })
  child.emitStderr('kaboom')
  child.close(1)
  assert.deepEqual(ev.find('preset-apply-error'), { message: 'Process exited with code 1', error: 'kaboom' })
})

// ── apply-filmparam / apply-filmparambatch ───────────────────────────────────

test('apply-filmparam: spawns filmparam with full path + rotate and reports success', () => {
  h.loadHandler('../../ipc/apply-filmparam')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['apply-filmparam'](ev, {
    inputPath: '/in', outputPath: '/out', filename: 'a.jpg', params: '1,1,1,2,3', rotateClockwise: 90
  })
  const { args } = h.lastSpawn()
  assert.equal(args.includes('filmparam'), true)
  assert.equal(args[args.indexOf('--rotate-clockwise') + 1], '90')
  assert.equal(args[args.indexOf('--input') + 1], path.join('/in', 'a.jpg'))
  child.close(0)
  assert.equal(ev.find('filmparam-apply-success').outputFile, path.join('/out', 'a.jpg'))
})

test('apply-filmparambatch: forwards optional args and reports batch success', () => {
  h.loadHandler('../../ipc/apply-filmparambatch')
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['apply-filmparambatch'](ev, {
    inputPath: 'inDir', outputPath: 'outDir', params: '1,1,1,2,3',
    area: { x1: 1, y1: 2, x2: 3, y2: 4 }, exposure: 0.5, tone: 'auto'
  })
  const { args } = h.lastSpawn()
  assert.equal(args.includes('filmparambatch'), true)
  assert.equal(args[args.indexOf('--area') + 1], '1,2,3,4')
  assert.equal(args[args.indexOf('--exposure') + 1], '0.5')
  assert.equal(args[args.indexOf('--tone') + 1], 'auto')
  child.close(0)
  assert.equal(ev.channels().includes('filmparambatch-apply-success'), true)
})

// ── apply-preset-to-file ─────────────────────────────────────────────────────

test('apply-preset-to-file: missing preset file errors out before spawning', () => {
  h.loadHandler('../../ipc/apply-preset-to-file')
  const ev = h.makeEvent()
  h.ipc.on['apply-preset-to-file'](ev, {
    presetFile: path.join(os.tmpdir(), 'does-not-exist-xyz.json'),
    inputFilePath: '/in/a.jpg', outputFilePath: '/out/a.jpg'
  })
  assert.equal(ev.find('preset-to-file-error').message, 'Preset file not found')
  assert.equal(h.spawnCalls.length, 0)
})

test('apply-preset-to-file: errors when no preset entry matches the file', () => {
  h.loadHandler('../../ipc/apply-preset-to-file')
  const dir = tmpDir()
  const presetFile = path.join(dir, 'p.json')
  fs.writeFileSync(presetFile, JSON.stringify({ 'other.jpg': {} }))
  const ev = h.makeEvent()
  h.ipc.on['apply-preset-to-file'](ev, { presetFile, inputFilePath: '/in/a.jpg', outputFilePath: '/out/a.jpg' })
  assert.equal(ev.find('preset-to-file-error').message, 'Preset not found for file')
  assert.equal(h.spawnCalls.length, 0)
})

test('apply-preset-to-file: builds param string from preset and reports success', () => {
  h.loadHandler('../../ipc/apply-preset-to-file')
  const dir = tmpDir()
  const presetFile = path.join(dir, 'p.json')
  fs.writeFileSync(presetFile, JSON.stringify({ 'a.jpg': { mask_r: 1, mask_g: 1, mask_b: 1, gamma: 2, contrast: 3 } }))
  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  h.ipc.on['apply-preset-to-file'](ev, { presetFile, inputFilePath: '/in/a.jpg', outputFilePath: '/out/a.jpg' })
  const { args } = h.lastSpawn()
  assert.equal(args[args.indexOf('--param') + 1], '1,1,1,2,3')
  assert.equal(args.includes('--rotate-clockwise'), false) // to-file omits rotate
  child.close(0)
  assert.equal(ev.channels().includes('preset-to-file-success'), true)
})

// ── apply-preset-to-batch ────────────────────────────────────────────────────

test('apply-preset-to-batch: processes a matching file and reports batch success', async () => {
  h.loadHandler('../../ipc/apply-preset-to-batch')
  const inputDir = tmpDir('olk-in-')
  const outputDir = path.join(tmpDir('olk-out-'), 'out')
  fs.writeFileSync(path.join(inputDir, 'a.jpg'), 'img')
  const presetFile = path.join(inputDir, 'p.json')
  fs.writeFileSync(presetFile, JSON.stringify({ 'a.jpg': { mask_r: 1, mask_g: 1, mask_b: 1, gamma: 2, contrast: 3 } }))

  const child = h.makeChild(); h.setSpawn(child)
  const ev = h.makeEvent()
  const p = h.ipc.on['apply-preset-to-batch'](ev, { presetFile, inputDir, outputDir })
  const { args } = h.lastSpawn()
  assert.equal(args.includes('filmparam'), true)
  assert.equal(args[args.indexOf('--param') + 1], '1,1,1,2,3')
  child.close(0)
  await p
  assert.equal(ev.channels().includes('preset-to-batch-success'), true)
})

test('apply-preset-to-batch: missing preset file errors out', async () => {
  h.loadHandler('../../ipc/apply-preset-to-batch')
  const ev = h.makeEvent()
  await h.ipc.on['apply-preset-to-batch'](ev, {
    presetFile: path.join(os.tmpdir(), 'nope-abc.json'),
    inputDir: tmpDir(), outputDir: tmpDir()
  })
  assert.equal(ev.find('preset-to-batch-error').message, 'Preset file not found')
})
