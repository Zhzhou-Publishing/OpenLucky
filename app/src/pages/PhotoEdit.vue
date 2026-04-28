<template>
  <div class="photo-edit-page">
    <div class="header">
      <button @click="goBack" class="back-button">{{ $t('photoEdit.back') }}</button>
      <h1 class="page-title">{{ currentPageTitle }}</h1>
      <div class="image-info">{{ currentFileName }}</div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ $t('photoEdit.loading') }}</p>
    </div>

    <div v-else-if="images.length === 0" class="empty-state">
      <p class="empty-icon">📷</p>
      <h2>{{ $t('photoEdit.noImages') }}</h2>
      <p>{{ $t('photoEdit.noImagesDesc') }}</p>
    </div>

    <div v-else class="content">
      <!-- Thumbnail Navigation - Left Side -->
      <div class="thumbnails-container">
        <div class="thumbnails-wrapper">
          <div v-for="(image, index) in images" :key="image.name" class="thumbnail-item"
            :class="{ active: index === currentIndex, affected: affectedImages.has(image.name), 'cursor-wait': isAllImagesAffected }"
            @click="!isAllImagesAffected && selectImage(index)">
            <img :src="getImageUrlWithTimestamp(image)" :alt="image.name" class="thumbnail" loading="lazy" />
            <div v-if="affectedImages.has(image.name)" class="thumbnail-overlay">
              <div class="thumbnail-spinner"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Content Area - Right Side -->
      <div class="main-content">
        <!-- Large Image Display -->
        <div class="image-display" :style="{ height: imageDisplayHeight }">
          <div class="image-wrapper">
            <img v-if="fullResImageUrl" :src="fullResImageUrl" :alt="currentImage.name" class="main-image" />
            <div v-if="isCurrentImageAffected" class="applying-badge">{{ $t('photoEdit.applying') }}</div>
            <!-- Rotate buttons -->
            <div class="rotate-controls">
              <button @click="rotateCounterClockwiseBtn" class="rotate-button rotate-counterclockwise-btn"
                :disabled="isAllImagesAffected || isCurrentImageAffected" title="Rotate counter-clockwise">
                ↺
              </button>
              <button @click="rotateClockwiseBtn" class="rotate-button rotate-clockwise-btn"
                :disabled="isAllImagesAffected || isCurrentImageAffected" title="Rotate clockwise">
                ↻
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Operation Area - Fixed at Page Bottom -->
      <div ref="operationAreaRef" class="operation-area">
        <Tabs :tabs="[
          { id: 'basic', label: $t('photoEdit.basicTab') },
          { id: 'dye_concentration_correction', label: $t('photoEdit.advancedTab') }
        ]" :default-tab="'basic'" @tab-change="handleTabChange">
          <template #default="{ activeTab }">
            <!-- Basic Parameters Tab -->
            <div v-if="activeTab === 'basic'" class="tab-content">
              <NumberInput :label="$t('photoEdit.maskR')" v-model="input1" :max="255" :min="0" increase-key="Q"
                decrease-key="A" :disabled="isAllImagesAffected || isCurrentImageAffected"
                @keydown="handleInputKeydown" />
              <NumberInput :label="$t('photoEdit.maskG')" v-model="input2" :max="255" :min="0" increase-key="W"
                decrease-key="S" :disabled="isAllImagesAffected || isCurrentImageAffected"
                @keydown="handleInputKeydown" />
              <NumberInput :label="$t('photoEdit.maskB')" v-model="input3" :max="255" :min="0" increase-key="E"
                decrease-key="D" :disabled="isAllImagesAffected || isCurrentImageAffected"
                @keydown="handleInputKeydown" />
              <NumberInput :label="$t('photoEdit.gamma')" v-model="input4" :max="5" :min="0.01" increase-key="R"
                decrease-key="F" :step-value="0.01" :large-step-value="0.1" large-step-increase-key="Alt + Shift + R"
                large-step-decrease-key="Alt + Shift + F" :disabled="isAllImagesAffected || isCurrentImageAffected"
                @keydown="handleInputKeydown" />
              <NumberInput :label="$t('photoEdit.contrast')" v-model="input5" :max="2" :min="0.5" increase-key="T"
                decrease-key="G" :step-value="0.01" :large-step-value="0.05" large-step-increase-key="Alt + Shift + T"
                large-step-decrease-key="Alt + Shift + G" :disabled="isAllImagesAffected || isCurrentImageAffected"
                @keydown="handleInputKeydown" />
            </div>

            <!-- Advanced Parameters Tab -->
            <div v-if="activeTab === 'dye_concentration_correction'" class="tab-content">
              <NumberInput :label="$t('photoEdit.contrastR')" v-model="contrastR" :max="2" :min="0.5" :step-value="0.01"
                :disabled="isAllImagesAffected || isCurrentImageAffected" @keydown="handleInputKeydown" />
              <NumberInput :label="$t('photoEdit.contrastG')" v-model="contrastG" :max="2" :min="0.5" :step-value="0.01"
                :disabled="isAllImagesAffected || isCurrentImageAffected" @keydown="handleInputKeydown" />
              <NumberInput :label="$t('photoEdit.contrastB')" v-model="contrastB" :max="2" :min="0.5" :step-value="0.01"
                :disabled="isAllImagesAffected || isCurrentImageAffected" @keydown="handleInputKeydown" />
            </div>

            <!-- Common Action Buttons -->
            <div class="action-buttons">
              <button @click="apply" class="apply-button" title="Enter" style="display: none;"
                :disabled="isAllImagesAffected || isCurrentImageAffected">{{ $t('photoEdit.apply') }}</button>
              <button @click="applyAll" class="apply-all-button" title="CTRL + Enter" :disabled="isAllImagesAffected">{{
                $t('photoEdit.applyAll') }}</button>
              <SaveAllButton :is-disabled="isAllImagesAffected" @click="saveAll" />
            </div>
          </template>
        </Tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import NumberInput from '../components/NumberInput.vue'
import SaveAllButton from '../components/SaveAllButton.vue'
import Tabs from '../components/Tabs.vue'
import { setSaveAllClicked, getSaveAllClicked } from '../utils/globalState'

// Get path module for Electron environment
const path = window.require ? window.require('path') : { basename: (p) => p }

// Debounce utility function
function debounce(fn, delay) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
      timer = null
    }, delay)
  }
}

const router = useRouter()
const route = useRoute()

const images = ref([])
const isLoading = ref(true)
const affectedImages = reactive(new Set())
const currentIndex = ref(0)
const fullResImageUrl = ref('')
const input1 = ref(0)
const input2 = ref(0)
const input3 = ref(0)
const input4 = ref(0)
const input5 = ref(0)
const contrastR = ref(1.0)
const contrastG = ref(1.0)
const contrastB = ref(1.0)
const presetsData = ref({})
const operationAreaRef = ref(null)
const operationAreaHeight = ref(80) // 默认值
const previousImageDimensions = ref({ width: 6000, height: 4000 })
const presetLoaded = ref(false)
const rotateClockwiseMap = ref({}) // Store rotation for each image

const workingDirectory = computed(() => route.query.workingDirectory || '')
const outputDirectory = computed(() => route.query.outputDirectory || '')
const originalDirectory = computed(() => route.query.originalDirectory || '')
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

const currentRotateClockwise = computed(() => {
  if (currentImage.value) {
    return rotateClockwiseMap.value[currentImage.value.name] || 0
  }
  return 0
})

const isCurrentImageAffected = computed(() => {
  if (!currentImage.value) return false
  return affectedImages.has(currentImage.value.name)
})

const isAllImagesAffected = computed(() => {
  return images.value.length > 0 && images.value.every(img => affectedImages.has(img.name))
})

const currentPageTitle = computed(() => {
  if (originalDirectory.value) {
    const parts = originalDirectory.value.split(/[/\\]/)
    return parts[parts.length - 1] || 'Photo Edit'
  }
  return 'Photo Edit'
})

const imageDisplayHeight = computed(() => {
  return `calc(100vh - 64px - 80px - ${operationAreaHeight.value}px)`
})

const updateOperationAreaHeight = () => {
  if (operationAreaRef.value) {
    operationAreaHeight.value = operationAreaRef.value.offsetHeight
  }
}

const handleTabChange = (tabId) => {
  console.log('Tab changed to:', tabId)
  // 切换标签页后重新计算高度
  setTimeout(updateOperationAreaHeight, 100)
}

const goBack = () => {
  router.push({
    path: '/photo-gallery',
    query: {
      workingDirectory: workingDirectory.value,
      originalDirectory: originalDirectory.value
    }
  })
}

const selectImage = (index) => {
  currentIndex.value = index
}

const rotateClockwiseBtn = () => {
  if (!currentImage.value) return
  const imageName = currentImage.value.name
  let currentAngle = rotateClockwiseMap.value[imageName] || 0
  let newAngle = (currentAngle + 90) % 360
  if (newAngle === 360) newAngle = 0
  rotateClockwiseMap.value[imageName] = newAngle
  applyPreview()
}

const rotateCounterClockwiseBtn = () => {
  if (!currentImage.value) return
  const imageName = currentImage.value.name
  let currentAngle = rotateClockwiseMap.value[imageName] || 0
  let newAngle = currentAngle - 90
  if (newAngle < 0) newAngle = newAngle + 360
  rotateClockwiseMap.value[imageName] = newAngle
  applyPreview()
}

// Helper function to trigger Vue reactivity for images array
const triggerImagesReactivity = () => {
  // Push pop operation to trigger Vue's reactivity system
  const temp = images.value[images.value.length - 1]
  images.value.push(temp)
  images.value.pop()
}

// Helper function to get image URL with timestamp
const getImageUrlWithTimestamp = (image) => {
  // Use image's own timestamp if available, otherwise use current time
  const timestamp = image.timestamp || Date.now()

  // Check if URL already has a 't' parameter
  const urlParts = image.url.split('?')
  if (urlParts.length > 1) {
    // URL already has query parameters
    const baseUrl = urlParts[0]
    const queryString = urlParts[1]
    const params = new URLSearchParams(queryString)

    // Update the 't' parameter
    params.set('t', timestamp)
    return baseUrl + '?' + params.toString()
  } else {
    // URL has no query parameters, add 't' parameter
    return image.url + '?t=' + timestamp
  }
}

// Helper function to update image timestamp and trigger reactivity
const updateImageTimestamp = (imageName) => {
  const imageIndex = images.value.findIndex(img => img.name === imageName)
  if (imageIndex !== -1) {
    // Update the specific image's timestamp
    images.value[imageIndex].timestamp = Date.now()
    // Trigger Vue's reactivity system
    triggerImagesReactivity()
  }
}

const apply = () => {
  if (!currentImage.value || !workingDirectory.value) {
    console.error('No current image or working directory')
    return
  }

  if (!window.require) {
    console.error('Not running in Electron')
    return
  }

  // Reset global isSaveAllClicked state
  setSaveAllClicked(false)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    const imageName = currentImage.value.name;

    // Construct parameters string: "mask_r,mask_g,mask_b,gamma,contrast,contrast_r,contrast_g,contrast_b"
    const params = `${input1.value},${input2.value},${input3.value},${input4.value},${input5.value},${contrastR.value},${contrastG.value},${contrastB.value}`

    // Mark image as affected to disable controls
    affectedImages.add(imageName)

    // Send request to main process
    ipcRenderer.send('apply-filmparam', {
      inputPath: workingDirectory.value,
      outputPath: outputDirectory.value,
      filename: imageName,
      params: params,
      rotateClockwise: currentRotateClockwise.value
    })

    // Handle response
    ipcRenderer.once('filmparam-apply-started', (_, result) => {
      console.log(result.message)
    })

    ipcRenderer.once('filmparam-apply-progress', (_, result) => {
      console.log(result.data)
    })

    // 使用一个命名的函数，方便处理逻辑
    const handleResponse = (_, result) => {
      // 关键：由于是全局频道，所有的 apply 请求都会触发这个 handleResponse
      // 我们必须判断返回的结果是不是当前这张图
      // result.outputFile 是完整路径，需要从中提取文件名
      const resultFilename = result.outputFile ? path.basename(result.outputFile) : null
      console.log(`resultFilename:${resultFilename}    result.outputFile:${result.outputFile}    imageName:${imageName}`)
      if (resultFilename === imageName || result.outputFile?.includes(imageName)) {
        updateImageTimestamp(imageName);
        loadFullResImage();
        loadPresets();
        affectedImages.delete(imageName);

        // 处理完自己的事情后，移除这个特定的监听器
        ipcRenderer.removeListener('filmparam-apply-success', handleResponse);
      }
    };
    ipcRenderer.on('filmparam-apply-success', handleResponse);

    const handleError = (_, error) => {
      console.error('Error applying film parameters:', error);
      // 关键：同样要判断是不是当前这张图的错误
      // error.outputFile 是完整路径，需要从中提取文件名
      const errorFilename = error.outputFile ? path.basename(error.outputFile) : null
      if (errorFilename === imageName || error.outputFile?.includes(imageName)) {
        // Re-enable controls immediately on error
        affectedImages.delete(imageName);
        // 处理完自己的事情后，移除这个特定的监听器
        ipcRenderer.removeListener('filmparam-apply-error', handleError);
      }
    };
    ipcRenderer.on('filmparam-apply-error', handleError);
  } catch (error) {
    // Re-enable controls immediately on error
    affectedImages.delete(imageName);
  }
}

const applyPreview = () => {
  if (!currentImage.value || !workingDirectory.value) {
    console.error('No current image or working directory')
    return
  }

  if (!window.require) {
    console.error('Not running in Electron')
    return
  }

  // Reset global isSaveAllClicked state
  setSaveAllClicked(false)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    const imageName = currentImage.value.name;

    // Construct parameters string: "mask_r,mask_g,mask_b,gamma,contrast,contrast_r,contrast_g,contrast_b"
    const params = `${input1.value},${input2.value},${input3.value},${input4.value},${input5.value},${contrastR.value},${contrastG.value},${contrastB.value}`

    // Mark image as affected to disable controls
    affectedImages.add(imageName)

    // Send request to main process
    ipcRenderer.send('apply-filmparam', {
      inputPath: workingDirectory.value,
      outputPath: outputDirectory.value,
      filename: imageName,
      params: params,
      rotateClockwise: currentRotateClockwise.value
    })

    // Handle response
    ipcRenderer.once('filmparam-apply-started', (_, result) => {
      console.log(result.message)
    })

    ipcRenderer.once('filmparam-apply-progress', (_, result) => {
      console.log(result.data)
    })

    // 使用一个命名的函数，方便处理逻辑
    const handleResponse = (_, result) => {
      // 关键：由于是全局频道，所有的 apply 请求都会触发这个 handleResponse
      // 我们必须判断返回的结果是不是当前这张图
      // result.outputFile 是完整路径，需要从中提取文件名
      const resultFilename = result.outputFile ? path.basename(result.outputFile) : null
      console.log(`resultFilename:${resultFilename}    result.outputFile:${result.outputFile}    imageName:${imageName}`)
      if (resultFilename === imageName || result.outputFile?.includes(imageName)) {
        updateImageTimestamp(imageName);
        loadFullResImage();
        loadPresets();
        affectedImages.delete(imageName);

        // 处理完自己的事情后，移除这个特定的监听器
        ipcRenderer.removeListener('filmparam-apply-success', handleResponse);
      }
    };
    ipcRenderer.on('filmparam-apply-success', handleResponse);

    const handleError = (_, error) => {
      console.error('Error applying film parameters:', error);
      // 关键：同样要判断是不是当前这张图的错误
      // error.outputFile 是完整路径，需要从中提取文件名
      const errorFilename = error.outputFile ? path.basename(error.outputFile) : null
      if (errorFilename === imageName || error.outputFile?.includes(imageName)) {
        affectedImages.delete(imageName);
        // 处理完自己的事情后，移除这个特定的监听器
        ipcRenderer.removeListener('filmparam-apply-error', handleError);
      }
    };
    ipcRenderer.on('filmparam-apply-error', handleError);
  } catch (error) {
    affectedImages.delete(imageName);
  }
}

const applyAll = () => {
  if (!workingDirectory.value) {
    console.error('No working directory')
    return
  }

  if (!window.require) {
    console.error('Not running in Electron')
    return
  }

  // Reset global isSaveAllClicked state
  setSaveAllClicked(false)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    // Construct parameters string: "mask_r,mask_g,mask_b,gamma,contrast"
    const params = `${input1.value},${input2.value},${input3.value},${input4.value},${input5.value}`

    // Mark all images as affected to disable controls
    images.value.forEach(img => affectedImages.add(img.name))

    // Remove existing listeners to avoid duplicates
    ipcRenderer.removeAllListeners('filmparambatch-apply-started')
    ipcRenderer.removeAllListeners('filmparambatch-apply-progress')
    ipcRenderer.removeAllListeners('filmparambatch-apply-success')
    ipcRenderer.removeAllListeners('filmparambatch-apply-error')

    // Send request to main process
    ipcRenderer.send('apply-filmparambatch', {
      inputPath: workingDirectory.value,
      outputPath: outputDirectory.value,
      params: params,
      rotateClockwise: currentRotateClockwise.value
    })

    // Handle response
    ipcRenderer.once('filmparambatch-apply-started', (_, result) => {
      console.log(result.message)
    })

    ipcRenderer.once('filmparambatch-apply-progress', (_, result) => {
      console.log(result.data)
    })

    ipcRenderer.once('filmparambatch-apply-success', (_, result) => {
      console.log(result.message)
      // Update all image timestamps to refresh display without reloading page
      images.value.forEach(img => {
        img.timestamp = Date.now()
      })
      triggerImagesReactivity()
      loadFullResImage()
      // Reload presets and enable controls
      loadPresets()
      affectedImages.clear()
    })

    ipcRenderer.once('filmparambatch-apply-error', (_, error) => {
      console.error('Error applying film parameters to all images:', error)
      // Re-enable controls immediately on error
      affectedImages.clear()
    })
  } catch (error) {
    console.error('Error applying film parameters to all images:', error)
    // Re-enable controls immediately on error
    affectedImages.clear()
  }
}

const saveAll = () => {
  if (!workingDirectory.value || !originalDirectory.value) {
    console.error('No working directory or original directory')
    return
  }

  if (!window.require) {
    console.error('Not running in Electron')
    return
  }

  // Set global isSaveAllClicked state
  setSaveAllClicked(true)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    // Mark all images as affected to disable controls
    images.value.forEach(img => affectedImages.add(img.name))

    // Remove existing listeners to avoid duplicates
    ipcRenderer.removeAllListeners('preset-to-batch-started')
    ipcRenderer.removeAllListeners('preset-to-batch-progress')
    ipcRenderer.removeAllListeners('preset-to-batch-success')
    ipcRenderer.removeAllListeners('preset-to-batch-error')

    // Prepare the output directory path
    const outputDir = path.join(originalDirectory.value, 'output')

    // Send request to main process
    ipcRenderer.send('apply-preset-to-batch', {
      presetFile: path.join(workingDirectory.value, '.preset.json'),
      inputDir: originalDirectory.value,
      outputDir: outputDir
    })

    // Handle started
    ipcRenderer.once('preset-to-batch-started', (_, result) => {
      console.log(result.message)
    })

    // Handle progress
    ipcRenderer.on('preset-to-batch-progress', (_, result) => {
      console.log(result.data)
    })

    // Handle success
    ipcRenderer.once('preset-to-batch-success', (_, result) => {
      console.log(result.message)
      // Update all image timestamps to refresh display without reloading page
      images.value.forEach(img => {
        img.timestamp = Date.now()
      })
      triggerImagesReactivity()
      affectedImages.clear()
    })

    // Handle error
    ipcRenderer.once('preset-to-batch-error', (_, result) => {
      console.error('Error saving all files:', result.message, result.error)
      affectedImages.clear()
    })
  } catch (error) {
    console.error('Error saving all files:', error)
    affectedImages.clear()
  }
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
        fullResImageUrl.value = result.url + '?t=' + Date.now()
      })

      ipcRenderer.once('full-res-image-error', (_, error) => {
        console.error('Error loading full resolution image:', error)
        // Check if this is a RAW file not yet converted
        if (currentImage.value.isRaw && error.error === 'RAW file not yet converted') {
          // Show placeholder for RAW file still converting
          const width = previousImageDimensions.value.width
          const height = previousImageDimensions.value.height
          const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
            <rect width="${width}" height="${height}" fill="#cccccc"/>
            <text x="${width / 2}" y="${height / 2}" font-family="Arial, sans-serif" font-size="24" text-anchor="middle" fill="#666666">RAW file converting...</text>
          </svg>`
          fullResImageUrl.value = 'data:image/svg+xml;base64,' + btoa(svg)
        } else {
          fullResImageUrl.value = currentImage.value.url + '?t=' + Date.now()
        }
      })
    } catch (error) {
      console.error('Error loading full resolution image:', error)
      fullResImageUrl.value = currentImage.value.url
    }
  } else {
    fullResImageUrl.value = currentImage.value.url + '?t=' + Date.now()
  }
}

const nextImage = () => {
  if (isAllImagesAffected.value) {
    return
  }
  if (currentIndex.value < images.value.length - 1) {
    currentIndex.value++
  } else {
    currentIndex.value = 0
  }
}

const previousImage = () => {
  if (isAllImagesAffected.value) {
    return
  }
  if (currentIndex.value > 0) {
    currentIndex.value--
  } else {
    currentIndex.value = images.value.length - 1
  }
}

function handleKeydown(event) {
  // Check if this is one of our navigation shortcuts
  const isNavigationShortcut = (event.key === 'ArrowUp' && event.ctrlKey) ||
    (event.key === 'ArrowDown' && event.ctrlKey) ||
    event.key === 'Enter'

  // If it's not a navigation shortcut and the target is an input/textarea, don't process
  if (!isNavigationShortcut && (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA')) {
    return
  }

  switch (event.key) {
    case 's':
    case 'S':
      if (event.ctrlKey) {
        event.preventDefault()
        saveAll()
      }
      break
    case 'Enter':
      event.preventDefault()
      if (event.ctrlKey) {
        applyAll()
      } else {
        apply()
      }
      break
    case 'ArrowDown':
      if (event.ctrlKey) {
        event.preventDefault()
        if (!isAllImagesAffected.value) {
          nextImage()
        }
      }
      break
    case 'ArrowUp':
      if (event.ctrlKey) {
        event.preventDefault()
        if (!isAllImagesAffected.value) {
          previousImage()
        }
      }
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
        images.value = result.images.map(img => ({
          ...img,
          timestamp: Date.now()
        }))
        if (filename.value) {
          const index = images.value.findIndex(img => img.name === filename.value)
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
    contrastR.value = preset.contrast_r || 1.0
    contrastG.value = preset.contrast_g || 1.0
    contrastB.value = preset.contrast_b || 1.0
    rotateClockwiseMap.value[currentFileName.value] = preset.rotate_clockwise || 0
  } else {
    // Reset to default if no preset found
    input1.value = 0
    input2.value = 0
    input3.value = 0
    input4.value = 0
    input5.value = 0
    contrastR.value = 1.0
    contrastG.value = 1.0
    contrastB.value = 1.0
    rotateClockwiseMap.value[currentFileName.value] = 0
  }

  // Set presetLoaded to true after loading presets, enabling preview debounce
  presetLoaded.value = true
}

watch(currentIndex, () => {
  // Get current image dimensions before switching
  const img = new Image()
  img.onload = () => {
    previousImageDimensions.value = { width: img.naturalWidth, height: img.naturalHeight }
  }
  img.src = fullResImageUrl.value

  // Set placeholder image before loading new one
  const width = previousImageDimensions.value.width
  const height = previousImageDimensions.value.height
  const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg"><rect width="${width}" height="${height}" fill="white"/></svg>`
  fullResImageUrl.value = 'data:image/svg+xml;base64,' + btoa(svg)

  // Reset presetLoaded state when switching images
  presetLoaded.value = false

  loadFullResImage()
  loadPresetForCurrentImage()
})

watch(images, () => {
  if (images.value.length > 0) {
    // Initialize rotateClockwiseMap for all images to 0
    images.value.forEach(img => {
      if (!rotateClockwiseMap.value[img.name]) {
        rotateClockwiseMap.value[img.name] = 0
      }
    })
    loadFullResImage()
    loadPresetForCurrentImage()
  }
})

// Create debounced version of applyPreview
const debouncedApplyPreview = debounce(() => {
  if (!presetLoaded.value) {
    return
  }
  applyPreview()
}, 5000)

// Handle keydown events in input fields for preview
function handleInputKeydown(event) {
  // Only process if target is an input field and preset is loaded
  if (event.target.tagName !== 'INPUT' || !presetLoaded.value) {
    return
  }

  // Apply debounced preview
  debouncedApplyPreview()
}

// Watch for input value changes to restart debounce (only if user has already started typing)
const inputsToWatch = [input1, input2, input3, input4, input5, contrastR, contrastG, contrastB]
inputsToWatch.forEach(input => {
  watch(input, () => {
    // Only restart debounce if preset is loaded and current image is affected
    // This ensures we don't start previewing automatically after mounted
    if (!presetLoaded.value || !isCurrentImageAffected.value) {
      return
    }

    // Apply debounced preview (this will restart the timer)
    debouncedApplyPreview()
  })
})

onMounted(() => {
  loadImages()
  loadPresets()
  window.addEventListener('keydown', handleKeydown)

  // 初始化操作区域高度
  setTimeout(updateOperationAreaHeight, 100)
  window.addEventListener('resize', updateOperationAreaHeight)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', updateOperationAreaHeight)
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
  z-index: 10;
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
  overflow: hidden;
  position: relative;
}

/* Thumbnails Container - Left Side */
.thumbnails-container {
  width: 100px;
  height: calc(100vh - 64px - 80px);
  background: white;
  border-right: 1px solid #e0e0e0;
  overflow-y: scroll;
  overflow-x: hidden;
  flex-shrink: 0;
}

.thumbnails-container::-webkit-scrollbar {
  width: 6px;
}

.thumbnails-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.thumbnails-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.thumbnails-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px 10px;
  align-items: center;
  width: 100%;
}

.thumbnail-item {
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
}

.thumbnail-item:hover {
  transform: scale(1.05);
}

.thumbnail-item.active {
  border-color: #42b883;
  box-shadow: 0 0 0 2px rgba(66, 184, 131, 0.3);
}

.thumbnail-item.affected {
  opacity: 0.7;
}

.thumbnail-item.cursor-wait {
  cursor: wait;
}

.thumbnail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.thumbnail-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.thumbnail {
  width: 80px;
  height: 80px;
  object-fit: cover;
  display: block;
}

/* Main Content Area - Right Side */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-width: 0;
}

/* Image Display - Takes available space */
.image-display {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 20px;
  overflow: hidden;
  width: 100%;
}

.image-wrapper {
  position: relative;
  display: inline-block;
  max-width: 100%;
  height: 100%;
}

.main-image {
  height: 100%;
  width: auto;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.applying-badge {
  position: absolute;
  bottom: 5%;
  right: 5%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  z-index: 10;
  animation: fadeIn 0.3s ease;
  pointer-events: none;
}

.rotate-controls {
  position: absolute;
  bottom: 10px;
  left: 10px;
  display: flex;
  gap: 8px;
  z-index: 20;
}

.rotate-button {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.rotate-button:hover:not(:disabled) {
  background: #42b883;
  color: white;
  transform: scale(1.1);
}

.rotate-button:active:not(:disabled) {
  transform: scale(0.95);
}

.rotate-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Operation Area - Fixed at Page Bottom */
.operation-area {
  position: fixed;
  bottom: 0;
  left: 100px;
  right: 0;
  padding: 8px 16px;
  background: white;
  border-top: 1px solid #e0e0e0;
  z-index: 100;
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}

.tab-content {
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: center;
  padding: 4px 8px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: center;
  width: 100%;
  margin-top: 8px;
}

.apply-button,
.apply-all-button {
  padding: 8px 20px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.apply-button:hover:not(:disabled),
.apply-all-button:hover:not(:disabled) {
  background: #35a372;
}

.apply-button:active:not(:disabled),
.apply-all-button:active:not(:disabled) {
  transform: scale(0.98);
}

.apply-button:disabled,
.apply-all-button:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
