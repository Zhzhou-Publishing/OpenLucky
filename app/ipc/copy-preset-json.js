const { registerHandler } = require('../ipc/engine')
const fs = require('fs')
const path = require('path')
const { createLogger } = require('../shared/logger')

const logger = createLogger('CopyPresetJson')

function register() {
  registerHandler('copy-preset-json', async (event, { workingDirectory, originalDirectory }) => {
    try {
      const presetJsonSource = path.join(workingDirectory, '.preset.json')
      const presetJsonDest = path.join(originalDirectory, '.preset.json')

      if (!fs.existsSync(presetJsonSource)) {
        event.sender.send('copy-preset-json-error', { message: 'Source .preset.json not found in working directory' })
        return
      }

      if (!fs.existsSync(originalDirectory)) {
        event.sender.send('copy-preset-json-error', { message: 'Original directory does not exist' })
        return
      }

      fs.copyFileSync(presetJsonSource, presetJsonDest)

      event.sender.send('copy-preset-json-success', { message: '.preset.json copied successfully' })
    } catch (error) {
      logger.error('Error copying .preset.json:', error)
      event.sender.send('copy-preset-json-error', { message: 'Error copying .preset.json', error: error.message })
    }
  })
}

module.exports = { register }
