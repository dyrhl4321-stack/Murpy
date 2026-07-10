# Claude Automation Guide

This tool should be used by Claude Code when it works on Murpy World customization assets.

The user should not need to manually understand every layer detail.

## Goal

Claude Code can automatically validate and preview character customization layers before adding them to the app.

The browser UI is for human review.

The Python CLI is for Claude automation.

## Important Files

- `tools/character-customizer/murpy_layers.json`
- `tools/character-customizer/customizer_cli.py`
- `tools/character-customizer/index.html`
- `tools/character-customizer/ITEM_PRODUCTION_PIPELINE.md`
- `tools/character-customizer/out/`

## Standard

- Sheet size: 423 x 896
- Frame size: 141 x 224
- Columns: idle, walk1, walk2
- Rows: down, up, left, right
- Layer order: body, bottom, shoes, top, hair, hat, accessory

## Claude Code Workflow

When the user provides a new customization item:

1. Put the draft PNG in the correct layer slot.
2. Run validation.
3. If validation fails, do not add it to `index.html`.
4. Fix or regenerate the layer until validation passes.
5. Export a preview frame and/or composited sheet.
6. Ask for visual approval if the result is uncertain.
7. Only then connect the final asset to the app item data.

## Commands

Validate the current default layer set:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py validate
```

Validate with a new hair file:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py validate --layer hair=C:\path\to\hair.png
```

Export one preview frame:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py preview --direction down --frame idle
```

Export a full composited sprite sheet:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py compose
```

Outputs are saved in:

```text
C:\Users\won\Murpy\tools\character-customizer\out
```

## Rule

Claude Code should treat this tool as the gate before app integration.

If an item fails validation, it should remain a draft.

Do not silently add invalid assets to Murpy World.

## Preferred User Experience

The ideal workflow is not that the user manually operates the tool.

The ideal workflow is:

1. The user provides a real item photo or style reference.
2. Claude Code uses AI/image tooling to create a Murpy-compatible pixel layer.
3. Claude Code runs this automation tool.
4. Claude Code shows the preview result.
5. The user only performs final visual approval.
6. Claude Code registers the approved item in the customization UI.

Read `ITEM_PRODUCTION_PIPELINE.md` before producing new customization items.
