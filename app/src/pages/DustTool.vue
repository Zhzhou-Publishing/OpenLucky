<template>
  <div class="dust-tool">
    <div class="dust-header">
      <div class="dust-title">除尘</div>
      <div class="dust-photo">{{ context?.photo || '' }}</div>
      <div class="dust-actions">
        <button class="dust-btn" :disabled="busy || !imageUrl" @click="runPreview">
          {{ showingPreview ? '显示原图' : '应用预览' }}
        </button>
        <button class="dust-btn primary" :disabled="busy || rois.length === 0" @click="confirm">
          确认
        </button>
      </div>
    </div>

    <div class="dust-body">
      <div class="dust-canvas">
        <div class="dust-wrapper">
          <img
            v-if="imageUrl"
            ref="imgRef"
            :src="imageUrl"
            class="dust-image"
            :style="{ cursor: 'crosshair' }"
            @load="onImageLoad"
            @mousedown="onMouseDown"
          />
          <div
            v-for="(roi, i) in rois"
            :key="i"
            class="dust-roi"
            :style="roiStyle(roi)"
            @dblclick="removeRoi(i)"
          ></div>
          <div v-if="drawing" class="dust-roi" :style="drawingStyle"></div>
        </div>
        <div v-if="error" class="dust-error">{{ error }}</div>
        <div class="dust-hint">
          在图片上拖拽框选灰尘区域（双击选区可删除）。点击「应用预览」看效果，确认后主窗自动应用。
        </div>
      </div>

      <div class="dust-panel">
        <h3>除尘设置</h3>
        <Slider
          v-model="grainLevel"
          :min="0"
          :max="1"
          :step="0.1"
          label="粗细（细=抹颗粒 / 粗=只抠灰尘）"
          :popover-left="'细'"
          :popover-right="'粗'"
        />
        <Slider
          v-model="dustSize"
          :min="5"
          :max="15"
          :step="2"
          label="最大灰尘直径 (px)"
        />
        <div class="roi-list">
          <div v-if="rois.length === 0" class="roi-empty">尚未框选区域</div>
          <div v-for="(roi, i) in rois" :key="i" class="roi-item">
            <span>ROI {{ i + 1 }} ({{ roi.x1 }},{{ roi.y1 }})</span>
            <button class="dust-btn small" @click="removeRoi(i)">删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 除尘工具窗（pr/024.dust.md / pr/025.tool_windows.md）。
// 子窗体：主窗锁定，关闭本窗后返回主窗；「确认」把配置经 tool-result 回传，
// 主窗合并进照片 params 并自动应用。
import { computed, onMounted, onUnmounted, ref } from 'vue'
import backend from '../services/backend'
import Slider from '../components/Slider.vue'

const context = ref(null)
const imageUrl = ref('')
const beforeUrl = ref('')
const naturalDims = ref(null)
const imgRef = ref(null)
const rois = ref([])
const drawStart = ref(null)
const drawCurrent = ref(null)
const busy = ref(false)
const error = ref('')
const showingPreview = ref(false)

const grainLevel = ref(0.3)
const dustSize = ref(9)

onMounted(async () => {
  try {
    context.value = await backend.getToolContext()
  } catch (e) {
    error.value = String((e && e.message) || e)
    return
  }
  if (context.value && context.value.dust) {
    grainLevel.value = context.value.dust.grain_level
    dustSize.value = context.value.dust.dust_size
    rois.value = (context.value.dust.regions || []).map(r => ({
      x1: r.x1, y1: r.y1, x2: r.x2, y2: r.y2,
    }))
  }
  await loadImage()
})

async function loadImage() {
  try {
    const c = context.value
    const result = await backend.getFullResImage({
      directoryPath: c.workingDir,
      filename: c.photo,
    })
    const url = result.url + '?t=' + Date.now()
    beforeUrl.value = url
    imageUrl.value = url
    showingPreview.value = false
  } catch (e) {
    error.value = String((e && e.error) || e)
  }
}

function onImageLoad(e) {
  naturalDims.value = { w: e.target.naturalWidth, h: e.target.naturalHeight }
}

function getImgRect() {
  const img = imgRef.value
  if (!img) return null
  return img.getBoundingClientRect()
}

const drawing = computed(() => !!drawStart.value)

function onMouseDown(e) {
  if (e.button !== 0) return
  const rect = getImgRect()
  if (!rect || rect.width === 0 || rect.height === 0) return
  e.preventDefault()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  drawStart.value = { x, y }
  drawCurrent.value = { x, y }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(e) {
  if (!drawStart.value) return
  const rect = getImgRect()
  if (!rect) return
  const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left))
  const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top))
  drawCurrent.value = { x, y }
}

function onUp() {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  if (!drawStart.value || !drawCurrent.value) {
    drawStart.value = null
    return
  }
  const rect = getImgRect()
  const dims = naturalDims.value
  if (!rect || !dims || rect.width === 0 || rect.height === 0) {
    drawStart.value = null
    return
  }
  const sx = drawStart.value.x
  const sy = drawStart.value.y
  const cx = drawCurrent.value.x
  const cy = drawCurrent.value.y
  drawStart.value = null
  drawCurrent.value = null
  // 显示像素 → 自然像素（--area-basis 同帧）。
  const x1 = Math.round(Math.min(sx, cx) * dims.w / rect.width)
  const y1 = Math.round(Math.min(sy, cy) * dims.h / rect.height)
  const x2 = Math.round(Math.max(sx, cx) * dims.w / rect.width)
  const y2 = Math.round(Math.max(sy, cy) * dims.h / rect.height)
  if (x2 - x1 < 2 || y2 - y1 < 2) return
  rois.value = [...rois.value, { x1, y1, x2, y2 }]
}

function removeRoi(i) {
  rois.value = rois.value.filter((_, idx) => idx !== i)
}

// reactive 数组元素是代理，直接走 structured clone 会静默失败，手动展开成纯对象。
function plainRois() {
  return rois.value.map(r => ({ x1: r.x1, y1: r.y1, x2: r.x2, y2: r.y2 }))
}

function roiStyle(roi) {
  const d = naturalDims.value
  if (!d || !d.w || !d.h) return {}
  return {
    left: `${(roi.x1 / d.w) * 100}%`,
    top: `${(roi.y1 / d.h) * 100}%`,
    width: `${((roi.x2 - roi.x1) / d.w) * 100}%`,
    height: `${((roi.y2 - roi.y1) / d.h) * 100}%`,
  }
}

const drawingStyle = computed(() => {
  if (!drawStart.value || !drawCurrent.value) return {}
  const s = drawStart.value
  const c = drawCurrent.value
  const left = Math.min(s.x, c.x)
  const top = Math.min(s.y, c.y)
  const width = Math.abs(c.x - s.x)
  const height = Math.abs(c.y - s.y)
  if (width < 2 || height < 2) return {}
  return { left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` }
})

async function runPreview() {
  if (showingPreview.value) {
    imageUrl.value = beforeUrl.value
    showingPreview.value = false
    return
  }
  const c = context.value
  if (!c || rois.value.length === 0) return
  busy.value = true
  try {
    await backend.applyFilmparam({
      inputPath: c.workingDir,
      outputPath: c.outputDir,
      filename: c.photo,
      params: c.params,
      rotateClockwise: c.rotateClockwise,
      area: c.area,
      areaBasis: naturalDims.value || c.areaBasis,
      exposure: c.exposure,
      whiteBalance: c.whiteBalance,
      tone: c.tone,
      colorMode: c.colorMode,
      dust: { grain_level: grainLevel.value, dust_size: dustSize.value },
      dustRois: plainRois(),
    })
    // 应用后输出写到 outputDir/photo，重新加载即显示除尘结果。
    const result = await backend.getFullResImage({
      directoryPath: c.workingDir,
      filename: c.photo,
    })
    imageUrl.value = result.url + '?t=' + Date.now()
    showingPreview.value = true
  } catch (e) {
    error.value = String((e && e.error) || e)
  } finally {
    busy.value = false
  }
}

function confirm() {
  backend.notifyToolResult('dust', {
    photo: context.value.photo,
    dust: {
      grain_level: grainLevel.value,
      dust_size: dustSize.value,
      regions: plainRois(),
    },
  })
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
})
</script>

<style scoped>
.dust-tool {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: 'Noto Sans SC', sans-serif;
}

.dust-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.dust-title {
  font-size: 15px;
  font-weight: 600;
}

.dust-photo {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.dust-actions {
  display: flex;
  gap: 8px;
}

.dust-btn {
  padding: 6px 14px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
}

.dust-btn:hover:not(:disabled) { background: var(--bg-surface-hover); }
.dust-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.dust-btn.primary { background: var(--accent); color: var(--text-on-accent); border-color: var(--accent); }
.dust-btn.primary:hover:not(:disabled) { background: var(--accent-hover); }
.dust-btn.small { padding: 2px 8px; font-size: 12px; }

.dust-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.dust-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 16px;
}

.dust-wrapper {
  position: relative;
  display: inline-block;
  line-height: 0;
}

.dust-image {
  display: block;
  max-width: calc(100vw - 300px);
  max-height: calc(100vh - 130px);
  user-select: none;
}

.dust-roi {
  position: absolute;
  border: 2px solid #ff5252;
  background: rgba(255, 82, 82, 0.12);
  box-sizing: border-box;
}

.dust-roi:hover {
  background: rgba(255, 82, 82, 0.22);
}

.dust-error {
  margin-top: 8px;
  padding: 6px 12px;
  color: var(--danger);
  background: var(--bg-surface);
  border: 1px solid var(--danger);
  border-radius: 4px;
  font-size: 12px;
}

.dust-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-tertiary);
  text-align: center;
}

.dust-panel {
  width: 260px;
  flex-shrink: 0;
  padding: 16px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-color);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dust-panel h3 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.roi-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.roi-empty {
  font-size: 12px;
  color: var(--text-tertiary);
}

.roi-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 8px;
  border: 1px solid var(--border-light);
  border-radius: 4px;
}
</style>
