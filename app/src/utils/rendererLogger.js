import log from 'electron-log'

export function createRendererLogger(scope) {
  return {
    debug: (...args) => log.debug(`[${scope}]`, ...args),
    info: (...args) => log.info(`[${scope}]`, ...args),
    warn: (...args) => log.warn(`[${scope}]`, ...args),
    error: (...args) => log.error(`[${scope}]`, ...args),
  }
}
