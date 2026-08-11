const { registerHandler } = require('../ipc/engine')
const { getToolContext } = require('../main/tool-windows')

function register() {
  registerHandler('get-tool-context', (event) => {
    return getToolContext(event.sender)
  })
}

module.exports = { register }
