const { registerHandler } = require('../ipc/engine')
const { BrowserWindow } = require('electron')
const { openToolWindow } = require('../main/tool-windows')

function register() {
  registerHandler('open-tool-window', (event, payload) => {
    const ownerWin = BrowserWindow.fromWebContents(event.sender)
    return openToolWindow(payload.tool, payload.payload, ownerWin)
  })
}

module.exports = { register }
