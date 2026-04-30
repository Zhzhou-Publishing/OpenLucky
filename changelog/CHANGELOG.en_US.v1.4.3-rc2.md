# Changelog for v1.4.3-rc2

## Photo Edit

- New **White Balance** tab: tick **Auto**, or manually drag the Temperature (blue–amber) and Tint (magenta–green) sliders; coloured tracks indicate the adjustment direction and a paired number input lets you fine-tune by 1.
- New **Exposure** tab: dial in exposure compensation across ±3 EV with a linked slider and number input.
- New **white-point area selector**: drag a rectangle on the main image to choose where the white point is sampled; the selection follows rotations and gets re-mapped to the full-resolution image at Save All time.
- New **eyedropper**: sample the cast colour straight from the original RAW/TIFF (more accurate than picking from the preview) and have it filled into Mask. After picking, the white-point selector starts automatically so you can pick and frame in a single flow.
- Progress messages now appear while parameters are being applied and while the working folder is being prepared, so long-running steps no longer feel silent.

## Software Updates

- The update check now respects release channels: stable users only see stable releases, while alpha / beta / rc users only see the next release on their own channel — no more cross-channel noise.

## Other

- The **Cancel** button in the Apply Preset dialog has been re-purposed as a **Pick Colour** shortcut.
- **Save All** now replays the white-point area, white balance, and exposure settings against the full-resolution originals.
