export default {
  navbar: {
    home: 'Accueil',
    about: 'À propos',
    leaveConfirm: 'Quitter cette page entraînera la perte des images chargées. Continuer ?',
    closeConfirm: 'Les modifications non enregistrées seront perdues si vous fermez la fenêtre. Fermer quand même ?'
  },
  photoDirectory: {
    title: 'Sélectionner le répertoire de photos',
    description: 'Choisissez un dossier local contenant vos photos',
    installationError: '❌ L\'installation du logiciel est incomplète. Cela peut être dû à votre antivirus qui a endommagé le logiciel. Veuillez réinstaller.',
    electronWarning: '⚠️ N\'est pas exécuté dans un environnement Electron',
    selectButton: '📁 Sélectionner le répertoire',
    loading: 'Chargement...',
    selectedPath: 'Chemin sélectionné :',
    processingProgress: 'Préparation de l\'aperçu',
    compressPreview: 'Compresser l\'aperçu',
    compressPreviewTip: 'Les miniatures seront compressées à 1920 px de largeur pour accélérer l\'aperçu. Cela accélère l\'aperçu de la suppression du masque mais ralentit le processus de chargement.',
    cancel: 'Annuler',
  },
  photoGallery: {
    back: '← Retour',
    refresh: '🔄 Actualiser',
    imagesCount: '{count} images',
    loading: 'Chargement des images...',
    noImages: 'Aucune image trouvée',
    noImagesDesc: 'Aucun fichier image (jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf ou raf) n\'a été trouvé dans le répertoire sélectionné.',
    applying: 'Application en cours...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: 'Application',
    saving: 'Enregistrement'
  },
  photoEdit: {
    back: '← Retour',
    loading: 'Chargement des images...',
    noImages: 'Aucune image trouvée',
    noImagesDesc: 'Aucun fichier image n\'a été trouvé dans le répertoire.',
    applying: 'Application en cours...',
    previewing: 'Aperçu en cours...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Gamma',
    contrast: 'Contraste',
    apply: 'Appliquer',
    applyAll: 'Tout appliquer',
    basicTab: 'Paramètres de base',
    advancedTab: 'Correction de la concentration de l\'émulsion',
    exposureTab: 'Exposition',
    toneTab: 'Correction de latitude',
    tonePivot: 'Pivot d\'exposition',
    toneCurve: 'Contraste d\'exposition',
    tonePivotLeft: 'Décaler à gauche',
    tonePivotRight: 'Décaler à droite',
    toneCurveLeft: 'Réduire le contraste',
    toneCurveRight: 'Augmenter le contraste',
    whiteBalanceTab: 'Balance des blancs',
    whiteBalanceAuto: 'Automatique',
    whiteBalanceTemp: 'Température',
    whiteBalanceTint: 'Teinte',
    contrastR: 'Contraste R',
    contrastG: 'Contraste G',
    contrastB: 'Contraste B',
    contextMenu: {
      copyParams: 'Copier les paramètres',
      pasteParams: 'Coller les paramètres',
      applyPreset: 'Appliquer un préréglage',
      pickMaskColor: 'Prélever la couleur du masque',
      pickWhitePointArea: 'Sélectionner la zone du point blanc',
      clearWhitePointArea: 'Effacer la zone du point blanc',
      rotate: 'Rotation',
      rotateClockwise: 'Sens horaire 90°',
      rotateCounterClockwise: 'Sens antihoraire 90°',
      rotate180: 'Rotation 180°',
      resetImage: 'Réinitialiser l\'image',
    },
    eyedropper: {
      exitHint: 'Pipette active — cliquez sur l\'image pour prélever, ÉCHAP pour annuler'
    },
    areaSelect: {
      exitHint: 'Sélection de zone active — glissez du haut-gauche au bas-droit, ÉCHAP pour annuler'
    },
    applyPresetModal: {
      title: 'Sélectionner un préréglage',
      save: 'Appliquer',
      pickColor: 'Prélever la couleur du masque'
    }
  },
  bottomMenu: {
    preset: 'Préréglage :',
    apply: 'Appliquer',
    applying: 'Application en cours...'
  },
  saveAllButton: {
    saveAll: 'Tout enregistrer',
    unappliedTooltip: "Certaines images n'ont pas encore de paramètres appliqués"
  },
  languageMismatch: {
    message: 'La langue de votre système diffère de la langue actuelle de l\'interface. Passer à la langue du système ?',
    yes: 'Oui',
    no: 'Non',
    dontRemind: 'Non, ne plus me rappeler'
  },
  about: {
    title: 'À propos d\'OpenLucky Desktop',
    version: 'Informations de version',
    description: 'Description',
    descriptionText: 'OpenLucky Desktop est une application de bureau puissante pour le traitement de pellicules et les opérations par lots. Construite avec Electron et Vue 3, elle offre une interface moderne et efficace pour gérer votre flux de travail.',
    homepage: 'Page d\'accueil',
    license: 'Licence',
    licenseSummary: 'Autorise l\'utilisation commerciale, la modification, la distribution et l\'utilisation privée ; impose la conservation de la mention de copyright et l\'indication des modifications importantes ; n\'accorde aucun droit de marque et ne fournit aucune garantie.',
    language: 'Langue Language',
    theme: 'Thème',
    themeLight: 'Clair',
    themeDark: 'Sombre'
  }
}
