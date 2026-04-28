<template>
  <div v-if="!isLoading && imagesCount > 0" class="bottom-menu">
    <div class="menu-item">
      <label class="menu-label">{{ $t('bottomMenu.preset') }}</label>
      <select
        v-model="internalSelectedPreset"
        class="preset-select"
        :disabled="isLoading || isApplyingPreset || isSavingAll"
      >
        <option v-for="preset in presets" :key="preset.value" :value="preset.value">
          {{ preset.label }}
        </option>
      </select>
      <button
        @click="handleApplyPreset"
        class="apply-button"
        :disabled="isLoading || isApplyingPreset || isSavingAll"
      >
        {{ applyButtonText }}
        <span v-if="hasUnappliedChanges" class="red-dot"></span>
      </button>
      <button
        @click="handleSaveAll"
        class="save-all-button"
        :disabled="isSavingAll"
        title="Ctrl + S"
      >
        {{ $t('saveAllButton.saveAll') }}
        <span v-if="!isSaveAllClicked" class="red-dot"></span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { presets, fetchPresets } from '../utils/presetCache'
import { globalState } from '../utils/globalState'

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
  isSavingAll: {
    type: Boolean,
    default: false
  },
  imagesCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:selectedPreset', 'apply', 'saveAll'])

const internalSelectedPreset = computed({
  get: () => props.selectedPreset,
  set: (value) => {
    emit('update:selectedPreset', value)
  }
})

const applyButtonText = computed(() => {
  return props.isApplyingPreset ? t('bottomMenu.applying') : t('bottomMenu.apply')
})

const isSaveAllClicked = computed(() => globalState.isSaveAllClicked)

const handleApplyPreset = () => {
  emit('apply')
}

const handleSaveAll = () => {
  emit('saveAll')
}

// Silent refresh: re-fetch in background, never blocks the UI.
onMounted(() => {
  fetchPresets().catch(() => {})
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

.save-all-button {
  padding: 8px 20px;
  background: #42a5f5;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: background 0.3s ease;
  margin-left: 10px;
  min-width: 120px;
  position: relative;
}

.save-all-button:hover:not(:disabled) {
  background: #2196f3;
}

.save-all-button:active:not(:disabled) {
  transform: scale(0.98);
}

.save-all-button:disabled {
  background: #90caf9;
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
