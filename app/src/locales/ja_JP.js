export default {
  navbar: {
    home: 'ホーム',
    about: 'について',
    leaveConfirm: 'このページを離れると、読み込んだ画像は失われます。続行しますか？',
    closeConfirm: 'ウィンドウを閉じると保存していない変更が失われます。閉じてもよろしいですか？'
  },
  photoDirectory: {
    title: '写真の場所を選択',
    description: '写真が保存されている場所を選択してください',
    installationError: '❌ 本ソフトの導入が不完全です。お使いのウイルス対策ソフトによって損傷した可能性があります。再度導入してください。',
    electronWarning: '⚠️ Electron 環境で実行されていません',
    selectButton: '📁 場所を選択',
    loading: '読み込み中...',
    selectedPath: '選択された場所：',
    processingProgress: 'プレビューを準備中',
    compressPreview: 'プレビューを圧縮',
    compressPreviewTip: 'サムネイルを 1920px 幅に圧縮してプレビューを高速化します。マスク除去のプレビューは速くなりますが、読み込み処理は遅くなります。',
    cancel: 'キャンセル',
  },
  photoGallery: {
    back: '← 戻る',
    refresh: '🔄 更新',
    imagesCount: '{count} 枚の画像',
    loading: '画像を読み込み中...',
    noImages: '画像が見つかりません',
    noImagesDesc: '選択された場所には画像（jpg、jpeg、png、gif、webp、tiff、arw、cr2、cr3、nef、dng、orf、raf）が見つかりませんでした。',
    applying: '適用中...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: '適用中',
    saving: '保存中'
  },
  photoEdit: {
    back: '← 戻る',
    loading: '画像を読み込み中...',
    noImages: '画像が見つかりません',
    noImagesDesc: '選択された場所に画像が見つかりませんでした。',
    applying: '適用中...',
    previewing: 'プレビュー中...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'ガンマ',
    contrast: 'コントラスト',
    apply: '適用',
    applyAll: 'すべてに適用',
    basicTab: '基本設定',
    advancedTab: '乳剤濃度補正',
    exposureTab: '露出',
    toneTab: 'ラチチュード補正',
    tonePivot: '露出ピボット',
    toneCurve: '露出コントラスト',
    tonePivotLeft: '左へシフト',
    tonePivotRight: '右へシフト',
    toneCurveLeft: 'コントラストを下げる',
    toneCurveRight: 'コントラストを上げる',
    whiteBalanceTab: 'ホワイトバランス',
    whiteBalanceAuto: '自動',
    whiteBalanceTemp: '色温',
    whiteBalanceTint: '色合い',
    contrastR: 'コントラスト R',
    contrastG: 'コントラスト G',
    contrastB: 'コントラスト B',
    contextMenu: {
      copyParams: 'パラメータをコピー',
      pasteParams: 'パラメータを貼り付け',
      applyPreset: 'プリセットを適用',
      pickMaskColor: 'マスクの色を取得',
      pickWhitePointArea: 'ホワイトポイント領域を選択',
      clearWhitePointArea: 'ホワイトポイント領域をクリア',
      rotate: '回転',
      rotateClockwise: '時計回り 90°',
      rotateCounterClockwise: '反時計回り 90°',
      rotate180: '180° 回転',
      resetImage: '画像をリセット',
    },
    eyedropper: {
      exitHint: 'スポイトモード — 画像をクリックして取得、ESC でキャンセル'
    },
    areaSelect: {
      exitHint: '領域選択モード — 左上から右下へドラッグして領域を選択、ESC でキャンセル'
    },
    applyPresetModal: {
      title: 'プリセットを選択',
      save: '適用',
      pickColor: 'マスクの色を取得'
    }
  },
  bottomMenu: {
    preset: 'プリセット：',
    apply: '適用',
    applying: '適用中...'
  },
  saveAllButton: {
    saveAll: 'すべて保存',
    unappliedTooltip: 'パラメータが適用されていない画像があります'
  },
  languageMismatch: {
    message: 'システム言語と現在の表示言語が一致しません。システム言語に切り替えますか？',
    yes: 'はい',
    no: 'いいえ',
    dontRemind: 'いいえ、今後表示しない'
  },
  about: {
    title: 'OpenLucky Desktop について',
    version: 'バージョン情報',
    description: '説明',
    descriptionText: 'OpenLucky Desktop はフィルム処理と一括操作のための強力なソフトウェアです。Electron と Vue 3 で構築され、作業の流れを管理するための現代的で効率的な操作画面を提供します。',
    homepage: '公式サイト',
    license: '使用許諾',
    licenseSummary: '商用利用、改変、配布、私的利用を許可しています。著作権表示の保持と重要な変更点の明示が必要です。商標権の付与はなく、いかなる保証も提供しません。',
    language: '言語 Language',
    theme: 'テーマ',
    themeLight: 'ライト',
    themeDark: 'ダーク'
  }
}
