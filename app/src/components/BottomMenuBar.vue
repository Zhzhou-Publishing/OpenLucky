<template>
  <div v-if="!isLoading && imagesCount > 0" class="bottom-menu">
    <div class="menu-item">
      <label class="menu-label">{{ $t('bottomMenu.preset') }}</label>
      <select
        v-model="internalSelectedPreset"
        class="preset-select"
        :disabled="isLoading || isApplyingPreset || isLoadingPresets"
      >
        <option v-for="preset in internalPresets" :key="preset.value" :value="preset.value">
          {{ preset.label }}
        </option>
      </select>
      <button
        @click="handleApplyPreset"
        class="apply-button"
        :disabled="isLoading || isApplyingPreset || isLoadingPresets"
      >
        {{ applyButtonText }}
        <span v-if="hasUnappliedChanges && !isLoadingPresets" class="red-dot"></span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getCachedPresets, updateCachedPresets } from '../utils/presetCache'

const { t } = useI18n()

const props = defineProps({
  selectedPreset: {
    type: String,
    required: true
  },
  hasUnappliedChanges: {
    type: Boolean,
    default: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  isApplyingPreset: {
    type: Boolean,
    default: false
  },
  imagesCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:selectedPreset', 'apply', 'presets-loaded'])

const internalPresets = ref([])
const isLoadingPresets = ref(true)

const internalSelectedPreset = computed({
  get: () => props.selectedPreset,
  set: (value) => {
    emit('update:selectedPreset', value)
  }
})

const applyButtonText = computed(() => {
  return props.isApplyingPreset ? t('bottomMenu.applying') : t('bottomMenu.apply')
})

const handleApplyPreset = () => {
  emit('apply')
}

const loadPresets = async () => {
  try {
    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      // 先尝试使用缓存
      const cachedPresets = getCachedPresets()
      if (cachedPresets && cachedPresets.length > 0) {
        // 使用缓存数据，不显示加载状态
        internalPresets.value = cachedPresets
        isLoadingPresets.value = false
        emit('presets-loaded', cachedPresets)
      }

      // 在后台静默更新缓存
      ipcRenderer.send('get-presets')

      ipcRenderer.once('presets-loaded', (_, result) => {
        // 更新缓存
        updateCachedPresets(result.presets)

        // 如果结果与缓存不同，静默更新 presets
        const currentPresets = JSON.stringify(internalPresets.value)
        const newPresets = JSON.stringify(result.presets)
        if (currentPresets !== newPresets) {
          internalPresets.value = result.presets
          emit('presets-loaded', result.presets)
        }
        isLoadingPresets.value = false
      })

      ipcRenderer.once('presets-error', (_, error) => {
        console.error('Error loading presets:', error)
        // 如果有缓存，继续使用缓存
        if (!cachedPresets) {
          isLoadingPresets.value = false
        }
      })
    }
  } catch (error) {
    console.error('Error loading presets:', error)
    isLoadingPresets.value = false
  }
}

const setPresets = (presets) => {
  internalPresets.value = presets
  isLoadingPresets.value = false
}

const setIsLoadingPresets = (loading) => {
  isLoadingPresets.value = loading
}

// 暴露方法给父组件
defineExpose({
  loadPresets,
  setPresets,
  setIsLoadingPresets
})

// 组件挂载时自动加载 presets
onMounted(() => {
  loadPresets()
})
</script>

<style scoped>
.bottom-menu {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #e0e0e0;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  padding: 16px 20px;
  display: flex;
  justify-content: center;
  z-index: 100;
  animation: slideUp 1s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(100%);
    opacity: 0;
  }

  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-label {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.preset-select {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
  min-width: 400px;
}

.preset-select:hover {
  border-color: #42b883;
}

.preset-select:focus {
  outline: none;
  border-color: #42b883;
  box-shadow: 0 0 0 3px rgba(66, 184, 131, 0.1);
}

.preset-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.apply-button {
  padding: 8px 16px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, opacity 0.2s ease;
  position: relative;
  margin-left: 10px;
  min-width: 120px;
}

.apply-button:hover:not(:disabled) {
  background: #35a372;
}

.apply-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.red-dot {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 12px;
  height: 12px;
  background: #ff4444;
  border-radius: 50%;
  border: 2px solid white;
}
</style>
