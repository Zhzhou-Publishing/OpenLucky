<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="context-menu"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
      @contextmenu.prevent
    >
      <template v-for="(item, idx) in items" :key="idx">
        <div v-if="item.type === 'separator'" class="ctx-separator" />
        <div
          v-else
          class="ctx-row"
          :class="{
            'ctx-disabled': item.disabled,
            'ctx-has-children': !!item.children,
            'ctx-active': openIndex === idx
          }"
          @mouseenter="onRowEnter(idx, $event)"
          @click="onRowClick(item)"
        >
          <span class="ctx-label">{{ item.label }}</span>
          <span v-if="item.children" class="ctx-arrow">▸</span>
        </div>
      </template>
    </div>
    <ContextMenu
      v-if="modelValue && currentChildren"
      :model-value="true"
      :items="currentChildren"
      :position="submenuPos"
      :is-submenu="true"
      @select="onChildSelect"
    />
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, nextTick } from 'vue'
import ContextMenu from './ContextMenu.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
  position: { type: Object, default: () => ({ x: 0, y: 0 }) },
  isSubmenu: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select'])

const openIndex = ref(-1)
const submenuPos = ref({ x: 0, y: 0 })

const currentChildren = computed(() =>
  openIndex.value !== -1 ? props.items[openIndex.value]?.children : null
)

function onRowEnter(idx, evt) {
  const item = props.items[idx]
  if (item.disabled || item.type === 'separator') {
    openIndex.value = -1
    return
  }
  if (item.children) {
    const rect = evt.currentTarget.getBoundingClientRect()
    submenuPos.value = { x: rect.right - 4, y: rect.top - 4 }
    openIndex.value = idx
  } else {
    openIndex.value = -1
  }
}

function onRowClick(item) {
  if (item.disabled || item.type === 'separator' || item.children) return
  emit('select', item)
  if (typeof item.action === 'function') item.action()
  if (!props.isSubmenu) emit('update:modelValue', false)
}

function onChildSelect(item) {
  emit('select', item)
  if (!props.isSubmenu) emit('update:modelValue', false)
}

function close() {
  emit('update:modelValue', false)
}

function onDocPointer(e) {
  if (!props.modelValue) return
  if (!e.target?.closest?.('.context-menu')) close()
}

function onKey(e) {
  if (e.key === 'Escape') close()
}

watch(() => props.modelValue, (v) => {
  if (props.isSubmenu) return
  if (v) {
    nextTick(() => {
      document.addEventListener('mousedown', onDocPointer, true)
      document.addEventListener('contextmenu', onDocPointer, true)
      document.addEventListener('keydown', onKey)
    })
  } else {
    openIndex.value = -1
    document.removeEventListener('mousedown', onDocPointer, true)
    document.removeEventListener('contextmenu', onDocPointer, true)
    document.removeEventListener('keydown', onKey)
  }
})

onBeforeUnmount(() => {
  if (props.isSubmenu) return
  document.removeEventListener('mousedown', onDocPointer, true)
  document.removeEventListener('contextmenu', onDocPointer, true)
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 1000;
  min-width: 200px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: 0 6px 18px var(--shadow);
  padding: 4px 0;
  font-size: 14px;
  color: var(--text-primary);
  user-select: none;
}

.ctx-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 14px;
  cursor: pointer;
  transition: background 0.1s ease, color 0.1s ease;
}

.ctx-row:hover:not(.ctx-disabled),
.ctx-row.ctx-active:not(.ctx-disabled) {
  background: var(--bg-surface-hover);
  color: var(--accent);
}

.ctx-row.ctx-disabled {
  color: var(--text-tertiary);
  cursor: default;
}

.ctx-arrow {
  font-size: 11px;
  color: var(--text-tertiary);
}

.ctx-row.ctx-active .ctx-arrow,
.ctx-row:hover:not(.ctx-disabled) .ctx-arrow {
  color: var(--accent);
}

.ctx-separator {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.ctx-label {
  flex: 1;
  white-space: nowrap;
}
</style>
