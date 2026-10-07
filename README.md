# STARBEASTS

A 2D pixel-creature RPG in Python + Pygame. Explore a little island, wander
through tall grass, battle wild Starbeasts, catch them with orbs, and
complete your bestiary: **catch all 8 species!**

All pixel art is hand-made and defined **in code** (`sprites.py`) as
16x16 string maps — there are zero image files in this project.

## How to run

```bash
pip install -r requirements.txt   # or: pip install pygame
python main.py
```

## Controls

| Key | What it does |
|---|---|
| Arrow keys / WASD | Move around the map |
| ENTER | Confirm / advance dialogue / rest at the tent |
| B | Open / close the bestiary |
| S | Save the game |
| L (title screen) | Load saved game |
| In battle: ↑/↓ + ENTER | Pick menu options and moves |
| In battle: ESC | Back out of FIGHT / SWITCH menus |

## Features

- **Overworld**: 24x18 tile island with water borders, trees, paths, tall
  grass, and a healer's tent. Tile-based smooth movement with collision.
- **8 Starbeasts** across 3 types (Ember / Aqua / Leaf) with a type chart:
  Ember > Leaf > Aqua > Ember (x1.5 super-effective, x0.6 resisted,
  x0.8 same-type).
- **Pick a starter**: Cindercub (Ember), Bloopfin (Aqua), or Sproutle (Leaf).
- **Turn-based battles**: FIGHT (2 moves each), SWITCH (party of up to 4),
  ORB (catching, 8 orbs), RUN (75% escape). Turn order by speed.
- **Catching**: catch chance rises as the wild creature gets weaker.
- **XP & levels**: the active creature earns XP; level-ups raise stats and
  heal 25% HP.
- **Tent**: rest to fully heal your party, refill orbs to 8, and save.
- **Blackout**: if your whole party faints you wake up at the tent, healed.
- **Bestiary** (B key): caught species shown in full color, uncaught ones
  as silhouettes. Catch all 8 for the victory screen!
- **Save/load**: progress is stored in `save.dat` (JSON).

## Project layout

```
main.py       - entry point: game loop + all screens (title, starter,
                overworld, bestiary, victory)
sprites.py    - ALL pixel art as 16x16 string maps (player, 8 creatures,
                6 tiles), scaled 2x in the overworld, 3x in battle
creatures.py  - species data, type chart, moves, XP/level-up,
                damage + catch formulas
world.py      - tile map, player movement, collision, tall-grass steps
battle.py     - turn-based battle state machine + battle UI
game.py       - game state machine, party, bestiary, tent, save/load
test_smoke.py - headless smoke test (no window needed)
```

## How to add a new creature

1. Draw a 16x16 string-map sprite in `sprites.py` (add it to `SPRITES`,
   using only characters from `PALETTE` plus `.` for transparent).
2. Add an entry to `SPECIES` in `creatures.py`:

```python
"frostbite": {
    "name": "Frostbite", "type": "Aqua", "rarity": "common",
    "desc": "A chilly little cube.",
    "base": (42, 11, 10, 10),   # hp, atk, def, spd
},
```

   Rarity can be `"common"`, `"uncommon"`, `"rare"` (wild encounter
   weight) or `"starter"`.
3. Add `"frostbite"` to `BESTIARY_ORDER` in `creatures.py` so it shows up
   in the bestiary.

That's it — battles, catching, XP, and the bestiary pick it up
automatically.
