const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const h = require('./harness')

function tmpDir(prefix = 'olk-prep-') {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix))
}

// spawn that returns a child which auto-closes with the given code on the next
// tick — lets us await handlers whose resize step runs after `await needsResize`.
function autoClose(code = 0) {
  h.setSpawnImpl(() => {
    const c = h.makeChild()
    setImmediate(() => c.close(code))
    return c
  })
}

test.beforeEach(() => h.resetMocks())

test('prepare-working-directory: copies small images (no resize) and reports prepared', async () => {
  h.loadHandler('../../ipc/prepare-working-directory')
  h.setImageSize(() => ({ width: 640, height: 480 })) // below 800 → copy, no resize
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'a.jpg'), 'img-bytes')
  fs.writeFileSync(path.join(dir, '.preset.json'), '{"a.jpg":{}}')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory'](ev, dir)

  const payload = ev.find('working-directory-prepared')
  assert.ok(payload, 'should emit working-directory-prepared')
  assert.equal(payload.originalDirectory, dir)
  assert.equal(path.basename(payload.outputDirectory), 'output')
  // file + preset copied into the working dir, output dir created
  assert.equal(fs.readFileSync(path.join(payload.workingDirectory, 'a.jpg'), 'utf-8'), 'img-bytes')
  assert.equal(fs.existsSync(path.join(payload.workingDirectory, '.preset.json')), true)
  assert.equal(fs.existsSync(payload.outputDirectory), true)
  assert.equal(h.spawnCalls.length, 0) // copy path never spawns resize
})

test('prepare-working-directory: large images go through the resize CLI', async () => {
  h.loadHandler('../../ipc/prepare-working-directory')
  h.setImageSize(() => ({ width: 4000, height: 3000 })) // >= 800 → resize
  autoClose(0)
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'big.jpg'), 'img')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory'](ev, dir, { compressPreview: true })

  assert.ok(ev.find('working-directory-prepared'))
  assert.equal(h.spawnCalls.length, 1)
  const { args } = h.lastSpawn()
  assert.equal(args.includes('resize'), true)
  // compressPreview → -v 1920
  assert.equal(args[args.indexOf('-v') + 1], '1920')
})

test('prepare-working-directory-from-selected: success path reports prepared', async () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  h.setImageSize(() => ({ width: 640, height: 480 }))
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'a.jpg'), 'img')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory-from-selected'](ev, dir)

  const payload = ev.find('working-directory-from-selected-prepared')
  assert.ok(payload, 'should emit working-directory-from-selected-prepared')
  assert.equal(payload.originalDirectory, dir)
  assert.equal(fs.existsSync(path.join(payload.workingDirectory, 'a.jpg')), true)
})

test('prepare-working-directory-from-selected: early-use writes manifest, streams image-ready, partial-ready at threshold', async () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  h.setImageSize(() => ({ width: 640, height: 480 })) // copy, no resize
  const dir = tmpDir('olk-src-')
  for (let i = 0; i < 6; i++) {
    fs.writeFileSync(path.join(dir, `img${i}.jpg`), 'img')
  }
  fs.writeFileSync(path.join(dir, '.preset.json'), '{"img0.jpg":{}}')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory-from-selected'](ev, dir)

  // partial-ready fires exactly once, at ceil(6 * 1/3) = 2 ready images
  const partials = ev.sent.filter(m => m.channel === 'working-directory-partial-ready')
  assert.equal(partials.length, 1)
  const partial = partials[0].payload
  assert.equal(partial.total, 6)
  assert.equal(partial.readyCount, 2)

  // one image-ready per successful file
  assert.equal(ev.sent.filter(m => m.channel === 'working-image-ready').length, 6)

  // complete still fires
  const complete = ev.find('working-directory-from-selected-prepared')
  assert.ok(complete)

  // manifest + .preset.json are in the working dir up front
  const wd = complete.workingDirectory
  const manifest = JSON.parse(fs.readFileSync(path.join(wd, '.manifest.json'), 'utf-8'))
  assert.equal(manifest.total, 6)
  assert.equal(manifest.files.length, 6)
  assert.equal(fs.existsSync(path.join(wd, '.preset.json')), true)
})

test('prepare-working-directory-from-selected: a resize failure emits image-error, records it, and still completes', async () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  h.setImageSize(() => ({ width: 4000, height: 3000 })) // → resize
  autoClose(1) // resize CLI exits non-zero
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'big.jpg'), 'img')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory-from-selected'](ev, dir)

  const errs = ev.sent.filter(m => m.channel === 'working-image-error')
  assert.equal(errs.length, 1)
  assert.equal(errs[0].payload.name, 'big.jpg')

  // a per-file failure does not abort the job (partial-ready fires defensively)
  assert.ok(ev.find('working-directory-partial-ready'))
  assert.ok(ev.find('working-directory-from-selected-prepared'))

  const wd = ev.find('working-directory-from-selected-prepared').workingDirectory
  const errors = JSON.parse(fs.readFileSync(path.join(wd, '.errors.json'), 'utf-8'))
  assert.ok(errors['big.jpg'])
})

test('prepare-working-directory-from-selected: RAW sources use their coerced .tif working name', async () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  autoClose(0) // resize CLI succeeds
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'scan.arw'), 'raw-bytes')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory-from-selected'](ev, dir)

  // manifest + image-ready both record the WORKING name (scan.tif), not the source (scan.arw)
  const wd = ev.find('working-directory-from-selected-prepared').workingDirectory
  const manifest = JSON.parse(fs.readFileSync(path.join(wd, '.manifest.json'), 'utf-8'))
  assert.equal(manifest.files[0].name, 'scan.tif')
  assert.equal(manifest.files[0].isRaw, true)

  const ready = ev.find('working-image-ready')
  assert.equal(ready.name, 'scan.tif')
})

test('prepare-working-directory-from-selected: .fff is converted via fff2tiff to a .tif working name', async () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  autoClose(0)
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'scan.fff'), 'fff-bytes')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory-from-selected'](ev, dir)

  // fff2tiff (not tool resize) is spawned for the .fff source
  const { args } = h.lastSpawn()
  assert.equal(args.includes('fff2tiff'), true)
  assert.equal(args.includes('resize'), false)

  // manifest + image-ready use the .tif working name
  const wd = ev.find('working-directory-from-selected-prepared').workingDirectory
  const manifest = JSON.parse(fs.readFileSync(path.join(wd, '.manifest.json'), 'utf-8'))
  assert.equal(manifest.files[0].name, 'scan.tif')
  assert.equal(ev.find('working-image-ready').name, 'scan.tif')
})

test('prepare-working-directory-from-selected: emits an initial [0/N] progress so the button is never blank', async () => {
  h.loadHandler('../../ipc/prepare-working-directory-from-selected')
  h.setImageSize(() => ({ width: 640, height: 480 })) // copy, no resize
  const dir = tmpDir('olk-src-')
  fs.writeFileSync(path.join(dir, 'a.jpg'), 'img')

  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory-from-selected'](ev, dir)

  const progressMsgs = ev.sent.filter(m => m.channel === 'processing-progress-update').map(m => m.payload.progress)
  assert.equal(progressMsgs[0], '[0/1]')
})

test('prepare-working-directory: a read error surfaces working-directory-error', async () => {
  h.loadHandler('../../ipc/prepare-working-directory')
  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory'](ev, path.join(os.tmpdir(), 'no-such-dir-xyz-123'))
  assert.ok(ev.find('working-directory-error'))
})
