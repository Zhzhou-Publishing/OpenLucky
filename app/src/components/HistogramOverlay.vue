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
  // [R, G, B, L] from `openlucky tool histogram -d 256 -n <H> -m log`.
  // Values must already be normalized to [0, height]; we draw them
  // directly without re-scaling.
  histogram: { type: Array, default: null },
  width: { type: Number, default: 256 },
  height: { type: Number, default: 100 },
  initialX: { type: Number, default: 120 },
  initialY: { type: Number, default: 80 },
  loading: { type: Boolean, default: false },
})

const x = ref(props.initialX)
const y = ref(props.initialY)
const dragging = ref(false)
let dragOffsetX = 0
let dragOffsetY = 0

const overlayStyle = computed(() => ({
  left: `${x.value}px`,
  top: `${y.value}px`,
  width: `${props.width}px`,
  height: `${props.height}px`,
}))

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

function buildPath(channel) {
  if (!Array.isArray(channel) || channel.length === 0) return ''
  const w = props.width
  const h = props.height
  const n = channel.length
  // SVG y is flipped: bin value v (already in [0, h]) → py = h - v.
  const denom = n > 1 ? n - 1 : 1
  const points = []
  for (let i = 0; i < n; i++) {
    const px = (i * (w - 1)) / denom
    const py = h - clamp(channel[i], 0, h)
    points.push(`${px.toFixed(2)},${py.toFixed(2)}`)
  }
  return points.join(' ')
}

const paths = computed(() => {
  const h = props.histogram
  if (!Array.isArray(h) || h.length < 4) return {}
  return {
    r: buildPath(h[0]),
    g: buildPath(h[1]),
    b: buildPath(h[2]),
    l: buildPath(h[3]),
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
  x.value = clamp(e.clientX - dragOffsetX, margin, window.innerWidth - props.width - margin)
  y.value = clamp(e.clientY - dragOffsetY, margin, window.innerHeight - props.height - margin)
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
