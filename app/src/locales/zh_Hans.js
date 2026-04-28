export default {
  navbar: {
    home: '首页',
    about: '关于',
    leaveConfirm: '离开当前页面将丢失已加载的图片，确定继续吗？',
    closeConfirm: '关闭窗口将丢失尚未保存的修改，确定要关闭吗？'
  },
  photoDirectory: {
    title: '选择照片目录',
    description: '选择包含您照片的本地文件夹',
    installationError: '❌ 软件安装不完整。这可能是因为您的杀毒软件损坏了软件。请重新安装。',
    electronWarning: '⚠️ 未在 Electron 环境中运行',
    selectButton: '📁 选择目录',
    loading: '加载中...',
    selectedPath: '已选择路径:',
    processingProgress: '正在准备预览'
  },
  photoGallery: {
    back: '← 返回',
    refresh: '🔄 刷新',
    imagesCount: '{count} 张图片',
    loading: '加载图片中...',
    noImages: '未找到图片',
    noImagesDesc: '在选定的目录中未找到图片文件（jpg、jpeg、png、gif、webp、tiff、arw、cr2、cr3、nef、dng、orf 或 raf）。',
    applying: '应用中...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: '应用中',
    saving: '保存中'
  },
  photoEdit: {
    back: '← 返回',
    loading: '加载图片中...',
    noImages: '未找到图片',
    noImagesDesc: '目录中未找到图片文件。',
    applying: '应用中...',
    previewing: '预览中...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Gamma',
    contrast: '对比度',
    apply: '应用',
    applyAll: '全部应用',
    basicTab: '基础参数',
    advancedTab: '乳剂浓度校正',
    contrastR: '对比度 R',
    contrastG: '对比度 G',
    contrastB: '对比度 B',
    contextMenu: {
      copyParams: '复制参数',
      pasteParams: '粘贴参数',
      rotate: '旋转',
      rotateClockwise: '顺时针 90°',
      rotateCounterClockwise: '逆时针 90°'
    }
  },
  bottomMenu: {
    preset: '预设:',
    apply: '应用',
    applying: '应用中...'
  },
  saveAllButton: {
    saveAll: '全部保存'
  },
  about: {
    title: '关于 OpenLucky 桌面版',
    version: '版本信息',
    description: '描述',
    descriptionText: 'OpenLucky 桌面版是一个用于胶片处理和批量操作的强大桌面应用程序。基于 Electron 和 Vue 3 构建，它为管理工作流程提供了现代高效的界面。',
    homepage: '项目首页',
    license: '开源协议',
    licenseSummary: '允许商业使用、修改、分发与私人使用；需保留版权声明并标明重大改动；不授予商标权，亦不提供任何担保。',
    language: '语言 Language'
  }
}
