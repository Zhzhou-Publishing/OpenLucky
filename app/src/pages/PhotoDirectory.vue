<template>
  <div class="photo-directory-page">
    <div class="container">
      <h1 class="page-title">{{ $t('photoDirectory.title') }}</h1>
      <p class="page-description">{{ $t('photoDirectory.description') }}</p>

      <!-- OpenLucky installation error (always occupies space) -->
      <div class="installation-error" :class="{ hidden: openluckyAvailable }">
        {{ $t('photoDirectory.installationError') }}
      </div>

      <!-- Electron environment indicator (always occupies space) -->
      <div class="warning-box" :class="{ hidden: isElectron }">
        {{ $t('photoDirectory.electronWarning') }}
      </div>

      <button
        @click="selectDirectory"
        class="select-button"
        :disabled="isLoading || !isElectron || !openluckyAvailable"
      >
        <span v-if="!isLoading">{{ $t('photoDirectory.selectButton') }}</span>
        <span v-else>{{ $t('photoDirectory.loading') }}</span>
      </button>

      <div class="selected-info" :class="{ hidden: !selectedPath && !processingProgress }">
        <p class="path-label">{{ processingProgress ? $t('photoDirectory.processingProgress') : $t('photoDirectory.selectedPath') }}</p>
        <p class="path-text">{{ processingProgress || selectedPath }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchPresets } from '../utils/presetCache'

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

      // Pre-load preset list so PhotoGallery can show it immediately
      fetchPresets().catch(() => {})
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
const processingProgress = ref('')

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
      console.log('Output directory:', result.outputDirectory)
      console.log('Original directory:', result.originalDirectory)
      isLoading.value = false

      // Navigate to PhotoGallery page with working directory
      router.push({
        path: '/photo-gallery',
        query: {
          workingDirectory: result.workingDirectory,
          outputDirectory: result.outputDirectory,
          originalDirectory: result.originalDirectory
        }
      })
    })

    // Handle window title update
    ipcRenderer.on('window-title-update', (_, { title }) => {
      document.title = title
    })

    // Handle processing progress update
    ipcRenderer.on('processing-progress-update', (_, { progress }) => {
      processingProgress.value = progress
    })

    // Handle processing progress clear
    ipcRenderer.on('processing-progress-clear', () => {
      processingProgress.value = ''
    })

    // Handle window title restore
    ipcRenderer.on('window-title-restore', () => {
      document.title = 'OpenLucky Desktop App'
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
  padding: 30vh 20px 40px;
  display: flex;
  justify-content: center;
  min-height: 100vh;
}

.container {
  text-align: center;
  max-width: 600px;
  width: 100%;
}

.page-title {
  font-size: 32px;
  color: var(--accent);
  margin-bottom: 10px;
}

.page-description {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.installation-error {
  background: #f8d7da;
  border: 1px solid #dc3545;
  color: #721c24;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  font-size: 15px;
  box-shadow: 0 2px 4px var(--shadow);
}

.installation-error.hidden {
  margin: 0;
  padding: 0;
  border: none;
  max-height: 0;
  overflow: hidden;
}

.warning-box {
  background: #fff3cd;
  border: 1px solid #ffc107;
  color: #856404;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  font-size: 15px;
  box-shadow: 0 2px 4px var(--shadow);
}

.warning-box.hidden {
  margin: 0;
  padding: 0;
  border: none;
  max-height: 0;
  overflow: hidden;
}

.select-button {
  width: 100%;
  padding: 40px;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-on-accent);
  background: linear-gradient(135deg, #42b883 0%, #35495e 100%);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px var(--shadow);
}

.select-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px var(--shadow);
}

.select-button:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 4px var(--shadow);
}

.select-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.selected-info {
  margin-top: 40px;
  padding: 20px;
  background: var(--bg-surface);
  border-radius: 8px;
  box-shadow: 0 2px 4px var(--shadow);
}

.selected-info.hidden {
  margin: 0;
  padding: 0;
  border: none;
  max-height: 0;
  overflow: hidden;
}

.path-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.path-text {
  font-size: 16px;
  color: var(--accent);
  font-family: monospace;
  word-break: break-all;
}

.files-info {
  margin-top: 20px;
  padding: 20px;
  background: var(--bg-surface);
  border-radius: 8px;
  box-shadow: 0 2px 4px var(--shadow);
}

.files-count {
  font-size: 14px;
  color: var(--text-secondary);
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
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
}

.file-item:last-child {
  border-bottom: none;
}

.file-item.more-files {
  color: var(--text-tertiary);
  font-style: italic;
}
</style>
