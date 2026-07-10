# Murpy World Character Customizer Tool

This is a standalone browser tool for reviewing and preparing Murpy World character customization layers.

It does not modify the main app.

Open:

`C:\Users\won\Murpy\tools\character-customizer\index.html`

## What It Does

- Loads body and item layer sheets.
- Shows a composited character preview.
- Switches direction: down, up, left, right.
- Switches frame: idle, walk1, walk2.
- Checks sheet size and transparency.
- Allows small x/y nudge checks per layer.
- Exports the current frame as PNG.
- Exports a full composited sprite sheet as PNG.

## Current Standard

- Sheet size: 423 x 896
- Frame size: 141 x 224
- Columns: idle, walk1, walk2
- Rows: down, up, left, right

All new layer items should preserve the same canvas size and frame alignment.

## Intended Workflow

1. Create or extract a transparent item layer PNG.
2. Open this tool.
3. Load the base body.
4. Upload the item into the correct slot.
5. Check all four directions and all walking frames.
6. Fix the PNG if it is misaligned.
7. Only add the final approved PNG to the app.

## Ownership

Claude Code can use this tool as a reference when implementing app changes.

Codex uses this tool for review, sprite standards, item validation, and future asset pipeline work.
