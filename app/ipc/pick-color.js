const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { getOpenLuckyPath } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

const logger = createLogger('PickColor')

function register() {
  ipcMain.handle('pick-color', async (_event, { filePath, x, y, format = '8' }) => {
    return new Promise((resolve, reject) => {
      const command = getOpenLuckyPath()
      const args = [
        'tool', 'pick',
        '-i', filePath,
        '-x', String(x),
        '-y', String(y),
        '-f', String(format),
      ]
      logger.info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      const child = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      })

      let stdout = ''
      let stderr = ''
      child.stdout.on('data', (data) => { stdout += data.toString() })
      child.stderr.on('data', (data) => { stderr += data.toString() })

      child.on('error', (err) => {
        reject(new Error(`Failed to spawn pick: ${err.message}`))
      })

      child.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(stderr.trim() || `pick exited with code ${code}`))
          return
        }
        try {
          resolve(JSON.parse(stdout))
        } catch (e) {
          reject(new Error(`Failed to parse pick output: ${e.message}`))
        }
      })
    })
  })
}

module.exports = { register }
