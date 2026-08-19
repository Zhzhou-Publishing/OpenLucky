const { registerHandler } = require('../ipc/engine')
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
  resizeImage,
  convertFffToTiff
} = require('../shared/utils')
const { writeManifest, recordError } = require('../shared/manifest')
const { EARLY_USE_READY_RATIO } = require('../shared/config')
const { createLogger } = require('../shared/logger')

const logger = createLogger('PrepareWorkingDirFromSelected')

// Single-flight: only one prepare job runs at a time (single-window flow).
// Starting a new job cancels/abandons the previous one so its background tail
// doesn't keep resizing into an orphaned temp dir. Every event also carries
// `workingDirectory`, so the renderer filters out stray events from an
// abandoned job regardless.
let activeJob = null

// The on-disk filename a source file maps to in the working directory.
// `tool resize` converts RAW to TIFF via with_suffix('.tif'), and `fff2tiff`
// converts .fff to a standard TIFF — so both become <stem>.tif; everything else
// keeps its name. get-images checks disk by this name, so the manifest must
// record it (not the source name).
function workingFileName(file) {
  const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
  if (checkExtension(RAW_EXTENSIONS, ext) || ext === '.fff') {
    return file.slice(0, file.lastIndexOf('.')) + '.tif'
  }
  return file
}

function register() {
  registerHandler('prepare-working-directory-from-selected', async (event, directoryPath, options = {}) => {
    // Abandon any previous still-running job.
    if (activeJob && !activeJob.finished) {
      activeJob.cancelled = true
    }

    const job = { workingDirectory: '', cancelled: false, finished: false }
    activeJob = job

    const onCancel = () => { job.cancelled = true }
    ipcMain.once('cancel-processing', onCancel)

    const send = (channel, payload) => {
      if (event.sender && !event.sender.isDestroyed()) {
        event.sender.send(channel, payload)
      }
    }

    try {
      const compressPreview = options.compressPreview === true
      const resizeOptions = compressPreview ? { value: 1920 } : {}

      const workingDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
      const workingDirectory = workingDirObj.name
      job.workingDirectory = workingDirectory

      const concurrencyLimit = Math.max(1, Math.floor(os.cpus().length / 2))
      const limit = pLimit(concurrencyLimit)

      const files = fs.readdirSync(directoryPath)

      const filesToProcess = files.filter(file => {
        if (file === '.preset.json') return true
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        const isFile = fs.statSync(path.join(directoryPath, file)).isFile()
        return isFile && (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext))
      })

      const imageFiles = filesToProcess.filter(file => file !== '.preset.json')

      // Manifest = the full inventory, written once up front. Ready-ness is
      // "file exists in workingDirectory" — never a separate in-memory flag.
      // Names are the WORKING filenames (RAW → <stem>.tif), matching what
      // get-images checks on disk.
      const manifest = imageFiles.map(file => ({
        name: workingFileName(file),
        isRaw: checkExtension(RAW_EXTENSIONS, file.toLowerCase().slice(file.lastIndexOf('.')))
      }))
      writeManifest(workingDirectory, manifest)

      // Copy .preset.json up front (not after Promise.all) so hasUnappliedImages
      // / saveAll see a complete base before every image is processed.
      const presetJsonPath = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetJsonPath)) {
        fs.copyFileSync(presetJsonPath, path.join(workingDirectory, '.preset.json'))
      }

      const outputDirectory = path.join(workingDirectory, 'output')
      if (!fs.existsSync(outputDirectory)) {
        fs.mkdirSync(outputDirectory, { recursive: true })
      }

      const totalImages = imageFiles.length
      const threshold = Math.max(1, Math.ceil(totalImages * EARLY_USE_READY_RATIO))

      let readyCount = 0
      let partialReadySent = false

      // Initial progress so the button/title are never blank while the first
      // (slow) batch of RAW/FFF conversions is still in flight.
      if (totalImages > 0) {
        const initialProgress = `[0/${totalImages}]`
        send('processing-progress-update', { progress: initialProgress })
        send('window-title-update', { title: `OpenLucky Desktop App - ${initialProgress}` })
      }

      const imageProcessings = imageFiles.map(file => limit(async () => {
        const srcPath = path.join(directoryPath, file)
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        const workingName = workingFileName(file)
        const destPath = path.join(workingDirectory, workingName)

        if (job.cancelled) {
          throw new Error('CANCELLED')
        }

        let result
        if (ext === '.fff') {
          // .fff (Hasselblad/Imacon scanner, big-endian TIFF) needs a dedicated
          // conversion to a standard TIFF — Chromium/sharp can't render it.
          result = await convertFffToTiff(srcPath, destPath)
        } else if (await needsResize(srcPath)) {
          result = await resizeImage(srcPath, destPath, resizeOptions)
        } else {
          try {
            fs.copyFileSync(srcPath, destPath)
            result = { success: true }
          } catch (err) {
            result = { success: false, error: err.message }
          }
        }

        if (result.success) {
          readyCount += 1
          // Incremental event — no thumbnail here; the renderer calls
          // refreshImage to fetch the entry (keeps the job thin, reads disk).
          send('working-image-ready', { workingDirectory, name: workingName })
          if (!partialReadySent) {
            // Progress shows the LOADED count (readyCount), same metric as the
            // threshold below — so the number on screen is what drives entry.
            const progress = `[${readyCount}/${totalImages}] ${srcPath}`
            send('processing-progress-update', { progress })
            send('window-title-update', { title: `OpenLucky Desktop App - ${progress}` })
            if (readyCount >= threshold) {
              partialReadySent = true
              send('processing-progress-clear', {})
              send('window-title-restore', {})
              send('working-directory-partial-ready', {
                workingDirectory,
                outputDirectory,
                originalDirectory: directoryPath,
                readyCount,
                total: totalImages
              })
            }
          }
        } else {
          logger.error('Failed to process image (resize/copy):', file, result.error)
          recordError(workingDirectory, workingName, result.error || 'unknown error')
          send('working-image-error', {
            workingDirectory,
            name: workingName,
            error: result.error || 'unknown error'
          })
        }
      }))

      await Promise.all(imageProcessings)

      if (job.cancelled) {
        throw new Error('CANCELLED')
      }

      // Defensive: partial-ready must always fire before complete — otherwise
      // the facade (which resolves on it) hangs when every image failed or the
      // directory was empty, so readyCount never reached the threshold.
      if (!partialReadySent) {
        partialReadySent = true
        send('processing-progress-clear', {})
        send('window-title-restore', {})
        send('working-directory-partial-ready', {
          workingDirectory,
          outputDirectory,
          originalDirectory: directoryPath,
          readyCount,
          total: totalImages
        })
      }

      // Terminal "complete" event — distinct from partial-ready so the gallery
      // can unlock saveAll/applyPreset only once everything is done.
      send('working-directory-from-selected-prepared', {
        workingDirectory,
        outputDirectory,
        originalDirectory: directoryPath
      })
    } catch (error) {
      if (error.message === 'CANCELLED') {
        logger.info('Processing cancelled by user, cleaning up temp directory')
        try { fs.rmSync(job.workingDirectory, { recursive: true, force: true }) } catch (_) {}
        send('processing-progress-clear', {})
        send('window-title-restore', {})
        return
      }
      logger.error('Error preparing working directory:', error)
      send('processing-progress-clear', {})
      send('window-title-restore', {})
      send('working-directory-from-selected-error', {
        workingDirectory: job.workingDirectory,
        error: error.message
      })
    } finally {
      ipcMain.removeListener('cancel-processing', onCancel)
      job.finished = true
      if (activeJob === job) {
        activeJob = null
      }
    }
  })
}

module.exports = { register }
