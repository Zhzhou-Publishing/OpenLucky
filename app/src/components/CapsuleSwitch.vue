<template>
  <label class="capsule-switch" :class="{ 'is-on': modelValue, 'is-disabled': disabled }">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      class="capsule-switch__input"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="capsule-switch__track">
      <span class="capsule-switch__thumb" />
    </span>
  </label>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<style scoped>
.capsule-switch {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  vertical-align: middle;
}

.capsule-switch__input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}

.capsule-switch__track {
  position: relative;
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: #c0c4cc;
  transition: background 0.25s ease;
}

.capsule-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform 0.25s ease;
}

.capsule-switch.is-on .capsule-switch__track {
  background: #42b883;
}

.capsule-switch.is-on .capsule-switch__thumb {
  transform: translateX(20px);
}

.capsule-switch.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
