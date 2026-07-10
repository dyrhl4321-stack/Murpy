# MURPY WORLD Claude/Codex Workflow

This document defines how Murpy World work should be divided between Claude Code and Codex.

## Core Rule

Claude Code should focus on implementing the app.

Codex should focus on review, system design, character customization stability, and asset/tool pipeline design.

Do not rebuild major Murpy World systems without checking the documents in this folder first.

Primary references:

- `docs/murpyworld-roadmap.md`
- `docs/claude-codex-workflow.md`

## Role Split

### Claude Code

Claude Code is responsible for:

- Editing `index.html`
- Implementing Murpy World UI and behavior
- Connecting data to Firebase or local app state
- Applying final approved image assets
- Keeping the current tab structure and existing app flow stable
- Fixing concrete UI bugs after review

Claude Code should avoid:

- Replacing the character customization direction without discussion
- Returning to full-character sprite replacement for new items
- Creating temporary dress-up screens that are separate from Murpy World unless explicitly requested
- Changing sprite scale, frame size, direction mapping, or asset conventions without documenting it

### Codex

Codex is responsible for:

- Reviewing Claude Code changes
- Finding rendering bugs and structural risks
- Designing the Murpy World customization architecture
- Stabilizing the character layer system
- Creating or improving item production tools
- Defining sprite sheet standards
- Checking asset alignment, frame size, transparency, and layer order
- Planning future Murpy World game systems

Codex may create helper scripts, asset validation tools, extraction tools, or documentation, but app-facing changes should be coordinated with Claude Code unless the user asks Codex to implement them directly.

## Character Customization Direction

Murpy World customization should move toward a layer-based system.

The goal is to stop producing a new full character sheet for every outfit.

The target structure is:

1. Body
2. Bottom
3. Shoes
4. Top
5. Hair
6. Hat
7. Accessory

The base body should be a clean body layer:

- Face included
- Eyes included
- Eyebrows included
- Ears included
- Skin/body included
- No hair
- No normal clothing
- No shoes
- No hat
- No accessories
- Neutral undergarment or simple base coverage is acceptable

Eyebrows belong to the body/face layer, not the hair layer.

Hair should be a separate transparent layer. Short hair, long hair, hats, and accessories should naturally cover or reveal eyebrows depending on their pixels.

## Current Sprite Sheet Standard

Current Murpy World character assets use:

- 3 columns
- 4 rows
- 12 frames total
- Columns: idle, walk1, walk2
- Rows: down, up, left, right
- Current actual frame size: 141 x 224
- Current actual sheet size: 423 x 896

All new layer sheets should keep the same canvas size, frame size, alignment, row order, and column order unless the whole system is intentionally migrated.

Do not crop layers.

Do not resize individual frames.

Do not move item pixels after alignment is approved.

Transparent empty space is expected and important.

## Rendering Rules

The character renderer should:

- Render the body at the bottom
- Render equipped layers above it in a fixed order
- Change only the selected item layer when the user equips an item
- Keep the body source stable
- Use the same direction and frame index for every layer
- Use absolute overlap or equivalent exact positioning
- Use pixel-friendly rendering so pixel art does not blur
- Keep item data in arrays or objects so adding future items is simple

New items should not require manually generating a full character image.

New items should be generated or extracted as layer sheets that align to the base body.

## Asset Production Direction

The long-term goal is to build a Murpy World customization production tool.

The tool should eventually support:

- Uploading a base body sheet
- Uploading an item concept or rough item sheet
- Extracting only the target item pixels
- Removing checkerboard backgrounds
- Removing mannequin/body guide pixels
- Preserving exact canvas size
- Preserving exact frame alignment
- Previewing body + equipped layers together
- Checking all four directions
- Checking idle and walking frames
- Exporting app-ready transparent PNG layer sheets
- Creating thumbnails for the shop/customization UI
- Validating file size, dimensions, transparency, and frame count

Until this tool is stable, AI-generated item sheets should be treated as drafts. They must be checked and cleaned before being added to the app.

## Legacy Handling

Existing full-character sprite assets can remain as legacy assets.

However, new customization items should be produced in the layer format.

If a legacy asset is used temporarily, document it clearly so it does not become the default future workflow.

## Immediate Priorities

1. Stabilize the existing Murpy World character renderer.
2. Confirm the base body sheet.
3. Produce a clean default hair layer.
4. Produce top, bottom, shoes, hat, and accessory layers separately.
5. Add validation rules for dimensions and transparency.
6. Build a preview/export workflow for future item creation.
7. Only then expand the item catalog.

## Collaboration Rule

When Claude Code modifies Murpy World, it should keep the layer system compatible with this document.

When Codex reviews Murpy World, it should check whether changes preserve:

- Layer order
- Frame alignment
- Direction mapping
- Pixel clarity
- Existing UI/tab structure
- Future item expandability

The shared goal is to make Murpy World customization easy to expand without repeated full-sprite manual work.
