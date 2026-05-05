const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { getOpenLuckyPath } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('ApplyPreset')

function register() {
  ipcMain.on('apply-preset', async (event, { inputPath, outputPath, preset }) => {
    try {
      const command = getOpenLuckyPath()
      const args = ['filmbatch', '--input', inputPath, '--output', outputPath, '--preset', preset]
      logger.info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('preset-apply-started', { message: 'Processing started' })

      const child = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      child.stdout.on('data', (data) => {
        output += data.toString()
        if (event.sender.isDestroyed()) return
        event.sender.send('preset-apply-progress', { data: data.toString() })
      })

      child.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      child.on('close', (code) => {
        if (event.sender.isDestroyed()) return
        if (code === 0) {
          event.sender.send('preset-apply-success', { message: 'Preset applied successfully' })
        } else {
          event.sender.send('preset-apply-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      child.on('error', (err) => {
        if (event.sender.isDestroyed()) return
        event.sender.send('preset-apply-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      logger.error('Error applying preset:', error)
      event.sender.send('preset-apply-error', { message: 'Error applying preset', error: error.message })
    }
  })
}

module.exports = { register }
