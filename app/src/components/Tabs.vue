<template>
  <div class="tabs-container">
    <div class="tabs-header">
      <button
        v-for="(tab, index) in tabs"
        :key="tab.id || index"
        :class="['tab-button', { 'tab-button-active': activeTab === (tab.id || index) }]"
        @click="selectTab(tab.id || index)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="tabs-content">
      <slot :activeTab="activeTab"></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  tabs: {
    type: Array,
    required: true,
    validator: (value) => value.every(tab => tab.label)
  },
  defaultTab: {
    type: [String, Number],
    default: 0
  }
})

const emit = defineEmits(['tab-change'])

const activeTab = ref(props.defaultTab)

const selectTab = (tabId) => {
  activeTab.value = tabId
  emit('tab-change', tabId)
}

watch(() => props.defaultTab, (newDefault) => {
  activeTab.value = newDefault
})
</script>

<style scoped>
.tabs-container {
  width: 100%;
}

.tabs-header {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 16px;
}

.tab-button {
  padding: 12px 24px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: color 0.2s ease;
  font-family: inherit;
}

.tab-button:hover {
  color: #42b883;
}

.tab-button-active {
  color: #42b883;
  font-weight: 600;
}

.tab-button-active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: #42b883;
  border-radius: 2px 2px 0 0;
}

.tabs-content {
  padding: 8px 0;
}
</style>
