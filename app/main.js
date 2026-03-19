const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const fs = require('fs')
const path = require('path')

function createWindow () {
  // 创建浏览器窗口
  const win = new BrowserWindow({
    width: 800,
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

  // 打开开发者工具
  win.webContents.openDevTools()

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

  // Handle get-images request
  ipcMain.on('get-images', async (event, directoryPath) => {
    try {
      // Supported image extensions
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

      // Read files in the directory
      const files = fs.readdirSync(directoryPath)

      // Filter for image files only
      const imageFiles = files.filter(file => {
        const ext = file.toLowerCase().slice(file.lastIndexOf('.'))
        return imageExtensions.includes(ext) && fs.statSync(path.join(directoryPath, file)).isFile()
      })

      // Create image objects with URLs
      const images = imageFiles.map(file => {
        const fullPath = path.join(directoryPath, file)
        return {
          name: file,
          path: fullPath,
          url: `file://${fullPath}`
        }
      })

      win.webContents.send('images-loaded', {
        images: images
      })
    } catch (error) {
      console.error('Error loading images:', error)
      win.webContents.send('images-error', error.message)
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
