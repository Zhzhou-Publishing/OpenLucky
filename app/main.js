const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron')
const fs = require('fs')
const os = require('os')
const path = require('path')
const sharp = require('sharp')
const sizeOf = require('image-size')
const { spawn } = require('child_process')
const tmp = require('tmp')
const https = require('https')
const pLimit = require('p-limit').default

/**
 * Get the path to the openlucky CLI executable
 * In production (Windows): uses openlucky command from PATH
 * In production (non-Windows): uses Resources/openlucky/openlucky
 * In development (Windows): uses ../bin/openlucky
 * In development (non-Windows): uses ../bin/openlucky/openlucky
 */
function getOpenLuckyPath() {

  if (app.isPackaged) {
    if (process.platform === 'win32') {
      // Windows production: use openlucky from PATH
      return 'openlucky'
    } else {
      // macOS/Linux production: use resourcesPath which points to Contents/Resources
      return path.join(process.resourcesPath, 'openlucky', 'openlucky')
    }
  } else {
    // In development, use local openlucky command from bin directory
    if (process.platform === 'win32') {
      // Windows: bin/openlucky (executable file)
      return path.join(__dirname, '..', 'bin', 'openlucky')
    } else {
      // macOS/Linux: bin/openlucky/openlucky
      return path.join(__dirname, '..', 'bin', 'openlucky', 'openlucky')
    }
  }
}

// Image format constants
const IMAGE_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.bmp',
  '.tif',
  '.tiff'
]

const RAW_EXTENSIONS = [
  '.arw',
  '.cr2',
  '.cr3',
  '.nef',
  '.dng',
  '.orf',
  '.raf'
]

const TIFF_EXTENSIONS = [
  '.tif',
  '.tiff'
]

// Helper function to check file extension with case-insensitive matching
const checkExtension = (extensions, ext) => {
  return extensions.includes(ext.toLowerCase())
}

// Read .preset.json from a working directory. Returns {} if missing or
// unparseable so callers can treat the result as a plain lookup.
function readPresetJson(directoryPath) {
  const presetsFile = path.join(directoryPath, '.preset.json')
  if (!fs.existsSync(presetsFile)) return {}
  try {
    return JSON.parse(fs.readFileSync(presetsFile, 'utf-8'))
  } catch (err) {
    console.error('Error reading .preset.json:', err)
    return {}
  }
}

// Single source of truth for "which on-disk file represents this image":
// prefer the preset-recorded output_dir if it points at an existing file,
// otherwise the original under directoryPath. Used for both thumbnails
// and the full-resolution viewer so they can never disagree.
function resolveImagePath(directoryPath, filename, presets) {
  const entry = presets && presets[filename]
  if (entry && entry.output_dir && fs.existsSync(entry.output_dir)) {
    return entry.output_dir
  }
  return path.join(directoryPath, filename)
}

// Build a thumbnail-ready descriptor for one image: its path, isRaw flag,
// and a `file://` URL with cache-buster. TIFF files are transcoded to a
// 300×200 JPEG inside the supplied tempDir. Used by get-images (batch)
// and refresh-image (single, post-apply).
async function buildThumbnailEntry(directoryPath, filename, presets, tempDir, timestamp) {
  const fullPath = resolveImagePath(directoryPath, filename, presets)
  const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'))
  const isRaw = checkExtension(RAW_EXTENSIONS, ext)
  let url = `file://${fullPath}?t=${timestamp}`
  if (checkExtension(TIFF_EXTENSIONS, ext)) {
    try {
      const thumbnailPath = path.join(tempDir, `${path.basename(filename, ext)}.jpg`)
      await sharp(fullPath)
        .resize(300, 200, { fit: 'cover' })
        .jpeg({ quality: 80 })
        .toFile(thumbnailPath)
      url = `file://${thumbnailPath}?t=${timestamp}`
    } catch (err) {
      console.error('Error generating thumbnail for', filename, err)
    }
  }
  return { name: filename, path: fullPath, url, isRaw }
}

// Update checker constants
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
  console.log('[UpdateChecker] System locale:', locale)
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
    // 使用 Electron 的 app.getVersion() 方法，它会从应用程序的元数据中读取版本号
    // 这个方法在开发环境和打包环境中都能正常工作
    let version = app.getVersion()

    // 确保版本号带v前缀，以便与GitHub API返回的版本格式一致
    if (version && !version.startsWith('v')) {
      version = 'v' + version
    }

    return version
  } catch (error) {
    console.error('[UpdateChecker] Error reading version:', error)
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
    console.log(`[UpdateChecker] saved ${storageFilePath}`)
    return storageFilePath
  } catch (error) {
    console.error('Error getting user data path:', error)
    // Fallback to current working directory
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
    console.error('Error reading last check time:', e)
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

    // Ensure userData directory exists
    if (!fs.existsSync(userDataDir)) {
      fs.mkdirSync(userDataDir, { recursive: true })
    }

    fs.writeFileSync(filePath, Date.now().toString(), 'utf-8')
  } catch (e) {
    console.error('Failed to save check time:', e)
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
      console.log('[RecallStatus] Read from storage:', data)

      // Check if data starts with 'recall:'
      if (data.startsWith('recall:')) {
        const recalledVersion = data.substring(7) // Remove 'recall:' prefix
        console.log('[RecallStatus] Found recall marker for version:', recalledVersion)

        const currentVersion = getCurrentVersion()
        console.log('[RecallStatus] Current version:', currentVersion)

        // Check if the recalled version matches current version
        if (recalledVersion === currentVersion) {
          console.log('[RecallStatus] Current version matches recalled version')
          return { recalled: true, version: recalledVersion }
        } else {
          console.log('[RecallStatus] Current version does not match recalled version, ignoring recall')
          return { recalled: false }
        }
      } else {
        console.log('[RecallStatus] No recall marker found, data is timestamp')
        return { recalled: false }
      }
    }
    console.log('[RecallStatus] Storage file does not exist')
    return { recalled: false }
  } catch (e) {
    console.error('Error reading recall status:', e)
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

    // Ensure userData directory exists
    if (!fs.existsSync(userDataDir)) {
      fs.mkdirSync(userDataDir, { recursive: true })
    }

    const recallData = `recall:${version}`
    fs.writeFileSync(filePath, recallData, 'utf-8')
    console.log('[RecallStatus] Saved recall status:', recallData)
  } catch (e) {
    console.error('Failed to save recall status:', e)
  }
}

/**
 * Check if we should check for updates based on hour interval
 * Returns { shouldCheck: boolean, recallStatus: { recalled: boolean, version?: string } }
 */
function shouldCheckForUpdates() {
  // First, check if there's a recall status in the file
  const recallStatus = getRecallStatus()
  if (recallStatus.recalled) {
    console.log('[UpdateChecker] Found recall status for current version, should check')
    return { shouldCheck: true, recallStatus }
  }

  // If no recall status, check timestamp as before
  const lastCheck = getLastCheckTime()
  if (lastCheck === 0) {
    console.log('[UpdateChecker] Never checked before, should check')
    return { shouldCheck: true, recallStatus }
  }

  const now = Date.now()
  const lastCheckHour = Math.floor(lastCheck / (60 * 60 * 1000))
  const currentHour = Math.floor(now / (60 * 60 * 1000))

  // Check if we're in a new hour interval
  const shouldCheck = currentHour > lastCheckHour
  console.log('[UpdateChecker] Hour interval check:', shouldCheck ? 'should check' : 'skip')
  return { shouldCheck, recallStatus }
}

/**
 * Check if current version is recalled (release deleted)
 * Returns { recalled: boolean, version: string } or null on error
 */
async function checkVersionRecalled() {
  try {
    const currentVersion = getCurrentVersion()
    console.log('[VersionRecallChecker] Checking if version is recalled...')
    console.log('[VersionRecallChecker] Current version:', currentVersion)

    // Ensure version has v prefix
    const tag = currentVersion.startsWith('v') ? currentVersion : 'v' + currentVersion
    const url = `https://api.github.com/repos/Zhzhou-Publishing/openlucky/releases/tags/${tag}`
    console.log('[VersionRecallChecker] Checking release tag:', url)

    return new Promise((resolve, reject) => {
      const options = {
        headers: {
          'User-Agent': 'openlucky-desktop-version-recall-checker'
        },
        timeout: 10000
      }

      const req = https.get(url, options, (res) => {
        console.log('[VersionRecallChecker] HTTP Status Code:', res.statusCode)

        if (res.statusCode === 404) {
          console.log('[VersionRecallChecker] Version recalled (404 Not Found)')
          resolve({
            recalled: true,
            version: currentVersion
          })
          return
        }

        if (res.statusCode === 200) {
          console.log('[VersionRecallChecker] Version exists and is active')
          resolve({
            recalled: false,
            version: currentVersion
          })
          return
        }

        // Other status codes
        console.error('[VersionRecallChecker] Unexpected status code:', res.statusCode)
        reject(new Error(`GitHub API returned unexpected status code: ${res.statusCode}`))
      })

      req.on('timeout', () => {
        req.destroy()
        console.error('[VersionRecallChecker] Request timed out')
        reject(new Error('GitHub API request timed out'))
      })

      req.on('error', (err) => {
        console.error('[VersionRecallChecker] Network error:', err.message)
        reject(new Error(`Network error: ${err.message}`))
      })
    })
  } catch (error) {
    console.error('[VersionRecallChecker] Error checking version recall:', error)
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
      console.error('[UpdateChecker] Network error:', err.message)
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
      console.log('[UpdateChecker] Already checked this hour, skipping')
      return { skipped: true }
    }

    // First, check if there's a recall status from file
    if (recallStatus.recalled) {
      console.log('[UpdateChecker] Found recall status from file for current version, returning recall result')
      recalled = true
      return recallStatus
    }

    // Second, check if current version is recalled via GitHub API
    console.log('[UpdateChecker] Step 1: Checking if current version is recalled...')
    const recallResult = await checkVersionRecalled()

    if (recallResult === null) {
      console.error('[UpdateChecker] Version recall check failed, proceeding with update check')
    } else if (recallResult.recalled) {
      console.log('[UpdateChecker] Version is recalled, saving recall status and returning')
      // Save recall status to file
      saveRecallStatus(recallResult.version)
      // Set global recalled variable
      recalled = true
      return recallResult
    } else {
      console.log('[UpdateChecker] Version is not recalled, proceeding with update check')
    }

    // Third, check for updates
    console.log('[UpdateChecker] Step 2: Checking for updates...')
    const currentVersion = getCurrentVersion()
    const currentChannel = getVersionChannel(currentVersion)
    console.log('[UpdateChecker] Current version:', currentVersion, 'channel:', currentChannel)

    const release = await fetchLatestReleaseForChannel(currentChannel)

    if (!release || !release.name) {
      console.log('[UpdateChecker] No matching release in channel:', currentChannel)
      return { hasUpdate: false }
    }

    console.log('[UpdateChecker] Latest version in channel:', release.name)

    // Save check time after successful API call (only if not recalled)
    if (!recalled) {
      saveCheckTime()
    }

    // Compare versions
    if (release.name !== currentVersion) {
      return {
        hasUpdate: true,
        version: release.name,
        publishedAt: release.published_at,
        htmlUrl: release.html_url
      }
    }

    console.log('[UpdateChecker] Already on latest version')
    return { hasUpdate: false }
  } catch (error) {
    console.error('[UpdateChecker] Error checking for updates:', error)
    return null
  }
}

// Set tmp to not cleanup on exit to preserve converted files during session
tmp.setGracefulCleanup()

/**
 * Initialize default config file if it doesn't exist
 * Copies config.yaml from bundled resources to ~/.openlucky/config.yaml
 */
function initializeConfigFile() {
  try {
    const homeDir = os.homedir()
    const configDir = path.join(homeDir, '.openlucky')
    const configFilePath = path.join(configDir, 'config.yaml')

    // Check if config file already exists
    if (fs.existsSync(configFilePath)) {
      console.log('[Config] Config file already exists at:', configFilePath)
      return
    }

    // Determine source config path
    let sourceConfigPath
    if (app.isPackaged) {
      // In production, config.yaml is in Resources directory
      sourceConfigPath = path.join(process.resourcesPath, 'config.yaml')
    } else {
      // In development, use config.yaml from project root
      sourceConfigPath = path.join(__dirname, '..', '..', 'config.yaml')
    }

    // Check if source config file exists
    if (!fs.existsSync(sourceConfigPath)) {
      console.error('[Config] Source config file not found at:', sourceConfigPath)
      return
    }

    // Create .openlucky directory if it doesn't exist
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true })
      console.log('[Config] Created config directory at:', configDir)
    }

    // Copy config file from resources to user home directory
    fs.copyFileSync(sourceConfigPath, configFilePath)
    console.log('[Config] Created config file from bundled resources at:', configFilePath)
  } catch (error) {
    console.error('[Config] Error initializing config file:', error)
  }
}

function createWindow() {
  // 创建浏览器窗口
  const win = new BrowserWindow({
    width: 1200,
    height: 1000,
    autoHideMenuBar: true,
    resizable: true,
    webPreferences: {
      devTools: true, // 开发环境启用开发者工具，生产环境禁用以提升性能
      spellCheck: false, // 极限节省性能：关闭拼写检查
      enableWebSQL: false, // 极限节省性能：关闭 WebSQL 支持
      offscreen: false, // 极限节省性能：不使用离屏渲染，如果涉及 CSS/Canvas 绘制问题，可以考虑开启
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  // 加载应用的 index.html
  win.loadFile('dist/index.html')

  // Ask the renderer whether the close should be confirmed (e.g., unsaved
  // images on PhotoGallery/PhotoEdit). The renderer replies with
  // 'confirm-close-response' carrying a boolean.
  let allowClose = false
  win.on('close', (e) => {
    if (allowClose) return
    e.preventDefault()
    win.webContents.send('confirm-close')
  })
  ipcMain.on('confirm-close-response', (_, allow) => {
    if (allow) {
      allowClose = true
      win.close()
    }
  })

  // 只在开发模式下打开开发者工具
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    win.webContents.openDevTools()
  }

  // Handle check-openlucky request
  ipcMain.on('check-openlucky', async (event) => {
    try {
      const command = getOpenLuckyPath()
      const args = ['--help']
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      // Spawn the process to check if openlucky --help works
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let errorOutput = ''

      process.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      process.on('close', (code) => {
        const success = code === 0
        event.sender.send('openlucky-checked', { success, error: errorOutput })
      })

      process.on('error', (err) => {
        event.sender.send('openlucky-checked', { success: false, error: err.message })
      })
    } catch (error) {
      console.error('Error checking openlucky:', error)
      event.sender.send('openlucky-checked', { success: false, error: error.message })
    }
  })

  // Handle directory selection request
  ipcMain.on('select-directory', async () => {
    try {
      const result = await dialog.showOpenDialog(win, {
        properties: ['openDirectory']
      })

      if (result.canceled) {
        win.webContents.send('directory-cancelled')
        return
      }

      const selectedPath = result.filePaths[0]

      // Read files in the selected directory
      const files = fs.readdirSync(selectedPath)

      win.webContents.send('directory-selected', {
        path: selectedPath,
        files: files
      })
    } catch (error) {
      console.error('Error selecting directory:', error)
      win.webContents.send('directory-error', error.message)
    }
  })

  ipcMain.on('open-external', (_, url) => {
    if (typeof url === 'string' && /^https?:\/\//i.test(url)) {
      shell.openExternal(url)
    }
  })

  // Handle get-images request
  ipcMain.on('get-images', async (_, directoryPath) => {
    try {
      // Read files in the directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files (including RAW files)
      const allImageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext)) && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      // Create temporary thumbnails directory using tmp
      const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-thumbnails_', unsafeCleanup: true })
      const tempDir = tempDirObj.name

      const presets = readPresetJson(directoryPath)

      // Add timestamp to bypass caching
      const timestamp = Date.now()

      const images = await Promise.all(
        allImageFiles.map(file => buildThumbnailEntry(directoryPath, file, presets, tempDir, timestamp))
      )

      win.webContents.send('images-loaded', {
        images: images
      })
    } catch (error) {
      console.error('Error loading images:', error)
      win.webContents.send('images-error', error.message)
    }
  })

  // Handle get-presets request
  ipcMain.on('get-presets', async (event) => {
    try {
      // Construct the command
      const command = getOpenLuckyPath()
      const args = ['config', 'read', '-f', 'json']
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      process.stdout.on('data', (data) => {
        output += data.toString()
      })

      process.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          try {
            const config = JSON.parse(output)
            // Convert preset keys to array format for frontend
            const presets = config.presets ? Object.keys(config.presets).map(key => ({
              ...config.presets[key],
              value: key,
              label: config.presets[key].label || key
            })) : []
            event.sender.send('presets-loaded', { presets })
          } catch (parseError) {
            event.sender.send('presets-error', { message: 'Failed to parse config', error: parseError.message })
          }
        } else {
          event.sender.send('presets-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      process.on('error', (err) => {
        event.sender.send('presets-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      console.error('Error getting presets:', error)
      event.sender.send('presets-error', { message: 'Error getting presets', error: error.message })
    }
  })

  // Handle prepare-working-directory request (from PhotoGallery)
  ipcMain.on('prepare-working-directory', async (event, directoryPath) => {
    try {
      // Create temporary working directory
      const workingDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
      const workingDirectory = workingDirObj.name

      // 设置并发限制：根据 CPU 核心数，留一个核心防止界面卡顿
      // 统一所有图片的并发控制，防止非 RAW 文件过多时造成系统压力
      const concurrencyLimit = Math.max(1, Math.floor(os.cpus().length / 2))
      const limit = pLimit(concurrencyLimit)

      // Read files in the source directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files and .preset.json
      const filesToProcess = files.filter(file => {
        if (file === '.preset.json') return true
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext)) && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      // Separate images and config file
      const imageFiles = filesToProcess.filter(file => file !== '.preset.json')

      // Function to check if image needs resize (long edge >= 800)
      const needsResize = async (imagePath) => {
        try {
          const ext = path.extname(imagePath).toLowerCase()

          // For RAW files, assume they need resizing (camera RAW files are typically large)
          if (checkExtension(RAW_EXTENSIONS, ext)) {
            return true
          }

          // For non-RAW files, read only the header via image-size (avoids Sharp/libvips native memory growth)
          const { width, height } = sizeOf(imagePath)
          const longEdge = Math.max(width, height)
          return longEdge >= 800
        } catch (error) {
          console.error('Error checking image dimensions:', error)
          return false // Default to no resize if check fails
        }
      }

      // Function to resize image using openlucky tool resize command
      const resizeImage = (inputPath, outputPath) => {
        return new Promise((resolve) => {
          const command = getOpenLuckyPath()
          const args = ['tool', 'resize', '-i', inputPath, '-o', outputPath, '-v', '800']
          console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

          const process = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: true
          })

          let stderrOutput = ''

          process.stderr.on('data', (data) => {
            stderrOutput += data.toString()
          })

          process.on('close', (code) => {
            if (code === 0) {
              resolve({ success: true })
            } else {
              console.error('Resize failed:', inputPath, 'Exit code:', code)
              console.error('Error output:', stderrOutput)
              resolve({ success: false, error: stderrOutput })
            }
          })

          process.on('error', (err) => {
            console.error('Resize error:', inputPath, err.message)
            resolve({ success: false, error: err.message })
          })
        })
      }

      // Process all images (both RAW and non-RAW) using pLimit to control concurrency.
      // 进度计数：每张图轮到处理时计数器自增并广播，UI 显示 [n/total] 路径。
      // 并发下次序与输入顺序未必一致，但计数单调递增，UI 看起来仍然连续。
      const totalImages = imageFiles.length
      let startedCount = 0
      const imageProcessings = imageFiles.map(file => limit(async () => {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        startedCount += 1
        const progress = `[${startedCount}/${totalImages}] ${srcPath}`
        event.sender.send('processing-progress-update', { progress })
        event.sender.send('window-title-update', { title: `OpenLucky Desktop App - ${progress}` })

        if (await needsResize(srcPath)) {
          // Resize image to 800px long edge
          const result = await resizeImage(srcPath, destPath)
          if (result.success) {
            console.log('Image processed (resized):', file)
            return { success: true, file }
          } else {
            console.error('Failed to process image (resize):', result.error)
            return { success: false, file, error: result.error }
          }
        } else {
          // Copy directly if no resize needed
          try {
            fs.copyFileSync(srcPath, destPath)
            console.log('Image processed (copied):', file)
            return { success: true, file }
          } catch (err) {
            console.error('Failed to process image (copy):', file, err.message)
            return { success: false, file, error: err.message }
          }
        }
      }))

      // Wait for all image processings to complete
      await Promise.all(imageProcessings)

      // Copy .preset.json to working directory
      const presetJsonPath = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetJsonPath)) {
        fs.copyFileSync(presetJsonPath, path.join(workingDirectory, '.preset.json'))
      }

      // Create output subdirectory
      const outputDirectory = path.join(workingDirectory, 'output')
      if (!fs.existsSync(outputDirectory)) {
        fs.mkdirSync(outputDirectory, { recursive: true })
      }

      event.sender.send('processing-progress-clear', {})
      event.sender.send('window-title-restore', {})
      event.sender.send('working-directory-prepared', { workingDirectory, outputDirectory, originalDirectory: directoryPath })
    } catch (error) {
      console.error('Error preparing working directory:', error)
      event.sender.send('processing-progress-clear', {})
      event.sender.send('window-title-restore', {})
      event.sender.send('working-directory-error', { error: error.message })
    }
  })

  // Handle prepare-working-directory-from-selected request (from PhotoDirectory)
  ipcMain.on('prepare-working-directory-from-selected', async (event, directoryPath) => {
    try {
      // Create temporary working directory
      const workingDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
      const workingDirectory = workingDirObj.name

      // 设置并发限制：根据 CPU 核心数，留一个核心防止界面卡顿
      const concurrencyLimit = Math.max(1, Math.floor(os.cpus().length / 2))
      const limit = pLimit(concurrencyLimit)

      // Read files in the source directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files and .preset.json only
      const filesToProcess = files.filter(file => {
        if (file === '.preset.json') return true
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        const isFile = fs.statSync(path.join(directoryPath, file)).isFile()
        return isFile && (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext))
      })

      // Separate images from config file
      const imageFiles = filesToProcess.filter(file => file !== '.preset.json')

      // Function to check if image needs resize (long edge >= 800)
      const needsResize = async (imagePath) => {
        try {
          const ext = path.extname(imagePath).toLowerCase()

          // For RAW files, assume they need resizing
          if (checkExtension(RAW_EXTENSIONS, ext)) {
            return true
          }

          // For non-RAW files, read header via image-size
          const { width, height } = sizeOf(imagePath)
          const longEdge = Math.max(width, height)
          return longEdge >= 800
        } catch (error) {
          console.error('Error checking image dimensions:', error)
          return false
        }
      }

      // Function to resize image using openlucky tool resize command
      const resizeImage = (inputPath, outputPath) => {
        return new Promise((resolve) => {
          const command = getOpenLuckyPath()
          const args = ['tool', 'resize', '-i', inputPath, '-o', outputPath, '-v', '800']
          console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

          const process = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: true
          })

          let stderrOutput = ''
          process.stderr.on('data', (data) => {
            stderrOutput += data.toString()
          })

          process.on('close', (code) => {
            if (code === 0) {
              resolve({ success: true })
            } else {
              console.error('Resize failed:', inputPath, 'Exit code:', code)
              resolve({ success: false, error: stderrOutput })
            }
          })

          process.on('error', (err) => {
            resolve({ success: false, error: err.message })
          })
        })
      }

      // Process all images using pLimit for concurrency control.
      // 进度计数：每张图轮到处理时计数器自增并广播，UI 显示 [n/total] 路径。
      const totalImages = imageFiles.length
      let startedCount = 0
      const imageProcessings = imageFiles.map(file => limit(async () => {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        startedCount += 1
        const progress = `[${startedCount}/${totalImages}] ${srcPath}`
        event.sender.send('processing-progress-update', { progress })
        event.sender.send('window-title-update', { title: `OpenLucky Desktop App - ${progress}` })

        if (await needsResize(srcPath)) {
          const result = await resizeImage(srcPath, destPath)
          if (result.success) {
            console.log('Image processed (resized):', file)
            return { success: true, file }
          } else {
            console.error('Failed to process image (resize):', result.error)
            return { success: false, file, error: result.error }
          }
        } else {
          try {
            fs.copyFileSync(srcPath, destPath)
            console.log('Image processed (copied):', file)
            return { success: true, file }
          } catch (err) {
            console.error('Failed to process image (copy):', file, err.message)
            return { success: false, file, error: err.message }
          }
        }
      }))

      // Wait for all processings to complete
      await Promise.all(imageProcessings)

      // Copy .preset.json to working directory
      const presetJsonPath = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetJsonPath)) {
        fs.copyFileSync(presetJsonPath, path.join(workingDirectory, '.preset.json'))
      }

      // Create output subdirectory
      const outputDirectory = path.join(workingDirectory, 'output')
      if (!fs.existsSync(outputDirectory)) {
        fs.mkdirSync(outputDirectory, { recursive: true })
      }

      event.sender.send('processing-progress-clear', {})
      event.sender.send('window-title-restore', {})
      event.sender.send('working-directory-from-selected-prepared', { workingDirectory, outputDirectory, originalDirectory: directoryPath })
    } catch (error) {
      console.error('Error preparing working directory:', error)
      event.sender.send('processing-progress-clear', {})
      event.sender.send('window-title-restore', {})
      event.sender.send('working-directory-from-selected-error', { error: error.message })
    }
  })

  // Handle get-full-res-image request
  ipcMain.on('get-full-res-image', async (event, { directoryPath, filename }) => {
    try {
      const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'))

      const presets = readPresetJson(directoryPath)
      const fullPath = resolveImagePath(directoryPath, filename, presets)

      let imageUrl = `file://${fullPath}`

      // Convert tif/tiff files to jpg for browser compatibility
      if (checkExtension(TIFF_EXTENSIONS, ext)) {
        try {
          // Create temporary directory using tmp
          const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-full-res_', unsafeCleanup: true })
          const tempDir = tempDirObj.name

          const convertedPath = path.join(tempDir, `${path.basename(filename, ext)}.jpg`)
          const buffer = await sharp(fullPath).jpeg({ quality: 95 }).toBuffer()
          fs.writeFileSync(convertedPath, buffer)
          imageUrl = `file://${convertedPath}`
        } catch (err) {
          console.error('Error converting image for', filename, err)
        }
      }

      event.sender.send('full-res-image-loaded', { url: imageUrl })
    } catch (error) {
      console.error('Error getting full resolution image:', error)
      event.sender.send('full-res-image-error', { error: error.message })
    }
  })

  // Handle read-preset-json request
  ipcMain.on('read-preset-json', async (event, directoryPath) => {
    try {
      event.sender.send('preset-json-loaded', { presets: readPresetJson(directoryPath) })
    } catch (error) {
      console.error('Error reading preset json:', error)
      event.sender.send('preset-json-error', { error: error.message })
    }
  })

  // Single-image refresh used by PhotoEdit after apply: rebuild the
  // thumbnail entry (TIFF transcode included) so image.url points at the
  // post-apply output, not the stale tmp file from the initial load.
  ipcMain.on('refresh-image', async (event, { directoryPath, filename }) => {
    try {
      const presets = readPresetJson(directoryPath)
      const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-thumbnail_', unsafeCleanup: true })
      const entry = await buildThumbnailEntry(
        directoryPath,
        filename,
        presets,
        tempDirObj.name,
        Date.now()
      )
      event.sender.send('image-refreshed', { filename, entry })
    } catch (error) {
      console.error('Error refreshing image:', error)
      event.sender.send('image-refresh-error', { filename, error: error.message })
    }
  })

  // Handle apply-preset request
  ipcMain.on('apply-preset', async (event, { inputPath, outputPath, preset }) => {
    try {
      // Construct the command
      const command = getOpenLuckyPath()
      const args = ['filmbatch', '--input', inputPath, '--output', outputPath, '--preset', preset]
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('preset-apply-started', { message: 'Processing started' })

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      process.stdout.on('data', (data) => {
        output += data.toString()
        // Send progress updates to renderer
        event.sender.send('preset-apply-progress', { data: data.toString() })
      })

      process.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          event.sender.send('preset-apply-success', { message: 'Preset applied successfully' })
        } else {
          event.sender.send('preset-apply-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      process.on('error', (err) => {
        event.sender.send('preset-apply-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      console.error('Error applying preset:', error)
      event.sender.send('preset-apply-error', { message: 'Error applying preset', error: error.message })
    }
  })

  // Handle apply-filmparam request
  ipcMain.on('apply-filmparam', async (event, { inputPath, outputPath, filename, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null }) => {
    try {
      // Construct the input file path
      const inputFile = path.join(inputPath, filename)

      // Construct the output file path (join output directory with filename)
      const outputFile = path.join(outputPath, filename)

      // Construct the command
      const command = getOpenLuckyPath()
      const args = ['filmparam', '--input', inputFile, '--output', outputFile, '--param', params, '--rotate-clockwise', rotateClockwise.toString()]
      if (area && Number.isInteger(area.x1) && Number.isInteger(area.y1) && Number.isInteger(area.x2) && Number.isInteger(area.y2)) {
        args.push('--area', `${area.x1},${area.y1},${area.x2},${area.y2}`)
        // basis is meaningful only alongside a valid area; CLI accepts area
        // without basis (treated as actual-image coords) for backward compat.
        if (areaBasis && Number.isInteger(areaBasis.w) && Number.isInteger(areaBasis.h) && areaBasis.w > 0 && areaBasis.h > 0) {
          args.push('--area-basis', `${areaBasis.w},${areaBasis.h}`)
        }
      }
      if (typeof exposure === 'number' && Number.isFinite(exposure)) {
        args.push('--exposure', exposure.toString())
      }
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('filmparam-apply-started', { message: 'Processing started' })

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      process.stdout.on('data', (data) => {
        output += data.toString()
        // Send progress updates to renderer
        event.sender.send('filmparam-apply-progress', { data: data.toString() })
      })

      process.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          event.sender.send('filmparam-apply-success', { message: 'Film processing completed successfully', outputFile })
        } else {
          event.sender.send('filmparam-apply-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      process.on('error', (err) => {
        event.sender.send('filmparam-apply-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      console.error('Error applying filmparam:', error)
      event.sender.send('filmparam-apply-error', { message: 'Error applying film parameters', error: error.message })
    }
  })

  // Handle pick-color request — eyedropper picks pixel from source TIFF/RAW
  // (not from JPEG preview) so the returned RGB matches the file's truth.
  // Promise-based so callers can `await ipcRenderer.invoke('pick-color', ...)`.
  ipcMain.handle('pick-color', async (_event, { filePath, x, y, format = '8' }) => {
    return new Promise((resolve, reject) => {
      const command = getOpenLuckyPath()
      const args = [
        'tool', 'pick',
        '-i', filePath,
        '-x', String(x),
        '-y', String(y),
        '-f', String(format),
      ]
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      const child = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      })

      let stdout = ''
      let stderr = ''
      child.stdout.on('data', (data) => { stdout += data.toString() })
      child.stderr.on('data', (data) => { stderr += data.toString() })

      child.on('error', (err) => {
        reject(new Error(`Failed to spawn pick: ${err.message}`))
      })

      child.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(stderr.trim() || `pick exited with code ${code}`))
          return
        }
        try {
          resolve(JSON.parse(stdout))
        } catch (e) {
          reject(new Error(`Failed to parse pick output: ${e.message}`))
        }
      })
    })
  })

  // Handle apply-filmparambatch request
  ipcMain.on('apply-filmparambatch', async (event, { inputPath, outputPath, params, rotateClockwise = 0, area = null, areaBasis = null, exposure = null }) => {
    try {
      // Construct the command
      const command = getOpenLuckyPath()
      const args = ['filmparambatch', '--input', inputPath, '--output', outputPath, '--param', params, '--rotate-clockwise', rotateClockwise.toString()]
      if (area && Number.isInteger(area.x1) && Number.isInteger(area.y1) && Number.isInteger(area.x2) && Number.isInteger(area.y2)) {
        args.push('--area', `${area.x1},${area.y1},${area.x2},${area.y2}`)
        if (areaBasis && Number.isInteger(areaBasis.w) && Number.isInteger(areaBasis.h) && areaBasis.w > 0 && areaBasis.h > 0) {
          args.push('--area-basis', `${areaBasis.w},${areaBasis.h}`)
        }
      }
      if (typeof exposure === 'number' && Number.isFinite(exposure)) {
        args.push('--exposure', exposure.toString())
      }
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('filmparambatch-apply-started', { message: 'Batch processing started' })

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      process.stdout.on('data', (data) => {
        output += data.toString()
        // Send progress updates to renderer
        event.sender.send('filmparambatch-apply-progress', { data: data.toString() })
      })

      process.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          event.sender.send('filmparambatch-apply-success', { message: 'Batch processing completed successfully' })
        } else {
          event.sender.send('filmparambatch-apply-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      process.on('error', (err) => {
        event.sender.send('filmparambatch-apply-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      console.error('Error applying filmparambatch:', error)
      event.sender.send('filmparambatch-apply-error', { message: 'Error applying batch film parameters', error: error.message })
    }
  })

  // Handle copy-preset-json request
  ipcMain.on('copy-preset-json', async (event, { workingDirectory, originalDirectory }) => {
    try {
      const presetJsonSource = path.join(workingDirectory, '.preset.json')
      const presetJsonDest = path.join(originalDirectory, '.preset.json')

      // Check if source .preset.json exists
      if (!fs.existsSync(presetJsonSource)) {
        event.sender.send('copy-preset-json-error', { message: 'Source .preset.json not found in working directory' })
        return
      }

      // Ensure original directory exists
      if (!fs.existsSync(originalDirectory)) {
        event.sender.send('copy-preset-json-error', { message: 'Original directory does not exist' })
        return
      }

      // Copy the file
      fs.copyFileSync(presetJsonSource, presetJsonDest)

      event.sender.send('copy-preset-json-success', { message: '.preset.json copied successfully' })
    } catch (error) {
      console.error('Error copying .preset.json:', error)
      event.sender.send('copy-preset-json-error', { message: 'Error copying .preset.json', error: error.message })
    }
  })

  // Handle apply-preset-to-file request (single file preset application)
  ipcMain.on('apply-preset-to-file', async (event, { presetFile, inputFilePath, outputFilePath }) => {
    try {
      // Read preset file
      if (!fs.existsSync(presetFile)) {
        event.sender.send('preset-to-file-error', { message: 'Preset file not found', error: `Preset file does not exist: ${presetFile}` })
        return
      }

      const presetContent = fs.readFileSync(presetFile, 'utf-8')
      const presetObj = JSON.parse(presetContent)

      // Get filename from input path
      const filename = path.basename(inputFilePath)
      const ext = path.extname(filename)
      const isRaw = checkExtension(RAW_EXTENSIONS, ext)

      // Try to find preset for this file
      let presetKey = null

      // Try multiple key formats for RAW files
      if (isRaw) {
        // Try: original filename, filename + .tif, filename + .tiff
        const possibleKeys = [
          filename,
          filename + '.tif',
          filename + '.tiff'
        ]

        for (const key of possibleKeys) {
          if (presetObj[key]) {
            presetKey = key
            break
          }
        }
      } else {
        // For non-RAW files, try direct filename match
        if (presetObj[filename]) {
          presetKey = filename
        }
      }

      if (!presetKey) {
        event.sender.send('preset-to-file-error', { message: 'Preset not found for file', error: `No preset found for file: ${filename}` })
        return
      }

      // Get preset parameters
      const presetParams = presetObj[presetKey]
      const paramsString = `${presetParams.mask_r},${presetParams.mask_g},${presetParams.mask_b},${presetParams.gamma},${presetParams.contrast}`

      // If RAW file and output is not TIFF format, add .tif extension
      let finalOutputPath = outputFilePath
      if (isRaw && !checkExtension(TIFF_EXTENSIONS, path.extname(outputFilePath))) {
        finalOutputPath += '.tif'
      }

      // Construct command
      const command = getOpenLuckyPath()
      const args = ['filmparam', '--input', inputFilePath, '--output', finalOutputPath, '--param', paramsString]
      console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      event.sender.send('preset-to-file-started', { message: 'Processing started' })

      // Spawn process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''

      process.stdout.on('data', (data) => {
        output += data.toString()
        // Send progress updates to renderer
        event.sender.send('preset-to-file-progress', { data: data.toString() })
      })

      process.stderr.on('data', (data) => {
        errorOutput += data.toString()
      })

      process.on('close', (code) => {
        if (code === 0) {
          event.sender.send('preset-to-file-success', { message: 'Preset applied to file successfully' })
        } else {
          event.sender.send('preset-to-file-error', { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      process.on('error', (err) => {
        event.sender.send('preset-to-file-error', { message: 'Failed to start process', error: err.message })
      })
    } catch (error) {
      console.error('Error applying preset to file:', error)
      event.sender.send('preset-to-file-error', { message: 'Error applying preset to file', error: error.message })
    }
  })

  // Handle apply-preset-to-batch request (batch preset application)
  ipcMain.on('apply-preset-to-batch', async (event, { presetFile, inputDir, outputDir }) => {
    try {
      // Read preset file
      if (!fs.existsSync(presetFile)) {
        event.sender.send('preset-to-batch-error', { message: 'Preset file not found', error: `Preset file does not exist: ${presetFile}` })
        return
      }

      const presetContent = fs.readFileSync(presetFile, 'utf-8')
      const presetObj = JSON.parse(presetContent)

      // Ensure output directory exists
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true })
      }

      // Get all image files from input directory (including RAW and non-RAW)
      const files = fs.readdirSync(inputDir)
      const imageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (checkExtension(IMAGE_EXTENSIONS, ext) || checkExtension(RAW_EXTENSIONS, ext)) && fs.statSync(path.join(inputDir, file)).isFile()
      })

      // Process each file
      let processedCount = 0
      const totalCount = imageFiles.length

      for (const file of imageFiles) {
        const ext = path.extname(file)
        const isRaw = checkExtension(RAW_EXTENSIONS, ext)

        // Try to find preset for this file
        let presetKey = null

        // Try multiple key formats for RAW files
        if (isRaw) {
          fileWithoutExt = file.slice(0, file.lastIndexOf('.'))
          const possibleKeys = [
            file,
            file + '.tif',
            file + '.tiff',
            fileWithoutExt + '.tif',
            fileWithoutExt + '.tiff'
          ]

          for (const key of possibleKeys) {
            if (presetObj[key]) {
              presetKey = key
              break
            }
          }
        } else {
          // For non-RAW files, try direct filename match
          if (presetObj[file]) {
            presetKey = file
          }
        }

        if (presetKey) {
          // Get preset parameters
          const presetParams = presetObj[presetKey]
          let paramsString = `${presetParams.mask_r},${presetParams.mask_g},${presetParams.mask_b},${presetParams.gamma},${presetParams.contrast}`
          if (presetParams.contrast_r !== undefined && presetParams.contrast_g !== undefined && presetParams.contrast_b !== undefined) {
            paramsString += `,${presetParams.contrast_r},${presetParams.contrast_g},${presetParams.contrast_b}`
          }
          const rotateClockwise = presetParams.rotate_clockwise || 0

          // Construct input and output paths
          const inputFilePath = path.join(inputDir, file)
          let outputFilePath = path.join(outputDir, file)

          // If RAW file and output is not TIFF format, add .tif extension
          if (isRaw && !checkExtension(TIFF_EXTENSIONS, path.extname(outputFilePath))) {
            outputFilePath += '.tif'
          }

          // Construct command
          const command = getOpenLuckyPath()
          const args = ['filmparam', '--input', inputFilePath, '--output', outputFilePath, '--param', paramsString, '--rotate-clockwise', rotateClockwise.toString()]

          // Replay the white-point ROI captured during apply against the
          // full-res original. CLI rescales using --area-basis, so we pass
          // the preview-frame coords + dims as-is.
          const presetArea = presetParams.area
          const presetBasis = presetParams.area_basis
          if (presetArea
              && Number.isInteger(presetArea.x1) && Number.isInteger(presetArea.y1)
              && Number.isInteger(presetArea.x2) && Number.isInteger(presetArea.y2)) {
            args.push('--area', `${presetArea.x1},${presetArea.y1},${presetArea.x2},${presetArea.y2}`)
            if (presetBasis
                && Number.isInteger(presetBasis.w) && Number.isInteger(presetBasis.h)
                && presetBasis.w > 0 && presetBasis.h > 0) {
              args.push('--area-basis', `${presetBasis.w},${presetBasis.h}`)
            }
          }
          const presetExposure = presetParams.exposure_ev
          if (typeof presetExposure === 'number' && Number.isFinite(presetExposure)) {
            args.push('--exposure', presetExposure.toString())
          }
          console.log(`[openlucky] Executing: ${command} ${args.join(' ')}`)

          event.sender.send('preset-to-batch-progress', {
            file: file,
            progress: `${processedCount + 1}/${totalCount}`,
            data: `Processing ${file}`
          })

          // Spawn process and wait for completion
          await new Promise((resolve) => {
            const process = spawn(command, args, {
              stdio: ['pipe', 'pipe', 'pipe'],
              windowsHide: true
            })

            process.on('close', (code) => {
              if (code !== 0) {
                console.error(`Error processing ${file}: Exit code ${code}`)
              }
              resolve()
            })

            process.on('error', (err) => {
              console.error(`Error processing ${file}:`, err.message)
              resolve()
            })
          })

          processedCount++
        }
      }

      event.sender.send('preset-to-batch-success', { message: `Batch processing completed. Processed ${processedCount}/${totalCount} files.` })
    } catch (error) {
      console.error('Error applying preset to batch:', error)
      event.sender.send('preset-to-batch-error', { message: 'Error applying preset to batch', error: error.message })
    }
  })
}

// 显示更新通知对话框
function showUpdateDialog(win, updateInfo, isRecalled = false) {
  const texts = getLocalizedText('update')
  let detail = texts.detail(updateInfo.publishedAt)

  // 如果是召回情况，添加召回提示
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
      // 用户点击"立即下载"按钮，使用默认浏览器打开 release 页面
      shell.openExternal(updateInfo.htmlUrl)
    } else if (isRecalled) {
      // 如果是召回情况且用户点击取消，退出应用
      app.quit()
    }
  }).catch((error) => {
    console.error('Error showing update dialog:', error)
  })
}

// 显示版本召回对话框，强制用户下载最新版本或退出
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
      // 用户点击"下载最新版本"按钮，使用默认浏览器打开 release 页面
      shell.openExternal(latestHtmlUrl).then(() => {
        // 打开链接后退出应用
        app.quit()
      }).catch((error) => {
        console.error('Error opening download URL:', error)
        // 即使打开链接失败，也要退出应用
        app.quit()
      })
    } else {
      // 用户点击"退出"按钮
      app.quit()
    }
  }).catch((error) => {
    console.error('Error showing recall dialog:', error)
    // 出错也要退出
    app.quit()
  })
}

// 极限节省性能：禁用硬件加速，如果涉及到图像处理和显示，可能会有更好的兼容性
app.disableHardwareAcceleration();

// 当 Electron 完成初始化时被调用
app.whenReady().then(async () => {
  // Initialize default config file if it doesn't exist
  initializeConfigFile()

  createWindow()

  // 检查更新
  const updateInfo = await checkForUpdates()

  // 处理版本召回情况
  if (updateInfo && updateInfo.recalled) {
    console.log('[App] Version is recalled, fetching latest release info...')
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
          // 如果窗口不可用，直接退出
          app.quit()
        }
      } else {
        // 无法获取最新版本信息，直接退出
        console.error('[App] Failed to fetch latest release info for recall, quitting...')
        app.quit()
      }
    } catch (error) {
      console.error('[App] Error fetching latest release for recall:', error)
      app.quit()
    }
    return
  }

  // 处理正常更新检查
  if (updateInfo && updateInfo.hasUpdate) {
    // 等待窗口准备好后显示更新对话框
    const win = BrowserWindow.getAllWindows()[0]
    if (win && !win.isDestroyed()) {
      setTimeout(() => {
        showUpdateDialog(win, updateInfo)
      }, 1000) // 延迟 1 秒显示，确保窗口完全加载
    }
  } else if (updateInfo === null) {
    // 检查更新失败，显示网络错误警告
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
          console.error('Error showing network error dialog:', error)
        })
      }, 1000) // 延迟 1 秒显示，确保窗口完全加载
    }
  }
  // updateInfo.hasUpdate === false 或 updateInfo.skipped === true 时不显示任何对话框
})

// 当所有窗口都被关闭时退出应用
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
