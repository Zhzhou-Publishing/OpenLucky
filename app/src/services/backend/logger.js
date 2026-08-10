// Renderer logger — Electron backend (electron-log).
//
// When a Tauri backend lands, add a tauri logger module here and select it at
// build time; for now Electron is the only implementation.

import log from 'electron-log'

export function createRendererLogger(scope) {
  return {
    debug: (...args) => log.debug(`[${scope}]`, ...args),
    info: (...args) => log.info(`[${scope}]`, ...args),
    warn: (...args) => log.warn(`[${scope}]`, ...args),
    error: (...args) => log.error(`[${scope}]`, ...args)
  }
}
