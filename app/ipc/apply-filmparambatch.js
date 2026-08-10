const { registerEntry } = require('../ipc/engine')
const { buildFilmparamArgs } = require('../shared/cli-args')

module.exports = {
  register: () => registerEntry('apply-filmparambatch', {
    buildArgs: ({ inputPath, outputPath, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null, whiteBalance = null, tone = null, colorMode = null }) =>
      buildFilmparamArgs({
        command: 'filmparambatch',
        input: inputPath,
        output: outputPath,
        param: params,
        rotateClockwise,
        area,
        areaBasis,
        exposure,
        whiteBalance,
        tone,
        colorMode
      }),
    startedMessage: 'Batch processing started',
    successMessage: 'Batch processing completed successfully',
    errorMessage: 'Error applying batch film parameters'
  })
}
