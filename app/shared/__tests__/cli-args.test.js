const test = require('node:test')
const assert = require('node:assert/strict')

const {
  appendArea,
  appendExposure,
  appendWhiteBalance,
  appendTone,
  buildFilmparamArgs,
  buildFilmbatchArgs,
  buildHistogramArgs,
  buildPickArgs,
  buildResizeArgs,
  buildParamString,
  resolvePresetKey,
  resolveOpenLuckyCommand
} = require('../cli-args')

// These tests pin the exact openlucky CLI argument contract. They double as the
// specification the Tauri/Rust shell must reproduce byte-for-byte.

// ── Optional-argument appenders ──────────────────────────────────────────────

test('appendArea pushes --area only when all four coords are integers', () => {
  assert.deepEqual(appendArea([], { x1: 1, y1: 2, x2: 3, y2: 4 }), ['--area', '1,2,3,4'])
  assert.deepEqual(appendArea([], { x1: 1, y1: 2, x2: 3, y2: 4.5 }), [])
  assert.deepEqual(appendArea([], null), [])
})

test('appendArea adds --area-basis only with positive integer dimensions', () => {
  assert.deepEqual(
    appendArea([], { x1: 1, y1: 2, x2: 3, y2: 4 }, { w: 6000, h: 4000 }),
    ['--area', '1,2,3,4', '--area-basis', '6000,4000']
  )
  // Zero / negative dimensions are rejected
  assert.deepEqual(
    appendArea([], { x1: 1, y1: 2, x2: 3, y2: 4 }, { w: 0, h: 4000 }),
    ['--area', '1,2,3,4']
  )
})

test('appendExposure pushes only finite numbers', () => {
  assert.deepEqual(appendExposure([], 1.5), ['--exposure', '1.5'])
  assert.deepEqual(appendExposure([], 0), ['--exposure', '0'])
  assert.deepEqual(appendExposure([], null), [])
  assert.deepEqual(appendExposure([], NaN), [])
  assert.deepEqual(appendExposure([], '1.5'), [])
})

test('appendWhiteBalance / appendTone push only non-empty strings', () => {
  assert.deepEqual(appendWhiteBalance([], 'auto'), ['--white-balance', 'auto'])
  assert.deepEqual(appendWhiteBalance([], ''), [])
  assert.deepEqual(appendWhiteBalance([], null), [])
  assert.deepEqual(appendTone([], 'auto'), ['--tone', 'auto'])
  assert.deepEqual(appendTone([], ''), [])
})

// ── filmparam / filmparambatch ───────────────────────────────────────────────

test('buildFilmparamArgs: minimal single-file form (apply-filmparam)', () => {
  assert.deepEqual(
    buildFilmparamArgs({ input: 'in.jpg', output: 'out.jpg', param: '1,1,1,2,3', rotateClockwise: 0 }),
    ['filmparam', '--input', 'in.jpg', '--output', 'out.jpg', '--param', '1,1,1,2,3', '--rotate-clockwise', '0']
  )
})

test('buildFilmparamArgs: full single-file form with all optionals in order', () => {
  assert.deepEqual(
    buildFilmparamArgs({
      input: 'in.jpg', output: 'out.tif', param: '1,1,1,2,3', rotateClockwise: 90,
      area: { x1: 10, y1: 20, x2: 30, y2: 40 }, areaBasis: { w: 6000, h: 4000 },
      exposure: 0.5, whiteBalance: 'auto', tone: 'auto'
    }),
    [
      'filmparam', '--input', 'in.jpg', '--output', 'out.tif', '--param', '1,1,1,2,3',
      '--rotate-clockwise', '90',
      '--area', '10,20,30,40', '--area-basis', '6000,4000',
      '--exposure', '0.5', '--white-balance', 'auto', '--tone', 'auto'
    ]
  )
})

test('buildFilmparamArgs: omits --rotate-clockwise when not provided (apply-preset-to-file)', () => {
  assert.deepEqual(
    buildFilmparamArgs({ input: 'in.jpg', output: 'out.jpg', param: '1,1,1,2,3' }),
    ['filmparam', '--input', 'in.jpg', '--output', 'out.jpg', '--param', '1,1,1,2,3']
  )
})

test('buildFilmparamArgs: command override produces filmparambatch', () => {
  assert.deepEqual(
    buildFilmparamArgs({ command: 'filmparambatch', input: 'inDir', output: 'outDir', param: '1,1,1,2,3', rotateClockwise: 0 }),
    ['filmparambatch', '--input', 'inDir', '--output', 'outDir', '--param', '1,1,1,2,3', '--rotate-clockwise', '0']
  )
})

// ── other commands ───────────────────────────────────────────────────────────

test('buildFilmbatchArgs', () => {
  assert.deepEqual(
    buildFilmbatchArgs({ input: 'inDir', output: 'outDir', preset: 'kodak' }),
    ['filmbatch', '--input', 'inDir', '--output', 'outDir', '--preset', 'kodak']
  )
})

test('buildHistogramArgs: default downsampling and log mode', () => {
  assert.deepEqual(
    buildHistogramArgs({ input: 'a.tif' }),
    ['tool', 'histogram', '-i', 'a.tif', '-d', '256', '-m', 'log']
  )
})

test('buildHistogramArgs: custom downsampling + area (no basis)', () => {
  assert.deepEqual(
    buildHistogramArgs({ input: 'a.tif', downsampling: 512, area: { x1: 1, y1: 2, x2: 3, y2: 4 } }),
    ['tool', 'histogram', '-i', 'a.tif', '-d', '512', '-m', 'log', '--area', '1,2,3,4']
  )
})

test('buildPickArgs: default 8-bit format, numbers stringified', () => {
  assert.deepEqual(
    buildPickArgs({ input: 'a.tif', x: 100, y: 200 }),
    ['tool', 'pick', '-i', 'a.tif', '-x', '100', '-y', '200', '-f', '8']
  )
})

test('buildResizeArgs: with and without value', () => {
  assert.deepEqual(
    buildResizeArgs({ input: 'a.arw', output: 'a.tif', value: 800 }),
    ['tool', 'resize', '-i', 'a.arw', '-o', 'a.tif', '-v', '800']
  )
  assert.deepEqual(
    buildResizeArgs({ input: 'a.arw', output: 'a.tif' }),
    ['tool', 'resize', '-i', 'a.arw', '-o', 'a.tif']
  )
})

// ── preset translation ───────────────────────────────────────────────────────

test('buildParamString: base 5-value form (apply-preset-to-file)', () => {
  const p = { mask_r: 1, mask_g: 1.1, mask_b: 1.2, gamma: 2, contrast: 3 }
  assert.equal(buildParamString(p), '1,1.1,1.2,2,3')
})

test('buildParamString: appends contrast RGB only when all three present', () => {
  const full = { mask_r: 1, mask_g: 1, mask_b: 1, gamma: 2, contrast: 3, contrast_r: 4, contrast_g: 5, contrast_b: 6 }
  assert.equal(buildParamString(full, { includeContrastRgb: true }), '1,1,1,2,3,4,5,6')
  // Partial RGB → not appended
  const partial = { mask_r: 1, mask_g: 1, mask_b: 1, gamma: 2, contrast: 3, contrast_r: 4 }
  assert.equal(buildParamString(partial, { includeContrastRgb: true }), '1,1,1,2,3')
  // includeContrastRgb default false ignores RGB even if present
  assert.equal(buildParamString(full), '1,1,1,2,3')
})

test('resolvePresetKey: non-RAW returns filename if present', () => {
  assert.equal(resolvePresetKey({ 'a.jpg': {} }, 'a.jpg', false), 'a.jpg')
  assert.equal(resolvePresetKey({}, 'a.jpg', false), null)
})

test('resolvePresetKey: RAW tries filename then .tif/.tiff suffixes', () => {
  assert.equal(resolvePresetKey({ 'a.arw.tif': {} }, 'a.arw', true), 'a.arw.tif')
  assert.equal(resolvePresetKey({ 'a.arw': {} }, 'a.arw', true), 'a.arw')
  assert.equal(resolvePresetKey({}, 'a.arw', true), null)
})

test('resolvePresetKey: stem variants only when requested (apply-preset-to-batch)', () => {
  const obj = { 'a.tif': {} }
  // Without stem variants the bare-stem key is not found
  assert.equal(resolvePresetKey(obj, 'a.arw', true), null)
  // With stem variants "a" + ".tif" matches
  assert.equal(resolvePresetKey(obj, 'a.arw', true, { includeStemVariants: true }), 'a.tif')
})

// ── executable resolution ────────────────────────────────────────────────────

const CTX = {
  python: 'python3',
  repoRoot: '/repo',
  packagedWinCommand: 'openlucky',
  packagedUnixCommand: '/res/openlucky/openlucky',
  devBinWinCommand: 'C:/bin/openlucky',
  devBinUnixCommand: '/bin/openlucky/openlucky'
}

test('resolveOpenLuckyCommand: packaged Windows uses bare command', () => {
  assert.deepEqual(
    resolveOpenLuckyCommand({ ...CTX, isPackaged: true, platform: 'win32' }),
    { command: 'openlucky', prefixArgs: [], spawnOptions: {} }
  )
})

test('resolveOpenLuckyCommand: packaged macOS uses resources path', () => {
  assert.deepEqual(
    resolveOpenLuckyCommand({ ...CTX, isPackaged: true, platform: 'darwin' }),
    { command: '/res/openlucky/openlucky', prefixArgs: [], spawnOptions: {} }
  )
})

test('resolveOpenLuckyCommand: dev default runs python -m cli.openlucky in repo root', () => {
  assert.deepEqual(
    resolveOpenLuckyCommand({ ...CTX, isPackaged: false, platform: 'darwin', useBin: false }),
    { command: 'python3', prefixArgs: ['-m', 'cli.openlucky'], spawnOptions: { cwd: '/repo' } }
  )
})

test('resolveOpenLuckyCommand: dev USEBIN falls back to the prebuilt binary', () => {
  assert.deepEqual(
    resolveOpenLuckyCommand({ ...CTX, isPackaged: false, platform: 'win32', useBin: true }),
    { command: 'C:/bin/openlucky', prefixArgs: [], spawnOptions: {} }
  )
})
