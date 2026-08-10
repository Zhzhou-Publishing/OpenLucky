const { registerHandler } = require('../ipc/engine')
const { getWin } = require('../shared/main-window')

let allowClose = false

function register() {
  registerHandler('confirm-close', (_, allow) => {
    if (allow) {
      allowClose = true
      const win = getWin()
      if (win && !win.isDestroyed()) {
        win.close()
      }
    }
  })
}

// Per-window: must be called for each new BrowserWindow
function setupWindow(win) {
  allowClose = false

  win.on('close', (e) => {
    if (allowClose) return
    e.preventDefault()
    if (!win.isDestroyed()) {
      win.webContents.send('confirm-close')
    }
  })
}

module.exports = { register, setupWindow }
