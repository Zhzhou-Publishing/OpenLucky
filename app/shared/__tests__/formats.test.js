const test = require('node:test')
const assert = require('node:assert/strict')
const path = require('path')

const {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  TIFF_EXTENSIONS,
  checkExtension,
  coerceRawOutputPath
} = require('../formats')

test('extension lists contain expected members', () => {
  assert.ok(IMAGE_EXTENSIONS.includes('.jpg'))
  assert.ok(IMAGE_EXTENSIONS.includes('.tiff'))
  assert.ok(RAW_EXTENSIONS.includes('.arw'))
  assert.ok(RAW_EXTENSIONS.includes('.dng'))
  assert.deepEqual(TIFF_EXTENSIONS, ['.tif', '.tiff'])
})

test('checkExtension is case-insensitive', () => {
  assert.equal(checkExtension(RAW_EXTENSIONS, '.ARW'), true)
  assert.equal(checkExtension(RAW_EXTENSIONS, '.arw'), true)
  assert.equal(checkExtension(RAW_EXTENSIONS, '.jpg'), false)
  assert.equal(checkExtension(IMAGE_EXTENSIONS, '.JPEG'), true)
})

test('coerceRawOutputPath appends .tif for RAW outputs lacking a TIFF extension', () => {
  assert.equal(
    coerceRawOutputPath('/out/IMG_0001.ARW', true, path.extname),
    '/out/IMG_0001.ARW.tif'
  )
})

test('coerceRawOutputPath leaves RAW outputs that already target TIFF', () => {
  assert.equal(
    coerceRawOutputPath('/out/IMG_0001.tif', true, path.extname),
    '/out/IMG_0001.tif'
  )
  assert.equal(
    coerceRawOutputPath('/out/IMG_0001.TIFF', true, path.extname),
    '/out/IMG_0001.TIFF'
  )
})

test('coerceRawOutputPath leaves non-RAW outputs untouched', () => {
  assert.equal(
    coerceRawOutputPath('/out/photo.jpg', false, path.extname),
    '/out/photo.jpg'
  )
})
