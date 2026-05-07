const log = require('electron-log');
const path = require('path');
const { app } = require('electron');

const isDev = !app.isPackaged;
log.transports.console.level = isDev ? 'debug' : 'info';
log.transports.file.level = 'debug';

log.transports.file.resolvePathFn = () => {
  const userDataPath = app.getPath('userData');
  return path.join(userDataPath, 'logs', 'main.log');
};

log.transports.file.maxSize = 5 * 1024 * 1024;

function createLogger(scope) {
  return {
    debug: (...args) => log.debug(`[${scope}]`, ...args),
    info: (...args) => log.info(`[${scope}]`, ...args),
    warn: (...args) => log.warn(`[${scope}]`, ...args),
    error: (...args) => log.error(`[${scope}]`, ...args),
  };
}

module.exports = { log, createLogger };
