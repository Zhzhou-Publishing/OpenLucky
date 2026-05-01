const { ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')

function register() {
  ipcMain.on('reset-image', async (event, { workingDirectory, outputDirectory, filename }) => {
    try {
      const presetFile = path.join(workingDirectory, '.preset.json')
      if (fs.existsSync(presetFile)) {
        const presets = JSON.parse(fs.readFileSync(presetFile, 'utf-8'))
        if (presets[filename]) {
          delete presets[filename]
          fs.writeFileSync(presetFile, JSON.stringify(presets, null, 2), 'utf-8')
        }
      }

      if (outputDirectory && fs.existsSync(outputDirectory)) {
        const outputFile = path.join(outputDirectory, filename)
        if (fs.existsSync(outputFile)) {
          fs.unlinkSync(outputFile)
        }
      }

      event.sender.send('image-reset', { filename, success: true })
    } catch (error) {
      console.error('Error resetting image:', error)
      event.sender.send('image-reset-error', { filename, error: error.message })
    }
  })
}

module.exports = { register }
