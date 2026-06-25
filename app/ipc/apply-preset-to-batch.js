const { ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')
const {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  checkExtension,
  coerceRawOutputPath,
  buildOpenLuckyCommand
} = require('../shared/utils')
const { buildParamString, resolvePresetKey, buildFilmparamArgs } = require('../shared/cli-args')
const { createLogger } = require('../shared/logger')

const logger = createLogger('ApplyPresetToBatch')

function register() {
  ipcMain.on('apply-preset-to-batch', async (event, { presetFile, inputDir, outputDir }) => {
    try {
      if (!fs.existsSync(presetFile)) {
        event.sender.send('preset-to-batch-error', { message: 'Preset file not found', error: `Preset file does not exist: ${presetFile}` })
        return
      }

      const presetContent = fs.readFileSync(presetFile, 'utf-8')
      const presetObj = JSON.parse(presetContent)

      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true })
      }

      const files = fs.readdirSync(inputDir)
      const imageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext))
          && fs.statSync(path.join(inputDir, file)).isFile()
      })

      let processedCount = 0
      const totalCount = imageFiles.length

      for (const file of imageFiles) {
        const ext = path.extname(file)
        const isRaw = checkExtension(RAW_EXTENSIONS, ext)

        const presetKey = resolvePresetKey(presetObj, file, isRaw, { includeStemVariants: true })

        if (presetKey) {
          const presetParams = presetObj[presetKey]
          const paramsString = buildParamString(presetParams, { includeContrastRgb: true })
          const rotateClockwise = presetParams.rotate_clockwise || 0

          const inputFilePath = path.join(inputDir, file)
          const outputFilePath = coerceRawOutputPath(path.join(outputDir, file), isRaw, path.extname)

          const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
          const args = [...prefixArgs, ...buildFilmparamArgs({
            input: inputFilePath, output: outputFilePath, param: paramsString,
            rotateClockwise,
            area: presetParams.area,
            areaBasis: presetParams.area_basis,
            exposure: presetParams.exposure_ev,
            whiteBalance: presetParams.white_balance,
            tone: presetParams.tone
          })]
          logger.info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

          if (!event.sender.isDestroyed()) {
            event.sender.send('preset-to-batch-progress', {
              file: file,
              progress: `${processedCount + 1}/${totalCount}`,
              data: `Processing ${file}`
            })
          }

          await new Promise((resolve) => {
            const child = spawn(command, args, {
              ...spawnOptions,
              stdio: ['pipe', 'pipe', 'pipe'],
              windowsHide: true
            })

            child.on('close', (code) => {
              if (code !== 0) {
                logger.error(`Error processing ${file}: Exit code ${code}`)
              }
              resolve()
            })

            child.on('error', (err) => {
              logger.error(`Error processing ${file}:`, err.message)
              resolve()
            })
          })

          processedCount++
        }
      }

      if (event.sender.isDestroyed()) return
      event.sender.send('preset-to-batch-success', { message: `Batch processing completed. Processed ${processedCount}/${totalCount} files.` })
    } catch (error) {
      logger.error('Error applying preset to batch:', error)
      if (event.sender.isDestroyed()) return
      event.sender.send('preset-to-batch-error', { message: 'Error applying preset to batch', error: error.message })
    }
  })
}

module.exports = { register }
