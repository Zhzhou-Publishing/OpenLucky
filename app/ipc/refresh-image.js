const { ipcMain } = require('electron')
const tmp = require('tmp')
const { readPresetJson, buildThumbnailEntry } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('RefreshImage')

function register() {
  ipcMain.on('refresh-image', async (event, { directoryPath, filename }) => {
    try {
      const presets = readPresetJson(directoryPath)
      const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-thumbnail_', unsafeCleanup: true })
      const entry = await buildThumbnailEntry(
        directoryPath,
        filename,
        presets,
        tempDirObj.name,
        Date.now()
      )
      if (event.sender.isDestroyed()) return
      event.sender.send('image-refreshed', { filename, entry })
    } catch (error) {
      logger.error('Error refreshing image:', error)
      if (event.sender.isDestroyed()) return
      event.sender.send('image-refresh-error', { filename, error: error.message })
    }
  })
}

module.exports = { register }
