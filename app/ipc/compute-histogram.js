const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand, readPresetJson, resolveImagePath } = require('../shared/utils')
const { buildHistogramArgs } = require('../shared/cli-args')

function register() {
  ipcMain.handle('compute-histogram', async (_event, { directoryPath, filename, downsampling = 256, area = null }) => {
    return new Promise((resolve, reject) => {
      const presets = readPresetJson(directoryPath)
      const filePath = resolveImagePath(directoryPath, filename, presets)
      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [...prefixArgs, ...buildHistogramArgs({ input: filePath, downsampling, area })]
      const child = spawn(command, args, {
        ...spawnOptions,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      })

      let stdout = ''
      let stderr = ''
      child.stdout.on('data', (data) => { stdout += data.toString() })
      child.stderr.on('data', (data) => { stderr += data.toString() })

      child.on('error', (err) => {
        reject(new Error(`Failed to spawn histogram: ${err.message}`))
      })

      child.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(stderr.trim() || `histogram exited with code ${code}`))
          return
        }
        try {
          resolve(JSON.parse(stdout))
        } catch (e) {
          reject(new Error(`Failed to parse histogram output: ${e.message}`))
        }
      })
    })
  })
}

module.exports = { register }
