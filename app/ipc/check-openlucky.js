const { registerEntry } = require('../ipc/engine')

module.exports = {
  register: () => registerEntry('check-openlucky', {
    buildArgs: () => ['--help'],
    finalize: ({ code, stderr, send }) => send('openlucky-checked', { success: code === 0, error: stderr }),
    onSpawnError: ({ error, send }) => send('openlucky-checked', { success: false, error: error.message }),
    onError: ({ error, send }) => send('openlucky-checked', { success: false, error: error.message })
  })
}
