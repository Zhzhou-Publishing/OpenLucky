const { ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const os = require('os')
const tmp = require('tmp')
const pLimit = require('p-limit').default
const {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  checkExtension,
  needsResize,
  resizeImage
} = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('PrepareWorkingDir')

function register() {
  ipcMain.on('prepare-working-directory', async (event, directoryPath, options = {}) => {
    try {
      const compressPreview = options.compressPreview === true
      const resizeOptions = compressPreview ? { value: 1920 } : {}

      const workingDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
      const workingDirectory = workingDirObj.name

      const concurrencyLimit = Math.max(1, Math.floor(os.cpus().length / 2))
      const limit = pLimit(concurrencyLimit)

      const files = fs.readdirSync(directoryPath)

      const filesToProcess = files.filter(file => {
        if (file === '.preset.json') return true
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext))
          && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      const imageFiles = filesToProcess.filter(file => file !== '.preset.json')

      const totalImages = imageFiles.length
      let startedCount = 0
      const imageProcessings = imageFiles.map(file => limit(async () => {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        startedCount += 1
        const progress = `[${startedCount}/${totalImages}] ${srcPath}`
        if (!event.sender.isDestroyed()) {
          event.sender.send('processing-progress-update', { progress })
          event.sender.send('window-title-update', { title: `OpenLucky Desktop App - ${progress}` })
        }

        if (await needsResize(srcPath)) {
          const result = await resizeImage(srcPath, destPath, resizeOptions)
          if (result.success) {
            logger.info('Image processed (resized):', file)
            return { success: true, file }
          } else {
            logger.error('Failed to process image (resize):', result.error)
            return { success: false, file, error: result.error }
          }
        } else {
          try {
            fs.copyFileSync(srcPath, destPath)
            logger.info('Image processed (copied):', file)
            return { success: true, file }
          } catch (err) {
            logger.error('Failed to process image (copy):', file, err.message)
            return { success: false, file, error: err.message }
          }
        }
      }))

      await Promise.all(imageProcessings)

      const presetJsonPath = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetJsonPath)) {
        fs.copyFileSync(presetJsonPath, path.join(workingDirectory, '.preset.json'))
      }

      const outputDirectory = path.join(workingDirectory, 'output')
      if (!fs.existsSync(outputDirectory)) {
        fs.mkdirSync(outputDirectory, { recursive: true })
      }

      if (!event.sender.isDestroyed()) {
        event.sender.send('processing-progress-clear', {})
        event.sender.send('window-title-restore', {})
        event.sender.send('working-directory-prepared', { workingDirectory, outputDirectory, originalDirectory: directoryPath })
      }
    } catch (error) {
      logger.error('Error preparing working directory:', error)
      if (!event.sender.isDestroyed()) {
        event.sender.send('processing-progress-clear', {})
        event.sender.send('window-title-restore', {})
        event.sender.send('working-directory-error', { error: error.message })
      }
    }
  })
}

module.exports = { register }
