const { registerHandler } = require('../ipc/engine')
const { forwardToolResult } = require('../main/tool-windows')

function register() {
  registerHandler('tool-result', (event, payload) => {
    forwardToolResult(payload.tool, payload.result)
  })
}

module.exports = { register }
