// Pure, dependency-free builders for the openlucky CLI command line.
//
// These functions are the single source of truth for HOW the desktop app
// invokes the openlucky binary. They are extracted from the IPC handlers and
// shared/utils.js so that:
//   1. the exact argument contract can be unit-tested without electron, and
//   2. the planned Tauri/Rust shell has a precise, tested specification to
//      reproduce (the Rust side must emit byte-identical argv).
//
// Every builder returns a plain string[] of arguments that come AFTER the
// command/prefix produced by resolveOpenLuckyCommand(). No spawning, no I/O.

const { checkExtension, TIFF_EXTENSIONS } = require('./formats')

// ── Optional-argument appenders ──────────────────────────────────────────────
// Each mirrors the validation rules the handlers apply before pushing a flag.
// They mutate and return `args` for convenient chaining.

function appendArea(args, area, areaBasis) {
  if (area
      && Number.isInteger(area.x1) && Number.isInteger(area.y1)
      && Number.isInteger(area.x2) && Number.isInteger(area.y2)) {
    args.push('--area', `${area.x1},${area.y1},${area.x2},${area.y2}`)
    if (areaBasis
        && Number.isInteger(areaBasis.w) && Number.isInteger(areaBasis.h)
        && areaBasis.w > 0 && areaBasis.h > 0) {
      args.push('--area-basis', `${areaBasis.w},${areaBasis.h}`)
    }
  }
  return args
}

function appendExposure(args, exposure) {
  if (typeof exposure === 'number' && Number.isFinite(exposure)) {
    args.push('--exposure', exposure.toString())
  }
  return args
}

function appendWhiteBalance(args, whiteBalance) {
  if (typeof whiteBalance === 'string' && whiteBalance.length > 0) {
    args.push('--white-balance', whiteBalance)
  }
  return args
}

function appendTone(args, tone) {
  if (typeof tone === 'string' && tone.length > 0) {
    args.push('--tone', tone)
  }
  return args
}

function appendColorMode(args, colorMode) {
  if (typeof colorMode === 'string' && colorMode.length > 0) {
    args.push('--color-mode', colorMode)
  }
  return args
}

function appendAreaBasis(args, areaBasis) {
  if (areaBasis
      && Number.isInteger(areaBasis.w) && Number.isInteger(areaBasis.h)
      && areaBasis.w > 0 && areaBasis.h > 0) {
    args.push('--area-basis', `${areaBasis.w},${areaBasis.h}`)
  }
  return args
}

// `dust` is { grain_level (0-1 粗细 slider), dust_size (px) } — presence of
// --dust enables dust removal. pr/024.dust.md
function appendDust(args, dust) {
  if (dust
      && typeof dust.grain_level === 'number' && Number.isFinite(dust.grain_level)
      && dust.grain_level >= 0 && dust.grain_level <= 1
      && Number.isInteger(dust.dust_size)) {
    args.push('--dust', `${dust.grain_level},${dust.dust_size}`)
  }
  return args
}

// dustRois are { x1,y1,x2,y2 } rects in the same basis frame as --area
// (measured on the working-dir preview).
function appendDustRois(args, dustRois) {
  if (Array.isArray(dustRois) && dustRois.length > 0
      && dustRois.every(r => r && Number.isInteger(r.x1) && Number.isInteger(r.y1)
                              && Number.isInteger(r.x2) && Number.isInteger(r.y2))) {
    args.push('--dust-rois', dustRois.map(r => `${r.x1},${r.y1},${r.x2},${r.y2}`).join(';'))
  }
  return args
}

// ── Command builders ─────────────────────────────────────────────────────────

// `filmparam` (single file) and `filmparambatch` share this shape. Pass
// command: 'filmparambatch' for the batch variant. When `rotateClockwise` is
// null/undefined the --rotate-clockwise flag is omitted (matches apply-preset-to-file).
function buildFilmparamArgs({
  command = 'filmparam',
  input,
  output,
  param,
  rotateClockwise,
  area = null,
  areaBasis = null,
  exposure = null,
  whiteBalance = null,
  tone = null,
  colorMode = null,
  dust = null,
  dustRois = null
}) {
  const args = [command, '--input', input, '--output', output, '--param', param]
  if (rotateClockwise !== null && rotateClockwise !== undefined) {
    args.push('--rotate-clockwise', rotateClockwise.toString())
  }
  const hasArea = area && Number.isInteger(area.x1) && Number.isInteger(area.y1)
    && Number.isInteger(area.x2) && Number.isInteger(area.y2)
  const hasDustRois = Array.isArray(dustRois) && dustRois.length > 0
  appendArea(args, area, areaBasis)
  appendExposure(args, exposure)
  appendWhiteBalance(args, whiteBalance)
  appendTone(args, tone)
  appendColorMode(args, colorMode)
  appendDust(args, dust)
  appendDustRois(args, dustRois)
  // Dust ROIs are drawn on the same basis frame as --area; emit --area-basis
  // for them even when there is no white-point --area to measure.
  if (hasDustRois && !hasArea) appendAreaBasis(args, areaBasis)
  return args
}

// `filmbatch` — apply a named preset across a directory.
function buildFilmbatchArgs({ input, output, preset }) {
  return ['filmbatch', '--input', input, '--output', output, '--preset', preset]
}

// `tool histogram`
function buildHistogramArgs({ input, downsampling = 256, area = null }) {
  const args = ['tool', 'histogram', '-i', input, '-d', String(downsampling), '-m', 'log']
  if (area
      && Number.isInteger(area.x1) && Number.isInteger(area.y1)
      && Number.isInteger(area.x2) && Number.isInteger(area.y2)) {
    args.push('--area', `${area.x1},${area.y1},${area.x2},${area.y2}`)
  }
  return args
}

// `tool pick`
function buildPickArgs({ input, x, y, format = '8' }) {
  return ['tool', 'pick', '-i', input, '-x', String(x), '-y', String(y), '-f', String(format)]
}

// `tool resize`. When `value` is null/undefined the -v flag is omitted, which
// tells the CLI to copy non-RAW directly and convert RAW to TIFF without resize.
function buildResizeArgs({ input, output, value }) {
  const args = ['tool', 'resize', '-i', input, '-o', output]
  if (value !== undefined && value !== null) {
    args.push('-v', String(value))
  }
  return args
}

// ── Preset → CLI translation ─────────────────────────────────────────────────

// Build the comma-joined --param string from a stored preset entry.
// Base form: mask_r,mask_g,mask_b,gamma,contrast
// With includeContrastRgb: appends contrast_r,contrast_g,contrast_b when all
// three are present (matches apply-preset-to-batch).
function buildParamString(p, { includeContrastRgb = false } = {}) {
  let s = `${p.mask_r},${p.mask_g},${p.mask_b},${p.gamma},${p.contrast}`
  if (includeContrastRgb
      && p.contrast_r !== undefined && p.contrast_g !== undefined && p.contrast_b !== undefined) {
    s += `,${p.contrast_r},${p.contrast_g},${p.contrast_b}`
  }
  return s
}

// Resolve which key in a .preset.json object corresponds to `filename`.
// Non-RAW: the filename itself, if present.
// RAW: tries filename, filename+.tif, filename+.tiff, and (when
//      includeStemVariants) the basename-without-extension + .tif/.tiff.
// Returns the matching key or null.
function resolvePresetKey(presetObj, filename, isRaw, { includeStemVariants = false } = {}) {
  if (!isRaw) {
    return presetObj[filename] ? filename : null
  }
  const keys = [filename, filename + '.tif', filename + '.tiff']
  if (includeStemVariants) {
    const stem = filename.slice(0, filename.lastIndexOf('.'))
    keys.push(stem + '.tif', stem + '.tiff')
  }
  for (const key of keys) {
    if (presetObj[key]) return key
  }
  return null
}

// ── Executable resolution ────────────────────────────────────────────────────

// Decide which command / prefix args / spawn options invoke openlucky, given a
// resolved environment context. Kept pure (no electron, no path/fs) so every
// branch is testable; shared/utils.js supplies the real ctx values.
//
// ctx:
//   isPackaged          boolean
//   platform            process.platform string ('win32', 'darwin', ...)
//   useBin              OPENLUCKY_DEV_USEBIN === '1'
//   python              interpreter to use in dev-py mode
//   repoRoot            cwd for dev-py mode
//   packagedWinCommand  command when packaged on Windows
//   packagedUnixCommand command when packaged on non-Windows
//   devBinWinCommand    command for dev OPENLUCKY_DEV_USEBIN on Windows
//   devBinUnixCommand   command for dev OPENLUCKY_DEV_USEBIN on non-Windows
function resolveOpenLuckyCommand(ctx) {
  const isWin = ctx.platform === 'win32'

  if (ctx.isPackaged) {
    return {
      command: isWin ? ctx.packagedWinCommand : ctx.packagedUnixCommand,
      prefixArgs: [],
      spawnOptions: {}
    }
  }

  if (ctx.useBin) {
    return {
      command: isWin ? ctx.devBinWinCommand : ctx.devBinUnixCommand,
      prefixArgs: [],
      spawnOptions: {}
    }
  }

  return {
    command: ctx.python,
    prefixArgs: ['-m', 'cli.openlucky'],
    spawnOptions: { cwd: ctx.repoRoot }
  }
}

// Convenience re-export so callers can coerce RAW outputs alongside arg building.
const { coerceRawOutputPath } = require('./formats')

module.exports = {
  appendArea,
  appendAreaBasis,
  appendExposure,
  appendWhiteBalance,
  appendTone,
  appendColorMode,
  appendDust,
  appendDustRois,
  buildFilmparamArgs,
  buildFilmbatchArgs,
  buildHistogramArgs,
  buildPickArgs,
  buildResizeArgs,
  buildParamString,
  resolvePresetKey,
  resolveOpenLuckyCommand,
  coerceRawOutputPath,
  // re-exported for callers that already imported these from here
  checkExtension,
  TIFF_EXTENSIONS
}
