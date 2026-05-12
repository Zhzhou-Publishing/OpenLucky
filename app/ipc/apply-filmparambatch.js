const { ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('ApplyFilmparambatch')

function register() {
  ipcMain.on('apply-filmparambatch', async (event, { inputPath, outputPath, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null, whiteBalance = null, tone = null }) => {
    try {
      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [...prefixArgs, 'filmparambatch', '--input', inputPath, '--output', outputPath, '--param', params, '--rotate-clockwise', rotateClockwise.toString()]
      if (area && Number.isInteger(area.x1) && Number.isInteger(area.y1) && Number.isInteger(area.x2) && Number.isInteger(area.y2)) {
        args.push('--area', `${area.x1},${area.y1},${area.x2},${area.y2}`)
        if (areaBasis && Number.isInteger(areaBasis.w) && Number.isInteger(areaBasis.h) && areaBasis.w > 0 && areaBasis.h > 0) {
          args.push('--area-basis', `${areaBasis.w},${areaBasis.h}`)
        }
      }
      if (typeof exposure === 'number' && Number.isFinite(exposure)) {
        args.push('--exposure', exposure.toString())
      }
      if (typeof whiteBalance === 'string' && whiteBalance.length > 0) {
        args.push('--white-balance', whiteBalance)
      }
      if (typeof tone === 'string' && tone.length > 0) {
        args.push('--tone', tone)
      }
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
