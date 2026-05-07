export default {
  navbar: {
    home: '홈',
    about: '정보(情報)',
    leaveConfirm: '이 페이지를 떠나면 불러온 사진 데이터가 삭제될 수 있습니다. 계속하시겠습니까?',
    closeConfirm: '창을 닫으면 저장(貯藏)되지 않은 변경(變更) 사항이 손실(損失)됩니다. 그래도 닫으시겠습니까?'
  },
  photoDirectory: {
    title: '사진 폴더 선택',
    description: '사진이 들어 있는 로컬 폴더를 선택하세요.',
    installationError: '❌ 소프트웨어 설치가 불완전(不完全)합니다. 백신(Vaccine) 프로그램이 일부 파일을 손상시켰을 수 있습니다. 다시 설치해 주세요.',
    electronWarning: '⚠️ Electron 환경(環境)에서 실행 중이 아닙니다.',
    selectButton: '📁 폴더 선택',
    loading: '불러오는 중...',
    selectedPath: '선택한 경로(經路):',
    processingProgress: '미리보기 준비(準備) 중',
    compressPreview: '미리보기 압축(壓縮)',
    compressPreviewTip: '미리보기를 빠르게 하기 위해 썸네일이 1920px 너비로 압축(壓縮)됩니다. 마스크 제거(除去) 미리보기는 빨라지지만 불러오는 과정(過程)은 느려집니다.',
    cancel: '취소(取消)',
  },
  photoGallery: {
    back: '← 뒤로',
    refresh: '🔄 새로고침',
    imagesCount: '사진 {count}장',
    loading: '사진을 불러오는 중...',
    noImages: '사진을 찾을 수 없습니다',
    noImagesDesc: '선택한 폴더에서 사진 파일(jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf, raf)을 찾지 못했습니다.',
    applying: '적용(適用) 중...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: '적용(適用) 중',
    saving: '저장(貯藏) 중'
  },
  photoEdit: {
    back: '← 뒤로',
    loading: '사진을 불러오는 중...',
    noImages: '사진을 찾을 수 없습니다',
    noImagesDesc: '폴더에서 사진 파일을 찾지 못했습니다.',
    applying: '적용(適用) 중...',
    previewing: '미리보기 생성 중...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: '감마(Gamma)',
    contrast: '대비(對比)',
    apply: '적용(適用)',
    applyAll: '모두에 적용(適用)',
    basicTab: '기본 매개변수(媒介變數)',
    advancedTab: '유제(乳劑) 농도(濃度) 보정(補正)',
    exposureTab: '노출(露出)',
    whiteBalanceTab: '화이트밸런스',
    whiteBalanceAuto: '자동(自動)',
    whiteBalanceTemp: '색온도(色溫度)',
    whiteBalanceTint: '색조(色調)',
    contrastR: '대비(對比) R',
    contrastG: '대비(對比) G',
    contrastB: '대비(對比) B',
    contextMenu: {
      copyParams: '매개변수(媒介變數) 복사',
      pasteParams: '매개변수(媒介變數) 붙여넣기',
      applyPreset: '프리셋 적용(適用)',
      pickMaskColor: '마스크 색상(色相) 추출(抽出)',
      pickWhitePointArea: '화이트 포인트 영역(領域) 선택(選擇)',
      clearWhitePointArea: '화이트 포인트 영역(領域) 지우기',
      rotate: '회전(回轉)',
      rotateClockwise: '시계 방향 90°',
      rotateCounterClockwise: '반시계 방향 90°',
      rotate180: '180° 회전',
      resetImage: '이미지 재설정(再設定)',
    },
    eyedropper: {
      exitHint: '스포이트 활성(活性) — 이미지를 클릭(click)하여 추출(抽出), ESC로 취소(取消)'
    },
    areaSelect: {
      exitHint: '영역(領域) 선택(選擇) 활성(活性) — 좌상단(左上端)에서 우하단(右下端)으로 드래그, ESC로 취소(取消)'
    },
    applyPresetModal: {
      title: '프리셋 선택(選擇)',
      save: '적용(適用)',
      pickColor: '마스크 색상(色相) 추출(抽出)'
    }
  },
  bottomMenu: {
    preset: '사전 설정(設定):',
    apply: '적용(適用)',
    applying: '적용(適用) 중...'
  },
  saveAllButton: {
    saveAll: '모두 저장(貯藏)',
    unappliedTooltip: '매개변수(媒介變數)가 적용(適用)되지 않은 사진이 있습니다'
  },
  about: {
    title: 'OpenLucky Desktop 정보(情報)',
    version: '버전 정보(情報)',
    description: '설명(說明)',
    descriptionText: 'OpenLucky Desktop은 필름 처리(處理)와 일괄(一括) 작업을 위한 강력한 데스크톱 응용 프로그램입니다. Electron과 Vue 3로 제작되어 작업 흐름을 관리할 수 있는 현대적이고 효율적인 사용자 인터페이스를 제공합니다.',
    homepage: '프로젝트 홈페이지',
    license: '라이선스(License)',
    licenseSummary: '상업적 사용, 수정, 배포(配布), 사적 사용을 허용합니다. 저작권 표시를 유지하고 중요한 변경 사항을 명시해야 하며, 상표권은 부여하지 않고 어떠한 보증도 제공하지 않습니다.',
    language: '언어(言語) Language',
    theme: '테마',
    themeLight: '밝은 테마',
    themeDark: '어두운 테마'
  },
  languageSwitcher: {
    label: '언어(言語)'
  }
}