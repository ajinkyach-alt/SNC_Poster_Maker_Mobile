# SNC शेतकरी बाजार – Mobile Poster Maker

This is an Android/Kivy version of the existing Python poster maker.

## What it does
- 8 vegetable tiles
- Select a photo for each tile
- Enter exact vegetable name and price
- Date, contact and address fields
- Generates JPG using the same `template.png` + Pillow layout
- Bundles Noto Sans Devanagari fonts for Marathi rendering
- Empty tiles remain empty (no automatic "भाजीपाला")

## Build APK
Buildozer is normally run in Linux/WSL2, not native Windows CMD.

```bash
pip install buildozer
buildozer android debug
```

The APK will be placed in the `bin/` folder.

## Important
Keep `template.png` at the project root. If you redesign the PowerPoint template and export it, replace this file with the new PNG while keeping the same 1:1 layout and the vegetable-card area approximately in the same position. The current Python generator uses fixed card coordinates.
