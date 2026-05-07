const { ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const tmp = require('tmp')
const { getWin } = require('../shared/main-window')
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
  ipcMain.on('get-images', async (_, directoryPath) => {
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

      const win = getWin()
      if (win && !win.isDestroyed()) {
        win.webContents.send('images-loaded', { images })
      }
    } catch (error) {
      logger.error('Error loading images:', error)
      const win = getWin()
      if (win && !win.isDestroyed()) {
        win.webContents.send('images-error', error.message)
      }
    }
  })
}

module.exports = { register }
