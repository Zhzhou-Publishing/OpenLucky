<template>
  <div class="number-input-wrapper">
    <label v-if="label" class="number-label">{{ label }}</label>
    <div class="number-input">
      <input
        ref="inputRef"
        v-model="inputValue"
        type="number"
        :min="min"
        :max="max"
        :step="stepValue"
        :disabled="disabled"
        @input="onInput"
        @blur="onBlur"
        @keydown="onKeydown"
        class="number-field"
      />
      <div class="buttons">
        <button @click="increment(props.stepValue)" class="up-btn" :disabled="disabled || inputValue >= max" :title="upBtnTooltip">▲</button>
        <button @click="decrement(props.stepValue)" class="down-btn" :disabled="disabled || inputValue <= min" :title="downBtnTooltip">▼</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: ''
  },
  modelValue: {
    type: Number,
    default: 0
  },
  max: {
    type: Number,
    default: 255
  },
  min: {
    type: Number,
    default: 0
  },
  increaseKey: {
    type: String,
    default: ''
  },
  decreaseKey: {
    type: String,
    default: ''
  },
  stepValue: {
    type: Number,
    default: 1
  },
  largeStepIncreaseKey: {
    type: String,
    default: ''
  },
  largeStepDecreaseKey: {
    type: String,
    default: ''
  },
  largeStepValue: {
    type: Number,
    default: 1
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'keydown'])

const inputRef = ref(null)
const inputValue = ref(props.modelValue)

const upBtnTooltip = computed(() => {
  const tips = []
  if (props.increaseKey) {
    tips.push(`Shortcut Key: ${props.increaseKey}`)
  }
  if (props.largeStepIncreaseKey) {
    tips.push(`Shortcut Key of A Large Step (+${props.largeStepValue}): ${props.largeStepIncreaseKey}`)
  }
  return tips.join('\n')
})

const downBtnTooltip = computed(() => {
  const tips = []
  if (props.decreaseKey) {
    tips.push(`Shortcut Key: ${props.decreaseKey}`)
  }
  if (props.largeStepDecreaseKey) {
    tips.push(`Shortcut Key of A Large Step (-${props.largeStepValue}): ${props.largeStepDecreaseKey}`)
  }
  return tips.join('\n')
})

watch(() => props.modelValue, (newValue) => {
  inputValue.value = newValue
})

watch(inputValue, (newValue) => {
  if (newValue !== '' && newValue !== null && newValue !== undefined) {
    emit('update:modelValue', newValue)
  }
})

function onInput(event) {
  let value = event.target.value
  if (value !== '' && value !== null && value !== undefined) {
    const numValue = parseFloat(value)
    if (!isNaN(numValue)) {
      inputValue.value = Math.max(props.min, Math.min(props.max, numValue))
    }
  }
}

function onBlur() {
  if (inputValue.value === '' || inputValue.value === null || inputValue.value === undefined) {
    inputValue.value = props.min
  } else {
    const numValue = parseFloat(inputValue.value)
    if (!isNaN(numValue)) {
      inputValue.value = Math.max(props.min, Math.min(props.max, numValue))
    }
  }
}

function onKeydown(event) {
  emit('keydown', event)
}

function increment(step) {
  const newValue = Math.min(props.max, inputValue.value + step)
  inputValue.value = parseFloat(newValue.toFixed(10))
  inputRef.value?.focus()
}

function decrement(step) {
  const newValue = Math.max(props.min, inputValue.value - step)
  inputValue.value = parseFloat(newValue.toFixed(10))
  inputRef.value?.focus()
}

function handleKeydown(event) {
  const key = event.key.toLowerCase()
  const modifiers = []

  if (event.shiftKey) modifiers.push('shift')
  if (event.ctrlKey) modifiers.push('ctrl')
  if (event.altKey) modifiers.push('alt')
  if (event.metaKey) modifiers.push('meta')

  modifiers.push(key)
  const shortcut = modifiers.join('+')

  // Normalize shortcut keys by removing spaces and converting to lowercase
  const normalizeShortcut = (key) => key.toLowerCase().replace(/\s+/g, '')

  const increaseKey = normalizeShortcut(props.increaseKey)
  const decreaseKey = normalizeShortcut(props.decreaseKey)
  const largeStepIncreaseKey = normalizeShortcut(props.largeStepIncreaseKey)
  const largeStepDecreaseKey = normalizeShortcut(props.largeStepDecreaseKey)

  // Check if this is one of our configured shortcuts
  const isOurShortcut = shortcut === increaseKey ||
                     shortcut === decreaseKey ||
                     shortcut === largeStepIncreaseKey ||
                     shortcut === largeStepDecreaseKey

  // If it's not our shortcut and the target is an input/textarea, don't process
  if (!isOurShortcut && (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA')) {
    return
  }

  if (isOurShortcut) {
    event.preventDefault()
    if (shortcut === increaseKey) {
      increment(props.stepValue)
    } else if (shortcut === decreaseKey) {
      decrement(props.stepValue)
    } else if (shortcut === largeStepIncreaseKey) {
      increment(props.largeStepValue)
    } else if (shortcut === largeStepDecreaseKey) {
      decrement(props.largeStepValue)
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.number-input-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.number-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.number-input {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  overflow: hidden;
  width: fit-content;
}

.number-field {
  width: 80px;
  padding: 8px 12px;
  border: none;
  outline: none;
  font-size: 14px;
  text-align: center;
  background: var(--bg-input);
  color: var(--text-primary);
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: textfield;
}

.number-field::-webkit-inner-spin-button,
.number-field::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}


.buttons {
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--border-light);
}

.up-btn,
.down-btn {
  width: 32px;
  height: 20px;
  border: none;
  background: var(--bg-input);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: var(--text-secondary);
  transition: background 0.2s;
  padding: 0;
}

.up-btn:hover:not(:disabled),
.down-btn:hover:not(:disabled) {
  background: var(--bg-surface-hover);
}

.up-btn:disabled,
.down-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.up-btn {
  border-bottom: 1px solid var(--border-light);
}

.down-btn {
  border-top: none;
}
</style>
