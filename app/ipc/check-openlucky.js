const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { getOpenLuckyPath } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('CheckOpenlucky')

function register() {
  ipcMain.on('check-openlucky', async (event) => {
    try {
      const command = getOpenLuckyPath()
      const args = ['--help']
      logger.info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      const child = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let errorOutput = ''

      child.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      child.on('close', (code) => {
        if (event.sender.isDestroyed()) return
        const success = code === 0
        event.sender.send('openlucky-checked', { success, error: errorOutput })
      })

      child.on('error', (err) => {
        if (event.sender.isDestroyed()) return
        event.sender.send('openlucky-checked', { success: false, error: err.message })
      })
    } catch (error) {
      logger.error('Error checking openlucky:', error)
      event.sender.send('openlucky-checked', { success: false, error: error.message })
    }
  })
}

module.exports = { register }
