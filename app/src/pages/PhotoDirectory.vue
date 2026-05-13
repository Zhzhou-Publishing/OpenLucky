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
        @click="onButtonClick"
        class="select-button"
        :class="{ loading: isLoading }"
        :disabled="!isElectron || !openluckyAvailable"
        @mouseenter="isHoveringButton = true"
        @mouseleave="isHoveringButton = false"
      >
        <template v-if="!isLoading">
          <span class="btn-text">{{ $t('photoDirectory.selectButton') }}</span>
        </template>
        <template v-else>
          <span v-if="isHoveringButton" class="btn-text">{{ $t('photoDirectory.cancel') }}</span>
          <span v-else class="btn-progress">{{ processingProgress }}</span>
        </template>
      </button>

      <!-- Compress preview toggle -->
      <div class="compress-toggle">
        <CapsuleSwitch v-model="compressPreview" :disabled="isLoading" />
        <span class="compress-label">{{ $t('photoDirectory.compressPreview') }}</span>
        <Popover :text="$t('photoDirectory.compressPreviewTip')" />
      </div>
    </div>

    <Modal
      v-model="showLangMismatch"
      :save-label="`${systemLabels.yes} ${currentLabels.yes}`"
      :cancel-label="`${systemLabels.no} ${currentLabels.no}`"
      :extra-label="`${systemLabels.dontRemind} ${currentLabels.dontRemind}`"
      @save="onAcceptSystemLanguage"
      @cancel="onDeclineSystemLanguage"
      @extra="onSilenceSystemLanguage"
    >
      <p class="lang-mismatch-line">{{ systemLabels.message }}</p>
      <p class="lang-mismatch-line lang-mismatch-line-secondary">{{ currentLabels.message }}</p>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchPresets } from '../utils/presetCache'
import CapsuleSwitch from '../components/CapsuleSwitch.vue'
import Popover from '../components/Popover.vue'
import Modal from '../components/Modal.vue'
import { createRendererLogger } from '../utils/rendererLogger'
import { detectSystemLocale, SUPPORTED_LOCALES } from '../i18n'

const logger = createRendererLogger('PhotoDirectory')

const router = useRouter()
const { locale, messages } = useI18n({ useScope: 'global' })

const systemLocale = ref(detectSystemLocale())
const showLangMismatch = ref(false)

const fallbackLabels = { message: '', yes: 'Yes', no: 'No' }

const currentLabels = computed(() => {
  const dict = messages.value?.[locale.value]?.languageMismatch
  return dict || fallbackLabels
})

const systemLabels = computed(() => {
  const dict = messages.value?.[systemLocale.value]?.languageMismatch
  return dict || fallbackLabels
})

const languageFamily = (loc) => String(loc).split('_')[0]

function checkLanguageMismatch() {
  const system = systemLocale.value
  if (!SUPPORTED_LOCALES.includes(system)) return
  if (system === locale.value) return
  if (languageFamily(system) === languageFamily(locale.value)) return

  if (localStorage.getItem('localeMismatchSilenced') === '1') return
  if (sessionStorage.getItem('localeMismatchDismissedSession') === '1') return

  showLangMismatch.value = true
}

function onAcceptSystemLanguage() {
  locale.value = systemLocale.value
  localStorage.setItem('locale', systemLocale.value)
  localStorage.removeItem('localeMismatchSilenced')
  sessionStorage.removeItem('localeMismatchDismissedSession')
  showLangMismatch.value = false
}

function onDeclineSystemLanguage() {
  sessionStorage.setItem('localeMismatchDismissedSession', '1')
  showLangMismatch.value = false
}

function onSilenceSystemLanguage() {
  localStorage.setItem('localeMismatchSilenced', '1')
  showLangMismatch.value = false
}

// Check if running in Electron environment
let ipcRenderer = null
const isElectron = ref(false)
const openluckyAvailable = ref(true)
const isCheckingOpenLucky = ref(true)

onMounted(() => {
  checkLanguageMismatch()

  // Multiple checks to detect Electron environment
  const isElectronEnv = window.process?.type === 'renderer' ||
                       window?.require?.('electron') ||
                       navigator.userAgent?.includes('Electron')

  isElectron.value = !!isElectronEnv

  if (isElectron.value) {
    try {
      ipcRenderer = window.require('electron').ipcRenderer
      logger.debug('Electron environment detected, ipcRenderer loaded')

      // Check if openlucky is available
      checkOpenLucky()

      // Pre-load preset list so PhotoGallery can show it immediately
      fetchPresets().catch(() => {})
    } catch (error) {
      logger.error('Failed to load electron APIs:', error)
      isElectron.value = false
    }
  } else {
    logger.warn('Not running in Electron environment')
    logger.warn('Please run: npm run dev (in terminal 1) && npm run electron (in terminal 2)')
  }
})

const checkOpenLucky = () => {
  ipcRenderer.send('check-openlucky')

  ipcRenderer.once('openlucky-checked', (_, result) => {
    openluckyAvailable.value = result.success
    isCheckingOpenLucky.value = false

    if (!result.success) {
      logger.error('openlucky check failed:', result.error)
    }
  })
}

const selectedPath = ref('')
const isLoading = ref(false)
const processingProgress = ref('')
const compressPreview = ref(false)
const isHoveringButton = ref(false)

const onButtonClick = () => {
  if (isLoading.value) {
    cancelLoading()
  } else {
    selectDirectory()
  }
}

const cancelLoading = () => {
  if (ipcRenderer) {
    ipcRenderer.send('cancel-processing')
  }
  isLoading.value = false
  processingProgress.value = ''
}

const selectDirectory = async () => {
  try {
    // Check if running in Electron
    if (!isElectron.value || !ipcRenderer) {
      alert('This feature requires running in Electron environment\n\nRun these commands in two terminals:\nTerminal 1: npm run dev\nTerminal 2: npm run electron')
      return
    }

    isLoading.value = true
    logger.info('Sending select-directory request...')

    // Request directory selection from main process
    ipcRenderer.send('select-directory')

    // Listen for the selected directory response
    ipcRenderer.once('directory-selected', (_, result) => {
      logger.info('Received directory-selected response:', result)
      selectedPath.value = result.path

      // Print to console as requested
      logger.info('Selected directory:', result.path)

      // Prepare working directory from selected directory
      isLoading.value = true
      ipcRenderer.send('prepare-working-directory-from-selected', result.path, { compressPreview: compressPreview.value })
    })

    // Handle working directory preparation success
    ipcRenderer.once('working-directory-from-selected-prepared', (_, result) => {
      logger.info('Working directory prepared:', result.workingDirectory)
      logger.info('Output directory:', result.outputDirectory)
      logger.info('Original directory:', result.originalDirectory)
      isLoading.value = false

      // Navigate to PhotoGallery page with working directory
      router.push({
        path: '/photo-gallery',
        query: {
          workingDirectory: result.workingDirectory,
          outputDirectory: result.outputDirectory,
          originalDirectory: result.originalDirectory,
          compressPreview: compressPreview.value ? '1' : ''
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
      logger.error('Error preparing working directory:', error)
      alert('Failed to prepare working directory: ' + error.error)
      isLoading.value = false
    })

    // Handle cancellation
    ipcRenderer.once('directory-cancelled', () => {
      logger.info('Directory selection cancelled')
      isLoading.value = false
    })

    // Handle errors
    ipcRenderer.once('directory-error', (_, error) => {
      logger.error('Directory selection error:', error)
      isLoading.value = false
    })

  } catch (error) {
    logger.error('Error selecting directory:', error)
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

.compress-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 24px 0;
}

.compress-label {
  font-size: 15px;
  color: var(--text-primary);
}

.select-button {
  width: 100%;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 40px;
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

.select-button.loading {
  opacity: 1;
  cursor: default;
}

.select-button.loading:hover {
  cursor: pointer;
  background: linear-gradient(135deg, #f5a623 0%, #cc7000 100%);
  color: #fff;
}

.btn-text {
  font-size: 24px;
  font-weight: 600;
}

.btn-progress {
  font-size: 16px;
  font-weight: 400;
  font-family: monospace;
  word-break: break-all;
  text-align: center;
  line-height: 1.5;
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

.lang-mismatch-line {
  font-size: 15px;
  color: var(--text-primary);
  line-height: 1.5;
  margin: 0;
}

.lang-mismatch-line + .lang-mismatch-line {
  margin-top: 10px;
}

.lang-mismatch-line-secondary {
  color: var(--text-secondary);
}
</style>
