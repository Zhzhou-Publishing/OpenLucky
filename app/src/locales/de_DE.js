export default {
  navbar: {
    home: 'Startseite',
    about: 'Über',
    leaveConfirm: 'Wenn Sie diese Seite verlassen, gehen die geladenen Bilder verloren. Fortfahren?',
    closeConfirm: 'Beim Schließen des Fensters gehen nicht gespeicherte Änderungen verloren. Trotzdem schließen?'
  },
  photoDirectory: {
    title: 'Fotoverzeichnis auswählen',
    description: 'Wählen Sie einen lokalen Ordner mit Ihren Fotos',
    installationError: '❌ Die Software-Installation ist unvollständig. Möglicherweise wurde die Software durch Ihr Antivirenprogramm beschädigt. Bitte neu installieren.',
    electronWarning: '⚠️ Wird nicht in einer Electron-Umgebung ausgeführt',
    selectButton: '📁 Verzeichnis auswählen',
    loading: 'Wird geladen...',
    selectedPath: 'Ausgewählter Pfad:',
    processingProgress: 'Vorschau wird vorbereitet'
  },
  photoGallery: {
    back: '← Zurück',
    refresh: '🔄 Aktualisieren',
    imagesCount: '{count} Bilder',
    loading: 'Bilder werden geladen...',
    noImages: 'Keine Bilder gefunden',
    noImagesDesc: 'Im ausgewählten Verzeichnis wurden keine Bilddateien (jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf oder raf) gefunden.',
    applying: 'Wird angewendet...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: 'Anwenden',
    saving: 'Speichern'
  },
  photoEdit: {
    back: '← Zurück',
    loading: 'Bilder werden geladen...',
    noImages: 'Keine Bilder gefunden',
    noImagesDesc: 'Im Verzeichnis wurden keine Bilddateien gefunden.',
    applying: 'Wird angewendet...',
    previewing: 'Vorschau wird erstellt...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Gamma',
    contrast: 'Kontrast',
    apply: 'Anwenden',
    applyAll: 'Auf alle anwenden',
    basicTab: 'Grundparameter',
    advancedTab: 'Korrektur der Emulsionskonzentration',
    exposureTab: 'Belichtung',
    whiteBalanceTab: 'Weißabgleich',
    whiteBalanceAuto: 'Automatisch',
    whiteBalanceTemp: 'Farbtemperatur',
    whiteBalanceTint: 'Farbton',
    contrastR: 'Kontrast R',
    contrastG: 'Kontrast G',
    contrastB: 'Kontrast B',
    contextMenu: {
      copyParams: 'Parameter kopieren',
      pasteParams: 'Parameter einfügen',
      applyPreset: 'Voreinstellung anwenden',
      pickMaskColor: 'Maskenfarbe aufnehmen',
      pickWhitePointArea: 'Weißpunkt-Bereich auswählen',
      clearWhitePointArea: 'Weißpunkt-Bereich löschen',
      rotate: 'Drehen',
      rotateClockwise: 'Im Uhrzeigersinn 90°',
      rotateCounterClockwise: 'Gegen den Uhrzeigersinn 90°'
    },
    eyedropper: {
      exitHint: 'Pipette aktiv — Bild anklicken zum Aufnehmen, ESC zum Abbrechen'
    },
    areaSelect: {
      exitHint: 'Bereichsauswahl aktiv — von oben-links nach unten-rechts ziehen, ESC zum Abbrechen'
    },
    applyPresetModal: {
      title: 'Voreinstellung auswählen',
      save: 'Anwenden',
      pickColor: 'Maskenfarbe aufnehmen'
    }
  },
  bottomMenu: {
    preset: 'Voreinstellung:',
    apply: 'Anwenden',
    applying: 'Wird angewendet...'
  },
  saveAllButton: {
    saveAll: 'Alle speichern',
    unappliedTooltip: 'Einige Bilder haben noch keine Parameter angewendet'
  },
  about: {
    title: 'Über OpenLucky Desktop',
    version: 'Versionsinformationen',
    description: 'Beschreibung',
    descriptionText: 'OpenLucky Desktop ist eine leistungsstarke Desktop-Anwendung für die Filmverarbeitung und Stapelvorgänge. Erstellt mit Electron und Vue 3, bietet sie eine moderne und effiziente Benutzeroberfläche zur Verwaltung Ihres Workflows.',
    homepage: 'Startseite',
    license: 'Lizenz',
    licenseSummary: 'Erlaubt kommerzielle Nutzung, Modifikation, Verbreitung und private Nutzung; erfordert die Beibehaltung des Copyright-Hinweises und die Angabe wesentlicher Änderungen; gewährt keine Markenrechte und bietet keine Garantie.',
    language: 'Sprache Language'
  }
}
