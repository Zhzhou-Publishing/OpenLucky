export default {
  navbar: {
    home: 'Strona główna',
    about: 'O programie',
    leaveConfirm: 'Opuszczenie tej strony spowoduje utratę załadowanych obrazów. Kontynuować?',
    closeConfirm: 'Niezapisane zmiany zostaną utracone po zamknięciu okna. Zamknąć mimo to?'
  },
  photoDirectory: {
    title: 'Wybierz katalog zdjęć',
    description: 'Wybierz lokalny folder zawierający Twoje zdjęcia',
    installationError: '❌ Instalacja oprogramowania jest niekompletna. Możliwe, że Twój program antywirusowy uszkodził oprogramowanie. Proszę zainstalować ponownie.',
    electronWarning: '⚠️ Nie uruchomiono w środowisku Electron',
    selectButton: '📁 Wybierz katalog',
    loading: 'Ładowanie...',
    selectedPath: 'Wybrana ścieżka:',
    processingProgress: 'Przygotowywanie podglądu',
    compressPreview: 'Kompresuj podgląd',
    compressPreviewTip: 'Miniatury zostaną skompresowane do szerokości 1920 px, aby przyspieszyć podgląd. Przyspiesza to podgląd usuwania maski, ale spowalnia proces ładowania.',
    cancel: 'Anuluj',
  },
  photoGallery: {
    back: '← Wstecz',
    refresh: '🔄 Odśwież',
    imagesCount: '{count} obrazów',
    loading: 'Ładowanie obrazów...',
    noImages: 'Nie znaleziono obrazów',
    noImagesDesc: 'W wybranym katalogu nie znaleziono plików obrazów (jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf lub raf).',
    applying: 'Stosowanie...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: 'Stosowanie',
    saving: 'Zapisywanie'
  },
  photoEdit: {
    back: '← Wstecz',
    loading: 'Ładowanie obrazów...',
    noImages: 'Nie znaleziono obrazów',
    noImagesDesc: 'Nie znaleziono plików obrazów w katalogu.',
    applying: 'Stosowanie...',
    previewing: 'Podgląd...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Gamma',
    contrast: 'Kontrast',
    apply: 'Zastosuj',
    applyAll: 'Zastosuj do wszystkich',
    basicTab: 'Parametry podstawowe',
    advancedTab: 'Korekcja stężenia emulsji',
    exposureTab: 'Ekspozycja',
    toneTab: 'Korekta szerokości tonalnej',
    tonePivot: 'Punkt obrotu ekspozycji',
    toneCurve: 'Kontrast ekspozycji',
    tonePivotLeft: 'Przesuń w lewo',
    tonePivotRight: 'Przesuń w prawo',
    toneCurveLeft: 'Obniż kontrast',
    toneCurveRight: 'Podnieś kontrast',
    toneAuto: 'Automatyczny',
    whiteBalanceTab: 'Balans bieli',
    whiteBalanceAuto: 'Automatyczny',
    whiteBalanceTemp: 'Temperatura',
    whiteBalanceTint: 'Odcień',
    contrastR: 'Kontrast R',
    contrastG: 'Kontrast G',
    contrastB: 'Kontrast B',
    contextMenu: {
      copyParams: 'Kopiuj parametry',
      pasteParams: 'Wklej parametry',
      applyPreset: 'Zastosuj preset',
      pickMaskColor: 'Pobierz kolor maski',
      pickWhitePointArea: 'Wybierz obszar punktu bieli',
      clearWhitePointArea: 'Wyczyść obszar punktu bieli',
      rotate: 'Obróć',
      rotateClockwise: 'Zgodnie z ruchem wskazówek zegara 90°',
      rotateCounterClockwise: 'Przeciwnie do ruchu wskazówek zegara 90°',
      rotate180: 'Obróć o 180°',
      resetImage: 'Resetuj obraz',
    },
    eyedropper: {
      exitHint: 'Pipeta aktywna — kliknij obraz, aby pobrać, ESC aby anulować'
    },
    areaSelect: {
      exitHint: 'Wybór obszaru aktywny — przeciągnij od lewego górnego do prawego dolnego rogu, ESC aby anulować'
    },
    applyPresetModal: {
      title: 'Wybierz preset',
      save: 'Zastosuj',
      pickColor: 'Pobierz kolor maski'
    }
  },
  bottomMenu: {
    preset: 'Ustawienie wstępne:',
    apply: 'Zastosuj',
    applying: 'Stosowanie...'
  },
  saveAllButton: {
    saveAll: 'Zapisz wszystkie',
    unappliedTooltip: 'Niektóre obrazy nie mają jeszcze zastosowanych parametrów'
  },
  languageMismatch: {
    message: 'Język systemu różni się od bieżącego języka interfejsu. Przełączyć na język systemu?',
    yes: 'Tak',
    no: 'Nie',
    dontRemind: 'Nie, nie przypominaj ponownie'
  },
  about: {
    title: 'O OpenLucky Desktop',
    version: 'Informacje o wersji',
    description: 'Opis',
    descriptionText: 'OpenLucky Desktop to potężna aplikacja desktopowa do przetwarzania filmu fotograficznego i operacji wsadowych. Zbudowana z Electron i Vue 3, zapewnia nowoczesny i wydajny interfejs użytkownika do zarządzania przepływem pracy.',
    homepage: 'Strona główna projektu',
    license: 'Licencja',
    licenseSummary: 'Zezwala na użytek komercyjny, modyfikację, dystrybucję i użytek prywatny; wymaga zachowania informacji o prawach autorskich oraz wskazania istotnych zmian; nie udziela praw do znaków towarowych i nie zapewnia żadnej gwarancji.',
    language: 'Język Language',
    theme: 'Motyw',
    themeLight: 'Jasny',
    themeDark: 'Ciemny'
  }
}
