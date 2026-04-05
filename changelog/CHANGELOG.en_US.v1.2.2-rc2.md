# OpenLucky v1.2.2-rc2 Release Notes

## Summary
This release introduces comprehensive internationalization (i18n) support, enabling the application to support both Chinese (Simplified) and English languages. Users can now switch between languages dynamically, and all UI components have been localized.

## Changes

### New Features
- **Add internationalization support**: Implemented vue-i18n for comprehensive multilingual support throughout the application
- **Create language switcher component**: Added LanguageSwitcher component that allows users to toggle between Chinese (Simplified) and English (United States)
- **Localize all UI pages**: All user interface elements now support both languages including:
  - Navigation bar (Home, About)
  - Photo Directory page (title, descriptions, buttons, error messages)
  - Photo Gallery page (navigation, refresh button, image count, loading states, empty states)
  - Photo Edit page (navigation, operation labels, buttons, loading states, empty states)
  - Bottom Menu (preset labels, apply button states)
  - About page (title, version information, descriptions, technology list)

### Enhancements
- **Language persistence**: User's language preference is saved to localStorage and persists across sessions
- **Language selection UI**: Added language switcher in the navigation bar for easy access
- **Locale file structure**: Implemented clean separation of translation files (en_US.js, zh_Hans.js) for maintainability
- **Version update**: Updated app version to v1.2.2-rc2 to reflect new features
- **Inno Setup script update**: Updated installer script version to match app version

### Dependencies
- **Add vue-i18n**: Added version 11.3.0 of vue-i18n for internationalization support
- **Add i18n dependencies**: Added @intlify/* packages required for vue-i18n functionality

## Technical Details

### New Files
- `app/src/i18n/index.js`: Main i18n configuration file
- `app/src/locales/en_US.js`: English translation file containing all UI strings
- `app/src/locales/zh_Hans.js`: Chinese (Simplified) translation file containing all UI strings
- `app/src/components/LanguageSwitcher.vue`: Language selection component

### Modified Files
- `app/src/main.js`: Integrated i18n plugin with Vue application
- `app/src/components/Navbar.vue`: Added LanguageSwitcher component and i18n key routing
- `app/src/components/BottomMenuBar.vue`: Replaced hardcoded strings with i18n keys
- `app/src/pages/About.vue`: Implemented i18n for all content
- `app/src/pages/PhotoDirectory.vue`: Implemented i18n for all content
- `app/src/pages/PhotoGallery.vue`: Implemented i18n for all content with dynamic image count
- `app/src/pages/PhotoEdit.vue`: Implemented i18n for all content
- `app/package.json`: Updated version and added vue-i18n dependency
- `app/package-lock.json`: Updated lock file with new dependencies
- `app/yarn.lock`: Updated lock file with new dependencies
- `OpenLucky.iss`: Updated version to v1.2.2-rc2

### Translation Coverage
All user-facing text elements have been translated including:
- Navigation and routing
- Button labels and actions
- Loading and empty states
- Error messages and warnings
- Form labels and input placeholders
- Page titles and descriptions
- Operation buttons (Apply, Apply All, Back, Refresh)

## Language Support
- **Chinese (Simplified)**: zh_Hans - Default language
- **English**: en_US - Alternative language with full support

## Compatibility
- Requires vue-i18n 11.3.0
- Maintains backward compatibility with existing functionality
- Language preference stored in localStorage requires browser storage support
