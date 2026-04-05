<template>
  <div class="language-switcher">
    <label class="language-label">{{ $t('languageSwitcher.label') }}:</label>
    <select v-model="currentLocale" class="language-select" @change="changeLanguage">
      <option value="zh_Hans">{{ $t('languageSwitcher.zh_Hans') }}</option>
      <option value="en_US">{{ $t('languageSwitcher.en_US') }}</option>
    </select>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()
const currentLocale = ref(localStorage.getItem('locale') || 'zh_Hans')

const changeLanguage = () => {
  locale.value = currentLocale.value
  localStorage.setItem('locale', currentLocale.value)
}

watch(locale, (newLocale) => {
  currentLocale.value = newLocale
  localStorage.setItem('locale', newLocale)
})
</script>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
}

.language-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.language-select {
  padding: 6px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.language-select:hover {
  border-color: #42b883;
}

.language-select:focus {
  outline: none;
  border-color: #42b883;
  box-shadow: 0 0 0 3px rgba(66, 184, 131, 0.1);
}
</style>
