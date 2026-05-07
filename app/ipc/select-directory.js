const { ipcMain, dialog } = require('electron')
const fs = require('fs')
const { getWin } = require('../shared/main-window')
const { createLogger } = require('../shared/logger')

const logger = createLogger('SelectDirectory')

function register() {
  ipcMain.on('select-directory', async () => {
    try {
      const win = getWin()
      if (!win || win.isDestroyed()) return

      const result = await dialog.showOpenDialog(win, {
        properties: ['openDirectory']
      })

      if (result.canceled) {
        if (!win.isDestroyed()) {
          win.webContents.send('directory-cancelled')
        }
        return
      }

      const selectedPath = result.filePaths[0]
      const files = fs.readdirSync(selectedPath)

      if (!win.isDestroyed()) {
        win.webContents.send('directory-selected', {
          path: selectedPath,
          files: files
        })
      }
    } catch (error) {
      logger.error('Error selecting directory:', error)
      const win = getWin()
      if (win && !win.isDestroyed()) {
        win.webContents.send('directory-error', error.message)
      }
    }
  })
}

module.exports = { register }
