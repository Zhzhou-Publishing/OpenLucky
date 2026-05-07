const { app, BrowserWindow, dialog, nativeTheme, shell } = require('electron')
const fs = require('fs')
const os = require('os')
const path = require('path')
const https = require('https')
const { log, createLogger } = require('./shared/logger')
const { setWin } = require('./shared/main-window')

log.initialize()

const updateLogger = createLogger('UpdateChecker')
const configLogger = createLogger('Config')
const recallCheckLogger = createLogger('VersionRecallChecker')
const recallStatusLogger = createLogger('RecallStatus')
const appLogger = createLogger('App')

// ── IPC handlers (one per file) ──────────────────────────────────────────────
const ipcConfirmClose = require('./ipc/confirm-close')
const ipcCheckOpenlucky = require('./ipc/check-openlucky')
const ipcSelectDirectory = require('./ipc/select-directory')
const ipcOpenExternal = require('./ipc/open-external')
const ipcGetImages = require('./ipc/get-images')
const ipcGetPresets = require('./ipc/get-presets')
const ipcPrepareWorkingDir = require('./ipc/prepare-working-directory')
const ipcPrepareWorkingDirFromSelected = require('./ipc/prepare-working-directory-from-selected')
const ipcGetFullResImage = require('./ipc/get-full-res-image')
const ipcReadPresetJson = require('./ipc/read-preset-json')
const ipcRefreshImage = require('./ipc/refresh-image')
const ipcApplyPreset = require('./ipc/apply-preset')
const ipcApplyFilmparam = require('./ipc/apply-filmparam')
const ipcPickColor = require('./ipc/pick-color')
const ipcComputeHistogram = require('./ipc/compute-histogram')
const ipcApplyFilmparambatch = require('./ipc/apply-filmparambatch')
const ipcCopyPresetJson = require('./ipc/copy-preset-json')
const ipcApplyPresetToFile = require('./ipc/apply-preset-to-file')
const ipcApplyPresetToBatch = require('./ipc/apply-preset-to-batch')
const ipcResetImage = require('./ipc/reset-image')
const ipcSetTheme = require('./ipc/set-theme')

// ── Update checker constants ────────────────────────────────────────────────
const GITHUB_RELEASES_URL = 'https://api.github.com/repos/Zhzhou-Publishing/openlucky/releases?per_page=30'
const STORAGE_FILE_NAME = 'lastUpdateCheck.txt'

// Tumbleweed channels: a release only nudges users on the same channel.
// 'stable' (no suffix) → next stable
// 'rc' / 'beta' / 'alpha' → next release in the same channel
function getVersionChannel(version) {
  if (!version) return 'stable'
  const v = String(version).toLowerCase()
  if (/-rc/i.test(v)) return 'rc'
  if (/-beta/i.test(v)) return 'beta'
  if (/-alpha/i.test(v)) return 'alpha'
  return 'stable'
}

// Global variable to track if current version is recalled
let recalled = false

// Get system locale for i18n
function getSystemLocale() {
  const locale = app.getLocale() || 'en'
  updateLogger.info('System locale:', locale)
  return locale
}

// Check if current locale is Chinese (Simplified)
function isChineseLocale() {
  const locale = getSystemLocale().toLowerCase()
  return locale === 'zh_cn' || locale === 'zh-cn' || locale === 'zh-hans' || locale === 'zh_hans'
}

// Get localized text for dialogs
function getLocalizedText(type) {
  const isChinese = isChineseLocale()

  const texts = {
    update: {
      title: isChinese ? '新版本可用' : 'New Version Available',
      message: (version) => isChinese
        ? `发现新版本 ${version}`
        : `Found New Version ${version}`,
      detail: (publishedAt) => isChinese
        ? `发布时间: ${new Date(publishedAt).toLocaleString()}`
        : `Release Time: ${new Date(publishedAt).toLocaleString()}`,
      downloadButton: isChinese ? '立即下载' : 'Download',
      cancelButton: isChinese ? '取消' : 'Cancel',
      recallNotice: isChinese ? '当前软件版本已经不再有技术支持，请下载最新版本。' : 'Current software version is no longer supported. Please download the latest version.'
    },
    networkError: {
      title: isChinese ? '检查更新失败' : 'Checking Update Failed',
      message: isChinese ? '无法检查更新，请确认网络环境可以访问 GitHub。' : 'Cannot check update, please ensure that the network to Github is accessible.',
      okButton: isChinese ? '确定' : 'OK'
    },
    versionRecalled: {
      title: isChinese ? '版本已召回' : 'Version Recalled',
      message: isChinese ? '当前版本已被召回，软件将退出。' : 'Current version has been recalled. The application will exit.',
      detail: isChinese ? '当前软件版本已经不再有技术支持，请下载最新版本。' : 'Current software version is no longer supported. Please download the latest version.',
      downloadButton: isChinese ? '下载最新版本' : 'Download Latest Version',
      quitButton: isChinese ? '退出' : 'Quit'
    }
  }

  return texts[type]
}

// 读取当前版本号
function getCurrentVersion() {
  try {
    let version = app.getVersion()

    if (version && !version.startsWith('v')) {
      version = 'v' + version
    }

    return version
  } catch (error) {
    updateLogger.error('Error reading version:', error)
    return 'unknown'
  }
}

/**
 * Get the path to the storage file
 */
function getStorageFilePath() {
  try {
    const userDataPath = app.getPath('userData')
    const storageFilePath = path.join(userDataPath, STORAGE_FILE_NAME)
    updateLogger.info(`saved ${storageFilePath}`)
    return storageFilePath
  } catch (error) {
    updateLogger.error('Error getting user data path:', error)
    return path.join(process.cwd(), STORAGE_FILE_NAME)
  }
}

/**
 * Get the last check timestamp from file
 */
function getLastCheckTime() {
  try {
    const filePath = getStorageFilePath()
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf-8')
      return parseInt(data.trim(), 10) || 0
    }
    return 0
  } catch (e) {
    updateLogger.error('Error reading last check time:', e)
    return 0
  }
}

/**
 * Save the check timestamp to file
 */
function saveCheckTime() {
  try {
    const filePath = getStorageFilePath()
    const userDataDir = app.getPath('userData')

    if (!fs.existsSync(userDataDir)) {
      fs.mkdirSync(userDataDir, { recursive: true })
    }

    fs.writeFileSync(filePath, Date.now().toString(), 'utf-8')
  } catch (e) {
    updateLogger.error('Failed to save check time:', e)
  }
}

/**
 * Get recall status from storage file
 * Returns { recalled: boolean, version: string } or { recalled: false }
 */
function getRecallStatus() {
  try {
    const filePath = getStorageFilePath()
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf-8').trim()
      recallStatusLogger.info('Read from storage:', data)

      if (data.startsWith('recall:')) {
        const recalledVersion = data.substring(7)
        recallStatusLogger.info('Found recall marker for version:', recalledVersion)

        const currentVersion = getCurrentVersion()
        recallStatusLogger.info('Current version:', currentVersion)

        if (recalledVersion === currentVersion) {
          recallStatusLogger.info('Current version matches recalled version')
          return { recalled: true, version: recalledVersion }
        } else {
          recallStatusLogger.info('Current version does not match recalled version, ignoring recall')
          return { recalled: false }
        }
      } else {
        recallStatusLogger.info('No recall marker found, data is timestamp')
        return { recalled: false }
      }
    }
    recallStatusLogger.info('Storage file does not exist')
    return { recalled: false }
  } catch (e) {
    recallStatusLogger.error('Error reading recall status:', e)
    return { recalled: false }
  }
}

/**
 * Save recall status to file
 */
function saveRecallStatus(version) {
  try {
    const filePath = getStorageFilePath()
    const userDataDir = app.getPath('userData')

    if (!fs.existsSync(userDataDir)) {
      fs.mkdirSync(userDataDir, { recursive: true })
    }

    const recallData = `recall:${version}`
    fs.writeFileSync(filePath, recallData, 'utf-8')
    recallStatusLogger.info('Saved recall status:', recallData)
  } catch (e) {
    recallStatusLogger.error('Failed to save recall status:', e)
  }
}

/**
 * Check if we should check for updates based on hour interval
 * Returns { shouldCheck: boolean, recallStatus: { recalled: boolean, version?: string } }
 */
function shouldCheckForUpdates() {
  const recallStatus = getRecallStatus()
  if (recallStatus.recalled) {
    updateLogger.info('Found recall status for current version, should check')
    return { shouldCheck: true, recallStatus }
  }

  const lastCheck = getLastCheckTime()
  if (lastCheck === 0) {
    updateLogger.info('Never checked before, should check')
    return { shouldCheck: true, recallStatus }
  }

  const now = Date.now()
  const lastCheckHour = Math.floor(lastCheck / (60 * 60 * 1000))
  const currentHour = Math.floor(now / (60 * 60 * 1000))

  const shouldCheck = currentHour > lastCheckHour
  updateLogger.info('Hour interval check:', shouldCheck ? 'should check' : 'skip')
  return { shouldCheck, recallStatus }
}

/**
 * Check if current version is recalled (release deleted)
 * Returns { recalled: boolean, version: string } or null on error
 */
async function checkVersionRecalled() {
  try {
    const currentVersion = getCurrentVersion()
    recallCheckLogger.info('Checking if version is recalled...')
    recallCheckLogger.info('Current version:', currentVersion)

    const tag = currentVersion.startsWith('v') ? currentVersion : 'v' + currentVersion
    const url = `https://api.github.com/repos/Zhzhou-Publishing/openlucky/releases/tags/${tag}`
    recallCheckLogger.info('Checking release tag:', url)

    return new Promise((resolve, reject) => {
      const options = {
        headers: {
          'User-Agent': 'openlucky-desktop-version-recall-checker'
        },
        timeout: 10000
      }

      const req = https.get(url, options, (res) => {
        recallCheckLogger.info('HTTP Status Code:', res.statusCode)

        if (res.statusCode === 404) {
          recallCheckLogger.info('Version recalled (404 Not Found)')
          resolve({
            recalled: true,
            version: currentVersion
          })
          return
        }

        if (res.statusCode === 200) {
          recallCheckLogger.info('Version exists and is active')
          resolve({
            recalled: false,
            version: currentVersion
          })
          return
        }

        recallCheckLogger.error('Unexpected status code:', res.statusCode)
        reject(new Error(`GitHub API returned unexpected status code: ${res.statusCode}`))
      })

      req.on('timeout', () => {
        req.destroy()
        recallCheckLogger.error('Request timed out')
        reject(new Error('GitHub API request timed out'))
      })

      req.on('error', (err) => {
        recallCheckLogger.error('Network error:', err.message)
        reject(new Error(`Network error: ${err.message}`))
      })
    })
  } catch (error) {
    recallCheckLogger.error('Error checking version recall:', error)
    return null
  }
}

/**
 * Fetch the most recent GitHub release whose version suffix matches the
 * given channel. Returns the release object or null if no match found.
 * GitHub's /releases endpoint lists releases newest-first, so the first
 * channel match is the latest.
 */
function fetchLatestReleaseForChannel(channel) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'openlucky-desktop-updater'
      },
      timeout: 10000
    }

    const req = https.get(GITHUB_RELEASES_URL, options, (res) => {
      let data = ''

      if (res.statusCode !== 200) {
        reject(new Error(`GitHub API returned status code: ${res.statusCode}`))
        return
      }

      res.on('data', (chunk) => {
        data += chunk
      })

      res.on('end', () => {
        try {
          const releases = JSON.parse(data)
          if (!Array.isArray(releases)) {
            reject(new Error('GitHub API did not return a release list'))
            return
          }
          const match = releases.find(r =>
            r && !r.draft && r.name &&
            getVersionChannel(r.tag_name || r.name) === channel
          )
          resolve(match || null)
        } catch (e) {
          reject(new Error('Failed to parse GitHub API response'))
        }
      })
    })

    req.on('timeout', () => {
      req.destroy()
      reject(new Error('GitHub API request timed out'))
    })

    req.on('error', (err) => {
      updateLogger.error('Network error:', err.message)
      reject(new Error(`Network error: ${err.message}`))
    })
  })
}

/**
 * Check for updates
 * Returns { hasUpdate: boolean, version: string, publishedAt: string, htmlUrl: string } or
 *         { recalled: boolean, version: string } or
 *         { skipped: true } or
 *         null (on error)
 */
async function checkForUpdates() {
  try {
    const { shouldCheck, recallStatus } = shouldCheckForUpdates()

    if (!shouldCheck) {
      updateLogger.info('Already checked this hour, skipping')
      return { skipped: true }
    }

    if (recallStatus.recalled) {
      updateLogger.info('Found recall status from file for current version, returning recall result')
      recalled = true
      return recallStatus
    }

    updateLogger.info('Step 1: Checking if current version is recalled...')
    const recallResult = await checkVersionRecalled()

    if (recallResult === null) {
      updateLogger.error('Version recall check failed, proceeding with update check')
    } else if (recallResult.recalled) {
      updateLogger.info('Version is recalled, saving recall status and returning')
      saveRecallStatus(recallResult.version)
      recalled = true
      return recallResult
    } else {
      updateLogger.info('Version is not recalled, proceeding with update check')
    }

    updateLogger.info('Step 2: Checking for updates...')
    const currentVersion = getCurrentVersion()
    const currentChannel = getVersionChannel(currentVersion)
    updateLogger.info('Current version:', currentVersion, 'channel:', currentChannel)

    const release = await fetchLatestReleaseForChannel(currentChannel)

    if (!release || !release.name) {
      updateLogger.info('No matching release in channel:', currentChannel)
      return { hasUpdate: false }
    }

    updateLogger.info('Latest version in channel:', release.name)

    if (!recalled) {
      saveCheckTime()
    }

    if (release.name !== currentVersion) {
      return {
        hasUpdate: true,
        version: release.name,
        publishedAt: release.published_at,
        htmlUrl: release.html_url
      }
    }

    updateLogger.info('Already on latest version')
    return { hasUpdate: false }
  } catch (error) {
    updateLogger.error('Error checking for updates:', error)
    return null
  }
}

/**
 * Initialize default config file if it doesn't exist
 * Copies config.yaml from bundled resources to ~/.openlucky/config.yaml
 */
function initializeConfigFile() {
  try {
    const homeDir = os.homedir()
    const configDir = path.join(homeDir, '.openlucky')
    const configFilePath = path.join(configDir, 'config.yaml')

    if (fs.existsSync(configFilePath)) {
      configLogger.info('Config file already exists at:', configFilePath)
      return
    }

    let sourceConfigPath
    if (app.isPackaged) {
      sourceConfigPath = path.join(process.resourcesPath, 'config.yaml')
    } else {
      sourceConfigPath = path.join(__dirname, '..', '..', 'config.yaml')
    }

    if (!fs.existsSync(sourceConfigPath)) {
      configLogger.error('Source config file not found at:', sourceConfigPath)
      return
    }

    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true })
      configLogger.info('Created config directory at:', configDir)
    }

    fs.copyFileSync(sourceConfigPath, configFilePath)
    configLogger.info('Created config file from bundled resources at:', configFilePath)
  } catch (error) {
    configLogger.error('Error initializing config file:', error)
  }
}

// ── Window creation ─────────────────────────────────────────────────────────
let ipcHandlersRegistered = false

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 1000,
    show: false,
    autoHideMenuBar: true,
    resizable: true,
    webPreferences: {
      devTools: true,
      spellCheck: false,
      enableWebSQL: false,
      offscreen: false,
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  setWin(win)

  win.loadFile('dist/index.html')

  win.maximize()
  win.once('ready-to-show', () => {
    win.show()
  })

  // Register all IPC handlers once — ipcMain.handle throws on duplicate
  if (!ipcHandlersRegistered) {
    ipcConfirmClose.register()
    ipcCheckOpenlucky.register()
    ipcSelectDirectory.register()
    ipcOpenExternal.register()
    ipcGetImages.register()
    ipcGetPresets.register()
    ipcPrepareWorkingDir.register()
    ipcPrepareWorkingDirFromSelected.register()
    ipcGetFullResImage.register()
    ipcReadPresetJson.register()
    ipcRefreshImage.register()
    ipcApplyPreset.register()
    ipcApplyFilmparam.register()
    ipcPickColor.register()
    ipcComputeHistogram.register()
    ipcApplyFilmparambatch.register()
    ipcCopyPresetJson.register()
    ipcApplyPresetToFile.register()
    ipcApplyPresetToBatch.register()
    ipcResetImage.register()
    ipcSetTheme.register()
    ipcHandlersRegistered = true
  }

  // Per-window: confirm-close needs fresh event listeners on each window
  ipcConfirmClose.setupWindow(win)

  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    win.webContents.openDevTools()
  }
}

// ── Update dialogs ──────────────────────────────────────────────────────────
function showUpdateDialog(win, updateInfo, isRecalled = false) {
  const texts = getLocalizedText('update')
  let detail = texts.detail(updateInfo.publishedAt)

  if (isRecalled) {
    detail += '\n\n' + texts.recallNotice
  }

  dialog.showMessageBox(win, {
    type: 'info',
    title: texts.title,
    message: texts.message(updateInfo.version),
    detail: detail,
    buttons: [texts.downloadButton, texts.cancelButton],
    defaultId: 0,
    cancelId: 1
  }).then((result) => {
    if (result.response === 0) {
      shell.openExternal(updateInfo.htmlUrl)
    } else if (isRecalled) {
      app.quit()
    }
  }).catch((error) => {
    appLogger.error('Error showing update dialog:', error)
  })
}

function showRecallDialog(win, latestVersion, latestHtmlUrl) {
  const texts = getLocalizedText('versionRecalled')

  dialog.showMessageBox(win, {
    type: 'warning',
    title: texts.title,
    message: texts.message,
    detail: texts.detail,
    buttons: [texts.downloadButton, texts.quitButton],
    defaultId: 0,
    cancelId: 1
  }).then((result) => {
    if (result.response === 0) {
      shell.openExternal(latestHtmlUrl).then(() => {
        app.quit()
      }).catch((error) => {
        appLogger.error('Error opening download URL:', error)
        app.quit()
      })
    } else {
      app.quit()
    }
  }).catch((error) => {
    appLogger.error('Error showing recall dialog:', error)
    app.quit()
  })
}

// ── App lifecycle ───────────────────────────────────────────────────────────
app.disableHardwareAcceleration()

app.whenReady().then(async () => {
  nativeTheme.themeSource = 'dark'
  initializeConfigFile()
  createWindow()

  const updateInfo = await checkForUpdates()

  if (updateInfo && updateInfo.recalled) {
    appLogger.info('Version is recalled, fetching latest release info...')
    try {
      const currentChannel = getVersionChannel(getCurrentVersion())
      const latestRelease = await fetchLatestReleaseForChannel(currentChannel)
      if (latestRelease && latestRelease.name && latestRelease.html_url) {
        const win = BrowserWindow.getAllWindows()[0]
        if (win && !win.isDestroyed()) {
          setTimeout(() => {
            showRecallDialog(win, latestRelease.name, latestRelease.html_url)
          }, 1000)
        } else {
          app.quit()
        }
      } else {
        appLogger.error('Failed to fetch latest release info for recall, quitting...')
        app.quit()
      }
    } catch (error) {
      appLogger.error('Error fetching latest release for recall:', error)
      app.quit()
    }
    return
  }

  if (updateInfo && updateInfo.hasUpdate) {
    const win = BrowserWindow.getAllWindows()[0]
    if (win && !win.isDestroyed()) {
      setTimeout(() => {
        showUpdateDialog(win, updateInfo)
      }, 1000)
    }
  } else if (updateInfo === null) {
    const win = BrowserWindow.getAllWindows()[0]
    if (win && !win.isDestroyed()) {
      const texts = getLocalizedText('networkError')
      setTimeout(() => {
        dialog.showMessageBox(win, {
          type: 'warning',
          title: texts.title,
          message: texts.message,
          buttons: [texts.okButton]
        }).catch((error) => {
          appLogger.error('Error showing network error dialog:', error)
        })
      }, 1000)
    }
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
