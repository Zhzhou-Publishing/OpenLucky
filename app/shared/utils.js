const { app } = require('electron')
const path = require('path')
const fs = require('fs')
const sharp = require('sharp')
const sizeOf = require('image-size')
const tmp = require('tmp')
const { spawn } = require('child_process')
const { createLogger } = require('./logger')

const logger = createLogger('OpenLucky')

// Keep temp files alive for the session
tmp.setGracefulCleanup()

// Image format constants
const IMAGE_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.bmp',
  '.tif',
  '.tiff'
]

const RAW_EXTENSIONS = [
  '.arw',
  '.cr2',
  '.cr3',
  '.nef',
  '.dng',
  '.orf',
  '.raf'
]

const TIFF_EXTENSIONS = [
  '.tif',
  '.tiff'
]

// Helper function to check file extension with case-insensitive matching
const checkExtension = (extensions, ext) => {
  return extensions.includes(ext.toLowerCase())
}

/**
 * Get the path to the openlucky CLI executable
 * In production (Windows): uses openlucky command from PATH
 * In production (non-Windows): uses Resources/openlucky/openlucky
 * In development (Windows): uses ../bin/openlucky
 * In development (non-Windows): uses ../bin/openlucky/openlucky
 */
function getOpenLuckyPath() {
  if (app.isPackaged) {
    if (process.platform === 'win32') {
      return 'openlucky'
    } else {
      return path.join(process.resourcesPath, 'openlucky', 'openlucky')
    }
  } else {
    if (process.platform === 'win32') {
      return path.join(__dirname, '..', '..', 'bin', 'openlucky')
    } else {
      return path.join(__dirname, '..', '..', 'bin', 'openlucky', 'openlucky')
    }
  }
}

// Read .preset.json from a working directory. Returns {} if missing or
// unparseable so callers can treat the result as a plain lookup.
function readPresetJson(directoryPath) {
  const presetsFile = path.join(directoryPath, '.preset.json')
  if (!fs.existsSync(presetsFile)) return {}
  try {
    return JSON.parse(fs.readFileSync(presetsFile, 'utf-8'))
  } catch (err) {
    logger.error('Error reading .preset.json:', err)
    return {}
  }
}

// Single source of truth for "which on-disk file represents this image":
// prefer the preset-recorded output_dir if it points at an existing file,
// otherwise the original under directoryPath. Used for both thumbnails
// and the full-resolution viewer so they can never disagree.
function resolveImagePath(directoryPath, filename, presets) {
  const entry = presets && presets[filename]
  if (entry && entry.output_dir && fs.existsSync(entry.output_dir)) {
    return entry.output_dir
  }
  return path.join(directoryPath, filename)
}

// Build a thumbnail-ready descriptor for one image: its path, isRaw flag,
// and a `file://` URL with cache-buster. TIFF files are transcoded to a
// 300×200 JPEG inside the supplied tempDir. Used by get-images (batch)
// and refresh-image (single, post-apply).
async function buildThumbnailEntry(directoryPath, filename, presets, tempDir, timestamp) {
  const fullPath = resolveImagePath(directoryPath, filename, presets)
  const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'))
  const isRaw = checkExtension(RAW_EXTENSIONS, ext)
  let url = `file://${fullPath}?t=${timestamp}`
  if (checkExtension(TIFF_EXTENSIONS, ext)) {
    try {
      const thumbnailPath = path.join(tempDir, `${path.basename(filename, ext)}.jpg`)
      await sharp(fullPath)
        .resize(300, 200, { fit: 'cover' })
        .jpeg({ quality: 80 })
        .toFile(thumbnailPath)
      url = `file://${thumbnailPath}?t=${timestamp}`
    } catch (err) {
      logger.error('Error generating thumbnail for', filename, err)
    }
  }
  return { name: filename, path: fullPath, url, isRaw }
}

// Check if image needs resize (long edge >= 800)
async function needsResize(imagePath) {
  try {
    const ext = path.extname(imagePath).toLowerCase()

    if (checkExtension(RAW_EXTENSIONS, ext)) {
      return true
    }

    const { width, height } = sizeOf(imagePath)
    const longEdge = Math.max(width, height)
    return longEdge >= 800
  } catch (error) {
    logger.error('Error checking image dimensions:', error)
    return false
  }
}

// Resize image using openlucky tool resize command.
// options.value: when provided, passes -v <value>; when absent, -v is omitted
//   so the CLI copies non-RAW directly and converts RAW to TIFF without resize.
function resizeImage(inputPath, outputPath, options = {}) {
  return new Promise((resolve) => {
    const command = getOpenLuckyPath()
    const args = ['tool', 'resize', '-i', inputPath, '-o', outputPath]
    if (options.value !== undefined && options.value !== null) {
      args.push('-v', String(options.value))
    }
    logger.info(`Executing: ${command} ${args.join(' ')}`)

    const child = spawn(command, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true
    })

    let stderrOutput = ''

    child.stderr.on('data', (data) => {
      stderrOutput += data.toString()
    })

    child.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true })
      } else {
        logger.error('Resize failed:', inputPath, 'Exit code:', code)
        logger.error('Error output:', stderrOutput)
        resolve({ success: false, error: stderrOutput })
      }
    })

    child.on('error', (err) => {
      logger.error('Resize error:', inputPath, err.message)
      resolve({ success: false, error: err.message })
    })
  })
}

module.exports = {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  TIFF_EXTENSIONS,
  checkExtension,
  getOpenLuckyPath,
  readPresetJson,
  resolveImagePath,
  buildThumbnailEntry,
  needsResize,
  resizeImage
}
