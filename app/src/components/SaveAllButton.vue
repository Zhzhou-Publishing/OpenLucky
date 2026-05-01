<template>
  <button
    @click="handleClick"
    class="save-all-button"
    :disabled="isDisabled"
    :title="titleText"
  >
    {{ $t('saveAllButton.saveAll') }}
    <span v-if="!isSaveAllClicked && !isDisabled" class="red-dot"></span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { globalState } from '../utils/globalState'

const { t } = useI18n()

const props = defineProps({
  isDisabled: {
    type: Boolean,
    default: false
  },
  hasUnappliedImages: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const titleText = computed(() => {
  if (props.hasUnappliedImages) return t('saveAllButton.unappliedTooltip')
  return `${t('saveAllButton.saveAll')} (Ctrl + S)`
})

const isSaveAllClicked = computed(() => globalState.isSaveAllClicked)

const handleClick = () => {
  emit('click')
}
</script>

<style scoped>
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
  min-width: 120px;
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
  position: relative;
}
</style>
