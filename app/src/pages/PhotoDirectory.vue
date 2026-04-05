<template>
  <div class="photo-directory-page">
    <div class="container">
      <h1 class="page-title">Select Photo Directory</h1>
      <p class="page-description">Choose a local folder containing your photos</p>

      <!-- OpenLucky installation error -->
      <div v-if="!openluckyAvailable" class="installation-error">
        ❌ The software installation is incomplete. This may be due to your antivirus software damaging the software. Please reinstall.
      </div>

      <!-- Electron environment indicator -->
      <div v-if="!isElectron" class="warning-box">
        ⚠️ Not running in Electron environment
      </div>

      <button
        @click="selectDirectory"
        class="select-button"
        :disabled="isLoading || !isElectron || !openluckyAvailable"
      >
        <span v-if="!isLoading">📁 Select Directory</span>
        <span v-else>Loading...</span>
      </button>

      <div v-if="selectedPath" class="selected-info">
        <p class="path-label">Selected Path:</p>
        <p class="path-text">{{ selectedPath }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// Check if running in Electron environment
let ipcRenderer = null
const isElectron = ref(false)
const openluckyAvailable = ref(true)
const isCheckingOpenLucky = ref(true)

onMounted(() => {
  // Multiple checks to detect Electron environment
  const isElectronEnv = window.process?.type === 'renderer' ||
                       window?.require?.('electron') ||
                       navigator.userAgent?.includes('Electron')

  isElectron.value = !!isElectronEnv

  if (isElectron.value) {
    try {
      ipcRenderer = window.require('electron').ipcRenderer
      console.log('Electron environment detected, ipcRenderer loaded')

      // Check if openlucky is available
      checkOpenLucky()
    } catch (error) {
      console.error('Failed to load electron APIs:', error)
      isElectron.value = false
    }
  } else {
    console.warn('Not running in Electron environment')
    console.warn('Please run: npm run dev (in terminal 1) && npm run electron (in terminal 2)')
  }
})

const checkOpenLucky = () => {
  ipcRenderer.send('check-openlucky')

  ipcRenderer.once('openlucky-checked', (_, result) => {
    openluckyAvailable.value = result.success
    isCheckingOpenLucky.value = false

    if (!result.success) {
      console.error('openlucky check failed:', result.error)
    }
  })
}

const selectedPath = ref('')
const isLoading = ref(false)

const selectDirectory = async () => {
  try {
    // Check if running in Electron
    if (!isElectron.value || !ipcRenderer) {
      alert('This feature requires running in Electron environment\n\nRun these commands in two terminals:\nTerminal 1: npm run dev\nTerminal 2: npm run electron')
      return
    }

    isLoading.value = true
    console.log('Sending select-directory request...')

    // Request directory selection from main process
    ipcRenderer.send('select-directory')

    // Listen for the selected directory response
    ipcRenderer.once('directory-selected', (_, result) => {
      console.log('Received directory-selected response:', result)
      selectedPath.value = result.path

      // Print to console as requested
      console.log('Selected directory:', result.path)

      // Prepare working directory from selected directory
      isLoading.value = true
      ipcRenderer.send('prepare-working-directory-from-selected', result.path)
    })

    // Handle working directory preparation success
    ipcRenderer.once('working-directory-from-selected-prepared', (_, result) => {
      console.log('Working directory prepared:', result.workingDirectory)
      console.log('Original directory:', result.originalDirectory)
      isLoading.value = false

      // Navigate to PhotoGallery page with working directory
      router.push({
        path: '/photo-gallery',
        query: {
          workingDirectory: result.workingDirectory,
          originalDirectory: result.originalDirectory
        }
      })
    })

    // Handle working directory preparation error
    ipcRenderer.once('working-directory-from-selected-error', (_, error) => {
      console.error('Error preparing working directory:', error)
      alert('Failed to prepare working directory: ' + error.error)
      isLoading.value = false
    })

    // Handle cancellation
    ipcRenderer.once('directory-cancelled', () => {
      console.log('Directory selection cancelled')
      isLoading.value = false
    })

    // Handle errors
    ipcRenderer.once('directory-error', (_, error) => {
      console.error('Directory selection error:', error)
      isLoading.value = false
    })

  } catch (error) {
    console.error('Error selecting directory:', error)
    isLoading.value = false
  }
}
</script>

<style scoped>
.photo-directory-page {
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

.container {
  text-align: center;
  max-width: 600px;
  width: 100%;
}

.page-title {
  font-size: 32px;
  color: #42b883;
  margin-bottom: 10px;
}

.page-description {
  font-size: 16px;
  color: #666;
  margin-bottom: 40px;
}

.installation-error {
  background: #f8d7da;
  border: 1px solid #dc3545;
  color: #721c24;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  font-size: 15px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.select-button {
  width: 100%;
  padding: 80px 40px;
  font-size: 24px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #42b883 0%, #35495e 100%);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.select-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.select-button:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.select-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.selected-info {
  margin-top: 40px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.path-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.path-text {
  font-size: 16px;
  color: #42b883;
  font-family: monospace;
  word-break: break-all;
}

.files-info {
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.files-count {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.files-list {
  list-style: none;
  padding: 0;
  text-align: left;
}

.file-item {
  padding: 8px 12px;
  font-size: 14px;
  color: #333;
  border-bottom: 1px solid #f0f0f0;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item.more-files {
  color: #999;
  font-style: italic;
}
</style>
