<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="modelValue" class="modal-overlay" @click.self="onCancel('overlay')">
        <div class="modal-box" role="dialog" aria-modal="true">
          <h3 v-if="title" class="modal-title">{{ title }}</h3>
          <div class="modal-body">
            <slot />
          </div>
          <div class="modal-actions">
            <button class="modal-cancel" @click="onCancel('button')">{{ cancelLabel }}</button>
            <button v-if="extraLabel" class="modal-extra" @click="onExtra">{{ extraLabel }}</button>
            <button class="modal-save" :disabled="saveDisabled" @click="onSave">{{ saveLabel }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  saveLabel: { type: String, default: 'OK' },
  cancelLabel: { type: String, default: 'Cancel' },
  extraLabel: { type: String, default: '' },
  saveDisabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'save', 'cancel', 'extra'])

function onCancel(source = 'button') {
  emit('cancel', source)
  emit('update:modelValue', false)
}

function onSave() {
  if (props.saveDisabled) return
  emit('save')
}

function onExtra() {
  emit('extra')
  emit('update:modelValue', false)
}

function onKey(e) {
  if (e.key === 'Escape') onCancel('esc')
}

watch(() => props.modelValue, (open) => {
  if (open) document.addEventListener('keydown', onKey)
  else document.removeEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}

.modal-box {
  background: var(--bg-surface);
  border-radius: 10px;
  box-shadow: 0 12px 32px var(--shadow);
  padding: 24px 28px;
  min-width: 360px;
  max-width: 90vw;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
  color: var(--text-primary);
}

.modal-body {
  margin-bottom: 20px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.modal-cancel,
.modal-extra,
.modal-save {
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.modal-cancel,
.modal-extra {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border-light);
}

.modal-cancel:hover,
.modal-extra:hover {
  background: var(--bg-input);
}

.modal-save {
  background: var(--accent);
  color: var(--text-on-accent);
  border: 1px solid var(--accent);
  font-weight: 600;
}

.modal-save:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.modal-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.15s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
