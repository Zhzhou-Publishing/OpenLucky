<template>
  <div class="language-switcher">
    <select v-model="currentLocale" class="language-select" @change="changeLanguage">
      <option value="zh_Hans">简体中文</option>
      <option value="zh_Hant">繁體中文</option>
      <option value="bo_CN">བོད་ཡིག (藏语)</option>
      <option value="en_US">English (United States)</option>
      <option value="fr_FR">Français</option>
      <option value="de_DE">Deutsch</option>
      <option value="pl_PL">Polski</option>
      <option value="ru_RU">Русский</option>
      <option value="es_ES">Español</option>
      <option value="pt_PT">Português</option>
      <option value="ja_JP">日本語</option>
      <option value="vi_VN">Tiếng Việt</option>
      <option value="hi_IN">हिन्दी</option>
    </select>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()
const currentLocale = ref(locale.value)

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
