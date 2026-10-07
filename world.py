"""STARBEASTS overworld: isometric tile map, player movement, collision.

ISOMETRIC MATH - how the 3D-ish look works!
-------------------------------------------
A normal top-down map draws every tile as a square. Here we draw each tile
as a DIAMOND that is 64 pixels wide and 32 tall:

    screen_x = (gx - gy) * 32
    screen_y = (gx + gy) * 16

Why does this work? Walk one step EAST (gx + 1): the diamond moves 32 px
right and 16 px DOWN on the screen. Walk one step SOUTH (gy + 1): it moves
32 px LEFT and 16 px down. So the map's x-axis runs diagonally down-right
and the y-axis runs diagonally down-left - that tilt is the classic
"isometric" look.

Depth sorting: a tile with a bigger (gx + gy) is CLOSER to the viewer, so
we draw far tiles first and near ones later (this is called the "painter's
algorithm", like painting the background before the foreground). Tall
things (trees, the tent, you!) are "billboards" - flat pictures standing
upright on their diamond - drawn in the same far-to-near order so they
overlap correctly.
"""

import random

import pygame

TILE = 32  # kept for compatibility; iso math uses ISO_W / ISO_H below
MAP_W, MAP_H = 24, 18

# Isometric diamond size (2:1 ratio, the classic look).
ISO_W, ISO_H = 64, 32
# Whole map in map-pixels: sx spans (0-17)*32-32 .. (23-0)*32+32.
MAP_PX_W = (MAP_W + MAP_H) * (ISO_W // 2)  # 1344
MAP_PX_H = (MAP_W + MAP_H) * (ISO_H // 2)  # 672

# Tile names used in the map grid.
GRASS, TALL, WATER, TREE, PATH, TENT = (
    "grass", "tall_grass", "water", "tree", "path", "tent"
)
# Phase 2 tiles: tilled soil, chopped stumps, walkable bridges, fences.
SOIL, STUMP, BRIDGE, FENCE = "soil", "stump", "bridge", "fence"
# Tiles the player cannot walk onto. Bridges ARE walkable (that's the point!).
SOLID = {WATER, TREE, STUMP, FENCE}

# Held-key directions mapped to GRID steps. On the isometric screen, "up"
# means walking toward the top corner of the diamond map, which is one step
# north-west on the grid: (-1, -1). The arrow keys still feel natural -
# Up always moves you up the screen.
DIR_DELTAS = {
    "up": (-1, -1),
    "down": (1, 1),
    "left": (-1, 1),
    "right": (1, -1),
}

# Billboards stand on a plain grass diamond (the tree/tent tiles in the
# grid only decide WHERE the billboard goes, not the ground art).
GROUND_FOR = {TREE: GRASS, TENT: GRASS}

DIAMOND = [(32, 0), (63, 16), (32, 31), (0, 16)]  # points of one tile


def tile_to_screen(gx, gy):
    """Grid tile -> top vertex of its diamond, in map pixels (pre-camera)."""
    return (gx - gy) * (ISO_W // 2), (gx + gy) * (ISO_H // 2)


# ------------------------------------------------------------ tile painters
def _speckle_points(rng, count):
    """Random pixel spots inside a 64x32 diamond, for texture."""
    pts = []
    while len(pts) < count:
        x = rng.randrange(6, ISO_W - 6)
        y = rng.randrange(6, ISO_H - 6)
        # Point-in-diamond test (with a small margin so speckles stay inside).
        if abs(x - 32) / 32 + abs(y - 16) / 16 <= 0.8:
            pts.append((x, y))
    return pts


def _diamond_surface(base, speckles, seed=1234):
    """A 64x32 diamond tile. speckles = [(color, count, size), ...]."""
    rng = random.Random(seed)
    surf = pygame.Surface((ISO_W, ISO_H), pygame.SRCALPHA)
    pygame.draw.polygon(surf, base, DIAMOND)
    for color, count, size in speckles:
        for x, y in _speckle_points(rng, count):
            pygame.draw.rect(surf, color, (x, y, size, size))
    return surf


def _water_surface(variant):
    """Blue diamond with light wave dashes (two variants for shimmer)."""
    surf = pygame.Surface((ISO_W, ISO_H), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (45, 125, 225), DIAMOND)
    rng = random.Random(99 + variant)
    for x, y in _speckle_points(rng, 4):
        pygame.draw.rect(surf, (130, 195, 255), (x, y, 7, 2))
    return surf


def _tall_grass_surface():
    """Grass diamond with darker blade tufts sticking up."""
    surf = _diamond_surface((80, 170, 80), [((62, 148, 62), 10, 2)], seed=7)
    rng = random.Random(8)
    for x, y in _speckle_points(rng, 9):
        pygame.draw.rect(surf, (40, 125, 50), (x, y, 2, 5))
    return surf


def _tree_surface():
    """A little pixel pine, 28x44. Anchor: bottom-center (the trunk base)."""
    s = pygame.Surface((28, 44), pygame.SRCALPHA)
    pygame.draw.rect(s, (125, 85, 50), (12, 32, 5, 12))  # trunk
    pygame.draw.polygon(s, (30, 110, 50), [(14, 36), (2, 24), (26, 24)])
    pygame.draw.polygon(s, (38, 130, 58), [(14, 28), (4, 16), (24, 16)])
    pygame.draw.polygon(s, (48, 150, 68), [(14, 20), (6, 8), (22, 8)])
    return s


def _tent_surface():
    """A canvas tent with a little flag. Anchor: bottom-center."""
    s = pygame.Surface((44, 40), pygame.SRCALPHA)
    pygame.draw.polygon(s, (235, 238, 245), [(22, 8), (4, 38), (40, 38)])
    pygame.draw.polygon(s, (90, 90, 110), [(22, 8), (4, 38), (40, 38)], 2)
    pygame.draw.polygon(s, (45, 45, 60), [(22, 22), (15, 38), (29, 38)])
    pygame.draw.line(s, (80, 140, 210), (22, 8), (22, 38), 3)  # stripe
    pygame.draw.rect(s, (125, 85, 50), (21, 0, 2, 9))  # flag pole
    pygame.draw.polygon(s, (205, 75, 75), [(23, 0), (31, 3), (23, 6)])  # flag
    return s


# ------------------------------------------------- phase 2: farm & build
def _soil_surface():
    """Tilled soil: a brown diamond. Crops grow on top of this."""
    return _diamond_surface((150, 110, 70),
                            [((120, 88, 55), 14, 2),
                             ((170, 130, 88), 6, 2)], seed=21)


def _bridge_surface():
    """Wooden planks over water. Walkable!"""
    surf = _diamond_surface((170, 130, 85), [((150, 112, 70), 8, 2)],
                            seed=22)
    # Plank seams across the diamond.
    pygame.draw.line(surf, (120, 88, 55), (14, 16), (50, 16), 2)
    pygame.draw.line(surf, (120, 88, 55), (24, 8), (40, 24), 2)
    pygame.draw.line(surf, (120, 88, 55), (24, 24), (40, 8), 2)
    return surf


def _stump_surface():
    """What a chopped tree leaves behind. Anchor: bottom-center."""
    s = pygame.Surface((24, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 45), (4, 6, 16, 10))   # stump body
    pygame.draw.rect(s, (150, 115, 75), (6, 4, 12, 4))   # cut top
    return s


def _fence_surface():
    """A wooden fence section. Anchor: bottom-center."""
    s = pygame.Surface((52, 28), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 45), (4, 4, 7, 24))    # left post
    pygame.draw.rect(s, (110, 75, 45), (41, 4, 7, 24))   # right post
    pygame.draw.rect(s, (140, 100, 60), (0, 8, 52, 5))   # top rail
    pygame.draw.rect(s, (140, 100, 60), (0, 18, 52, 5))  # bottom rail
    return s


def _crop_surface(stage):
    """A crop at growth stage 0 (sprout), 1 (plant) or 2 (mature golden).

    Anchor: bottom-center. Crops are NOT tiles - they live in World.crops
    and are drawn as billboards on top of soil.
    """
    if stage == 0:  # tiny sprout
        s = pygame.Surface((16, 20), pygame.SRCALPHA)
        pygame.draw.rect(s, (50, 140, 60), (7, 10, 2, 10))
        pygame.draw.polygon(s, (70, 170, 80), [(8, 12), (2, 8), (8, 6)])
        pygame.draw.polygon(s, (70, 170, 80), [(8, 12), (14, 8), (8, 6)])
        return s
    if stage == 1:  # bushy plant
        s = pygame.Surface((22, 30), pygame.SRCALPHA)
        pygame.draw.rect(s, (45, 125, 55), (10, 14, 3, 16))
        for dx, dy in [(-6, 6), (6, 6), (-4, 0), (4, 0)]:
            pygame.draw.polygon(s, (60, 160, 70),
                                [(11 + dx, 18 + dy), (11 + dx - 6, 12 + dy),
                                 (11 + dx + 6, 12 + dy)])
        return s
    # stage 2: mature golden wheat
    s = pygame.Surface((26, 36), pygame.SRCALPHA)
    for x in (6, 13, 20):
        pygame.draw.rect(s, (190, 170, 90), (x, 12, 2, 24))
        for j in range(4):
            pygame.draw.rect(s, (225, 195, 110), (x - 3, 4 + j * 4, 8, 3))
    return s


# Crops take this many real seconds to grow one stage (3 stages total).
CROP_STAGE_TIME = 45.0


class World:
    """The fixed 24x18 map, rendered isometric.

    Border of water, trees, grass patches, paths, and the healer's tent -
    same layout as before, brand-new look.
    """

    def __init__(self):
        # Start with plain grass everywhere.
        self.grid = [[GRASS for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.tent_tile = (13, 10)
        self._build()
        # Snapshot of the original layout, so save/load only needs to
        # store tiles the player actually changed (tilled, chopped, built).
        self.base_grid = [row[:] for row in self.grid]
        # Crops are NOT tiles: (gx, gy) -> {"stage": 0..2, "t": seconds,
        # "announced": bool}. The soil tile underneath stays SOIL.
        self.crops = {}
        # Pre-rendered art: painted once here, blitted every frame.
        self.ground = {
            GRASS: _diamond_surface((80, 170, 80),
                                    [((62, 148, 62), 14, 2)]),
            TALL: _tall_grass_surface(),
            PATH: _diamond_surface((214, 194, 148),
                                   [((196, 176, 128), 14, 2)]),
            SOIL: _soil_surface(),
            BRIDGE: _bridge_surface(),
        }
        self._water_a = _water_surface(0)
        self._water_b = _water_surface(1)
        self.billboards = {TREE: _tree_surface(), TENT: _tent_surface(),
                           STUMP: _stump_surface(), FENCE: _fence_surface()}
        self.crop_stages = [_crop_surface(0), _crop_surface(1),
                            _crop_surface(2)]
        self.cam_x, self.cam_y = 0, 0
        self._frame = 0

    def _set(self, tx, ty, tile):
        self.grid[ty][tx] = tile

    def _rect(self, x0, y0, x1, y1, tile):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self._set(x, y, tile)

    def _build(self):
        # Border of water.
        for x in range(MAP_W):
            self._set(x, 0, WATER)
            self._set(x, MAP_H - 1, WATER)
        for y in range(MAP_H):
            self._set(0, y, WATER)
            self._set(MAP_W - 1, y, WATER)

        # Walking paths (a cross through the middle).
        for x in range(1, MAP_W - 1):
            self._set(x, 9, PATH)
        for y in range(1, MAP_H - 1):
            self._set(12, y, PATH)

        # Tall-grass patches (wild encounters happen here).
        self._rect(3, 3, 6, 5, TALL)
        self._rect(16, 12, 20, 14, TALL)
        self._rect(17, 3, 21, 5, TALL)

        # Scattered trees (solid).
        for tx, ty in [
            (2, 2), (8, 2), (10, 5), (14, 2), (21, 2),
            (2, 7), (6, 10), (2, 13), (5, 15), (10, 13),
            (14, 15), (20, 16), (22, 8), (8, 16), (4, 11),
        ]:
            self._set(tx, ty, TREE)

        # The healer's tent.
        self._set(*self.tent_tile, TENT)

    # -- queries ----------------------------------------------------------
    def in_bounds(self, tx, ty):
        return 0 <= tx < MAP_W and 0 <= ty < MAP_H

    def tile_at(self, tx, ty):
        if not self.in_bounds(tx, ty):
            return WATER  # off the map counts as water (solid)
        return self.grid[ty][tx]

    def is_solid(self, tx, ty):
        return self.tile_at(tx, ty) in SOLID

    # -- phase 2: farming & building ------------------------------------
    def set_tile(self, tx, ty, tile):
        """Change one tile (till, chop, build...). Records nothing extra:
        modified_tiles() diffs against the base layout when saving."""
        if self.in_bounds(tx, ty):
            self.grid[ty][tx] = tile

    def modified_tiles(self):
        """{(tx, ty): tile} for every tile the player changed. For saves."""
        out = {}
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.grid[y][x] != self.base_grid[y][x]:
                    out[(x, y)] = self.grid[y][x]
        return out

    def regrow_stumps(self):
        """Chopped trees grow back (called when resting at the tent)."""
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.grid[y][x] == STUMP:
                    self.grid[y][x] = TREE

    def update_crops(self, dt):
        """Grow crops in real time. Returns how many just became mature
        (so the game can toast 'ready to harvest!')."""
        matured = 0
        for crop in self.crops.values():
            if crop["stage"] < 2:
                crop["t"] += dt
                while crop["t"] >= CROP_STAGE_TIME and crop["stage"] < 2:
                    crop["t"] -= CROP_STAGE_TIME
                    crop["stage"] += 1
                if crop["stage"] >= 2 and not crop["announced"]:
                    crop["announced"] = True
                    matured += 1
        return matured

    def apply_camera(self, px, py):
        """Map pixels -> on-screen pixels (subtract the camera)."""
        return px - self.cam_x, py - self.cam_y

    def draw(self, surf, sprites, player=None):
        """Isometric render.

        Pass 1: every ground diamond (they tile edge-to-edge, so order
        doesn't matter). Pass 2: billboards (trees, tent, player) sorted
        far-to-near by depth so nearer things correctly overlap farther ones.
        """
        self._frame += 1
        sw, sh = surf.get_width(), surf.get_height()

        # Camera: keep the focus point centered, clamped to the map edges.
        if player is not None:
            fx, fy = player.px, player.py + 16  # aim at the player's feet
        else:
            fx, fy = 96, 320  # middle of the island
        self.cam_x = max(0, min(fx - sw // 2, MAP_PX_W - sw))
        self.cam_y = max(0, min(fy - sh // 2, MAP_PX_H - sh))

        surf.fill((18, 42, 74))  # deep water in the corners past the island

        # -- pass 1: ground --
        water = self._water_b if (self._frame // 30) % 2 else self._water_a
        for gy in range(MAP_H):
            for gx in range(MAP_W):
                sx, sy = tile_to_screen(gx, gy)
                dx, dy = sx - self.cam_x, sy - self.cam_y
                if dx < -ISO_W or dx > sw or dy < -ISO_H or dy > sh:
                    continue  # off-screen, skip it
                tile = self.grid[gy][gx]
                if tile == WATER:
                    surf.blit(water, (dx, dy))
                else:
                    surf.blit(self.ground.get(tile, self.ground[GRASS]),
                              (dx, dy))

        # -- pass 2: billboards, far (small gx+gy) to near (big gx+gy) --
        # The player's depth key is py/16, which equals gx+gy exactly for
        # any tile - so it sorts perfectly even mid-glide between tiles.
        # Each entry is (depth, kind, gx, gy): kind is "billboard"
        # (trees, tent, stumps, fences), "crop", or "player".
        tall = []
        for gy in range(MAP_H):
            for gx in range(MAP_W):
                if self.grid[gy][gx] in self.billboards:
                    tall.append((gx + gy, "billboard", gx, gy))
        for (cx, cy) in self.crops:
            tall.append((cx + cy, "crop", cx, cy))
        if player is not None:
            tall.append((player.py / 16.0, "player", None, None))
        tall.sort(key=lambda t: t[0])

        for _, kind, gx, gy in tall:
            if kind == "player":
                img = sprites.get_scaled("player", 2)
                ax, ay = player.px, player.py + 16  # feet at diamond center
                shadow_w = 20
            elif kind == "crop":
                img = self.crop_stages[self.crops[(gx, gy)]["stage"]]
                sx, sy = tile_to_screen(gx, gy)
                ax, ay = sx, sy + 16
                shadow_w = 14
            else:
                img = self.billboards[self.grid[gy][gx]]
                sx, sy = tile_to_screen(gx, gy)
                ax, ay = sx, sy + 16  # anchored at diamond center
                shadow_w = img.get_width() - 8
            dx, dy = ax - self.cam_x, ay - self.cam_y
            if not (-64 < dx < sw + 64 and -64 < dy < sh + 64):
                continue
            # Soft shadow on the ground, then the billboard itself.
            pygame.draw.ellipse(surf, (0, 0, 0, 70),
                                (dx - shadow_w // 2, dy - 3, shadow_w, 6))
            surf.blit(img, (dx - img.get_width() // 2, dy - img.get_height()))


class Player:
    """Tile-based smooth movement: pick a tile, glide to it.

    px/py are map-pixel coordinates of the tile's diamond top vertex
    (see tile_to_screen). The camera is subtracted at draw time.
    """

    SPEED = 4  # pixels per frame (an iso step takes ~9 frames)

    def __init__(self, tx, ty):
        self.tx, self.ty = tx, ty          # current tile
        self.px, self.py = tile_to_screen(tx, ty)  # map-pixel position
        self.moving = False
        self.target = (tx, ty)
        self.facing = "down"

    def update(self, dirs, world):
        """`dirs` is a set like {'up','left'} of currently held directions.

        Returns the name of the tile stepped onto this frame, or None.
        """
        if not self.moving:
            # Pick a direction (priority: up, down, left, right).
            for d in ("up", "down", "left", "right"):
                if d in dirs:
                    self.facing = d
                    dx, dy = DIR_DELTAS[d]
                    nx, ny = self.tx + dx, self.ty + dy
                    if not world.is_solid(nx, ny):
                        self.target = (nx, ny)
                        self.moving = True
                    break  # one step at a time
        else:
            # Glide toward the target diamond.
            tx, ty = tile_to_screen(*self.target)
            if self.px < tx:
                self.px = min(tx, self.px + self.SPEED)
            elif self.px > tx:
                self.px = max(tx, self.px - self.SPEED)
            if self.py < ty:
                self.py = min(ty, self.py + self.SPEED)
            elif self.py > ty:
                self.py = max(ty, self.py - self.SPEED)
            if (self.px, self.py) == (tx, ty):
                # Arrived: this counts as one "step".
                self.tx, self.ty = self.target
                self.moving = False
                return world.tile_at(self.tx, self.ty)
        return None

    def draw(self, surf, sprites):
        """Standalone draw (no camera). The game itself draws the player
        inside World.draw, depth-sorted with the trees and the tent."""
        img = sprites.get_scaled("player", 2)
        surf.blit(img, (self.px - 16, self.py + 16 - 32))

    def teleport(self, tx, ty):
        self.tx, self.ty = tx, ty
        self.px, self.py = tile_to_screen(tx, ty)
        self.moving = False
        self.target = (tx, ty)
