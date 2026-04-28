import { createI18n } from 'vue-i18n'
import zh_Hans from '../locales/zh_Hans'
import zh_Hant from '../locales/zh_Hant'
import en_US from '../locales/en_US'
import fr_FR from '../locales/fr_FR'
import de_DE from '../locales/de_DE'
import pl_PL from '../locales/pl_PL'
import ru_RU from '../locales/ru_RU'
import es_ES from '../locales/es_ES'
import pt_PT from '../locales/pt_PT'
import ja_JP from '../locales/ja_JP'
import vi_VN from '../locales/vi_VN'
import hi_IN from '../locales/hi_IN'
import bo_CN from '../locales/bo_CN'

const SUPPORTED = [
  'zh_Hans', 'zh_Hant', 'en_US', 'fr_FR', 'de_DE', 'pl_PL',
  'ru_RU', 'es_ES', 'pt_PT', 'ja_JP', 'vi_VN', 'hi_IN', 'bo_CN'
]

function detectInitialLocale() {
  const stored = localStorage.getItem('locale')
  if (stored && SUPPORTED.includes(stored)) return stored

  const candidates = navigator.languages?.length
    ? navigator.languages
    : [navigator.language || '']

  for (const tag of candidates) {
    const lower = String(tag).toLowerCase()
    if (lower.startsWith('zh')) {
      if (
        lower.includes('hant') ||
        lower.startsWith('zh-tw') ||
        lower.startsWith('zh-hk') ||
        lower.startsWith('zh-mo')
      ) {
        return 'zh_Hant'
      }
      return 'zh_Hans'
    }
    if (lower.startsWith('en')) return 'en_US'
    if (lower.startsWith('fr')) return 'fr_FR'
    if (lower.startsWith('de')) return 'de_DE'
    if (lower.startsWith('pl')) return 'pl_PL'
    if (lower.startsWith('ru')) return 'ru_RU'
    if (lower.startsWith('es')) return 'es_ES'
    if (lower.startsWith('pt')) return 'pt_PT'
    if (lower.startsWith('ja')) return 'ja_JP'
    if (lower.startsWith('vi')) return 'vi_VN'
    if (lower.startsWith('hi')) return 'hi_IN'
    if (lower.startsWith('bo')) return 'bo_CN'
  }

  return 'en_US'
}

const i18n = createI18n({
  legacy: false,
  locale: detectInitialLocale(),
  fallbackLocale: 'en_US',
  messages: {
    zh_Hans,
    zh_Hant,
    en_US,
    fr_FR,
    de_DE,
    pl_PL,
    ru_RU,
    es_ES,
    pt_PT,
    ja_JP,
    vi_VN,
    hi_IN,
    bo_CN
  }
})

export default i18n
