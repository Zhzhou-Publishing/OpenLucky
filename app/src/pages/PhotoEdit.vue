<template>
  <div class="photo-edit-page">
    <div class="header">
      <button @click="goBack" class="back-button">← Back</button>
      <h1 class="page-title">{{ currentPageTitle }}</h1>
      <div class="image-info">{{ currentFileName }}</div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading images...</p>
    </div>

    <div v-else-if="images.length === 0" class="empty-state">
      <p class="empty-icon">📷</p>
      <h2>No Images Found</h2>
      <p>No image files were found in the directory.</p>
    </div>

    <div v-else class="content">
      <!-- Large Image Display -->
      <div class="image-display">
        <img v-if="fullResImageUrl" :src="fullResImageUrl" :alt="currentImage.name" class="main-image" />
      </div>

      <!-- Operation Area -->
      <div class="operation-area">
        <NumberInput label="Mask-R" v-model="input1" :max="255" :min="0" increase-key="q" decrease-key="a" />
        <NumberInput label="Mask-G" v-model="input2" :max="255" :min="0" increase-key="w" decrease-key="s" />
        <NumberInput label="Mask-B" v-model="input3" :max="255" :min="0" increase-key="e" decrease-key="d" />
        <NumberInput label="Gamma" v-model="input4" :max="3" :min="0.1" increase-key="r" decrease-key="f"
          :large-step-value="0.1" large-step-increase-key="R" large-step-decrease-key="F" />
        <NumberInput label="Contrast" v-model="input5" :max="2" :min="0.5" increase-key="t" decrease-key="g"
          :large-step-value="0.05" large-step-increase-key="T" large-step-decrease-key="G" />
      </div>

      <!-- Thumbnail Navigation -->
      <div class="thumbnails-container">
        <div class="thumbnails-wrapper">
          <div v-for="(image, index) in images" :key="index" class="thumbnail-item"
            :class="{ active: index === currentIndex }" @click="selectImage(index)">
            <img :src="image.url" :alt="image.name" class="thumbnail" loading="lazy" />
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Toolbar Space for Future Tools -->
    <div class="bottom-toolbar"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import NumberInput from '../components/NumberInput.vue'

const router = useRouter()
const route = useRoute()

const images = ref([])
const isLoading = ref(true)
const currentIndex = ref(0)
const fullResImageUrl = ref('')
const input1 = ref(0)
const input2 = ref(0)
const input3 = ref(0)
const input4 = ref(0)
const input5 = ref(0)
const presetsData = ref({})

const workingDirectory = computed(() => route.query.workingDirectory || '')
const filename = computed(() => route.query.filename || '')

const currentFileName = computed(() => {
  if (images.value[currentIndex.value]) {
    return images.value[currentIndex.value].name
  }
  return ''
})

const currentImage = computed(() => {
  if (images.value[currentIndex.value]) {
    return images.value[currentIndex.value]
  }
  return null
})

const currentPageTitle = computed(() => {
  if (workingDirectory.value) {
    const parts = workingDirectory.value.split(/[/\\]/)
    return parts[parts.length - 1] || 'Photo Edit'
  }
  return 'Photo Edit'
})

const goBack = () => {
  router.push({
    path: '/photo-gallery',
    query: { path: workingDirectory.value }
  })
}

const selectImage = (index) => {
  currentIndex.value = index
}

const apply = () => {
  console.log('Apply changes to current image')
  // TODO: Implement apply logic
}

const applyAll = () => {
  console.log('Apply changes to all images')
  // TODO: Implement applyAll logic
}

const loadFullResImage = async () => {
  if (!currentImage.value || !workingDirectory.value) {
    fullResImageUrl.value = ''
    return
  }

  if (window.require) {
    try {
      const ipcRenderer = window.require('electron').ipcRenderer

      // Remove existing listeners to avoid duplicates
      ipcRenderer.removeAllListeners('full-res-image-loaded')
      ipcRenderer.removeAllListeners('full-res-image-error')

      ipcRenderer.send('get-full-res-image', {
        directoryPath: workingDirectory.value,
        filename: currentImage.value.name
      })

      ipcRenderer.once('full-res-image-loaded', (_, result) => {
        fullResImageUrl.value = result.url
      })

      ipcRenderer.once('full-res-image-error', (_, error) => {
        console.error('Error loading full resolution image:', error)
        fullResImageUrl.value = currentImage.value.url
      })
    } catch (error) {
      console.error('Error loading full resolution image:', error)
      fullResImageUrl.value = currentImage.value.url
    }
  } else {
    fullResImageUrl.value = currentImage.value.url
  }
}

const nextImage = () => {
  if (currentIndex.value < images.value.length - 1) {
    currentIndex.value++
  } else {
    currentIndex.value = 0
  }
}

const previousImage = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
  } else {
    currentIndex.value = images.value.length - 1
  }
}

function handleKeydown(event) {
  // Check if this is one of our navigation shortcuts
  const isNavigationShortcut = event.key === 'ArrowRight' ||
    event.key === 'ArrowLeft' ||
    event.key === '[' ||
    event.key === ']' ||
    event.key === 'Enter'

  // If it's not a navigation shortcut and the target is an input/textarea, don't process
  if (!isNavigationShortcut && (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA')) {
    return
  }

  switch (event.key) {
    case 'Enter':
      event.preventDefault()
      if (event.ctrlKey) {
        applyAll()
      } else {
        apply()
      }
      break
    case 'ArrowRight':
    case ']':
      event.preventDefault()
      nextImage()
      break
    case 'ArrowLeft':
    case '[':
      event.preventDefault()
      previousImage()
      break
  }
}

const loadImages = async () => {
  try {
    isLoading.value = true
    fullResImageUrl.value = ''
    if (!workingDirectory.value) {
      goBack()
      return
    }

    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      ipcRenderer.send('get-images', workingDirectory.value, workingDirectory.value)

      ipcRenderer.once('images-loaded', (_, result) => {
        images.value = result.images
        if (filename.value) {
          const index = result.images.findIndex(img => img.name === filename.value)
          if (index !== -1) {
            currentIndex.value = index
          }
        }
        isLoading.value = false
      })

      ipcRenderer.once('images-error', (_, error) => {
        console.error('Error loading images:', error)
        isLoading.value = false
      })
    } else {
      console.warn('Not running in Electron, showing demo data')
      isLoading.value = false
    }
  } catch (error) {
    console.error('Error loading images:', error)
    isLoading.value = false
  }
}

const loadPresets = async () => {
  try {
    if (!workingDirectory.value || !window.require) {
      return
    }

    const ipcRenderer = window.require('electron').ipcRenderer

    ipcRenderer.send('read-preset-json', workingDirectory.value)

    ipcRenderer.once('preset-json-loaded', (_, result) => {
      presetsData.value = result.presets
      loadPresetForCurrentImage()
    })

    ipcRenderer.once('preset-json-error', (_, error) => {
      console.error('Error loading preset json:', error)
    })
  } catch (error) {
    console.error('Error loading preset json:', error)
  }
}

const loadPresetForCurrentImage = () => {
  if (!currentFileName.value || !presetsData.value) {
    return
  }

  const preset = presetsData.value[currentFileName.value]
  if (preset) {
    input1.value = preset.mask_r || 0
    input2.value = preset.mask_g || 0
    input3.value = preset.mask_b || 0
    input4.value = preset.gamma || 0
    input5.value = preset.contrast || 0
  } else {
    // Reset to default if no preset found
    input1.value = 0
    input2.value = 0
    input3.value = 0
    input4.value = 0
    input5.value = 0
  }
}

watch(currentIndex, () => {
  loadFullResImage()
  loadPresetForCurrentImage()
})

watch(images, () => {
  if (images.value.length > 0) {
    loadFullResImage()
    loadPresetForCurrentImage()
  }
})

onMounted(() => {
  loadImages()
  loadPresets()
  window.addEventListener('keydown', handleKeydown)
  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.send('set-window-resizable', true)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.send('set-window-resizable', false)
  }
})
</script>

<style scoped>
.photo-edit-page {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.back-button {
  padding: 10px 20px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s ease;
}

.back-button:hover {
  background: #35a372;
}

.page-title {
  font-size: 20px;
  color: #333;
  margin: 0;
  flex: 1;
  text-align: center;
}

.image-info {
  font-size: 14px;
  color: #666;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #666;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #42b883;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 16px;
  color: #666;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.image-display {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: hidden;
  width: 90%;
  margin: 0 auto;
}

.main-image {
  width: 100%;
  max-height: 50vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.operation-area {
  display: flex;
  gap: 16px;
  justify-content: center;
  padding: 16px;
  background: white;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.thumbnails-container {
  height: 100px;
  background: white;
  border-top: 1px solid #e0e0e0;
  overflow-x: auto;
  overflow-y: hidden;
  flex-shrink: 0;
}

.thumbnails-wrapper {
  display: flex;
  gap: 12px;
  padding: 10px 16px;
  height: 100%;
  align-items: center;
}

.thumbnail-item {
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.thumbnail-item:hover {
  transform: scale(1.05);
}

.thumbnail-item.active {
  border-color: #42b883;
  box-shadow: 0 0 0 2px rgba(66, 184, 131, 0.3);
}

.thumbnail {
  width: 80px;
  height: 80px;
  object-fit: cover;
  display: block;
}

.bottom-toolbar {
  height: 80px;
  background: white;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}
</style>
