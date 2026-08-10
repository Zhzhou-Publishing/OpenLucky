const { registerEntry } = require('../ipc/engine')
const { readPresetJson, resolveImagePath } = require('../shared/utils')
const { buildHistogramArgs } = require('../shared/cli-args')

module.exports = {
  register: () => registerEntry('compute-histogram', {
    buildArgs: ({ directoryPath, filename, downsampling = 256, area = null }) => {
      const presets = readPresetJson(directoryPath)
      const filePath = resolveImagePath(directoryPath, filename, presets)
      return buildHistogramArgs({ input: filePath, downsampling, area })
    },
    errors: {
      spawn: 'Failed to spawn histogram: ',
      exit: 'histogram exited with code ',
      parse: 'Failed to parse histogram output: '
    }
  })
}
