const { ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand } = require('../shared/utils')
const { buildFilmparamArgs } = require('../shared/cli-args')
const { createLogger } = require('../shared/logger')

const logger = createLogger('ApplyFilmparambatch')

function register() {
  ipcMain.on('apply-filmparambatch', async (event, { inputPath, outputPath, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null, whiteBalance = null, tone = null }) => {
    try {
      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [...prefixArgs, ...buildFilmparamArgs({
        command: 'filmparambatch',
        input: inputPath, output: outputPath, param: params,
        rotateClockwise, area, areaBasis, exposure, whiteBalance, tone
      })]
      logger.info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('filmparambatch-apply-started', { message: 'Batch processing started' })

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
        event.sender.send('filmparambatch-apply-progress', { data: data.toString() })
      })

      child.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      child.on('close', (code) => {
        if (event.sender.isDestroyed()) return
        if (code === 0) {
          event.sender.send('filmparambatch-apply-success', { message: 'Batch processing completed successfully' })
        } else {
          event.sender.send('filmparambatch-apply-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      child.on('error', (err) => {
        if (event.sender.isDestroyed()) return
        event.sender.send('filmparambatch-apply-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      logger.error('Error applying filmparambatch:', error)
      event.sender.send('filmparambatch-apply-error', { message: 'Error applying batch film parameters', error: error.message })
    }
  })
}

module.exports = { register }
