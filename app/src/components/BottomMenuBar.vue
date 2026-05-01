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
        :disabled="isSavingAll || hasUnappliedImages"
        :title="saveAllTitle"
      >
        {{ $t('saveAllButton.saveAll') }}
        <span v-if="!isSaveAllClicked && !isSavingAll && !hasUnappliedImages" class="red-dot"></span>
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
  },
  hasUnappliedImages: {
    type: Boolean,
    default: false
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

const saveAllTitle = computed(() => {
  if (props.hasUnappliedImages) return t('saveAllButton.unappliedTooltip')
  return 'Ctrl + S'
})

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
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  box-shadow: 0 -2px 8px var(--shadow);
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
  color: var(--text-primary);
  font-weight: 500;
}

.preset-select {
  padding: 8px 12px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-surface);
  cursor: pointer;
  transition: border-color 0.2s ease;
  min-width: 400px;
}

.preset-select:hover {
  border-color: var(--accent);
}

.preset-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(66, 184, 131, 0.1);
}

.preset-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.apply-button {
  padding: 8px 16px;
  background: var(--accent);
  color: var(--text-on-accent);
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
  background: var(--accent-hover);
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
  background: var(--danger);
  border-radius: 50%;
  border: 2px solid white;
}

.save-all-button {
  padding: 8px 20px;
  background: var(--btn-save-bg);
  color: var(--text-on-accent);
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
  background: var(--btn-save-hover);
}

.save-all-button:active:not(:disabled) {
  transform: scale(0.98);
}

.save-all-button:disabled {
  background: var(--btn-save-disabled);
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
