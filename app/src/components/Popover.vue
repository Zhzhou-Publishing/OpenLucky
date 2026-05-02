<template>
  <span class="popover-trigger">
    <span class="popover-icon">?</span>
    <span class="popover-bubble">{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  text: string
}>()
</script>

<style scoped>
.popover-trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: help;
}

.popover-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid #999;
  color: #999;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  transition: border-color 0.2s, color 0.2s;
}

.popover-trigger:hover .popover-icon {
  border-color: #42b883;
  color: #42b883;
}

.popover-bubble {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  background: #333;
  color: #fff;
  font-size: 13px;
  line-height: 1.5;
  padding: 10px 14px;
  border-radius: 8px;
  white-space: normal;
  width: 260px;
  text-align: left;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0.2s ease;
  z-index: 100;
  pointer-events: none;
}

.popover-bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #333;
}

.popover-trigger:hover .popover-bubble {
  opacity: 1;
  visibility: visible;
}
</style>
