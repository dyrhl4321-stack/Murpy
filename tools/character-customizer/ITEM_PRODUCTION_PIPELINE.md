# Murpy World Item Production Pipeline

This document defines the intended workflow for turning a real item photo or rough concept into a Murpy World customization item.

The user should not need to manually understand sprite sheets, frame grids, masks, or layer alignment.

## Target Workflow

1. User provides a real item photo, product image, or rough concept.
2. AI generates a Murpy-style pixel item layer for the base character.
3. The generated layer follows the Murpy sheet standard.
4. The automation tool validates the file.
5. The tool exports preview images.
6. User visually approves the result.
7. Claude Code registers the approved item in the Murpy World customization data.

## User Role

The user only needs to:

- Provide the item reference.
- Say which slot it belongs to.
- Review the final preview.
- Approve or reject.

The user should not need to:

- Manually crop sprite sheets.
- Manually remove checkerboard backgrounds.
- Manually align 12 frames.
- Manually edit `index.html`.
- Manually calculate frame coordinates.

## Claude Code Role

Claude Code should:

- Read this document before working on customization assets.
- Convert the user request into an item production task.
- Ask AI/image tools for a Murpy-compatible pixel layer when needed.
- Save draft outputs outside the final app asset path first.
- Run `customizer_cli.py validate`.
- Run `customizer_cli.py preview`.
- Show or provide the preview for user approval.
- Only after approval, copy/register the final PNG into `char/items`.
- Add the item to the app customization item data.

## Codex Role

Codex should:

- Maintain the customization architecture.
- Maintain this production pipeline.
- Review failed renderings.
- Improve extraction, validation, preview, and export tools.
- Keep Claude Code from returning to full-character sprite replacement for new items.

## Required Output From AI

For each item, AI should produce a transparent PNG layer sheet.

Current standard:

- Canvas: 423 x 896
- Frame: 141 x 224
- Columns: idle, walk1, walk2
- Rows: down, up, left, right
- Transparent background
- No body pixels except pixels that are truly part of the item
- No checkerboard background
- No mannequin guide
- No resizing after alignment
- No cropping

## Layer Slots

Use one of:

- `hair`
- `hat`
- `top`
- `bottom`
- `shoes`
- `accessory`

Body is not an item slot for normal customization.

## AI Prompt Template

Use this as the base prompt when generating an item layer from a real item or concept.

```text
Create a Murpy World pixel-art customization item layer from the provided reference.

Item slot:
{slot}

Target character format:
- 2D pixel art
- transparent PNG
- exact canvas size 423x896
- 3 columns x 4 rows
- each frame is 141x224
- columns are idle, walk1, walk2
- rows are front/down, back/up, left, right

Critical alignment rules:
- Keep every frame in the same position as the Murpy base character.
- Do not crop the canvas.
- Do not resize individual frames.
- Do not move frames.
- Do not include the base character body.
- Do not include a mannequin outline.
- Do not include checkerboard background.
- Output only the item pixels needed for this slot.

Visual rules:
- Match the Murpy World pixel-art style.
- Use clean readable pixel shapes.
- Use sharp pixel edges.
- Make the item look natural on the base body from front, back, left, and right.
- If the item is not visible from a direction, keep that frame transparent or minimally visible.

The result must be an app-ready transparent item layer sheet.
```

## Validation Commands

Validate a generated item:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py validate --layer {slot}=C:\path\to\generated_item.png
```

Create a front idle preview:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py preview --layer {slot}=C:\path\to\generated_item.png --direction down --frame idle
```

Create a full composited preview sheet:

```powershell
python C:\Users\won\Murpy\tools\character-customizer\customizer_cli.py compose --layer {slot}=C:\path\to\generated_item.png
```

## Approval Rule

No generated item should be added to the main Murpy app until:

1. The file passes validation.
2. The preview looks correct.
3. The user approves it.

Failed or uncertain items remain drafts.

## Product Direction

Murpy World customization should feel like this:

User gives a real item or style idea.

AI turns it into a Murpy-compatible pixel item.

Automation checks the technical correctness.

User approves the visual result.

Claude Code adds the approved item to the app.

This is the intended long-term workflow.
