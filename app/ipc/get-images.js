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
const { readManifest, readErrors } = require('../shared/manifest')
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
      const presets = readPresetJson(directoryPath)
      const timestamp = Date.now()

      const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-thumbnails_', unsafeCleanup: true })
      const tempDir = tempDirObj.name

      const manifest = readManifest(directoryPath)

      if (manifest) {
        // Early-use: drive off the manifest. Ready = file on disk; pending =
        // in manifest but not on disk; error = recorded failure. Placeholders
        // (pending/error) carry url:null and a status the renderer gates on.
        const errors = readErrors(directoryPath)
        const images = await Promise.all(manifest.files.map(async (f) => {
          const onDisk = fs.existsSync(path.join(directoryPath, f.name))
          if (!onDisk) {
            if (errors[f.name]) {
              return { name: f.name, isRaw: f.isRaw, url: null, status: 'error', error: errors[f.name] }
            }
            return { name: f.name, isRaw: f.isRaw, url: null, status: 'pending' }
          }
          const entry = await buildThumbnailEntry(directoryPath, f.name, presets, tempDir, timestamp)
          return { ...entry, status: 'ready' }
        }))
        send('images-loaded', { images })
        return
      }

      // Legacy fallback: no manifest → everything on disk is ready.
      const files = fs.readdirSync(directoryPath)

      const allImageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext))
          && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      const images = await Promise.all(
        allImageFiles.map(async file => {
          const entry = await buildThumbnailEntry(directoryPath, file, presets, tempDir, timestamp)
          return { ...entry, status: 'ready' }
        })
      )

      send('images-loaded', { images })
    } catch (error) {
      logger.error('Error loading images:', error)
      send('images-error', error.message)
    }
  })
}

module.exports = { register }
