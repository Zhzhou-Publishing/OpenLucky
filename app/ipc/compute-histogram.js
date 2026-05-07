const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand, readPresetJson, resolveImagePath } = require('../shared/utils')

function register() {
  ipcMain.handle('compute-histogram', async (_event, { directoryPath, filename, height = 100, downsampling = 256, area = null }) => {
    return new Promise((resolve, reject) => {
      const presets = readPresetJson(directoryPath)
      const filePath = resolveImagePath(directoryPath, filename, presets)
      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [
        ...prefixArgs,
        'tool', 'histogram',
        '-i', filePath,
        '-d', String(downsampling),
        '-n', String(height),
        '-m', 'log',
      ]
      if (area && Number.isInteger(area.x1) && Number.isInteger(area.y1) && Number.isInteger(area.x2) && Number.isInteger(area.y2)) {
        args.push('--area', `${area.x1},${area.y1},${area.x2},${area.y2}`)
      }
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
