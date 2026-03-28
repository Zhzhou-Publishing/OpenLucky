const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const fs = require('fs')
const path = require('path')
const sharp = require('sharp')
const { spawn } = require('child_process')
const tmp = require('tmp')

// Set tmp to not cleanup on exit to preserve converted files during session
tmp.setGracefulCleanup()

function createWindow() {
  // 创建浏览器窗口
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    autoHideMenuBar: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  // 加载应用的 index.html
  win.loadFile('dist/index.html')

  // 只在开发模式下打开开发者工具
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    win.webContents.openDevTools()
  }

  // Handle check-openlucky request
  ipcMain.on('check-openlucky', async (event) => {
    try {
      // Spawn the process to check if openlucky --help works
      const process = spawn('openlucky', ['--help'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
        detached: true
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

  // Handle set window resizable
  ipcMain.on('set-window-resizable', (_, resizable) => {
    const win = BrowserWindow.getAllWindows()[0]
    if (win) {
      win.setResizable(resizable)
    }
  })

  // Handle get-images request
  ipcMain.on('get-images', async (_, directoryPath) => {
    try {
      // Supported image extensions
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff']
      const rawExtensions = ['.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf']
      const tiffFormats = ['.tif', '.tiff']

      // Read files in the directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files (including RAW files)
      const allImageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (imageExtensions.includes(ext) || rawExtensions.includes(ext)) && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      // Create working directory in system temp
      const workingTempDir = path.join(app.getPath('temp'), 'openlucky_working_directory')
      if (!fs.existsSync(workingTempDir)) {
        const tmpDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
        fs.renameSync(tmpDirObj.name, workingTempDir)
      }

      // Create temporary thumbnails directory using tmp
      const tempDirObj = tmp.dirSync({ prefix: 'photo-gallery-thumbnails_', unsafeCleanup: true })
      const tempDir = tempDirObj.name

      // Read .preset.json from working directory
      let presets = {}
      const presetsFile = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetsFile)) {
        try {
          const presetsContent = fs.readFileSync(presetsFile, 'utf-8')
          presets = JSON.parse(presetsContent)
        } catch (err) {
          console.error('Error reading .preset.json:', err)
        }
      }

      // Create a placeholder SVG for RAW files using tmp
      const placeholderSvgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
        <rect width="300" height="200" fill="#cccccc"/>
        <text x="150" y="100" font-family="Arial, sans-serif" font-size="14" text-anchor="middle" fill="#666666">RAW</text>
      </svg>`

      // Add timestamp to bypass caching
      const timestamp = Date.now()

      // Separate RAW files and other image files
      const rawFiles = allImageFiles.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return rawExtensions.includes(ext)
      })

      const regularImageFiles = allImageFiles.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return !rawExtensions.includes(ext)
      })

      // Process RAW files - first return placeholders, then convert in background
      const rawImages = await Promise.all(rawFiles.map(async (file) => {
        const inputPath = path.join(directoryPath, file)
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        const baseName = path.basename(file, ext)
        const tiffFileName = `${baseName}.tif`
        const outputTiffPath = path.join(workingTempDir, tiffFileName)

        // Create placeholder thumbnail using tmp
        const placeholderSvgObj = tmp.fileSync({ prefix: `${baseName}_placeholder_`, postfix: '.svg' })
        const placeholderPath = placeholderSvgObj.name
        fs.writeFileSync(placeholderPath, placeholderSvgContent)

        // Check if TIFF already exists
        if (fs.existsSync(outputTiffPath)) {
          // TIFF exists, generate thumbnail
          try {
            const thumbnailPath = path.join(tempDir, `${baseName}_thumb.jpg`)
            await sharp(outputTiffPath)
              .resize(300, 200, { fit: 'cover' })
              .jpeg({ quality: 80 })
              .toFile(thumbnailPath)
            return {
              name: file,
              path: outputTiffPath,
              url: `file://${thumbnailPath}?t=${timestamp}`,
              isRaw: true,
              converted: true
            }
          } catch (err) {
            console.error('Error generating thumbnail for converted RAW file', file, err)
            return {
              name: file,
              path: outputTiffPath,
              url: `file://${placeholderPath}?t=${timestamp}`,
              isRaw: true,
              converted: true
            }
          }
        } else {
          // TIFF doesn't exist yet, start conversion in background
          // Start conversion in background (don't wait)
          const convertProcess = spawn('openlucky', ['raw2tiff', '-i', inputPath, '-o', outputTiffPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
            detached: true,
            windowsHide: true
          })

          let stdoutOutput = ''
          let stderrOutput = ''

          convertProcess.stdout.on('data', (data) => {
            stdoutOutput += data.toString()
          })

          convertProcess.stderr.on('data', (data) => {
            stderrOutput += data.toString()
          })

          convertProcess.on('close', async (code) => {
            if (code === 0 && fs.existsSync(outputTiffPath)) {
              console.log('RAW conversion successful:', file)
              // Conversion successful, the next get-images request will pick up the converted file
            } else {
              console.error('RAW conversion failed:', file, 'Exit code:', code)
              console.error('Command output (stdout):', stdoutOutput)
              console.error('Command errors (stderr):', stderrOutput)
            }
          })

          return {
            name: file,
            path: inputPath,
            url: `file://${placeholderPath}?t=${timestamp}`,
            isRaw: true,
            converted: false
          }
        }
      }))

      // Process regular image files
      const regularImages = await Promise.all(regularImageFiles.map(async (file) => {
        // Check if file has preset output_dir
        let fullPath = path.join(directoryPath, file)

        // If file exists in presets and has output_dir, use output path
        if (presets[file] && presets[file].output_dir) {
          const outputPath = presets[file].output_dir
          if (fs.existsSync(outputPath)) {
            fullPath = outputPath
          }
        }

        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))

        let imageUrl = `file://${fullPath}?t=${timestamp}`

        // Generate thumbnail for tif/tiff files
        if (tiffFormats.includes(ext)) {
          try {
            const thumbnailPath = path.join(tempDir, `${path.basename(file, ext)}.jpg`)
            await sharp(fullPath)
              .resize(300, 200, { fit: 'cover' })
              .jpeg({ quality: 80 })
              .toFile(thumbnailPath)
            imageUrl = `file://${thumbnailPath}?t=${timestamp}`
          } catch (err) {
            console.error('Error generating thumbnail for', file, err)
          }
        }

        return {
          name: file,
          path: fullPath,
          url: imageUrl
        }
      }))

      // Combine converted RAW files and regular images
      const allImages = [...rawImages, ...regularImages]

      win.webContents.send('images-loaded', {
        images: allImages
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
      const command = 'openlucky'
      const args = ['config', 'read', '-f', 'json']

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: true,
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

  // Handle get-full-res-image request
  ipcMain.on('get-full-res-image', async (event, { directoryPath, filename }) => {
    try {
      // Read .preset.json from working directory to find output path
      let fullPath = path.join(directoryPath, filename)
      const presetsFile = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetsFile)) {
        try {
          const presetsContent = fs.readFileSync(presetsFile, 'utf-8')
          const presets = JSON.parse(presetsContent)
          // If file exists in presets and has output_dir, use output path
          if (presets[filename] && presets[filename].output_dir) {
            const outputPath = presets[filename].output_dir
            if (fs.existsSync(outputPath)) {
              fullPath = outputPath
            }
          }
        } catch (err) {
          console.error('Error reading .preset.json:', err)
        }
      }

      const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'))
      const tiffFormats = ['.tif', '.tiff']

      let imageUrl = `file://${fullPath}`

      // Convert tif/tiff files to jpg for browser compatibility
      if (tiffFormats.includes(ext)) {
        try {
          const tempDir = path.join(app.getPath('temp'), 'photo-gallery-full-res')
          if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true })
          }

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
      const presetsFile = path.join(directoryPath, '.preset.json')
      let presets = {}
      if (fs.existsSync(presetsFile)) {
        try {
          const presetsContent = fs.readFileSync(presetsFile, 'utf-8')
          presets = JSON.parse(presetsContent)
        } catch (err) {
          console.error('Error reading .preset.json:', err)
        }
      }
      event.sender.send('preset-json-loaded', { presets })
    } catch (error) {
      console.error('Error reading preset json:', error)
      event.sender.send('preset-json-error', { error: error.message })
    }
  })

  // Handle apply-preset request
  ipcMain.on('apply-preset', async (event, { directoryPath, preset }) => {
    try {
      // Construct the command
      const command = 'openlucky'
      const args = ['filmbatch', '--input', directoryPath, '--preset', preset]

      event.sender.send('preset-apply-started', { message: 'Processing started' })

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: true,
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
  ipcMain.on('apply-filmparam', async (event, { directoryPath, filename, params }) => {
    try {
      // Construct input path
      const inputPath = path.join(directoryPath, filename)

      // Construct output path (put in output subdirectory)
      const outputDir = path.join(directoryPath, 'output')
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true })
      }
      const outputPath = path.join(outputDir, filename)

      // Construct the command
      const command = 'openlucky'
      const args = ['filmparam', '--input', inputPath, '--output', outputPath, '--param', params]

      event.sender.send('filmparam-apply-started', { message: 'Processing started' })

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: true,
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
          event.sender.send('filmparam-apply-success', { message: 'Film processing completed successfully', outputPath })
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

  // Handle apply-filmparambatch request
  ipcMain.on('apply-filmparambatch', async (event, { directoryPath, params }) => {
    try {
      // Construct the command
      const command = 'openlucky'
      const args = ['filmparambatch', '--input', directoryPath, '--param', params]

      event.sender.send('filmparambatch-apply-started', { message: 'Batch processing started' })

      // Spawn the process
      const process = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: true,
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
}

// 当 Electron 完成初始化时被调用
app.whenReady().then(createWindow)

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
