// Pure, dependency-free image-format helpers.
//
// Extracted from shared/utils.js so the classification rules can be unit-tested
// without pulling in `electron`/`sharp`, and so the upcoming Tauri/Rust port has
// a single, tested specification to mirror. utils.js re-exports these for
// backward compatibility.

// Image format constants
const IMAGE_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.bmp',
  '.tif',
  '.tiff',
  '.fff'
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

// Check file extension with case-insensitive matching. `ext` is expected to
// include the leading dot (e.g. ".JPG").
function checkExtension(extensions, ext) {
  return extensions.includes(ext.toLowerCase())
}

// RAW outputs must be written as TIFF. If `outputPath` is a RAW source whose
// target does not already carry a .tif/.tiff extension, append ".tif".
// `extname` is injected so this stays dependency-free (callers pass path.extname).
function coerceRawOutputPath(outputPath, isRaw, extname) {
  if (isRaw && !checkExtension(TIFF_EXTENSIONS, extname(outputPath))) {
    return outputPath + '.tif'
  }
  return outputPath
}

module.exports = {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  TIFF_EXTENSIONS,
  checkExtension,
  coerceRawOutputPath
}
