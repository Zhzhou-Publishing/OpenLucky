export default {
  navbar: {
    home: '首頁',
    about: '關於',
    leaveConfirm: '離開當前頁面將會丟失已載入的圖片，確定繼續嗎？',
    closeConfirm: '關閉視窗將會遺失尚未儲存的修改，確定要關閉嗎？'
  },
  photoDirectory: {
    title: '選擇相片目錄',
    description: '選擇包含您相片的本地文件夾',
    installationError: '❌ 軟件安裝不完整。這可能是因為您的防毒軟件損壞了軟件。請重新安裝。',
    electronWarning: '⚠️ 未在 Electron 環境中運行',
    selectButton: '📁 選擇目錄',
    loading: '載入中...',
    selectedPath: '已選擇路徑：',
    processingProgress: '正在準備預覽'
  },
  photoGallery: {
    back: '← 返回',
    refresh: '🔄 刷新',
    imagesCount: '{count} 張圖片',
    loading: '載入圖片中...',
    noImages: '找不到圖片',
    noImagesDesc: '在所選目錄中找不到圖片文件（jpg、jpeg、png、gif、webp、tiff、arw、cr2、cr3、nef、dng、orf 或 raf）。',
    applying: '應用中...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: '應用中',
    saving: '儲存中'
  },
  photoEdit: {
    back: '← 返回',
    loading: '載入圖片中...',
    noImages: '找不到圖片',
    noImagesDesc: '目錄中找不到圖片文件。',
    applying: '應用中...',
    previewing: '預覽中...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Gamma',
    contrast: '對比度',
    apply: '應用',
    applyAll: '全部應用',
    basicTab: '基礎參數',
    advancedTab: '乳劑濃度校正',
    contrastR: '對比度 R',
    contrastG: '對比度 G',
    contrastB: '對比度 B',
    contextMenu: {
      copyParams: '複製參數',
      pasteParams: '貼上參數',
      rotate: '旋轉',
      rotateClockwise: '順時針 90°',
      rotateCounterClockwise: '逆時針 90°'
    }
  },
  bottomMenu: {
    preset: '預設：',
    apply: '應用',
    applying: '應用中...'
  },
  saveAllButton: {
    saveAll: '全部儲存'
  },
  about: {
    title: '關於 OpenLucky 桌面版',
    version: '版本信息',
    description: '描述',
    descriptionText: 'OpenLucky 桌面版是一個用於底片處理和批量操作的強大桌面應用程序。基於 Electron 和 Vue 3 構建，為管理工作流程提供了現代且高效的界面。',
    homepage: '項目首頁',
    license: '開源許可證',
    licenseSummary: '允許商業使用、修改、分發與私人使用；需保留版權聲明並標明重大變更；不授予商標權，亦不提供任何擔保。',
    language: '語言 Language'
  }
}
