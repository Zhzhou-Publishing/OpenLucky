<template>
  <div class="slider-wrapper">
    <label v-if="label" class="slider-label">{{ label }}</label>
    <div
      ref="trackRef"
      class="slider-track"
      :class="{ disabled }"
      @mousedown="onTrackMouseDown"
    >
      <div class="slider-track-fill-bg" :style="trackGradient ? { background: trackGradient } : null"></div>
      <div
        v-if="showPopover && popoverText"
        class="slider-popover"
        :style="{ left: thumbLeftPct + '%' }"
      >
        {{ popoverText }}
      </div>
      <div
        class="slider-thumb"
        :style="{ left: thumbLeftPct + '%' }"
        @mousedown.stop="onThumbMouseDown"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  modelValue: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 },
  disabled: { type: Boolean, default: false },
  trackGradient: { type: String, default: '' },
  // Popover bubble shown above the thumb while dragging. Center is computed
  // as (min + max) / 2; left text appears when value < center, right when >.
  // When all three are empty, the popover stays hidden.
  popoverLeft: { type: String, default: '' },
  popoverRight: { type: String, default: '' },
  popoverCenter: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const trackRef = ref(null)
const dragging = ref(false)

const span = computed(() => props.max - props.min)
const center = computed(() => (props.min + props.max) / 2)

const thumbLeftPct = computed(() => {
  if (span.value <= 0) return 0
  const v = Math.max(props.min, Math.min(props.max, Number(props.modelValue) || 0))
  return ((v - props.min) / span.value) * 100
})

const showPopover = computed(() => dragging.value)

const popoverText = computed(() => {
  const v = Number(props.modelValue) || 0
  if (v < center.value) return props.popoverLeft
  if (v > center.value) return props.popoverRight
  return props.popoverCenter
})

function snapToStep(value) {
  const steps = Math.round((value - props.min) / props.step)
  const snapped = props.min + steps * props.step
  const clamped = Math.max(props.min, Math.min(props.max, snapped))
  // Avoid floating-point cruft like 0.30000000000000004 from accumulated step adds.
  const decimals = (props.step.toString().split('.')[1] || '').length
  return parseFloat(clamped.toFixed(decimals))
}

function valueFromClientX(clientX) {
  const track = trackRef.value
  if (!track) return props.modelValue
  const rect = track.getBoundingClientRect()
  if (rect.width <= 0) return props.modelValue
  const ratio = (clientX - rect.left) / rect.width
  const clampedRatio = Math.max(0, Math.min(1, ratio))
  return snapToStep(props.min + clampedRatio * span.value)
}

function emitFromClientX(clientX) {
  const v = valueFromClientX(clientX)
  if (v !== props.modelValue) emit('update:modelValue', v)
}

function onTrackMouseDown(e) {
  if (props.disabled) return
  emitFromClientX(e.clientX)
  startDrag()
}

function onThumbMouseDown(e) {
  if (props.disabled) return
  // Pre-position is unnecessary — thumb is already where the mouse is.
  startDrag()
  e.preventDefault()
}

function startDrag() {
  dragging.value = true
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e) {
  if (!dragging.value) return
  emitFromClientX(e.clientX)
}

function onDragEnd() {
  dragging.value = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
})
</script>

<style scoped>
.slider-wrapper {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  width: 100%;
}

.slider-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  text-align: center;
}

.slider-track {
  position: relative;
  height: 24px;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
}

.slider-track.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.slider-track-fill-bg {
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
}

.slider-thumb {
  position: absolute;
  top: 50%;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent);
  border: 2px solid var(--bg-surface);
  box-shadow: 0 1px 3px var(--shadow);
  transform: translate(-50%, -50%);
  cursor: grab;
}

.slider-thumb:active {
  cursor: grabbing;
}

.slider-track.disabled .slider-thumb {
  cursor: not-allowed;
  background: var(--btn-disabled-bg);
}

.slider-popover {
  position: absolute;
  bottom: calc(50% + 14px);
  transform: translateX(-50%);
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-on-accent);
  background: var(--accent);
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 2px 6px var(--shadow);
  z-index: 1;
}

.slider-popover::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: var(--accent);
}
</style>
