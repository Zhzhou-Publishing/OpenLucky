<template>
  <div
    class="histogram-overlay"
    :class="{ dragging }"
    :style="overlayStyle"
    @mousedown="onMouseDown"
    @contextmenu.prevent
  >
    <svg
      :width="width"
      :height="height"
      class="histogram-svg"
      :viewBox="`0 0 ${width} ${height}`"
      preserveAspectRatio="none"
    >
      <polyline v-if="!loading && paths.r" :points="paths.r" class="ch ch-r" />
      <polyline v-if="!loading && paths.g" :points="paths.g" class="ch ch-g" />
      <polyline v-if="!loading && paths.b" :points="paths.b" class="ch ch-b" />
      <polyline v-if="!loading && paths.l" :points="paths.l" class="ch ch-l" />
    </svg>
    <div v-if="loading" class="histogram-loading">
      <div class="histogram-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  // { data: { red, green, blue, luminosity }, visual_meta: { suggested_max_y, is_clipped, total_pixels } }
  // from `openlucky tool histogram -d 256 -m log`. We scale each bin by
  // `suggested_max_y` to fit the canvas; the back end picks that ceiling
  // so curves consistently fill the box without further front-end tuning.
  histogram: { type: Object, default: null },
  width: { type: Number, default: 256 },
  height: { type: Number, default: 256 },
  initialX: { type: Number, default: 120 },
  initialY: { type: Number, default: 80 },
  loading: { type: Boolean, default: false },
})

const PAD_X = 8
const PAD_Y = 8

const x = ref(props.initialX)
const y = ref(props.initialY)
const dragging = ref(false)
let dragOffsetX = 0
let dragOffsetY = 0

const outerW = computed(() => props.width + PAD_X * 2)
const outerH = computed(() => props.height + PAD_Y * 2)

const overlayStyle = computed(() => ({
  left: `${x.value}px`,
  top: `${y.value}px`,
  width: `${outerW.value}px`,
  height: `${outerH.value}px`,
}))

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

function buildPath(channel, maxY) {
  if (!Array.isArray(channel) || channel.length === 0 || !(maxY > 0)) return ''
  const w = props.width
  const h = props.height
  const n = channel.length
  const denom = n > 1 ? n - 1 : 1
  const points = []
  for (let i = 0; i < n; i++) {
    const px = (i * (w - 1)) / denom
    const ratio = clamp(channel[i] / maxY, 0, 1)
    const py = h - ratio * h
    points.push(`${px.toFixed(2)},${py.toFixed(2)}`)
  }
  return points.join(' ')
}

const paths = computed(() => {
  const payload = props.histogram
  if (!payload || !payload.data || !payload.visual_meta) return {}
  const maxY = payload.visual_meta.suggested_max_y
  const { red, green, blue, luminosity } = payload.data
  return {
    r: buildPath(red, maxY),
    g: buildPath(green, maxY),
    b: buildPath(blue, maxY),
    l: buildPath(luminosity, maxY),
  }
})

function onMouseDown(e) {
  dragging.value = true
  dragOffsetX = e.clientX - x.value
  dragOffsetY = e.clientY - y.value
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  e.preventDefault()
}

function onMouseMove(e) {
  if (!dragging.value) return
  // Keep the overlay inside the viewport so it can't get dragged offscreen.
  const margin = 4
  x.value = clamp(e.clientX - dragOffsetX, margin, window.innerWidth - outerW.value - margin)
  y.value = clamp(e.clientY - dragOffsetY, margin, window.innerHeight - outerH.value - margin)
}

function onMouseUp() {
  dragging.value = false
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})
</script>

<style scoped>
.histogram-overlay {
  position: fixed;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  cursor: grab;
  user-select: none;
  box-sizing: border-box;
  overflow: hidden;
  padding: 8px;
}

:global(:root.dark .histogram-overlay) {
  background: rgba(255, 255, 255, 0.08);
}

.histogram-overlay.dragging {
  cursor: grabbing;
}

.histogram-svg {
  display: block;
}

.ch {
  fill: none;
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}

.ch-r {
  stroke: rgba(255, 72, 72, 0.9);
}

.ch-g {
  stroke: rgba(80, 220, 80, 0.9);
}

.ch-b {
  stroke: rgba(96, 160, 255, 0.95);
}

.ch-l {
  stroke: rgba(255, 255, 255, 0.9);
}

.histogram-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
}

.histogram-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid var(--text-on-accent);
  border-radius: 50%;
  animation: hist-spin 1s linear infinite;
}

@keyframes hist-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
