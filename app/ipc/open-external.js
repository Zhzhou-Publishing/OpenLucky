const { registerHandler } = require('../ipc/engine')
const { shell } = require('electron')

function register() {
  registerHandler('open-external', (_, url) => {
    if (typeof url === 'string' && /^https?:\/\//i.test(url)) {
      shell.openExternal(url)
    }
  })
}

module.exports = { register }
