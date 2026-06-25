const { ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')
const sharp = require('sharp')
const tmp = require('tmp')
const {
  TIFF_EXTENSIONS,
  checkExtension,
  readPresetJson,
  resolveImagePath
} = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('GetFullResImage')

function register() {
  ipcMain.on('get-full-res-image', async (event, { directoryPath, filename }) => {
    try {
      const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'))

      const presets = readPresetJson(directoryPath)
      const fullPath = resolveImagePath(directoryPath, filename, presets)

      let imageUrl = `file://${fullPath}`

      if (checkExtension(TIFF_EXTENSIONS, ext)) {
        try {
          const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-full-res_', unsafeCleanup: true })
          const tempDir = tempDirObj.name

          const convertedPath = path.join(tempDir, `${path.basename(filename, ext)}.jpg`)
          // failOn:'none' so libtiff warnings on 16-bit RGB+IR scanner TIFFs
          // (4 samples, missing ExtraSamples tag) don't abort the convert
          // (default failOn:'warning' would throw → unrenderable file://*.tiff).
          // removeAlpha() drops the 4th (IR) band as a plain extra sample;
          // otherwise libvips treats it as alpha and jpegsave flattens RGB
          // against black, darkening the colours. limitInputPixels:false for
          // multi-GB BigTIFF filmstrip scans.
          const buffer = await sharp(fullPath, { failOn: 'none', limitInputPixels: false })
            .removeAlpha()
            .jpeg({ quality: 95 })
            .toBuffer()
          fs.writeFileSync(convertedPath, buffer)
          imageUrl = `file://${convertedPath}`
        } catch (err) {
          logger.error('Error converting image for', filename, err)
        }
      }

      if (event.sender.isDestroyed()) return
      event.sender.send('full-res-image-loaded', { url: imageUrl })
    } catch (error) {
      logger.error('Error getting full resolution image:', error)
      if (event.sender.isDestroyed()) return
      event.sender.send('full-res-image-error', { error: error.message })
    }
  })
}

module.exports = { register }
