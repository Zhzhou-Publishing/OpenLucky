const { registerEntry } = require('../ipc/engine')
const path = require('path')
const { buildFilmparamArgs } = require('../shared/cli-args')

module.exports = {
  register: () => registerEntry('apply-filmparam', {
    buildArgs: ({ inputPath, outputPath, filename, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null, whiteBalance = null, tone = null, colorMode = null }) =>
      buildFilmparamArgs({
        input: path.join(inputPath, filename),
        output: path.join(outputPath, filename),
        param: params,
        rotateClockwise,
        area,
        areaBasis,
        exposure,
        whiteBalance,
        tone,
        colorMode
      }),
    startedMessage: 'Processing started',
    successPayload: ({ outputPath, filename }) => ({
      message: 'Film processing completed successfully',
      outputFile: path.join(outputPath, filename)
    }),
    errorMessage: 'Error applying film parameters'
  })
}
