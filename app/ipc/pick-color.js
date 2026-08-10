const { registerEntry } = require('../ipc/engine')
const { buildPickArgs } = require('../shared/cli-args')

module.exports = {
  register: () => registerEntry('pick-color', {
    buildArgs: ({ filePath, x, y, format = '8' }) => buildPickArgs({ input: filePath, x, y, format }),
    errors: {
      spawn: 'Failed to spawn pick: ',
      exit: 'pick exited with code ',
      parse: 'Failed to parse pick output: '
    }
  })
}
