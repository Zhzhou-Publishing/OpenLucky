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
        @input="onInput"
        @blur="onBlur"
        class="number-field"
      />
      <div class="buttons">
        <button @click="increment(1)" class="up-btn" :disabled="inputValue >= max" :title="upBtnTooltip">▲</button>
        <button @click="decrement(1)" class="down-btn" :disabled="inputValue <= min" :title="downBtnTooltip">▼</button>
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
  }
})

const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)
const inputValue = ref(props.modelValue)

const upBtnTooltip = computed(() => {
  const tips = []
  if (props.increaseKey) {
    tips.push(`${props.increaseKey}`)
  }
  if (props.largeStepIncreaseKey) {
    tips.push(`(+${props.largeStepValue}): ${props.largeStepIncreaseKey}`)
  }
  return tips.join('\n')
})

const downBtnTooltip = computed(() => {
  const tips = []
  if (props.decreaseKey) {
    tips.push(`${props.decreaseKey}`)
  }
  if (props.largeStepDecreaseKey) {
    tips.push(`(-${props.largeStepValue}): ${props.largeStepDecreaseKey}`)
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

  const increaseKey = props.increaseKey.toLowerCase()
  const decreaseKey = props.decreaseKey.toLowerCase()
  const largeStepIncreaseKey = props.largeStepIncreaseKey.toLowerCase()
  const largeStepDecreaseKey = props.largeStepDecreaseKey.toLowerCase()

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
      increment(1)
    } else if (shortcut === decreaseKey) {
      decrement(1)
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
  color: #666;
  font-weight: 500;
}

.number-input {
  display: flex;
  align-items: stretch;
  border: 1px solid #ddd;
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
  border-left: 1px solid #ddd;
}

.up-btn,
.down-btn {
  width: 32px;
  height: 20px;
  border: none;
  background: #f5f5f5;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #666;
  transition: background 0.2s;
  padding: 0;
}

.up-btn:hover:not(:disabled),
.down-btn:hover:not(:disabled) {
  background: #e0e0e0;
}

.up-btn:disabled,
.down-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.up-btn {
  border-bottom: 1px solid #ddd;
}

.down-btn {
  border-top: none;
}
</style>
