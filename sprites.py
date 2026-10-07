"""STARBEASTS pixel art.

Every sprite is a hand-made 16x16 string map. Each character maps to a
color in PALETTE ('.' means transparent). No external image files.
"""

import pygame

# ---------------------------------------------------------------- palette
# One shared palette so every sprite uses the same colors.
PALETTE = {
    # player
    "H": (150, 110, 60),    # explorer hat (brown)
    "f": (240, 200, 160),   # skin
    "e": (40, 35, 30),      # eyes (dark)
    "r": (205, 75, 75),     # shirt (red)
    "s": (110, 75, 45),     # backpack straps
    "u": (70, 100, 190),    # pants (blue)
    "b": (60, 50, 40),      # boots
    # tiles
    "g": (80, 170, 80),     # grass
    "d": (62, 148, 62),     # grass speckle (dark)
    "t": (40, 125, 50),     # tall grass blades
    "w": (45, 125, 225),    # water
    "l": (130, 195, 255),   # water sparkle
    "T": (34, 118, 52),     # tree canopy
    "k": (24, 95, 40),      # tree canopy shadow
    "n": (125, 85, 50),     # tree trunk
    "p": (214, 194, 148),   # path
    "a": (196, 176, 128),   # path speckle
    "c": (235, 238, 245),   # tent canvas
    "v": (80, 140, 210),    # tent stripe
    "o": (45, 45, 60),      # tent opening (dark)
    # Ember creatures (orange / red family)
    "E": (215, 60, 25),     # ember dark
    "O": (245, 130, 35),    # ember mid
    "Y": (255, 215, 120),   # ember light / yellow
    "K": (45, 35, 35),      # dark outline / eyes
    # Aqua creatures (blue family)
    "A": (25, 110, 200),    # aqua dark
    "B": (60, 160, 240),    # aqua mid
    "C": (170, 225, 255),   # aqua light
    # Leaf creatures (green family)
    "L": (30, 120, 50),     # leaf dark
    "G": (70, 180, 80),     # leaf mid
    "I": (160, 230, 150),   # leaf light
    # misc
    "N": (120, 80, 45),     # brown (stems)
    "W": (245, 245, 250),   # white
}

# ---------------------------------------------------------------- sprites
# Every entry: 16 strings of 16 characters.

SPRITES = {
    # ------------------------------------------------------------ player
    "player": [
        "................",
        ".....HHHHHH.....",
        "...HHHHHHHHHH...",
        ".....ffffff.....",
        ".....feffef.....",
        ".....ffffff.....",
        ".....rrrrrr.....",
        "...frrrrrrrf....",
        "...frrssrrrf....",
        "...frrssrrrf....",
        ".....rrrrrr.....",
        ".....uuuuuu.....",
        ".....uuuuuu.....",
        ".....bb..bb.....",
        ".....bb..bb.....",
        "................",
    ],
    # ----------------------------------------------------- Ember family
    "cindercub": [  # fire lion cub (starter)
        "................",
        "....E......E....",
        "....EE....EE....",
        "....EOOOOOOE....",
        "....EOffffOE....",
        "....EOfKKfOE....",
        "....EOffffOE....",
        "....EOOffOOE....",
        ".....OOOOOO.....",
        "...EOOOOOOOOO...",
        "...OOYYYYYYOO...",
        "...OOYYYYYYOO...",
        "...OOOOOOOOOO...",
        "....OO.OO.OO....",
        "................",
        "................",
    ],
    "emberspark": [  # little flame blob (common)
        "................",
        ".......YY.......",
        ".......YY.......",
        "......YYYY......",
        "......YOOY......",
        "......OOOO......",
        ".....OOOOOO.....",
        ".....OOKKOO.....",
        ".....OOOOOO.....",
        "....OOOOOOOO....",
        "....OOYYYYOO....",
        "....OOYYYYOO....",
        ".....OOOOOO.....",
        "......O..O......",
        "................",
        "................",
    ],
    "novawisp": [  # ghostly flame wisp (rare)
        "................",
        ".......YY.......",
        "......YOOY......",
        "......OOOO......",
        ".....OOOOOO.....",
        ".....OEKKEO.....",
        ".....OOOOOO.....",
        "....OOOOOOOO....",
        "....OWWWWWWO....",
        "....OWWWWWWO....",
        ".....OOOOOO.....",
        ".....O.OO.O.....",
        "................",
        "..W...........W.",
        "................",
        "................",
    ],
    # ------------------------------------------------------ Aqua family
    "bloopfin": [  # round water blob (starter)
        "................",
        "................",
        "......AAAA......",
        "....AAAAAAAA....",
        "...AAAAAAAAAA...",
        "...ABBBBBBBA....",
        "..CABBBBBBBAC...",
        "..CABKBBKBBAC...",
        "...ABBBBBBBA....",
        "...ACCCCCCCA....",
        "...ACCCCCCCA....",
        "....AAAAAAAA....",
        ".....AA..AA.....",
        "................",
        "................",
        "................",
    ],
    "aquaffle": [  # fish-like blob (common)
        "................",
        ".....CC.........",
        "....CCCC........",
        ".....CC.........",
        "...BBBBBBB......",
        "..BBBBBBBBB.A...",
        ".BBBKBBBBB..AA..",
        ".BBBBBBBBB..AAA.",
        ".BBBCCCCCBB.AA..",
        "..BBBBBBBBB.A...",
        "...BBBBBBB......",
        "....BB..BB......",
        "................",
        "................",
        "................",
        "................",
    ],
    # ------------------------------------------------------ Leaf family
    "sproutle": [  # sprout buddy (starter)
        "................",
        "...II......II...",
        "....III..III....",
        ".....IIIIII.....",
        ".......G........",
        ".....GGGGG......",
        "....GGGGGGG.....",
        "....GKKKKKG.....",
        "....GGGGGGG.....",
        "....GIIIIIG.....",
        "....GIIIIIG.....",
        ".....GGGGG......",
        ".....GG.GG......",
        "................",
        "................",
        "................",
    ],
    "leafling": [  # leaf creature (common)
        "................",
        ".......LL.......",
        "......LLLL......",
        ".....LLLLLL.....",
        "....LLLLLLLL....",
        "...LLLKKKKLLL...",
        "...LLLIIIILLL...",
        "...LLIIIIILLL...",
        "....LLIIIILL....",
        ".....LLLLLL.....",
        "......LLLL......",
        ".....LL..LL.....",
        "................",
        "................",
        "................",
        "................",
    ],
    "thornbloom": [  # thorny flower (uncommon)
        "................",
        ".....YYYYYY.....",
        "....YYYYYYYY....",
        "...YYYYYYYYYY...",
        "...YYWWWWWWYY...",
        "...YWKKKKKKWY...",
        "...YYWWWWWWYY...",
        "...YYYYYYYYYY...",
        "....YYYYYYYY....",
        ".....YYYYYY.....",
        ".......NN.......",
        "....K..NN..K....",
        ".......NN.......",
        "...LL..NN..LL...",
        ".......NN.......",
        "................",
    ],
    # ------------------------------------------------------------- tiles
    "grass": [
        "gggggggggggggggg",
        "ggdgggggggdggggg",
        "gggggggggggggggg",
        "ggggggdggggggggg",
        "gggggggggggggdgg",
        "gdgggggggggggggg",
        "ggggggggggdggggg",
        "gggggggggggggggg",
        "gggdggggggggggdg",
        "gggggggggggggggg",
        "ggggggdggggggggg",
        "ggdggggggggggggg",
        "gggggggggggdgggg",
        "gggggggggggggggg",
        "ggggdgggggdggggg",
        "gggggggggggggggg",
    ],
    "tall_grass": [
        "gggggggggggggggg",
        "gggtggggggtggggg",
        "gggtggggggtggggg",
        "gggtggggggtggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "ggggggtgggggtggg",
        "ggggggtgggggtggg",
        "ggggggtgggggtggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "ggtggggggggtgggg",
        "ggtggggggggtgggg",
        "ggtggggggggtgggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
    ],
    "water": [
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwlwwwwlwwwwlww",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwlwwwwwwlwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwwlwwwwwwlwwww",
        "wwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwww",
        "wwwlwwwwlwwwwlww",
        "wwwwwwwwwwwwwwww",
    ],
    "tree": [
        "gggggggggggggggg",
        "gggggTTTTTgggggg",
        "gggTTTTTTTTggggg",
        "ggTTkTTTTTTTgggg",
        "ggTkTTTTTTTTTggg",
        "ggTTTTTTTTTTTTgg",
        "ggTTTTTTTTTTTTgg",
        "gggTTTTTTTTTTggg",
        "gggggTTTTTTggggg",
        "gggggggnnngggggg",
        "gggggggnnngggggg",
        "gggggggnnngggggg",
        "ggggggnnnnnggggg",
        "gggggggggggggggg",
        "ggdgggggggdggggg",
        "gggggggggggggggg",
    ],
    "path": [
        "pppppppppppppppp",
        "ppapppppppappppp",
        "pppppppppppppppp",
        "ppppppappppppppp",
        "pppppppppppppapp",
        "papppppppppppppp",
        "ppppppppppappppp",
        "pppppppppppppppp",
        "pppapappppppppap",
        "pppppppppppppppp",
        "ppppppappppppppp",
        "ppappppppppppppp",
        "pppppppppppapppp",
        "pppppppppppppppp",
        "ppppapppppappppp",
        "pppppppppppppppp",
    ],
    "tent": [
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggccggggggg",
        "ggggggccccgggggg",
        "gggggccccccggggg",
        "ggggccccvcccgggg",
        "gggcccccvccccggg",
        "gggccccooocccggg",
        "ggcccccoooccccgg",
        "ggcccccoooccccgg",
        "gccccccccccccccg",
        "gggggggggggggggg",
        "ggdgggggggdggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
    ],
}

# ------------------------------------------------------------------ build

_cache = {}


def validate_sprites():
    """Check every sprite is 16x16 and only uses known characters."""
    for name, grid in SPRITES.items():
        assert len(grid) == 16, f"{name}: {len(grid)} rows (want 16)"
        for i, row in enumerate(grid):
            assert len(row) == 16, f"{name} row {i}: {len(row)} chars (want 16)"
            for ch in row:
                assert ch == "." or ch in PALETTE, (
                    f"{name} row {i}: unknown char {ch!r}"
                )


def get_surface(name):
    """Return the 16x16 pygame Surface for a sprite (cached)."""
    if name not in _cache:
        grid = SPRITES[name]
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch != ".":
                    surf.set_at((x, y), PALETTE[ch])
        _cache[name] = surf
    return _cache[name]


_scaled_cache = {}


def get_scaled(name, scale):
    """Return a sprite scaled up by an integer factor (cached)."""
    key = (name, scale)
    if key not in _scaled_cache:
        base = get_surface(name)
        _scaled_cache[key] = pygame.transform.scale(
            base, (16 * scale, 16 * scale)
        )
    return _scaled_cache[key]
