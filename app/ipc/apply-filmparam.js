const { ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand } = require('../shared/utils')
const { buildFilmparamArgs } = require('../shared/cli-args')
const { createLogger } = require('../shared/logger')

const logger = createLogger('ApplyFilmparam')

function register() {
  ipcMain.on('apply-filmparam', async (event, { inputPath, outputPath, filename, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null, whiteBalance = null, tone = null, colorMode = null }) => {
    try {
      const inputFile = path.join(inputPath, filename)
      const outputFile = path.join(outputPath, filename)

      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [...prefixArgs, ...buildFilmparamArgs({
        input: inputFile, output: outputFile, param: params,
        rotateClockwise, area, areaBasis, exposure, whiteBalance, tone, colorMode
      })]
      logger.info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('filmparam-apply-started', { message: 'Processing started' })

      const child = spawn(command, args, {
        ...spawnOptions,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      child.stdout.on('data', (data) => {
        output += data.toString()
        if (event.sender.isDestroyed()) return
        event.sender.send('filmparam-apply-progress', { data: data.toString() })
      })

      child.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      child.on('close', (code) => {
        if (event.sender.isDestroyed()) return
        if (code === 0) {
          event.sender.send('filmparam-apply-success', { message: 'Film processing completed successfully', outputFile })
        } else {
          event.sender.send('filmparam-apply-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      child.on('error', (err) => {
        if (event.sender.isDestroyed()) return
        event.sender.send('filmparam-apply-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      logger.error('Error applying filmparam:', error)
      event.sender.send('filmparam-apply-error', { message: 'Error applying film parameters', error: error.message })
    }
  })
}

module.exports = { register }
