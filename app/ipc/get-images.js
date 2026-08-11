const { registerHandler } = require('../ipc/engine')
const fs = require('fs')
const path = require('path')
const tmp = require('tmp')
const {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  checkExtension,
  readPresetJson,
  buildThumbnailEntry
} = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('GetImages')

function register() {
  registerHandler('get-images', async (event, directoryPath) => {
    // Reply to the requesting window (not a hard-coded main-window send) so a
    // tool window that calls get-images gets its own results back. Matches the
    // event.sender semantics of the other handlers.
    const send = (channel, payload) => {
      if (event.sender && !event.sender.isDestroyed()) {
        event.sender.send(channel, payload)
      }
    }
    try {
      const files = fs.readdirSync(directoryPath)

      const allImageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext))
          && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-thumbnails_', unsafeCleanup: true })
      const tempDir = tempDirObj.name

      const presets = readPresetJson(directoryPath)
      const timestamp = Date.now()

      const images = await Promise.all(
        allImageFiles.map(file => buildThumbnailEntry(directoryPath, file, presets, tempDir, timestamp))
      )

      send('images-loaded', { images })
    } catch (error) {
      logger.error('Error loading images:', error)
      send('images-error', error.message)
    }
  })
}

module.exports = { register }
