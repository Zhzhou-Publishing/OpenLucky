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

      // Add timestamp to bypass caching
      const timestamp = Date.now()

      // Process all image files
      const images = await Promise.all(allImageFiles.map(async (file) => {
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
        const isRaw = rawExtensions.includes(ext)

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
          url: imageUrl,
          isRaw: isRaw
        }
      }))

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

  // Handle prepare-working-directory request (from PhotoGallery)
  ipcMain.on('prepare-working-directory', async (event, directoryPath) => {
    try {
      // Supported image extensions
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff']
      const rawExtensions = ['.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf']

      // Create temporary working directory
      const workingDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
      const workingDirectory = workingDirObj.name

      // Read files in the source directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files and .preset.json
      const filesToProcess = files.filter(file => {
        if (file === '.preset.json') return true
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return (imageExtensions.includes(ext) || rawExtensions.includes(ext)) && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      // Separate RAW and non-RAW files
      const rawFiles = filesToProcess.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return rawExtensions.includes(ext)
      })

      const nonRawFiles = filesToProcess.filter(file => {
        if (file === '.preset.json') return false
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return !rawExtensions.includes(ext)
      })

      // Function to check if image needs resize (long edge >= 800)
      const needsResize = async (imagePath) => {
        try {
          const ext = path.extname(imagePath).toLowerCase()
          const rawExtensions = ['.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf']

          // For RAW files, assume they need resizing (camera RAW files are typically large)
          if (rawExtensions.includes(ext)) {
            return true
          }

          // For non-RAW files, check dimensions with Sharp
          const metadata = await sharp(imagePath).metadata()
          const width = metadata.width
          const height = metadata.height
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
          const process = spawn('openlucky', ['tool', 'resize', '-i', inputPath, '-o', outputPath, '-v', '800'], {
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: true
          })

          let stderrOutput = ''

          process.stderr.on('data', (data) => {
            stderrOutput += data.toString()
          })

          process.on('close', (code) => {
            if (code === 0 && fs.existsSync(outputPath)) {
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

      // Copy and process non-RAW files to working directory
      for (const file of nonRawFiles) {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        if (await needsResize(srcPath)) {
          // Resize image to 800px long edge
          await resizeImage(srcPath, destPath)
        } else {
          // Copy directly if no resize needed
          fs.copyFileSync(srcPath, destPath)
        }
      }

      // Copy .preset.json to working directory
      const presetJsonPath = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetJsonPath)) {
        fs.copyFileSync(presetJsonPath, path.join(workingDirectory, '.preset.json'))
      }

      // Process RAW files using openlucky tool resize (no separate conversion step)
      const rawProcessings = rawFiles.map(async file => {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        if (await needsResize(srcPath)) {
          // Resize RAW image to 800px long edge directly
          const result = await resizeImage(srcPath, destPath)
          if (result.success) {
            console.log('RAW resized:', file)
            return { success: true, file }
          } else {
            console.error('Failed to resize RAW:', file)
            return { success: false, file, error: result.error }
          }
        } else {
          // Copy directly if no resize needed
          try {
            fs.copyFileSync(srcPath, destPath)
            console.log('RAW copied (no resize needed):', file)
            return { success: true, file }
          } catch (err) {
            console.error('Failed to copy RAW:', file, err.message)
            return { success: false, file, error: err.message }
          }
        }
      })

      // Wait for all RAW processings to complete
      await Promise.all(rawProcessings)

      // Create output subdirectory
      const outputDirectory = path.join(workingDirectory, 'output')
      if (!fs.existsSync(outputDirectory)) {
        fs.mkdirSync(outputDirectory, { recursive: true })
      }

      event.sender.send('working-directory-prepared', { workingDirectory, outputDirectory })
    } catch (error) {
      console.error('Error preparing working directory:', error)
      event.sender.send('working-directory-error', { error: error.message })
    }
  })

  // Handle prepare-working-directory-from-selected request (from PhotoDirectory)
  ipcMain.on('prepare-working-directory-from-selected', async (event, directoryPath) => {
    try {
      // Supported image extensions
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff']
      const rawExtensions = ['.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf']

      // Create temporary working directory
      const workingDirObj = tmp.dirSync({ prefix: 'openlucky_working_', unsafeCleanup: true })
      const workingDirectory = workingDirObj.name

      // Read files in the source directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files and .preset.json only (exclude subdirectories and other files)
      const filesToProcess = files.filter(file => {
        if (file === '.preset.json') return true
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        const isFile = fs.statSync(path.join(directoryPath, file)).isFile()
        return isFile && (imageExtensions.includes(ext) || rawExtensions.includes(ext))
      })

      // Separate RAW and non-RAW files
      const rawFiles = filesToProcess.filter(file => {
        if (file === '.preset.json') return false
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return rawExtensions.includes(ext)
      })

      const nonRawFiles = filesToProcess.filter(file => {
        if (file === '.preset.json') return false
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return !rawExtensions.includes(ext)
      })

      // Function to check if image needs resize (long edge >= 800)
      const needsResize = async (imagePath) => {
        try {
          const ext = path.extname(imagePath).toLowerCase()
          const rawExtensions = ['.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf']

          // For RAW files, assume they need resizing (camera RAW files are typically large)
          if (rawExtensions.includes(ext)) {
            return true
          }

          // For non-RAW files, check dimensions with Sharp
          const metadata = await sharp(imagePath).metadata()
          const width = metadata.width
          const height = metadata.height
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
          const process = spawn('openlucky', ['tool', 'resize', '-i', inputPath, '-o', outputPath, '-v', '800'], {
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: true
          })

          let stderrOutput = ''

          process.stderr.on('data', (data) => {
            stderrOutput += data.toString()
          })

          process.on('close', (code) => {
            if (code === 0 && fs.existsSync(outputPath)) {
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

      // Copy and process non-RAW files to working directory
      for (const file of nonRawFiles) {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        if (await needsResize(srcPath)) {
          // Resize image to 800px long edge
          await resizeImage(srcPath, destPath)
        } else {
          // Copy directly if no resize needed
          fs.copyFileSync(srcPath, destPath)
        }
      }

      // Copy .preset.json to working directory
      const presetJsonPath = path.join(directoryPath, '.preset.json')
      if (fs.existsSync(presetJsonPath)) {
        fs.copyFileSync(presetJsonPath, path.join(workingDirectory, '.preset.json'))
      }

      // Process RAW files using openlucky tool resize (no separate conversion step)
      const rawProcessings = rawFiles.map(async file => {
        const srcPath = path.join(directoryPath, file)
        const destPath = path.join(workingDirectory, file)

        if (await needsResize(srcPath)) {
          // Resize RAW image to 800px long edge directly
          const result = await resizeImage(srcPath, destPath)
          if (result.success) {
            console.log('RAW resized:', file)
            return { success: true, file }
          } else {
            console.error('Failed to resize RAW:', file)
            return { success: false, file, error: result.error }
          }
        } else {
          // Copy directly if no resize needed
          try {
            fs.copyFileSync(srcPath, destPath)
            console.log('RAW copied (no resize needed):', file)
            return { success: true, file }
          } catch (err) {
            console.error('Failed to copy RAW:', file, err.message)
            return { success: false, file, error: err.message }
          }
        }
      })

      // Wait for all RAW processings to complete
      await Promise.all(rawProcessings)

      // Create output subdirectory
      const outputDirectory = path.join(workingDirectory, 'output')
      if (!fs.existsSync(outputDirectory)) {
        fs.mkdirSync(outputDirectory, { recursive: true })
      }

      event.sender.send('working-directory-from-selected-prepared', { workingDirectory, outputDirectory, originalDirectory: directoryPath })
    } catch (error) {
      console.error('Error preparing working directory from selected:', error)
      event.sender.send('working-directory-from-selected-error', { error: error.message })
    }
  })

  // Handle get-full-res-image request
  ipcMain.on('get-full-res-image', async (event, { directoryPath, filename }) => {
    try {
      const ext = filename.toLowerCase().slice(filename.lastIndexOf('.'))
      const tiffFormats = ['.tif', '.tiff']

      let fullPath = path.join(directoryPath, filename)

      // Read .preset.json from working directory
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

      let imageUrl = `file://${fullPath}`

      // Convert tif/tiff files to jpg for browser compatibility
      if (tiffFormats.includes(ext)) {
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
  ipcMain.on('apply-preset', async (event, { inputPath, outputPath, preset }) => {
    try {
      // Construct the command
      const command = 'openlucky'
      const args = ['filmbatch', '--input', inputPath, '--output', outputPath, '--preset', preset]

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
  ipcMain.on('apply-filmparam', async (event, { inputPath, outputPath, filename, params }) => {
    try {
      // Construct the input file path
      const inputFile = path.join(inputPath, filename)

      // Construct the output file path (join output directory with filename)
      const outputFile = path.join(outputPath, filename)

      // Construct the command
      const command = 'openlucky'
      const args = ['filmparam', '--input', inputFile, '--output', outputFile, '--param', params]

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

  // Handle apply-filmparambatch request
  ipcMain.on('apply-filmparambatch', async (event, { inputPath, outputPath, params }) => {
    try {
      // Construct the command
      const command = 'openlucky'
      const args = ['filmparambatch', '--input', inputPath, '--output', outputPath, '--param', params]

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
