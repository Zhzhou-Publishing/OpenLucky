<template>
  <div class="photo-edit-page">
    <div class="header">
      <button @click="goBack" class="back-button">{{ $t('photoEdit.back') }}</button>
      <h1 class="file-name">{{ currentFileName }}</h1>
      <div class="directory-name">{{ currentDirectoryName }}</div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ $t('photoEdit.loading') }}</p>
    </div>

    <div v-else-if="images.length === 0" class="empty-state">
      <p class="empty-icon">📷</p>
      <h2>{{ $t('photoEdit.noImages') }}</h2>
      <p>{{ $t('photoEdit.noImagesDesc') }}</p>
    </div>

    <div v-else class="content">
      <!-- Thumbnail Navigation - Left Side -->
      <div class="thumbnails-container">
        <div class="thumbnails-wrapper">
          <div v-for="(image, index) in images" :key="image.name" class="thumbnail-item"
            :class="{ active: index === currentIndex, affected: affectedImages.has(image.name), 'cursor-wait': isAllImagesAffected }"
            @click="!isAllImagesAffected && selectImage(index)">
            <img :src="getImageUrlWithTimestamp(image)" :alt="image.name" class="thumbnail" loading="lazy" />
            <div v-if="affectedImages.has(image.name)" class="thumbnail-overlay">
              <div class="thumbnail-spinner"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Content Area - Right Side -->
      <div class="main-content">
        <!-- Large Image Display -->
        <div class="image-display"
             :class="{ 'eyedropper-active': eyedropperActive, 'area-select-active': areaSelectActive }"
             :style="{ height: imageDisplayHeight }"
             @wheel="onImageDisplayWheel"
             @contextmenu.prevent="onContextMenu">
          <div class="image-wrapper"
               :style="imageWrapperStyle"
               @mouseenter="onWrapperEnter"
               @mouseleave="onWrapperLeave"
               @mousedown="onWrapperMouseDown">
            <img v-if="fullResImageUrl"
                 ref="mainImgRef"
                 :src="fullResImageUrl"
                 :alt="currentImage.name"
                 class="main-image"
                 :style="{ cursor: mainImageCursor }"
                 @click="onImageClick"
                 @mousedown="onMainImageMouseDown"
                 @dblclick="onImageDblClick"
                 @load="onMainImageLoad" />
            <!-- 框选模式：未拖拽时整张图被半透明灰色遮罩覆盖 -->
            <div v-if="areaSelectActive && !liveSelectionDisplayRect" class="area-mask-full"></div>
            <!-- 框选模式：拖拽中用 box-shadow 反向"挖洞"，露出选中矩形并加红框 -->
            <div v-else-if="areaSelectActive && liveSelectionDisplayRect" class="area-cutout" :style="liveSelectionDisplayRect"></div>
            <!-- 非框选模式时，hover 已选过的图片显示纯红框预览 -->
            <div v-else-if="hoveringImage && storedSelectionDisplayRect" class="area-stored-preview" :style="storedSelectionDisplayRect"></div>
            <div v-if="isCurrentImageAffected" class="applying-badge">{{ $t('photoEdit.applying') }}</div>
          </div>
          <div v-if="eyedropperActive" class="eyedropper-hint">{{ $t('photoEdit.eyedropper.exitHint') }}</div>
          <div v-if="areaSelectActive" class="area-select-hint">{{ $t('photoEdit.areaSelect.exitHint') }}</div>
        </div>
      </div>

      <!-- Operation Area - Fixed at Page Bottom -->
      <div ref="operationAreaRef" class="operation-area">
        <Tabs :tabs="[
          { id: 'basic', label: $t('photoEdit.basicTab') },
          { id: 'dye_concentration_correction', label: $t('photoEdit.advancedTab') },
          { id: 'exposure', label: $t('photoEdit.exposureTab') },
          { id: 'tone', label: $t('photoEdit.toneTab') },
          { id: 'white_balance', label: $t('photoEdit.whiteBalanceTab') }
        ]" :default-tab="'basic'" @tab-change="handleTabChange">
          <template #default="{ activeTab }">
            <!-- Basic Parameters Tab -->
            <div v-if="activeTab === 'basic'" class="tab-content">
              <NumberInput :label="$t('photoEdit.maskR')" v-model="input1" :max="255" :min="0" increase-key="Q"
                decrease-key="A" :disabled="isAllImagesAffected || isCurrentImageAffected"
                />
              <NumberInput :label="$t('photoEdit.maskG')" v-model="input2" :max="255" :min="0" increase-key="W"
                decrease-key="S" :disabled="isAllImagesAffected || isCurrentImageAffected"
                />
              <NumberInput :label="$t('photoEdit.maskB')" v-model="input3" :max="255" :min="0" increase-key="E"
                decrease-key="D" :disabled="isAllImagesAffected || isCurrentImageAffected"
                />
              <NumberInput :label="$t('photoEdit.gamma')" v-model="input4" :max="5" :min="0.01" increase-key="R"
                decrease-key="F" :step-value="0.01" :large-step-value="0.1" large-step-increase-key="Alt + Shift + R"
                large-step-decrease-key="Alt + Shift + F" :disabled="isAllImagesAffected || isCurrentImageAffected"
                />
              <NumberInput :label="$t('photoEdit.contrast')" v-model="input5" :max="2" :min="0.5" increase-key="T"
                decrease-key="G" :step-value="0.01" :large-step-value="0.05" large-step-increase-key="Alt + Shift + T"
                large-step-decrease-key="Alt + Shift + G" :disabled="isAllImagesAffected || isCurrentImageAffected"
                />
            </div>

            <!-- Advanced Parameters Tab -->
            <div v-if="activeTab === 'dye_concentration_correction'" class="tab-content">
              <NumberInput :label="$t('photoEdit.contrastR')" v-model="contrastR" :max="2" :min="0.5" :step-value="0.01"
                :disabled="isAllImagesAffected || isCurrentImageAffected" />
              <NumberInput :label="$t('photoEdit.contrastG')" v-model="contrastG" :max="2" :min="0.5" :step-value="0.01"
                :disabled="isAllImagesAffected || isCurrentImageAffected" />
              <NumberInput :label="$t('photoEdit.contrastB')" v-model="contrastB" :max="2" :min="0.5" :step-value="0.01"
                :disabled="isAllImagesAffected || isCurrentImageAffected" />
            </div>

            <!-- Exposure Tab -->
            <div v-if="activeTab === 'exposure'" class="tab-content exposure-tab">
              <div class="exposure-slider">
                <Slider v-model="exposure" :min="-3.0" :max="3.0" :step="0.1"
                  :disabled="isAllImagesAffected || isCurrentImageAffected" />
              </div>
              <NumberInput :label="$t('photoEdit.exposureTab')" v-model="exposure" :max="3.0" :min="-3.0"
                :step-value="0.1" :disabled="isAllImagesAffected || isCurrentImageAffected"
                />
            </div>

            <!-- Tone Adjustment Tab -->
            <div v-if="activeTab === 'tone'" class="tab-content tone-tab">
              <div class="tone-rows">
                <div class="tone-row">
                  <Slider class="tone-row-slider" :label="$t('photoEdit.tonePivot')"
                    v-model="tonePivotUi" :min="-100" :max="100" :step="1"
                    :popover-left="$t('photoEdit.tonePivotLeft')"
                    :popover-right="$t('photoEdit.tonePivotRight')"
                    :disabled="tonePivotAuto || isAllImagesAffected || isCurrentImageAffected" />
                  <NumberInput v-model="tonePivotUi" :max="100" :min="-100" :step-value="1"
                    :disabled="tonePivotAuto || isAllImagesAffected || isCurrentImageAffected" />
                  <label class="tone-auto-label">
                    <input type="checkbox" v-model="tonePivotAuto"
                      :disabled="isAllImagesAffected || isCurrentImageAffected" />
                    {{ $t('photoEdit.toneAuto') }}
                  </label>
                </div>
                <div class="tone-row">
                  <Slider class="tone-row-slider" :label="$t('photoEdit.toneCurve')"
                    v-model="toneCurveUi" :min="-100" :max="100" :step="1"
                    :popover-left="$t('photoEdit.toneCurveLeft')"
                    :popover-right="$t('photoEdit.toneCurveRight')"
                    :disabled="toneCurveAuto || isAllImagesAffected || isCurrentImageAffected" />
                  <NumberInput v-model="toneCurveUi" :max="100" :min="-100" :step-value="1"
                    :disabled="toneCurveAuto || isAllImagesAffected || isCurrentImageAffected" />
                  <label class="tone-auto-label">
                    <input type="checkbox" v-model="toneCurveAuto"
                      :disabled="isAllImagesAffected || isCurrentImageAffected" />
                    {{ $t('photoEdit.toneAuto') }}
                  </label>
                </div>
              </div>
            </div>

            <!-- White Balance Tab -->
            <div v-if="activeTab === 'white_balance'" class="tab-content wb-tab">
              <label class="wb-auto-label">
                <input type="checkbox" v-model="whiteBalanceAuto"
                  :disabled="isAllImagesAffected || isCurrentImageAffected" />
                {{ $t('photoEdit.whiteBalanceAuto') }}
              </label>
              <div class="wb-rows">
                <div class="wb-row">
                  <Slider class="wb-row-slider" :label="$t('photoEdit.whiteBalanceTemp')"
                    v-model="whiteBalanceTemp" :min="-50" :max="50" :step="1"
                    :track-gradient="WB_TEMP_GRADIENT"
                    :disabled="whiteBalanceAuto || isAllImagesAffected || isCurrentImageAffected" />
                  <NumberInput v-model="whiteBalanceTemp" :max="50" :min="-50" :step-value="1"
                    :disabled="whiteBalanceAuto || isAllImagesAffected || isCurrentImageAffected"
                    />
                </div>
                <div class="wb-row">
                  <Slider class="wb-row-slider" :label="$t('photoEdit.whiteBalanceTint')"
                    v-model="whiteBalanceTint" :min="-50" :max="50" :step="1"
                    :track-gradient="WB_TINT_GRADIENT"
                    :disabled="whiteBalanceAuto || isAllImagesAffected || isCurrentImageAffected" />
                  <NumberInput v-model="whiteBalanceTint" :max="50" :min="-50" :step-value="1"
                    :disabled="whiteBalanceAuto || isAllImagesAffected || isCurrentImageAffected"
                    />
                </div>
              </div>
            </div>

            <!-- Common Action Buttons -->
            <div class="action-buttons">
              <button @click="apply" class="apply-button" title="Enter"
                :disabled="isAllImagesAffected || isCurrentImageAffected">{{ $t('photoEdit.apply') }}</button>
              <button @click="applyAll" class="apply-all-button" title="CTRL + Enter" :disabled="isAllImagesAffected">{{
                $t('photoEdit.applyAll') }}</button>
              <SaveAllButton :is-disabled="isAllImagesAffected || hasUnappliedImages" :has-unapplied-images="hasUnappliedImages" @click="saveAll" />
            </div>
          </template>
        </Tabs>
      </div>
    </div>

    <HistogramOverlay v-if="isHistogramDisplay" :histogram="histogramData" :loading="isHistogramLoading" />

    <ContextMenu v-model="ctxMenuVisible" :items="ctxMenuItems" :position="ctxMenuPos" />

    <Modal
      v-model="presetModalOpen"
      :title="$t('photoEdit.applyPresetModal.title')"
      :save-label="$t('photoEdit.applyPresetModal.save')"
      :cancel-label="$t('photoEdit.applyPresetModal.pickColor')"
      @save="applyPresetFromModal"
      @cancel="onPresetModalCancel"
    >
      <select v-model="selectedModalPreset" class="preset-modal-select">
        <option v-for="p in globalPresets" :key="p.value" :value="p.value">{{ p.label }}</option>
      </select>
    </Modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import NumberInput from '../components/NumberInput.vue'
import Slider from '../components/Slider.vue'
import HistogramOverlay from '../components/HistogramOverlay.vue'
import SaveAllButton from '../components/SaveAllButton.vue'
import Tabs from '../components/Tabs.vue'
import ContextMenu from '../components/ContextMenu.vue'
import Modal from '../components/Modal.vue'
import { setSaveAllClicked, getSaveAllClicked } from '../utils/globalState'
import { presets as globalPresets } from '../utils/presetCache'
import { createRendererLogger } from '../utils/rendererLogger'

const logger = createRendererLogger('PhotoEdit')

// Get path module for Electron environment
const path = window.require ? window.require('path') : { basename: (p) => p }

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const images = ref([])
const isLoading = ref(true)
const affectedImages = reactive(new Set())
const currentIndex = ref(0)
const fullResImageUrl = ref('')
const input1 = ref(255)
const input2 = ref(255)
const input3 = ref(255)
const input4 = ref(1)
const input5 = ref(1)
const contrastR = ref(1.0)
const contrastG = ref(1.0)
const contrastB = ref(1.0)
const exposure = ref(0)
const whiteBalanceAuto = ref(true)
const whiteBalanceTemp = ref(0)
const whiteBalanceTint = ref(0)
// 色调调整 UI 数值 [-100, 100]。重心 0 = 数学 p=0.5（对称中点），
// 反差 0 = 数学 k=1.0（恒等无变化）；两个滑块都用 0 居中表达"原片直出"。
const tonePivotUi = ref(0)
const toneCurveUi = ref(0)
// 重心 / 反差各自独立的 auto 开关。勾选后对应滑块禁用，序列化成 CLI
// --tone 的 'auto' 槽位，由 CLI 端 auto_pk 按直方图反推该参数。
// 默认开启：多数胶片冲扫直接吃自动值即可，需要手动微调再取消勾选。
const tonePivotAuto = ref(true)
const toneCurveAuto = ref(true)

// UI [-100, 100] → 内部 p ∈ [0.20, 0.80]（线性映射）
function tonePivotUiToInternal(ui) {
  return 0.50 + ui * 0.003
}
function tonePivotInternalToUi(p) {
  if (typeof p !== 'number') return 0
  return Math.max(-100, Math.min(100, Math.round((p - 0.50) / 0.003)))
}

// UI [-100, 100] → 内部 k ∈ [0.5, 3.0]（三段线性，0 居中代表 k=1.0）
// -100→0.5, 0→1.0, +50→1.8, +100→3.0
function toneCurveUiToInternal(ui) {
  if (ui <= 0) return 1.0 + ui * 0.005       // [-100, 0]  → [0.5, 1.0]
  if (ui <= 50) return 1.0 + ui * 0.016      // [0, 50]    → [1.0, 1.8]
  return 1.8 + (ui - 50) * 0.024             // [50, 100]  → [1.8, 3.0]
}
function toneCurveInternalToUi(k) {
  if (typeof k !== 'number') return 0
  let ui
  if (k <= 1.0) ui = (k - 1.0) / 0.005
  else if (k <= 1.8) ui = (k - 1.0) / 0.016
  else ui = 50 + (k - 1.8) / 0.024
  return Math.max(-100, Math.min(100, Math.round(ui)))
}

// 序列化成 CLI --tone 期望的字符串。每个槽位独立：勾了 auto 就给 'auto'，
// 否则给数值。CLI parse_tone 接受 'auto,K' / 'P,auto' / 'auto,auto' / 'P,K'。
function currentToneForIpc() {
  const pivotSlot = tonePivotAuto.value
    ? 'auto'
    : tonePivotUiToInternal(tonePivotUi.value).toFixed(4)
  const curveSlot = toneCurveAuto.value
    ? 'auto'
    : toneCurveUiToInternal(toneCurveUi.value).toFixed(4)
  return `${pivotSlot},${curveSlot}`
}
// 渐变贴在 slider 轨道上，给用户一个色温/色调拉杆方向的视觉锚点：
//   色温 -50 偏冷蓝 / 0 中性 / +50 偏暖琥珀
//   色调 -50 偏品红 / 0 中性 / +50 偏绿（CLI 里 +y 是抬绿色增益）
const WB_TEMP_GRADIENT = 'linear-gradient(to right, #4a90e2 0%, #cccccc 50%, #f5a623 100%)'
const WB_TINT_GRADIENT = 'linear-gradient(to right, #e91e63 0%, #cccccc 50%, #4caf50 100%)'
const presetsData = ref({})
const presetsDataLoaded = ref(false)
// 旋转操作：先发 IPC，成功后再旋转选区坐标，避免 IPC 失败时选区被错误旋转
const pendingRotation = ref(null) // null | { imageName: string, direction: 'cw' | 'ccw' }

// 直方图叠加层：每次主图加载完成或被 apply 刷新后重算一次。
// CLI 现在返回 { data: { red, green, blue, luminosity }, visual_meta: { suggested_max_y, ... } }，
// HistogramOverlay 用 suggested_max_y 把曲线归一化到 SVG 高度，不再依赖前端塞死 -n。
//
// 把目录+文件名透传给 main，由 main 端读最新 .preset.json 决定取哪个
// 版本（apply 后的 output_dir 或工作目录原图），避免依赖 renderer 这边
// 可能滞后的 currentImage.path。
const HISTOGRAM_BINS = 256
const histogramData = ref(null)
let histogramRequestSeq = 0
// apply 成功后 affectedImages 被同步清除但 loadPresets 是异步的，
// 桥接这个间隙保持 isHistogramDisplay 不闪烁。
const pendingApplyImage = ref(null)
function histogramCacheKey(directoryPath, filename, area) {
  const areaKey = area ? `${area.x1},${area.y1},${area.x2},${area.y2}` : 'full'
  return `histogram:${directoryPath}:${filename}:${areaKey}`
}

function readHistogramCache(key) {
  try {
    const raw = sessionStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeHistogramCache(key, data) {
  try {
    sessionStorage.setItem(key, JSON.stringify(data))
  } catch {
    // sessionStorage 满了就静默跳过
  }
}

function clearHistogramCache() {
  try {
    const keys = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i)
      if (key && key.startsWith('histogram:')) {
        keys.push(key)
      }
    }
    keys.forEach(k => sessionStorage.removeItem(k))
  } catch {
    // 静默跳过
  }
}

async function fetchHistogramFor(directoryPath, filename, area) {
  if (!directoryPath || !filename || !window.require) {
    histogramData.value = null
    return
  }
  // 只对有 output_dir 的图片采样。apply 进行中不采样——此时 .preset.json
  // 还没有 output_dir，compute-histogram 会退回底片路径。
  const entry = presetsData.value?.[filename]
  if (!entry || !entry.output_dir) {
    histogramData.value = null
    return
  }
  const cacheKey = histogramCacheKey(directoryPath, filename, area)
  const cached = readHistogramCache(cacheKey)
  if (cached) {
    histogramData.value = cached
    return
  }
  const seq = ++histogramRequestSeq
  try {
    const ipcRenderer = window.require('electron').ipcRenderer
    const result = await ipcRenderer.invoke('compute-histogram', {
      directoryPath,
      filename,
      downsampling: HISTOGRAM_BINS,
      area: area || null,
    })
    // 防止旧请求覆盖新结果（用户快速切图时容易触发）。
    if (seq === histogramRequestSeq) {
      histogramData.value = result
      writeHistogramCache(cacheKey, result)
    }
  } catch (err) {
    logger.error('Failed to compute histogram:', err)
    if (seq === histogramRequestSeq) {
      histogramData.value = null
    }
  }
}
const operationAreaRef = ref(null)
const operationAreaHeight = ref(80) // 默认值

// 右键菜单
const ctxMenuVisible = ref(false)
const ctxMenuPos = ref({ x: 0, y: 0 })
const paramClipboard = ref(null)

// 吸管模式：激活后 cursor 变十字，点击主图取色填入 mask + gamma + contrast，点完或按 ESC 自动退出。
const eyedropperActive = ref(false)
// 吸管 IPC 比白点框选快的时候先寄存在这，等用户完成框选再 flush 进 input1-5；
// 用户 ESC / 无效拖拽取消框选时被丢弃。
const pendingPickResult = ref(null)

// 框选模式：激活后整张图被半透明灰色遮罩覆盖，从左上向右下拖出选区，
// 选区内用 box-shadow 反向挖洞露出原图并加红框；松开鼠标后按文件名落入 sessionStorage，
// 此后非框选模式下 hover 已选过的图片仅显示红框轮廓。
const areaSelectActive = ref(false)
const areaSelectStart = ref(null)
const areaSelectCurrent = ref(null)
const hoveringImage = ref(false)
const mainImgRef = ref(null)
const currentImageNaturalDims = ref(null)
const areaSelectionsByName = ref({})

// Zoom & pan state
const zoomLevel = ref(1)
const panOffsetX = ref(0)
const panOffsetY = ref(0)
const isPanning = ref(false)
const panStartMouse = ref({ x: 0, y: 0 })
const panStartOffset = ref({ x: 0, y: 0 })

const AREA_SESSION_STORAGE_KEY = 'photoEditAreaSelections'

function loadAreaSelections() {
  try {
    return JSON.parse(sessionStorage.getItem(AREA_SESSION_STORAGE_KEY) || '{}')
  } catch (err) {
    logger.error('Failed to load area selections:', err)
    return {}
  }
}

// reactive 嵌套对象不能直接走 Electron structured clone（会被静默丢包），
// 这里做一次手动展开，把四个整数复制到一个全新的 plain object 里。
function unwrapArea(stored) {
  if (!stored) return null
  return {
    x1: stored.x1,
    y1: stored.y1,
    x2: stored.x2,
    y2: stored.y2,
  }
}

// 序列化白平衡为 CLI 字符串：自动模式直接给 "auto"，手动模式给 "temp,tint"。
// "none"（关闭白平衡）暂时不在 UI 里暴露，需要的话直接编辑 sessionStorage / 走 CLI。
function currentWhiteBalanceForIpc() {
  if (whiteBalanceAuto.value) return 'auto'
  return `${Math.round(whiteBalanceTemp.value)},${Math.round(whiteBalanceTint.value)}`
}

// ROI 的测量帧尺寸（即用户看到的 working-dir 预览图的自然像素），CLI 用这个
// 来反算原图坐标。没有 dims 时返回 null，main.js 会跳过 --area-basis 走兼容路径。
function currentAreaBasisForIpc() {
  const d = currentImageNaturalDims.value
  if (!d || !d.w || !d.h) return null
  return { w: d.w, h: d.h }
}

function persistAreaSelections() {
  try {
    sessionStorage.setItem(AREA_SESSION_STORAGE_KEY, JSON.stringify(areaSelectionsByName.value))
  } catch (err) {
    logger.error('Failed to persist area selections:', err)
  }
}

function startAreaSelect() {
  if (!currentImage.value || !fullResImageUrl.value) return
  if (isAllImagesAffected.value || isCurrentImageAffected.value) return
  if (eyedropperActive.value) eyedropperActive.value = false
  areaSelectStart.value = null
  areaSelectCurrent.value = null
  areaSelectActive.value = true
}

function exitAreaSelect() {
  areaSelectActive.value = false
  areaSelectStart.value = null
  areaSelectCurrent.value = null
  // 取消（ESC / 无效拖拽 / 重新进入其它模式）丢弃挂起的吸管结果，避免下次 flush 误填。
  pendingPickResult.value = null
  window.removeEventListener('mousemove', onAreaMouseMoveWindow)
  window.removeEventListener('mouseup', onAreaMouseUpWindow)
}

function clearAreaSelectionForCurrent() {
  if (!currentImage.value) return
  const next = { ...areaSelectionsByName.value }
  delete next[currentImage.value.name]
  areaSelectionsByName.value = next
  persistAreaSelections()
}

function getMainImgRect() {
  const img = mainImgRef.value
  if (!img) return null
  return img.getBoundingClientRect()
}

function onMainImageLoad(e) {
  currentImageNaturalDims.value = {
    w: e.target.naturalWidth,
    h: e.target.naturalHeight,
  }
}

function onWrapperEnter() {
  hoveringImage.value = true
}

function onWrapperLeave() {
  hoveringImage.value = false
}

function onMainImageMouseDown(e) {
  if (eyedropperActive.value) return
  if (!areaSelectActive.value) return
  if (e.button !== 0) return
  e.preventDefault()
  const rect = getMainImgRect()
  if (!rect || rect.width === 0 || rect.height === 0) return
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  areaSelectStart.value = { x, y }
  areaSelectCurrent.value = { x, y }
  // mousemove / mouseup 走 window，避免拖出图片边界后失联
  window.addEventListener('mousemove', onAreaMouseMoveWindow)
  window.addEventListener('mouseup', onAreaMouseUpWindow)
}

function onAreaMouseMoveWindow(e) {
  if (!areaSelectActive.value || !areaSelectStart.value) return
  const rect = getMainImgRect()
  if (!rect) return
  const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left))
  const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top))
  areaSelectCurrent.value = { x, y }
}

function onAreaMouseUpWindow(e) {
  window.removeEventListener('mousemove', onAreaMouseMoveWindow)
  window.removeEventListener('mouseup', onAreaMouseUpWindow)
  if (!areaSelectActive.value || !areaSelectStart.value) return

  const rect = getMainImgRect()
  const dims = currentImageNaturalDims.value
  if (!rect || !dims || rect.width === 0 || rect.height === 0) {
    exitAreaSelect()
    return
  }

  const sx = areaSelectStart.value.x
  const sy = areaSelectStart.value.y
  const cx = areaSelectCurrent.value.x
  const cy = areaSelectCurrent.value.y
  const dx1 = Math.min(sx, cx)
  const dy1 = Math.min(sy, cy)
  const dx2 = Math.max(sx, cx)
  const dy2 = Math.max(sy, cy)
  if (dx2 - dx1 < 2 || dy2 - dy1 < 2) {
    exitAreaSelect()
    return
  }

  // 显示像素 → 自然像素，落到存储里都是真实像素坐标
  const x1 = Math.max(0, Math.min(dims.w - 1, Math.round(dx1 * dims.w / rect.width)))
  const y1 = Math.max(0, Math.min(dims.h - 1, Math.round(dy1 * dims.h / rect.height)))
  const x2 = Math.max(0, Math.min(dims.w, Math.round(dx2 * dims.w / rect.width)))
  const y2 = Math.max(0, Math.min(dims.h, Math.round(dy2 * dims.h / rect.height)))
  if (x2 <= x1 || y2 <= y1) {
    exitAreaSelect()
    return
  }

  if (currentImage.value) {
    areaSelectionsByName.value = {
      ...areaSelectionsByName.value,
      [currentImage.value.name]: { x1, y1, x2, y2 },
    }
    persistAreaSelections()
    // 框选成功完成时 flush 吸管寄存结果。注意必须在 exitAreaSelect 之前，
    // exitAreaSelect 会清掉 pendingPickResult。
    if (pendingPickResult.value) {
      const picked = pendingPickResult.value
      pendingPickResult.value = null
      applyPickResult(picked)
    }
  }
  exitAreaSelect()
}

const liveSelectionDisplayRect = computed(() => {
  if (!areaSelectActive.value) return null
  const s = areaSelectStart.value
  const c = areaSelectCurrent.value
  if (!s || !c) return null
  const left = Math.min(s.x, c.x)
  const top = Math.min(s.y, c.y)
  const width = Math.abs(c.x - s.x)
  const height = Math.abs(c.y - s.y)
  if (width < 2 || height < 2) return null
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  }
})

const storedSelectionForCurrent = computed(() => {
  if (!currentImage.value) return null
  return areaSelectionsByName.value[currentImage.value.name] || null
})

const storedSelectionDisplayRect = computed(() => {
  const stored = storedSelectionForCurrent.value
  const dims = currentImageNaturalDims.value
  if (!stored || !dims || !dims.w || !dims.h) return null
  return {
    left: `${(stored.x1 / dims.w) * 100}%`,
    top: `${(stored.y1 / dims.h) * 100}%`,
    width: `${((stored.x2 - stored.x1) / dims.w) * 100}%`,
    height: `${((stored.y2 - stored.y1) / dims.h) * 100}%`,
  }
})

function startEyedropper() {
  if (!currentImage.value || !fullResImageUrl.value) return
  if (isAllImagesAffected.value || isCurrentImageAffected.value) return
  eyedropperActive.value = true
}

function exitEyedropper() {
  eyedropperActive.value = false
}

async function onImageClick(e) {
  if (!eyedropperActive.value) return
  if (!currentImage.value) return

  const img = e.currentTarget
  const rect = img.getBoundingClientRect()
  const naturalW = img.naturalWidth
  const naturalH = img.naturalHeight
  if (!naturalW || !naturalH || rect.width === 0 || rect.height === 0) {
    exitEyedropper()
    return
  }

  const xInImg = e.clientX - rect.left
  const yInImg = e.clientY - rect.top
  const pixelX = Math.max(0, Math.min(naturalW - 1, Math.floor(xInImg * naturalW / rect.width)))
  const pixelY = Math.max(0, Math.min(naturalH - 1, Math.floor(yInImg * naturalH / rect.height)))

  // 取色后立刻进入白点区域选择模式（startAreaSelect 自身会关闭吸管）。
  // 这一步同步执行，让用户感知不到任何等待，pick-color IPC 在后台并发完成。
  exitEyedropper()
  startAreaSelect()
  try {
    const ipcRenderer = window.require('electron').ipcRenderer
    const result = await ipcRenderer.invoke('pick-color', {
      filePath: path.join(workingDirectory.value, currentImage.value.name),
      x: pixelX,
      y: pixelY,
      format: '8',
    })
    if (result && Array.isArray(result.rgb) && result.rgb.length === 3) {
      const picked = { r: result.rgb[0], g: result.rgb[1], b: result.rgb[2] }
      if (areaSelectActive.value) {
        // 用户还没完成白点框选，先寄存；onAreaMouseUpWindow 成功路径会 flush。
        pendingPickResult.value = picked
      } else {
        // 极端情况：IPC 比 mouseup 还慢，框选已结束，直接落盘。
        applyPickResult(picked)
      }
    }
  } catch (err) {
    logger.error('Pick color failed:', err)
  }
}

function applyPickResult(picked) {
  input1.value = picked.r
  input2.value = picked.g
  input3.value = picked.b
  input4.value = 2.2
  input5.value = 1.1
  apply()
}

function copyParams() {
  paramClipboard.value = {
    mask_r: input1.value,
    mask_g: input2.value,
    mask_b: input3.value,
    gamma: input4.value,
    contrast: input5.value,
    contrast_r: contrastR.value,
    contrast_g: contrastG.value,
    contrast_b: contrastB.value,
    tone_pivot_ui: tonePivotUi.value,
    tone_curve_ui: toneCurveUi.value,
    tone_pivot_auto: tonePivotAuto.value,
    tone_curve_auto: toneCurveAuto.value,
  }
}

function pasteParams() {
  const c = paramClipboard.value
  if (!c) return
  input1.value = c.mask_r
  input2.value = c.mask_g
  input3.value = c.mask_b
  input4.value = c.gamma
  input5.value = c.contrast
  contrastR.value = c.contrast_r
  contrastG.value = c.contrast_g
  contrastB.value = c.contrast_b
  tonePivotUi.value = c.tone_pivot_ui ?? 0
  toneCurveUi.value = c.tone_curve_ui ?? 0
  tonePivotAuto.value = c.tone_pivot_auto ?? false
  toneCurveAuto.value = c.tone_curve_auto ?? false
}

const presetModalOpen = ref(false)
const selectedModalPreset = ref('')

function openPresetModal() {
  if (globalPresets.value.length > 0) {
    const stillExists = globalPresets.value.some(p => p.value === selectedModalPreset.value)
    if (!stillExists) selectedModalPreset.value = globalPresets.value[0].value
  }
  presetModalOpen.value = true
}

function onPresetModalCancel(source) {
  if (source === 'button') startEyedropper()
}

function applyPresetFromModal() {
  const preset = globalPresets.value.find(p => p.value === selectedModalPreset.value)
  if (!preset) return
  input1.value = preset.mask_r ?? 255
  input2.value = preset.mask_g ?? 255
  input3.value = preset.mask_b ?? 255
  input4.value = preset.gamma ?? 1
  input5.value = preset.contrast ?? 1
  contrastR.value = preset.contrast_r ?? 1.0
  contrastG.value = preset.contrast_g ?? 1.0
  contrastB.value = preset.contrast_b ?? 1.0
  applyTonePresetToUi(preset)
  presetModalOpen.value = false
  apply()
}

// Pull tone back from a preset entry (.preset.json or globalPreset). Tone is
// stored as a CLI --tone string; each slot is either a number or 'auto'
// (an 'auto:STRENGTH' suffix collapses to the auto flag — the UI doesn't
// expose strength). Missing/invalid → fall back to the default (both auto).
function applyTonePresetToUi(preset) {
  const resetToDefault = () => {
    tonePivotAuto.value = true
    toneCurveAuto.value = true
    tonePivotUi.value = 0
    toneCurveUi.value = 0
  }
  const raw = preset?.tone
  if (typeof raw !== 'string' || raw.length === 0) {
    resetToDefault()
    return
  }
  const parts = raw.split(',').map(s => s.trim())
  if (parts.length !== 2) {
    resetToDefault()
    return
  }
  const isAuto = (slot) => slot === 'auto' || slot.startsWith('auto:')

  if (isAuto(parts[0])) {
    tonePivotAuto.value = true
    tonePivotUi.value = 0
  } else {
    const p = parseFloat(parts[0])
    tonePivotAuto.value = false
    tonePivotUi.value = Number.isFinite(p) ? tonePivotInternalToUi(p) : 0
  }

  if (isAuto(parts[1])) {
    toneCurveAuto.value = true
    toneCurveUi.value = 0
  } else {
    const k = parseFloat(parts[1])
    toneCurveAuto.value = false
    toneCurveUi.value = Number.isFinite(k) ? toneCurveInternalToUi(k) : 0
  }
}

const ctxMenuItems = computed(() => {
  const busy = isAllImagesAffected.value || isCurrentImageAffected.value
  return [
    { label: t('photoEdit.contextMenu.copyParams'), action: copyParams, disabled: busy },
    { label: t('photoEdit.contextMenu.pasteParams'), action: pasteParams, disabled: busy || !paramClipboard.value },
    { label: t('photoEdit.contextMenu.applyPreset'), action: openPresetModal, disabled: busy || globalPresets.value.length === 0 },
    { label: t('photoEdit.contextMenu.pickMaskColor'), action: startEyedropper, disabled: busy || !currentImage.value || !fullResImageUrl.value },
    { label: t('photoEdit.contextMenu.pickWhitePointArea'), action: startAreaSelect, disabled: busy || !currentImage.value || !fullResImageUrl.value },
    { label: t('photoEdit.contextMenu.clearWhitePointArea'), action: clearAreaSelectionForCurrent, disabled: busy || !storedSelectionForCurrent.value },
    { type: 'separator' },
    {
      label: t('photoEdit.contextMenu.rotate'),
      disabled: busy,
      children: [
        { label: t('photoEdit.contextMenu.rotateClockwise'), action: rotateClockwiseBtn, disabled: busy },
        { label: t('photoEdit.contextMenu.rotateCounterClockwise'), action: rotateCounterClockwiseBtn, disabled: busy },
        { label: t('photoEdit.contextMenu.rotate180'), action: rotate180Btn, disabled: busy }
      ]
    },
    { type: 'separator' },
    { label: t('photoEdit.contextMenu.resetImage'), action: resetImage, disabled: busy }
  ]
})

function onContextMenu(e) {
  ctxMenuPos.value = { x: e.clientX, y: e.clientY }
  ctxMenuVisible.value = true
}
const previousImageDimensions = ref({ width: 6000, height: 4000 })
const presetLoaded = ref(false)
const rotateClockwiseMap = ref({}) // Store rotation for each image

const workingDirectory = computed(() => route.query.workingDirectory || '')
const outputDirectory = computed(() => route.query.outputDirectory || '')
const originalDirectory = computed(() => route.query.originalDirectory || '')
const filename = computed(() => route.query.filename || '')

const currentFileName = computed(() => {
  if (images.value[currentIndex.value]) {
    return images.value[currentIndex.value].name
  }
  return ''
})

const currentImage = computed(() => {
  if (images.value[currentIndex.value]) {
    return images.value[currentIndex.value]
  }
  return null
})

const currentRotateClockwise = computed(() => {
  if (currentImage.value) {
    return rotateClockwiseMap.value[currentImage.value.name] || 0
  }
  return 0
})

const isCurrentImageAffected = computed(() => {
  if (!currentImage.value) return false
  return affectedImages.has(currentImage.value.name)
})

const isAllImagesAffected = computed(() => {
  return images.value.length > 0 && images.value.every(img => affectedImages.has(img.name))
})

// Images whose parameters are not yet recorded in .preset.json. Once even
// one image is unapplied, SaveAll is blocked.
const hasUnappliedImages = computed(() => {
  if (!images.value.length || !presetsDataLoaded.value) return false
  return images.value.some(img => !presetsData.value || !presetsData.value[img.name])
})

const isCurrentImageApplied = computed(() => {
  if (!currentFileName.value || !presetsData.value) return false
  return !!presetsData.value[currentFileName.value]
})

// 浮层显示：已 apply（有 output_dir）或正在 apply 或刚完成 apply 等待 presets 刷新。
const isHistogramDisplay = computed(() => {
  if (!currentImage.value) return false
  if (isCurrentImageAffected.value) return true
  if (isCurrentImageApplied.value) return true
  if (pendingApplyImage.value === currentImage.value.name) return true
  return false
})

// 转圈：正在 apply、等待首次采样、或图片未 apply（等待用户操作）。
const isHistogramLoading = computed(() => {
  if (isCurrentImageAffected.value) return true
  if (!isCurrentImageApplied.value) return true
  if (!histogramData.value) return true
  return false
})

const currentDirectoryName = computed(() => {
  if (originalDirectory.value) {
    const parts = originalDirectory.value.split(/[/\\]/)
    return parts[parts.length - 1] || 'Photo Edit'
  }
  return 'Photo Edit'
})

const imageDisplayHeight = computed(() => {
  return `calc(100vh - 64px - 80px - ${operationAreaHeight.value}px)`
})

const updateOperationAreaHeight = () => {
  if (operationAreaRef.value) {
    operationAreaHeight.value = operationAreaRef.value.offsetHeight
  }
}

const handleTabChange = (tabId) => {
  logger.debug('Tab changed to:', tabId)
  // 高度变化由 ResizeObserver 自动捕获，这里无需手动触发
}

// Zoom & pan ──────────────────────────────────────────────────────────

const imageWrapperStyle = computed(() => ({
  transform: `translate(${panOffsetX.value}px, ${panOffsetY.value}px) scale(${zoomLevel.value})`,
  transformOrigin: 'center center',
}))

const mainImageCursor = computed(() => {
  if (eyedropperActive.value || areaSelectActive.value) return undefined
  if (zoomLevel.value > 1) return isPanning.value ? 'grabbing' : 'grab'
  return undefined
})

function onImageDisplayWheel(e) {
  if (!e.ctrlKey && !e.metaKey) return
  if (areaSelectActive.value || eyedropperActive.value) return
  e.preventDefault()

  const display = e.currentTarget
  const rect = display.getBoundingClientRect()
  const mx = e.clientX - rect.left - rect.width / 2
  const my = e.clientY - rect.top - rect.height / 2

  const delta = -e.deltaY * 0.005
  const newZoom = Math.max(0.5, Math.min(5, zoomLevel.value * (1 + delta)))

  const ratio = newZoom / zoomLevel.value
  panOffsetX.value = mx - (mx - panOffsetX.value) * ratio
  panOffsetY.value = my - (my - panOffsetY.value) * ratio
  zoomLevel.value = newZoom
}

function onWrapperMouseDown(e) {
  if (e.button !== 0) return
  if (eyedropperActive.value || areaSelectActive.value) return
  if (zoomLevel.value <= 1) return
  e.preventDefault()
  e.stopPropagation()
  isPanning.value = true
  panStartMouse.value = { x: e.clientX, y: e.clientY }
  panStartOffset.value = { x: panOffsetX.value, y: panOffsetY.value }
  window.addEventListener('mousemove', onPanMouseMove)
  window.addEventListener('mouseup', onPanMouseUp)
}

function onPanMouseMove(e) {
  if (!isPanning.value) return
  panOffsetX.value = panStartOffset.value.x + (e.clientX - panStartMouse.value.x)
  panOffsetY.value = panStartOffset.value.y + (e.clientY - panStartMouse.value.y)
}

function onPanMouseUp() {
  isPanning.value = false
  window.removeEventListener('mousemove', onPanMouseMove)
  window.removeEventListener('mouseup', onPanMouseUp)
}

function resetZoom() {
  zoomLevel.value = 1
  panOffsetX.value = 0
  panOffsetY.value = 0
}

function onImageDblClick() {
  if (eyedropperActive.value || areaSelectActive.value) return
  if (zoomLevel.value === 1) {
    // Zoom to 2x centered on the click point — reset (already at 1x) is a no-op,
    // but dblclick still shouldn't interfere with eyedropper / area-select.
    // For simplicity, just center-zoom to 2x.
    zoomLevel.value = 2
    panOffsetX.value = 0
    panOffsetY.value = 0
  } else {
    resetZoom()
  }
}

let operationAreaResizeObserver = null

const goBack = () => {
  router.push({
    path: '/photo-gallery',
    query: {
      workingDirectory: workingDirectory.value,
      originalDirectory: originalDirectory.value
    }
  })
}

const selectImage = (index) => {
  currentIndex.value = index
  resetZoom()
}

// 旋转已存白点采样区，使其在新方向的图像坐标系中跟随同一块画面内容。
// dims 必须是旋转 *前* 的显示自然像素尺寸，因为 ROI 当前就是这个坐标系。
function rotateStoredAreaSelection(imageName, direction) {
  const stored = areaSelectionsByName.value[imageName]
  if (!stored) return
  const dims = currentImageNaturalDims.value
  if (!dims || !dims.w || !dims.h) return
  const { w, h } = dims
  const { x1, y1, x2, y2 } = stored
  let rotated
  if (direction === '180') {
    rotated = { x1: w - x2, y1: h - y2, x2: w - x1, y2: h - y1 }
  } else if (direction === 'cw') {
    rotated = { x1: h - y2, y1: x1, x2: h - y1, y2: x2 }
    currentImageNaturalDims.value = { w: h, h: w }
  } else {
    rotated = { x1: y1, y1: w - x2, x2: y2, y2: w - x1 }
    currentImageNaturalDims.value = { w: h, h: w }
  }
  areaSelectionsByName.value = {
    ...areaSelectionsByName.value,
    [imageName]: rotated,
  }
  persistAreaSelections()
}

const rotateClockwiseBtn = () => {
  if (!currentImage.value) return
  const imageName = currentImage.value.name
  let currentAngle = rotateClockwiseMap.value[imageName] || 0
  let newAngle = (currentAngle + 90) % 360
  if (newAngle === 360) newAngle = 0
  rotateClockwiseMap.value[imageName] = newAngle
  pendingRotation.value = { imageName, direction: 'cw' }
  apply()
}

const rotateCounterClockwiseBtn = () => {
  if (!currentImage.value) return
  const imageName = currentImage.value.name
  let currentAngle = rotateClockwiseMap.value[imageName] || 0
  let newAngle = currentAngle - 90
  if (newAngle < 0) newAngle = newAngle + 360
  rotateClockwiseMap.value[imageName] = newAngle
  pendingRotation.value = { imageName, direction: 'ccw' }
  apply()
}

const rotate180Btn = () => {
  if (!currentImage.value) return
  const imageName = currentImage.value.name
  const currentAngle = rotateClockwiseMap.value[imageName] || 0
  const newAngle = (currentAngle + 180) % 360
  rotateClockwiseMap.value[imageName] = newAngle
  pendingRotation.value = { imageName, direction: '180' }
  apply()
}

// Helper function to trigger Vue reactivity for images array
const triggerImagesReactivity = () => {
  // Push pop operation to trigger Vue's reactivity system
  const temp = images.value[images.value.length - 1]
  images.value.push(temp)
  images.value.pop()
}

// Helper function to get image URL with timestamp
const getImageUrlWithTimestamp = (image) => {
  // Use image's own timestamp if available, otherwise use current time
  const timestamp = image.timestamp || Date.now()

  // Check if URL already has a 't' parameter
  const urlParts = image.url.split('?')
  if (urlParts.length > 1) {
    // URL already has query parameters
    const baseUrl = urlParts[0]
    const queryString = urlParts[1]
    const params = new URLSearchParams(queryString)

    // Update the 't' parameter
    params.set('t', timestamp)
    return baseUrl + '?' + params.toString()
  } else {
    // URL has no query parameters, add 't' parameter
    return image.url + '?t=' + timestamp
  }
}

// Helper function to update image timestamp and trigger reactivity
// Reset current image: remove preset entry, delete output file, restore
// all UI parameters to defaults, and refresh the display.
const resetImage = () => {
  if (!currentImage.value || !workingDirectory.value) return
  if (!window.require) return

  const ipcRenderer = window.require('electron').ipcRenderer
  const imageName = currentImage.value.name

  ipcRenderer.once('image-reset', (_, result) => {
    if (result.filename !== imageName) return
    // Reset UI parameters
    input1.value = 255
    input2.value = 255
    input3.value = 255
    input4.value = 1
    input5.value = 1
    contrastR.value = 1.0
    contrastG.value = 1.0
    contrastB.value = 1.0
    exposure.value = 0
    whiteBalanceAuto.value = true
    whiteBalanceTemp.value = 0
    whiteBalanceTint.value = 0
    tonePivotUi.value = 0
    toneCurveUi.value = 0
    tonePivotAuto.value = true
    toneCurveAuto.value = true
    rotateClockwiseMap.value[imageName] = 0
    // Clear area selection
    const next = { ...areaSelectionsByName.value }
    delete next[imageName]
    areaSelectionsByName.value = next
    persistAreaSelections()
    // Refresh display
    refreshImage(imageName)
    loadFullResImage()
    loadPresets()
  })

  ipcRenderer.once('image-reset-error', (_, result) => {
    if (result.filename !== imageName) return
    logger.error('Error resetting image:', result.error)
  })

  ipcRenderer.send('reset-image', {
    workingDirectory: workingDirectory.value,
    outputDirectory: outputDirectory.value,
    filename: imageName
  })
}

// After apply succeeds, the on-disk thumbnail/output for `imageName`
// has changed. Ask main to rebuild the entry (so image.url points at
// fresh content + bumps the timestamp) and patch our images array in
// place. Both the thumbnail strip and the main pic re-render together.
const refreshImage = (imageName) => {
  const imageIndex = images.value.findIndex(img => img.name === imageName)
  if (imageIndex === -1 || !window.require) return
  const ipcRenderer = window.require('electron').ipcRenderer

  const onRefreshed = (_, result) => {
    if (result.filename !== imageName) return
    cleanup()
    const idx = images.value.findIndex(img => img.name === imageName)
    if (idx === -1) return
    const ts = Date.now()
    images.value[idx] = { ...images.value[idx], ...result.entry, timestamp: ts }
    triggerImagesReactivity()
  }
  const onError = (_, result) => {
    if (result.filename !== imageName) return
    cleanup()
    logger.error('Error refreshing image:', result.error)
  }
  const cleanup = () => {
    ipcRenderer.removeListener('image-refreshed', onRefreshed)
    ipcRenderer.removeListener('image-refresh-error', onError)
  }

  ipcRenderer.on('image-refreshed', onRefreshed)
  ipcRenderer.on('image-refresh-error', onError)
  ipcRenderer.send('refresh-image', {
    directoryPath: workingDirectory.value,
    filename: imageName
  })
}

const apply = () => {
  if (!currentImage.value || !workingDirectory.value) {
    logger.error('No current image or working directory')
    return
  }

  if (!window.require) {
    logger.error('Not running in Electron')
    return
  }

  // Reset global isSaveAllClicked state
  setSaveAllClicked(false)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    const imageName = currentImage.value.name;

    // Construct parameters string: "mask_r,mask_g,mask_b,gamma,contrast,contrast_r,contrast_g,contrast_b"
    const params = `${input1.value},${input2.value},${input3.value},${input4.value},${input5.value},${contrastR.value},${contrastG.value},${contrastB.value}`

    // Mark image as affected to disable controls
    affectedImages.add(imageName)

    // Send request to main process
    // 注意：area 必须解包成纯对象，reactive proxy 直接发会让 Electron 的 structured clone 静默失败，
    // IPC 包根本到不了主进程。
    const areaForIpc = unwrapArea(areaSelectionsByName.value[imageName])
    const areaBasisForIpc = areaForIpc ? currentAreaBasisForIpc() : null
    ipcRenderer.send('apply-filmparam', {
      inputPath: workingDirectory.value,
      outputPath: outputDirectory.value,
      filename: imageName,
      params: params,
      rotateClockwise: currentRotateClockwise.value,
      area: areaForIpc,
      areaBasis: areaBasisForIpc,
      exposure: exposure.value,
      whiteBalance: currentWhiteBalanceForIpc(),
      tone: currentToneForIpc()
    })

    // Handle response
    ipcRenderer.once('filmparam-apply-started', (_, result) => {
      logger.info(result.message)
    })

    ipcRenderer.once('filmparam-apply-progress', (_, result) => {
      logger.debug(result.data)
    })

    // 使用一个命名的函数，方便处理逻辑
    const handleResponse = (_, result) => {
      // 关键：由于是全局频道，所有的 apply 请求都会触发这个 handleResponse
      // 我们必须判断返回的结果是不是当前这张图
      // result.outputFile 是完整路径，需要从中提取文件名
      const resultFilename = result.outputFile ? path.basename(result.outputFile) : null
      logger.debug(`resultFilename:${resultFilename}    result.outputFile:${result.outputFile}    imageName:${imageName}`)
      if (resultFilename === imageName || result.outputFile?.includes(imageName)) {
        affectedImages.delete(imageName);

        // 旋转操作：IPC 成功后旋转白点选区坐标
        if (pendingRotation.value && pendingRotation.value.imageName === imageName) {
          rotateStoredAreaSelection(imageName, pendingRotation.value.direction)
          pendingRotation.value = null
        }

        // 始终刷新缩略图和 presetsData（用户可能已切走），只有当前展示的图片才刷新主图和直方图
        refreshImage(imageName);
        if (currentImage.value && currentImage.value.name === imageName) {
          pendingApplyImage.value = imageName
          clearHistogramCache();
          loadFullResImage();
          loadPresets();
        } else {
          loadPresets({ skipLoadCurrent: true });
        }

        // 处理完自己的事情后，移除这个特定的监听器
        ipcRenderer.removeListener('filmparam-apply-success', handleResponse);
      }
    };
    ipcRenderer.on('filmparam-apply-success', handleResponse);

    const handleError = (_, error) => {
      logger.error('Error applying film parameters:', error)
      // 关键：同样要判断是不是当前这张图的错误
      // error.outputFile 是完整路径，需要从中提取文件名
      const errorFilename = error.outputFile ? path.basename(error.outputFile) : null
      if (errorFilename === imageName || error.outputFile?.includes(imageName)) {
        // Re-enable controls immediately on error
        affectedImages.delete(imageName);
        // IPC 失败时清除待旋转标记，避免选区被错误旋转
        if (pendingRotation.value && pendingRotation.value.imageName === imageName) {
          pendingRotation.value = null
        }
        // 处理完自己的事情后，移除这个特定的监听器
        ipcRenderer.removeListener('filmparam-apply-error', handleError);
      }
    };
    ipcRenderer.on('filmparam-apply-error', handleError);
  } catch (error) {
    // Re-enable controls immediately on error
    affectedImages.delete(imageName);
    pendingRotation.value = null;
  }
}


const applyAll = () => {
  if (!workingDirectory.value) {
    logger.error('No working directory')
    return
  }

  if (!window.require) {
    logger.error('Not running in Electron')
    return
  }

  // Reset global isSaveAllClicked state
  setSaveAllClicked(false)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    // Construct parameters string: "mask_r,mask_g,mask_b,gamma,contrast"
    const params = `${input1.value},${input2.value},${input3.value},${input4.value},${input5.value}`

    // Mark all images as affected to disable controls
    images.value.forEach(img => affectedImages.add(img.name))

    // Remove existing listeners to avoid duplicates
    ipcRenderer.removeAllListeners('filmparambatch-apply-started')
    ipcRenderer.removeAllListeners('filmparambatch-apply-progress')
    ipcRenderer.removeAllListeners('filmparambatch-apply-success')
    ipcRenderer.removeAllListeners('filmparambatch-apply-error')

    // Send request to main process
    // applyAll 走 filmparambatch，CLI 只能接一个 --area，这里复用当前图片的选区作为整批的取样窗口；
    // 其它图各自的选区暂不生效（saveAll 那条原图通路里再统一处理）。
    const areaForIpc = currentImage.value ? unwrapArea(areaSelectionsByName.value[currentImage.value.name]) : null
    const areaBasisForIpc = areaForIpc ? currentAreaBasisForIpc() : null
    ipcRenderer.send('apply-filmparambatch', {
      inputPath: workingDirectory.value,
      outputPath: outputDirectory.value,
      params: params,
      rotateClockwise: currentRotateClockwise.value,
      area: areaForIpc,
      areaBasis: areaBasisForIpc,
      exposure: exposure.value,
      whiteBalance: currentWhiteBalanceForIpc(),
      tone: currentToneForIpc()
    })

    // Handle response
    ipcRenderer.once('filmparambatch-apply-started', (_, result) => {
      logger.info(result.message)
    })

    ipcRenderer.once('filmparambatch-apply-progress', (_, result) => {
      logger.debug(result.data)
    })

    ipcRenderer.once('filmparambatch-apply-success', (_, result) => {
      logger.info(result.message)
      pendingApplyImage.value = currentImage.value?.name || null
      clearHistogramCache()
      // Update all image timestamps to refresh display without reloading page
      images.value.forEach(img => {
        img.timestamp = Date.now()
      })
      triggerImagesReactivity()
      loadFullResImage()
      // Reload presets and enable controls
      loadPresets()
      affectedImages.clear()
    })

    ipcRenderer.once('filmparambatch-apply-error', (_, error) => {
      logger.error('Error applying film parameters to all images:', error)
      // Re-enable controls immediately on error
      affectedImages.clear()
    })
  } catch (error) {
    logger.error('Error applying film parameters to all images:', error)
    // Re-enable controls immediately on error
    affectedImages.clear()
  }
}

const saveAll = () => {
  if (hasUnappliedImages.value) {
    logger.warn('SaveAll blocked: there are still images without applied parameters')
    return
  }
  if (!workingDirectory.value || !originalDirectory.value) {
    logger.error('No working directory or original directory')
    return
  }

  if (!window.require) {
    logger.error('Not running in Electron')
    return
  }

  // Set global isSaveAllClicked state
  setSaveAllClicked(true)

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    // Mark all images as affected to disable controls
    images.value.forEach(img => affectedImages.add(img.name))

    // Remove existing listeners to avoid duplicates
    ipcRenderer.removeAllListeners('preset-to-batch-started')
    ipcRenderer.removeAllListeners('preset-to-batch-progress')
    ipcRenderer.removeAllListeners('preset-to-batch-success')
    ipcRenderer.removeAllListeners('preset-to-batch-error')

    // Prepare the output directory path
    const outputDir = path.join(originalDirectory.value, 'output')

    // Send request to main process
    ipcRenderer.send('apply-preset-to-batch', {
      presetFile: path.join(workingDirectory.value, '.preset.json'),
      inputDir: originalDirectory.value,
      outputDir: outputDir
    })

    // Handle started
    ipcRenderer.once('preset-to-batch-started', (_, result) => {
      logger.info(result.message)
    })

    // Handle progress
    ipcRenderer.on('preset-to-batch-progress', (_, result) => {
      logger.debug(result.data)
    })

    // Handle success
    ipcRenderer.once('preset-to-batch-success', (_, result) => {
      logger.info(result.message)
      // Update all image timestamps to refresh display without reloading page
      images.value.forEach(img => {
        img.timestamp = Date.now()
      })
      triggerImagesReactivity()
      affectedImages.clear()
    })

    // Handle error
    ipcRenderer.once('preset-to-batch-error', (_, result) => {
      logger.error('Error saving all files:', result.message, result.error)
      affectedImages.clear()
    })
  } catch (error) {
    logger.error('Error saving all files:', error)
    affectedImages.clear()
  }
}

const loadFullResImage = async () => {
  if (!currentImage.value || !workingDirectory.value) {
    fullResImageUrl.value = ''
    return
  }

  if (window.require) {
    try {
      const ipcRenderer = window.require('electron').ipcRenderer

      // Remove existing listeners to avoid duplicates
      ipcRenderer.removeAllListeners('full-res-image-loaded')
      ipcRenderer.removeAllListeners('full-res-image-error')

      ipcRenderer.send('get-full-res-image', {
        directoryPath: workingDirectory.value,
        filename: currentImage.value.name
      })

      // Reuse the per-image timestamp so the main pic's cache-buster is
      // identical to the thumbnail's. After apply, refreshImage rebuilds
      // image.url and bumps timestamp; both views flip together.
      const ts = currentImage.value.timestamp || Date.now()

      ipcRenderer.once('full-res-image-loaded', (_, result) => {
        fullResImageUrl.value = result.url + '?t=' + ts
      })

      ipcRenderer.once('full-res-image-error', (_, error) => {
        logger.error('Error loading full resolution image:', error)
        // Check if this is a RAW file not yet converted
        if (currentImage.value.isRaw && error.error === 'RAW file not yet converted') {
          // Show placeholder for RAW file still converting
          const width = previousImageDimensions.value.width
          const height = previousImageDimensions.value.height
          const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
            <rect width="${width}" height="${height}" fill="#3c3c3c"/>
            <text x="${width / 2}" y="${height / 2}" font-family="Arial, sans-serif" font-size="24" text-anchor="middle" fill="#888888">RAW file converting...</text>
          </svg>`
          fullResImageUrl.value = 'data:image/svg+xml;base64,' + btoa(svg)
        } else {
          fullResImageUrl.value = getImageUrlWithTimestamp(currentImage.value)
        }
      })
    } catch (error) {
      logger.error('Error loading full resolution image:', error)
      fullResImageUrl.value = currentImage.value.url
    }
  } else {
    fullResImageUrl.value = getImageUrlWithTimestamp(currentImage.value)
  }
}

const nextImage = () => {
  if (isAllImagesAffected.value) {
    return
  }
  if (currentIndex.value < images.value.length - 1) {
    currentIndex.value++
  } else {
    currentIndex.value = 0
  }
}

const previousImage = () => {
  if (isAllImagesAffected.value) {
    return
  }
  if (currentIndex.value > 0) {
    currentIndex.value--
  } else {
    currentIndex.value = images.value.length - 1
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape' && eyedropperActive.value) {
    event.preventDefault()
    exitEyedropper()
    return
  }

  if (event.key === 'Escape' && areaSelectActive.value) {
    event.preventDefault()
    exitAreaSelect()
    return
  }

  // Ctrl/Cmd +/-/0: zoom main image instead of browser page
  if ((event.ctrlKey || event.metaKey) && (event.key === '=' || event.key === '+' || event.key === '-' || event.key === '0')) {
    if (areaSelectActive.value || eyedropperActive.value) return
    event.preventDefault()
    if (event.key === '0') {
      resetZoom()
    } else if (event.key === '-' || event.key === '_') {
      const newZoom = Math.max(0.5, zoomLevel.value / 1.2)
      const ratio = newZoom / zoomLevel.value
      panOffsetX.value = panOffsetX.value * ratio
      panOffsetY.value = panOffsetY.value * ratio
      zoomLevel.value = newZoom
    } else {
      const newZoom = Math.min(5, zoomLevel.value * 1.2)
      const ratio = newZoom / zoomLevel.value
      panOffsetX.value = panOffsetX.value * ratio
      panOffsetY.value = panOffsetY.value * ratio
      zoomLevel.value = newZoom
    }
    return
  }

  // Check if this is one of our navigation shortcuts
  const isNavigationShortcut = (event.key === 'ArrowUp' && event.ctrlKey) ||
    (event.key === 'ArrowDown' && event.ctrlKey) ||
    event.key === 'Enter'

  // If it's not a navigation shortcut and the target is an input/textarea, don't process
  if (!isNavigationShortcut && (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA')) {
    return
  }

  switch (event.key) {
    case 's':
    case 'S':
      if (event.ctrlKey) {
        event.preventDefault()
        saveAll()
      }
      break
    case 'Enter':
      event.preventDefault()
      if (event.ctrlKey) {
        applyAll()
      } else {
        apply()
      }
      break
    case 'ArrowDown':
      if (event.ctrlKey) {
        event.preventDefault()
        if (!isAllImagesAffected.value) {
          nextImage()
        }
      }
      break
    case 'ArrowUp':
      if (event.ctrlKey) {
        event.preventDefault()
        if (!isAllImagesAffected.value) {
          previousImage()
        }
      }
      break
  }
}

const loadImages = async () => {
  try {
    isLoading.value = true
    fullResImageUrl.value = ''
    if (!workingDirectory.value) {
      goBack()
      return
    }

    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      ipcRenderer.send('get-images', workingDirectory.value, workingDirectory.value)

      ipcRenderer.once('images-loaded', (_, result) => {
        images.value = result.images.map(img => ({
          ...img,
          timestamp: Date.now()
        }))
        if (filename.value) {
          const index = images.value.findIndex(img => img.name === filename.value)
          if (index !== -1) {
            currentIndex.value = index
          }
        }
        isLoading.value = false
      })

      ipcRenderer.once('images-error', (_, error) => {
        logger.error('Error loading images:', error)
        isLoading.value = false
      })
    } else {
      logger.warn('Not running in Electron, showing demo data')
      isLoading.value = false
    }
  } catch (error) {
    logger.error('Error loading images:', error)
    isLoading.value = false
  }
}

const loadPresets = async ({ skipLoadCurrent = false } = {}) => {
  try {
    if (!workingDirectory.value || !window.require) {
      return
    }

    const ipcRenderer = window.require('electron').ipcRenderer

    ipcRenderer.send('read-preset-json', workingDirectory.value)

    ipcRenderer.once('preset-json-loaded', (_, result) => {
      presetsData.value = result.presets || {}
      presetsDataLoaded.value = true
      if (!skipLoadCurrent) loadPresetForCurrentImage()
    })

    ipcRenderer.once('preset-json-error', (_, error) => {
      logger.error('Error loading preset json:', error)
      presetsDataLoaded.value = true
    })
  } catch (error) {
    logger.error('Error loading preset json:', error)
  }
}

const loadPresetForCurrentImage = () => {
  if (!currentFileName.value || !presetsData.value) {
    return
  }

  const preset = presetsData.value[currentFileName.value]
  if (preset) {
    input1.value = preset.mask_r ?? 255
    input2.value = preset.mask_g ?? 255
    input3.value = preset.mask_b ?? 255
    input4.value = preset.gamma ?? 1
    input5.value = preset.contrast ?? 1
    contrastR.value = preset.contrast_r ?? 1.0
    contrastG.value = preset.contrast_g ?? 1.0
    contrastB.value = preset.contrast_b ?? 1.0
    applyTonePresetToUi(preset)
    rotateClockwiseMap.value[currentFileName.value] = preset.rotate_clockwise || 0
  } else {
    // Reset to default if no preset found
    input1.value = 255
    input2.value = 255
    input3.value = 255
    input4.value = 1
    input5.value = 1
    contrastR.value = 1.0
    contrastG.value = 1.0
    contrastB.value = 1.0
    tonePivotUi.value = 0
    toneCurveUi.value = 0
    tonePivotAuto.value = true
    toneCurveAuto.value = true
    rotateClockwiseMap.value[currentFileName.value] = 0

    // Auto-prompt the apply-preset modal once we know .preset.json was
    // actually read (so we don't flash it during initial mount races) and
    // there's at least one preset to choose from.
    if (presetsDataLoaded.value && globalPresets.value.length > 0 && !presetModalOpen.value) {
      openPresetModal()
    }
  }

  presetLoaded.value = true
}

watch(currentIndex, () => {
  // 切图时强制退出框选模式，避免选区跨图错位；naturalDims 也清掉等新图 onload 重置
  if (areaSelectActive.value) exitAreaSelect()
  currentImageNaturalDims.value = null

  // Get current image dimensions before switching
  const img = new Image()
  img.onload = () => {
    previousImageDimensions.value = { width: img.naturalWidth, height: img.naturalHeight }
  }
  img.src = fullResImageUrl.value

  // Set placeholder image before loading new one
  const width = previousImageDimensions.value.width
  const height = previousImageDimensions.value.height
  const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg"><rect width="${width}" height="${height}" fill="#3c3c3c"/></svg>`
  fullResImageUrl.value = 'data:image/svg+xml;base64,' + btoa(svg)

  // Reset presetLoaded state when switching images
  presetLoaded.value = false

  loadFullResImage()
  loadPresetForCurrentImage()
})

watch(images, () => {
  if (images.value.length > 0) {
    // Initialize rotateClockwiseMap for all images to 0
    images.value.forEach(img => {
      if (!rotateClockwiseMap.value[img.name]) {
        rotateClockwiseMap.value[img.name] = 0
      }
    })
    loadFullResImage()
    loadPresetForCurrentImage()
  }
})

// 当前图片的白点取样区。计算成 computed 让它对 areaSelectionsByName
// 里这一项的增删/改全都触发响应。
const currentImageArea = computed(() => {
  if (!currentImage.value) return null
  return unwrapArea(areaSelectionsByName.value[currentImage.value.name]) || null
})

// 主图刷新（切图、apply 完成）或白点选区改动时重算直方图。
// fullResImageUrl 处理图片身份/时间戳变化，currentImageArea 处理选区变化。
// fetchHistogramFor 内部会判断图片是否已 apply，避免对底片做无意义的采样。
watch([fullResImageUrl, currentImageArea], () => {
  const filename = currentImage.value?.name
  if (filename && workingDirectory.value) {
    fetchHistogramFor(workingDirectory.value, filename, currentImageArea.value)
  } else {
    histogramData.value = null
  }
})

// apply 成功后 loadFullResImage（触发上方 watcher）和 loadPresets（更新 presetsData）
// 是并发异步的。如果 loadPresets 晚于 loadFullResImage 完成，上方 watcher 触发时
// presetsData 尚未更新，守卫会阻止采样。这里兜底：一旦 presetsData 就绪且当前图片
// 已 apply 但还没有直方图数据，补一次采样。
watch(isCurrentImageApplied, (applied) => {
  if (applied) {
    pendingApplyImage.value = null
    const filename = currentImage.value?.name
    if (filename && workingDirectory.value && !histogramData.value) {
      fetchHistogramFor(workingDirectory.value, filename, currentImageArea.value)
    }
  }
})


// 操作面板挂在 v-else 分支里，初次 onMounted 时 ref 还是 null。
// 用 watch 跟踪 ref 的挂载时机，一出现就接上 ResizeObserver，
// 之后元素重挂载也会自动重建。
watch(operationAreaRef, (el) => {
  if (operationAreaResizeObserver) {
    operationAreaResizeObserver.disconnect()
    operationAreaResizeObserver = null
  }
  if (el && typeof ResizeObserver !== 'undefined') {
    operationAreaResizeObserver = new ResizeObserver(updateOperationAreaHeight)
    operationAreaResizeObserver.observe(el)
  }
})

onMounted(() => {
  loadImages()
  loadPresets()
  areaSelectionsByName.value = loadAreaSelections()
  window.addEventListener('keydown', handleKeydown)
  // ResizeObserver 不可用的兜底：监听窗口尺寸变化。
  if (typeof ResizeObserver === 'undefined') {
    window.addEventListener('resize', updateOperationAreaHeight)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', updateOperationAreaHeight)
  // 防御：组件卸载时清掉拖拽期间挂在 window 上的临时监听器
  window.removeEventListener('mousemove', onAreaMouseMoveWindow)
  window.removeEventListener('mouseup', onAreaMouseUpWindow)
  window.removeEventListener('mousemove', onPanMouseMove)
  window.removeEventListener('mouseup', onPanMouseUp)
  if (operationAreaResizeObserver) {
    operationAreaResizeObserver.disconnect()
    operationAreaResizeObserver = null
  }
})
</script>

<style scoped>
.photo-edit-page {
  min-height: 100vh;
  background: var(--bg-page);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
  z-index: 10;
}

.back-button {
  padding: 10px 20px;
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s ease;
}

.back-button:hover {
  background: var(--accent-hover);
}

.file-name {
  font-size: 20px;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
  text-align: center;
}

.directory-name {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-secondary);
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid var(--border-light);
  border-top: 4px solid var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: 24px;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 16px;
  color: var(--text-secondary);
}

.content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

/* Thumbnails Container - Left Side */
.thumbnails-container {
  width: 100px;
  height: calc(100vh - 64px - 80px);
  background: var(--bg-surface);
  border-right: 1px solid var(--border-color);
  overflow-y: scroll;
  overflow-x: hidden;
  flex-shrink: 0;
}

.thumbnails-container::-webkit-scrollbar {
  width: 6px;
}

.thumbnails-container::-webkit-scrollbar-thumb {
  background: var(--btn-disabled-bg);
  border-radius: 3px;
}

.thumbnails-container::-webkit-scrollbar-thumb:hover {
  background: var(--btn-disabled-bg);
}

.thumbnails-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px 10px;
  align-items: center;
  width: 100%;
}

.thumbnail-item {
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
}

.thumbnail-item:hover {
  transform: scale(1.05);
}

.thumbnail-item.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(66, 184, 131, 0.3);
}

.thumbnail-item.affected {
  opacity: 0.7;
}

.thumbnail-item.cursor-wait {
  cursor: wait;
}

.thumbnail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.thumbnail-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid var(--bg-surface);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.thumbnail {
  width: 80px;
  height: 80px;
  object-fit: cover;
  display: block;
}

/* Main Content Area - Right Side */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-width: 0;
}

/* Image Display - Takes available space */
.image-display {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 20px;
  overflow: hidden;
  width: 100%;
  position: relative;
}

.image-display.eyedropper-active,
.image-display.eyedropper-active .main-image,
.image-display.area-select-active,
.image-display.area-select-active .main-image {
  cursor: crosshair;
}

.area-mask-full {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  pointer-events: none;
  z-index: 5;
}

.area-cutout {
  position: absolute;
  border: 2px solid #ff0000;
  box-sizing: border-box;
  pointer-events: none;
  /* 用 9999px 的 spread shadow 反向生成"挖洞"效果，外层 .image-wrapper overflow:hidden 会把它裁到图片边界 */
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
  z-index: 5;
}

.area-stored-preview {
  position: absolute;
  border: 2px solid #ff0000;
  box-sizing: border-box;
  pointer-events: none;
  z-index: 5;
}

.eyedropper-hint,
.area-select-hint {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.78);
  color: var(--text-on-accent);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  z-index: 20;
  pointer-events: none;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.image-wrapper {
  position: relative;
  display: inline-block;
  max-width: 100%;
  height: 100%;
  overflow: hidden;
}

.main-image {
  height: 100%;
  width: auto;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.applying-badge {
  position: absolute;
  bottom: 5%;
  right: 5%;
  background: rgba(0, 0, 0, 0.6);
  color: var(--text-on-accent);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  z-index: 10;
  animation: fadeIn 0.3s ease;
  pointer-events: none;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.preset-modal-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-input);
  cursor: pointer;
}

.preset-modal-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(66, 184, 131, 0.15);
}

/* Operation Area - Fixed at Page Bottom */
.operation-area {
  position: fixed;
  bottom: 0;
  left: 100px;
  right: 0;
  padding: 8px 16px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  z-index: 100;
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}

.tab-content {
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: center;
  padding: 4px 8px;
}

.tab-content.exposure-tab {
  gap: 16px;
}

.exposure-slider {
  flex: 1;
  max-width: 480px;
  min-width: 200px;
}

.tab-content.wb-tab {
  gap: 24px;
  align-items: center;
}

.wb-auto-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.wb-auto-label input[type="checkbox"] {
  cursor: pointer;
}

.wb-auto-label input[type="checkbox"]:disabled {
  cursor: not-allowed;
}

.wb-rows {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 560px;
  min-width: 240px;
}

.wb-row {
  display: flex;
  align-items: end;
  gap: 12px;
}

.wb-row-slider {
  flex: 1;
}

.tab-content.tone-tab {
  gap: 24px;
  align-items: center;
}

.tone-rows {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 560px;
  min-width: 240px;
}

.tone-row {
  display: flex;
  align-items: end;
  gap: 12px;
}

.tone-row-slider {
  flex: 1;
}

.tone-auto-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.tone-auto-label input[type="checkbox"] {
  cursor: pointer;
}

.tone-auto-label input[type="checkbox"]:disabled {
  cursor: not-allowed;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: center;
  width: 100%;
  margin-top: 8px;
}

.apply-button,
.apply-all-button {
  padding: 8px 20px;
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.apply-button:hover:not(:disabled),
.apply-all-button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.apply-button:active:not(:disabled),
.apply-all-button:active:not(:disabled) {
  transform: scale(0.98);
}

.apply-button:disabled,
.apply-all-button:disabled {
  background: var(--btn-disabled-bg);
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
