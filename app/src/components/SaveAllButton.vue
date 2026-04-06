<template>
  <button
    @click="handleClick"
    class="save-all-button"
    :disabled="isDisabled"
    :title="titleText"
  >
    {{ $t('saveAllButton.saveAll') }}
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  isDisabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const titleText = computed(() => {
  return `${t('saveAllButton.saveAll')} (Ctrl + S)`
})

const handleClick = () => {
  emit('click')
}
</script>

<style scoped>
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
  min-width: 120px;
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
