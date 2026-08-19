const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const {
  writeManifest,
  readManifest,
  recordError,
  readErrors,
  MANIFEST_FILENAME,
  ERRORS_FILENAME
} = require('../manifest')

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'olk-manifest-'))
}

test('manifest: write + read round-trips the full inventory', () => {
  const dir = tmpDir()
  writeManifest(dir, [{ name: 'a.jpg', isRaw: false }, { name: 'b.arw', isRaw: true }])
  assert.deepEqual(readManifest(dir), {
    total: 2,
    files: [{ name: 'a.jpg', isRaw: false }, { name: 'b.arw', isRaw: true }]
  })
})

test('manifest: readManifest returns null when absent or malformed', () => {
  const dir = tmpDir()
  assert.equal(readManifest(dir), null)
  fs.writeFileSync(path.join(dir, MANIFEST_FILENAME), '{not json')
  assert.equal(readManifest(dir), null)
})

test('manifest: recordError + readErrors accumulate per-file failures', () => {
  const dir = tmpDir()
  recordError(dir, 'a.jpg', 'boom')
  recordError(dir, 'b.arw', 'also bad')
  assert.deepEqual(readErrors(dir), { 'a.jpg': 'boom', 'b.arw': 'also bad' })
})

test('manifest: readErrors returns {} when absent or malformed', () => {
  const dir = tmpDir()
  assert.deepEqual(readErrors(dir), {})
  fs.writeFileSync(path.join(dir, ERRORS_FILENAME), 'not json')
  assert.deepEqual(readErrors(dir), {})
})
