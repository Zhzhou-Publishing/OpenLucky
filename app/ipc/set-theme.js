const { registerHandler } = require('../ipc/engine')
const { nativeTheme } = require('electron')

function register() {
  registerHandler('set-theme', (_, themeName) => {
    nativeTheme.themeSource = themeName === 'dark' ? 'dark' : 'light'
  })
}

module.exports = { register }
