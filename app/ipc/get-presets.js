const { registerEntry } = require('../ipc/engine')

module.exports = {
  register: () => registerEntry('get-presets', {
    buildArgs: () => ['config', 'read', '-f', 'json'],
    finalize: ({ code, stdout, stderr, send }) => {
      if (code === 0) {
        try {
          const config = JSON.parse(stdout)
          const presets = config.presets
            ? Object.keys(config.presets).map(key => ({
              ...config.presets[key],
              value: key,
              label: config.presets[key].label || key
            }))
            : []
          send('presets-loaded', { presets })
        } catch (parseError) {
          send('presets-error', { message: 'Failed to parse config', error: parseError.message })
        }
      } else {
        send('presets-error', { message: `Process exited with code ${code}`, error: stderr })
      }
    },
    onSpawnError: ({ error, send }) => send('presets-error', { message: 'Failed to start process', error: error.message }),
    onError: ({ error, send }) => send('presets-error', { message: 'Error getting presets', error: error.message })
  })
}
