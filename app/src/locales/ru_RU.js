export default {
  navbar: {
    home: 'Главная',
    about: 'О программе',
    leaveConfirm: 'Уход с этой страницы приведёт к потере загруженных изображений. Продолжить?',
    closeConfirm: 'Несохранённые изменения будут потеряны при закрытии окна. Всё равно закрыть?'
  },
  photoDirectory: {
    title: 'Выбрать каталог с фотографиями',
    description: 'Выберите локальную папку с вашими фотографиями',
    installationError: '❌ Установка программы неполная. Возможно, антивирус повредил файлы программы. Пожалуйста, переустановите.',
    electronWarning: '⚠️ Не запущено в среде Electron',
    selectButton: '📁 Выбрать каталог',
    loading: 'Загрузка...',
    selectedPath: 'Выбранный путь:',
    processingProgress: 'Preparing preview',
    compressPreview: 'Compress Preview',
    compressPreviewTip: 'Thumbnails will be compressed to 1920px width to speed up preview. This speeds up mask removal preview but slows down the loading process.'
  },
  photoGallery: {
    back: '← Назад',
    refresh: '🔄 Обновить',
    imagesCount: '{count} изображений',
    loading: 'Загрузка изображений...',
    noImages: 'Изображения не найдены',
    noImagesDesc: 'В выбранном каталоге не найдено файлов изображений (jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf или raf).',
    applying: 'Применение...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: 'Применение',
    saving: 'Сохранение'
  },
  photoEdit: {
    back: '← Назад',
    loading: 'Загрузка изображений...',
    noImages: 'Изображения не найдены',
    noImagesDesc: 'В каталоге не найдено файлов изображений.',
    applying: 'Применение...',
    previewing: 'Предпросмотр...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Гамма',
    contrast: 'Контраст',
    apply: 'Применить',
    applyAll: 'Применить ко всем',
    basicTab: 'Основные параметры',
    advancedTab: 'Коррекция плотности эмульсии',
    exposureTab: 'Экспозиция',
    whiteBalanceTab: 'Баланс белого',
    whiteBalanceAuto: 'Авто',
    whiteBalanceTemp: 'Температура',
    whiteBalanceTint: 'Оттенок',
    contrastR: 'Контраст R',
    contrastG: 'Контраст G',
    contrastB: 'Контраст B',
    contextMenu: {
      copyParams: 'Копировать параметры',
      pasteParams: 'Вставить параметры',
      applyPreset: 'Применить пресет',
      pickMaskColor: 'Взять цвет маски',
      pickWhitePointArea: 'Выбрать область белой точки',
      clearWhitePointArea: 'Очистить область белой точки',
      rotate: 'Поворот',
      rotateClockwise: 'По часовой 90°',
      rotateCounterClockwise: 'Против часовой 90°',
      resetImage: 'Reset Image',
    },
    eyedropper: {
      exitHint: 'Пипетка активна — кликните по изображению, ESC для отмены'
    },
    areaSelect: {
      exitHint: 'Выбор области активен — перетащите от верхнего-левого к нижнему-правому углу, ESC для отмены'
    },
    applyPresetModal: {
      title: 'Выберите пресет',
      save: 'Применить',
      pickColor: 'Взять цвет маски'
    }
  },
  bottomMenu: {
    preset: 'Предустановка:',
    apply: 'Применить',
    applying: 'Применение...'
  },
  saveAllButton: {
    saveAll: 'Сохранить все',
    unappliedTooltip: 'У некоторых изображений ещё не применены параметры'
  },
  about: {
    title: 'О программе OpenLucky Desktop',
    version: 'Информация о версии',
    description: 'Описание',
    descriptionText: 'OpenLucky Desktop — мощное настольное приложение для обработки плёнки и пакетных операций. Создано на Electron и Vue 3, оно предоставляет современный и эффективный интерфейс для управления рабочими процессами.',
    homepage: 'Главная страница проекта',
    license: 'Лицензия',
    licenseSummary: 'Разрешает коммерческое использование, изменение, распространение и частное использование; требует сохранения уведомления об авторских правах и указания значительных изменений; не предоставляет прав на товарные знаки и не даёт никаких гарантий.',
    language: 'Язык Language'
  }
}
