# Changelog for v1.4.3-rc1

## New Languages

- Added 12 more interface languages: Traditional Chinese (HK), English, French, German, Polish, Russian, Spanish, Portuguese, Japanese, Vietnamese, Hindi, Tibetan, and Korean.
- The app now follows your system language on first launch and falls back to English when it can't tell.

## About Page

- New layout with a project homepage link, open-source license summary, and an in-app language picker.
- When viewed in Tibetan, the page invites native speakers to help proofread the translation and links to the issue tracker.

## Window Behaviour

- The window can now be resized freely from any screen.
- Closing the window or navigating away from the gallery/edit pages while you have unsaved work prompts a confirmation.

## Photo Edit

- Right-click on the main image opens a contextual menu with Copy / Paste Parameters, Apply Preset, and Rotate — replacing the small floating rotate buttons.
- Opening an image that hasn't been processed yet automatically pops up the Apply Preset dialog so nothing slips through.
- Default knob values updated: Mask R/G/B start at 255; Gamma and Contrast start at 1.
- Top bar now centres the file name and shows the directory name on the side.

## Photo Gallery

- The preset list is fetched ahead of time so the dropdown is immediately populated when you arrive.
- "Save All" stays disabled until every image has its parameters applied; hovering the button explains why.

## Other

- Smoother synchronisation of the main image and thumbnail strip after applying parameters.
