import { createI18n } from 'vue-i18n'
import zh_Hans from '../locales/zh_Hans'
import en_US from '../locales/en_US'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh_Hans',
  fallbackLocale: 'en_US',
  messages: {
    zh_Hans,
    en_US
  }
})

export default i18n
