const { registerEntry } = require('../ipc/engine')
const { buildFilmbatchArgs } = require('../shared/cli-args')

module.exports = {
  register: () => registerEntry('apply-preset', {
    buildArgs: ({ inputPath, outputPath, preset }) => buildFilmbatchArgs({ input: inputPath, output: outputPath, preset }),
    startedMessage: 'Processing started',
    successMessage: 'Preset applied successfully',
    errorMessage: 'Error applying preset'
  })
}
