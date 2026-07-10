# MURPY WORLD Long-Term Roadmap

## Core Philosophy

Murpy World is not a separate game added to Murpy.

Murpy World is a world that helps people keep exercising.

Murpy is not only a workout SNS or matching app. It is a platform where people grow in both real life and a virtual world. In real life, users grow through exercise. In Murpy World, their character, room, items, achievements, and social presence grow with them.

The game must not replace exercise. Exercise must become the fuel that moves the game.

## Product Principles

Every Murpy World feature should satisfy at least one of these goals:

- Encourage users to exercise more.
- Increase community activity.
- Create more friend, crew, and center interactions.
- Stimulate item collection and customization desire.
- Support long-term content expansion.
- Avoid unfair competitive advantage in matching or feed exposure.

Cosmetic rewards are encouraged. Direct ranking or exposure advantages should be handled carefully.

## Character And Customization System

Character customization is one of the core Murpy World systems.

Going forward, new customization items should use a layer-based system instead of repeatedly generating complete full-character sprite sheets.

Layer order:

```text
body
bottom
shoes
top
hair
hat
accessory
```

Guidelines:

- `body` should be a clean base body layer, not a fully dressed character.
- Hair, tops, bottoms, shoes, hats, and accessories should be separate transparent PNG layers.
- Existing full-sprite characters can remain as legacy or special fixed characters.
- New items should be made as layer assets.
- All layers must share the same sprite sheet grid, frame size, direction order, and alignment.
- The current Murpy World runtime uses 3 columns x 4 rows:
  - Columns: idle, walk1, walk2
  - Rows: down, up, left, right
- Current app asset size is based on 141x224 per frame, 423x896 total sheet.

## Exercise-To-World Loop

The main progression loop should be:

```text
exercise
-> verification
-> experience / energy / coin
-> Murpy World activity
-> items / growth / social expression
-> motivation to exercise again
```

Examples:

- Workout verification gives energy.
- Energy can be used for mining, fishing, farming, exploration, crafting, or quests.
- Workout streaks unlock badges, titles, cosmetics, and room objects.
- Real event participation unlocks limited items.

## Item System

Items should be tied to real effort and community activity.

Examples:

- Workout verification -> coin
- Workout streak -> medal or title
- HYROX completion -> exclusive medal
- 100 workout days -> legendary title
- Center event -> limited hat
- Body profile verification -> special profile frame
- Crew mission -> crew item or room object

Items can be used in:

- Character customization
- Profile decoration
- Feed identity
- Comment badges
- Nickname decoration
- Room decoration
- Visit interactions

Important fairness rule:

- Items should not directly increase matching exposure or feed exposure.
- Items can express identity, effort, rarity, and status.

## Roadmap

### Phase 1: Current MVP

- Character display
- Character customization
- Room / field view
- Basic movement
- Basic map concept
- Basic user presence
- Visit concept
- Customization asset pipeline stabilization

### Phase 2: Life Content

- Mining
- Fishing
- Farming
- Crafting
- Shop
- Item upgrades
- Workout energy system
- Daily/weekly activity loop

### Phase 3: Center Content

- Center-specific backgrounds
- Center-specific NPCs
- Center-specific quests
- Center-specific collectibles
- Center badges
- Center achievements
- Check-in-based unlocks

### Phase 4: Crew Content

- Crew house
- Crew storage
- Crew achievements
- Crew ranking
- Cooperative quests
- Weekly crew missions
- Crew room decoration

### Phase 5: Center Dungeon

- Each center can become a unique local map or dungeon.
- Centers can have themes such as fire, ice, jungle, city, arena, or lab.
- Center-specific monsters, bosses, rare items, hidden areas, and quests can exist.
- Access or rewards should be linked to real center check-ins or verified workouts.

### Phase 6: Seasons And Events

- Seasonal events
- Christmas
- Halloween
- Summer
- Cherry blossom season
- Limited items
- Limited costumes
- Limited NPCs
- Limited quests and maps

## Location-Based RPG Direction

The strongest long-term differentiator is a location-based and center-based RPG system.

Example:

```text
Center A -> fire theme
Center B -> ice theme
Center C -> jungle theme
```

Only users who actually exercise at or check in to a center should be able to unlock that center's quests, collectibles, badges, or limited items.

This makes real-world exercise part of the game.

The goal is not to make users stay home and play. The goal is to make users go exercise, meet people, join crews, visit centers, and bring that activity back into Murpy World.

## Near-Term Execution Order

1. Stabilize layer-based character customization.
2. Build a Murpy World asset production tool.
3. Connect workout verification rewards to character/items.
4. Build basic room, map, and visit loops.
5. Test center check-in rewards.
6. Expand into center quests and crew missions.

## Suggested Role Split

Claude Code:

- Implement app UI and behavior.
- Modify `index.html`.
- Handle Firebase and data integration.
- Apply final assets to the app.

Codex / Review Workflow:

- Review Claude Code output.
- Find rendering bugs and structural risks.
- Build customization and sprite production tools.
- Define item asset standards.
- Validate generated assets before app integration.
- Maintain long-term Murpy World architecture direction.

## North Star

When users exercise in real life, their Murpy World character and world should grow.

Murpy World should give users another reason to continue exercising, collect items, express identity, interact with friends, join crews, visit centers, and return to Murpy.
