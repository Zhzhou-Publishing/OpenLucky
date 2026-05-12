const { ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')
const {
  IMAGE_EXTENSIONS,
  RAW_EXTENSIONS,
  TIFF_EXTENSIONS,
  checkExtension,
  buildOpenLuckyCommand
} = require('../shared/utils')
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

        let presetKey = null

        if (isRaw) {
          const fileWithoutExt = file.slice(0, file.lastIndexOf('.'))
          const possibleKeys = [
            file,
            file + '.tif',
            file + '.tiff',
            fileWithoutExt + '.tif',
            fileWithoutExt + '.tiff'
          ]

          for (const key of possibleKeys) {
            if (presetObj[key]) {
              presetKey = key
              break
            }
          }
        } else {
          if (presetObj[file]) {
            presetKey = file
          }
        }

        if (presetKey) {
          const presetParams = presetObj[presetKey]
          let paramsString = `${presetParams.mask_r},${presetParams.mask_g},${presetParams.mask_b},${presetParams.gamma},${presetParams.contrast}`
          if (presetParams.contrast_r !== undefined && presetParams.contrast_g !== undefined && presetParams.contrast_b !== undefined) {
            paramsString += `,${presetParams.contrast_r},${presetParams.contrast_g},${presetParams.contrast_b}`
          }
          const rotateClockwise = presetParams.rotate_clockwise || 0

          const inputFilePath = path.join(inputDir, file)
          let outputFilePath = path.join(outputDir, file)

          if (isRaw && !checkExtension(TIFF_EXTENSIONS, path.extname(outputFilePath))) {
            outputFilePath += '.tif'
          }

          const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
          const args = [...prefixArgs, 'filmparam', '--input', inputFilePath, '--output', outputFilePath, '--param', paramsString, '--rotate-clockwise', rotateClockwise.toString()]

          const presetArea = presetParams.area
          const presetBasis = presetParams.area_basis
          if (presetArea
              && Number.isInteger(presetArea.x1) && Number.isInteger(presetArea.y1)
              && Number.isInteger(presetArea.x2) && Number.isInteger(presetArea.y2)) {
            args.push('--area', `${presetArea.x1},${presetArea.y1},${presetArea.x2},${presetArea.y2}`)
            if (presetBasis
                && Number.isInteger(presetBasis.w) && Number.isInteger(presetBasis.h)
                && presetBasis.w > 0 && presetBasis.h > 0) {
              args.push('--area-basis', `${presetBasis.w},${presetBasis.h}`)
            }
          }
          const presetExposure = presetParams.exposure_ev
          if (typeof presetExposure === 'number' && Number.isFinite(presetExposure)) {
            args.push('--exposure', presetExposure.toString())
          }
          const presetWhiteBalance = presetParams.white_balance
          if (typeof presetWhiteBalance === 'string' && presetWhiteBalance.length > 0) {
            args.push('--white-balance', presetWhiteBalance)
          }
          const presetTone = presetParams.tone
          if (typeof presetTone === 'string' && presetTone.length > 0) {
            args.push('--tone', presetTone)
          }
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
