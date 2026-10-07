"""STARBEASTS overworld: tile map, player movement, collision."""

TILE = 32          # one tile = 32x32 pixels
MAP_W, MAP_H = 24, 18  # matches the 768x576 window

# Tile names used in the map grid.
GRASS, TALL, WATER, TREE, PATH, TENT = (
    "grass", "tall_grass", "water", "tree", "path", "tent"
)
SOLID = {WATER, TREE}  # tiles the player cannot walk onto


class World:
    """The fixed 24x18 map. Border of water, trees, grass patches, tent."""

    def __init__(self):
        # Start with plain grass everywhere.
        self.grid = [[GRASS for _ in range(MAP_W)] for _ in range(MAP_H)]
        self.tent_tile = (13, 10)
        self._build()

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

    def draw(self, surf, sprites):
        """Draw every tile. `sprites` is the sprites module."""
        for y in range(MAP_H):
            for x in range(MAP_W):
                tile = self.grid[y][x]
                surf.blit(sprites.get_scaled(tile, 2), (x * TILE, y * TILE))


class Player:
    """Tile-based smooth movement: pick a tile, glide to it."""

    SPEED = 4  # pixels per frame (a tile takes 8 frames)

    def __init__(self, tx, ty):
        self.tx, self.ty = tx, ty          # current tile
        self.px, self.py = tx * TILE, ty * TILE  # pixel position
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
                    dx, dy = {"up": (0, -1), "down": (0, 1),
                              "left": (-1, 0), "right": (1, 0)}[d]
                    nx, ny = self.tx + dx, self.ty + dy
                    if not world.is_solid(nx, ny):
                        self.target = (nx, ny)
                        self.moving = True
                    break  # one step at a time
        else:
            # Glide toward the target tile.
            tx, ty = self.target[0] * TILE, self.target[1] * TILE
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
        surf.blit(sprites.get_scaled("player", 2), (self.px, self.py))

    def teleport(self, tx, ty):
        self.tx, self.ty = tx, ty
        self.px, self.py = tx * TILE, ty * TILE
        self.moving = False
        self.target = (tx, ty)
