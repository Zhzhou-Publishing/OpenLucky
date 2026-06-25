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

test('prepare-working-directory: a read error surfaces working-directory-error', async () => {
  h.loadHandler('../../ipc/prepare-working-directory')
  const ev = h.makeEvent()
  await h.ipc.on['prepare-working-directory'](ev, path.join(os.tmpdir(), 'no-such-dir-xyz-123'))
  assert.ok(ev.find('working-directory-error'))
})
