const { registerHandler } = require('../ipc/engine')
const { dialog, BrowserWindow } = require('electron')
const fs = require('fs')
const { createLogger } = require('../shared/logger')

const logger = createLogger('SelectDirectory')

function register() {
  registerHandler('select-directory', async (event) => {
    // Reply to the requesting window (not a hard-coded main-window send) so a
    // tool window that picks a directory gets its own results back.
    const send = (channel, payload) => {
      if (event.sender && !event.sender.isDestroyed()) {
        event.sender.send(channel, payload)
      }
    }
    // Parent the native dialog on the requesting window (null → non-modal).
    const parent = BrowserWindow.fromWebContents(event.sender)
    try {
      const result = await dialog.showOpenDialog(parent, {
        properties: ['openDirectory']
      })

      if (result.canceled) {
        send('directory-cancelled')
        return
      }

      const selectedPath = result.filePaths[0]
      const files = fs.readdirSync(selectedPath)

      send('directory-selected', {
        path: selectedPath,
        files: files
      })
    } catch (error) {
      logger.error('Error selecting directory:', error)
      send('directory-error', error.message)
    }
  })
}

module.exports = { register }
