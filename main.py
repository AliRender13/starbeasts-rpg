"""STARBEASTS - a 2D pixel-creature RPG. Run this file to play."""

import os

import pygame

import sprites
from creatures import BESTIARY_ORDER, SPECIES
from game import BUILD_OPTIONS, RECIPES, SAVE_FILE, Game
from world import DIAMOND, TILE, tile_to_screen

WIDTH, HEIGHT = 768, 576
FPS = 60

STARTER_KEYS = ["cindercub", "bloopfin", "sproutle"]

# The hand-drawn world map shown by the M key. Loaded once, on demand;
# if the file is missing the overlay shows a message instead of crashing.
WORLD_MAP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "world-map.png")
_world_map_cache = {"loaded": False, "image": None}


def get_world_map():
    """Load world-map.png once; return None when the file is missing."""
    if not _world_map_cache["loaded"]:
        _world_map_cache["loaded"] = True
        try:
            _world_map_cache["image"] = pygame.image.load(WORLD_MAP_FILE)
        except (pygame.error, FileNotFoundError, OSError):
            _world_map_cache["image"] = None
    return _world_map_cache["image"]


def make_silhouette(surf):
    """Black silhouette of a sprite (for uncaught bestiary entries)."""
    mask = pygame.mask.from_surface(surf)
    return mask.to_surface(setcolor=(25, 25, 40), unsetcolor=(0, 0, 0, 0))


def _wrap(text, font, max_width):
    """Split text into lines that fit max_width pixels."""
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def main():
    pygame.init()
    pygame.display.set_caption("STARBEASTS")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font_big = pygame.font.Font(None, 44)
    font = pygame.font.Font(None, 30)
    font_small = pygame.font.Font(None, 24)

    game = Game()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        game.tick_toast(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if game.state == "TITLE":
                    if key == pygame.K_RETURN:
                        game.state = "STARTER"
                    elif key == pygame.K_l:
                        if game.load():
                            game.set_toast("Save loaded!")
                        else:
                            game.set_toast("No save file found.")
                elif game.state == "STARTER":
                    if key == pygame.K_LEFT:
                        game.starter_cursor = (game.starter_cursor - 1) % 3
                    elif key == pygame.K_RIGHT:
                        game.starter_cursor = (game.starter_cursor + 1) % 3
                    elif key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.select_starter(
                            STARTER_KEYS[game.starter_cursor])
                elif game.state == "OVERWORLD":
                    if key in (pygame.K_RETURN, pygame.K_SPACE):
                        if game.on_tent_tile():
                            game.rest_at_tent()
                    elif key == pygame.K_b:
                        game.state = "BESTIARY"
                    elif key == pygame.K_s:
                        game.save()
                        game.set_toast("Game saved.")
                    elif key == pygame.K_f:
                        game.interact()  # use the faced tile
                    elif key == pygame.K_c:
                        game.state = "CRAFT"
                        game.craft_cursor = 0
                    elif key == pygame.K_v:
                        game.state = "BUILD"
                        game.build_cursor = 0
                    elif key == pygame.K_i:
                        game.state = "INVENTORY"
                    elif key == pygame.K_m:
                        game.state = "WORLDMAP"  # fullscreen world map
                elif game.state == "CRAFT":
                    if key == pygame.K_UP:
                        game.craft_cursor = (game.craft_cursor - 1) % len(RECIPES)
                    elif key == pygame.K_DOWN:
                        game.craft_cursor = (game.craft_cursor + 1) % len(RECIPES)
                    elif key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.craft(game.craft_cursor)
                    elif key == pygame.K_ESCAPE:
                        game.state = "OVERWORLD"
                elif game.state == "BUILD":
                    if key == pygame.K_UP:
                        game.build_cursor = (game.build_cursor - 1) % len(BUILD_OPTIONS)
                    elif key == pygame.K_DOWN:
                        game.build_cursor = (game.build_cursor + 1) % len(BUILD_OPTIONS)
                    elif key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.build_choice = game.build_cursor
                        game.state = "BUILD_PLACE"
                    elif key == pygame.K_ESCAPE:
                        game.state = "OVERWORLD"
                elif game.state == "BUILD_PLACE":
                    # You can still walk around to aim the ghost preview.
                    if key in (pygame.K_f, pygame.K_RETURN, pygame.K_SPACE):
                        game.place_build()
                    elif key == pygame.K_ESCAPE:
                        game.state = "OVERWORLD"
                        game.build_choice = None
                elif game.state == "INVENTORY":
                    if key in (pygame.K_i, pygame.K_ESCAPE, pygame.K_RETURN):
                        game.state = "OVERWORLD"
                elif game.state == "WORLDMAP":
                    # M, ESC, or ENTER closes the map back to the overworld.
                    if key in (pygame.K_m, pygame.K_ESCAPE, pygame.K_RETURN):
                        game.state = "OVERWORLD"
                elif game.state == "BATTLE":
                    game.battle.handle_key(key)
                elif game.state == "BESTIARY":
                    if key in (pygame.K_b, pygame.K_ESCAPE, pygame.K_RETURN):
                        game.state = "OVERWORLD"
                elif game.state == "VICTORY":
                    if key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.state = "OVERWORLD"

        # Held-key movement matters in the overworld - and while placing
        # buildings, so you can walk the ghost preview into position.
        if game.state in ("OVERWORLD", "BUILD_PLACE"):
            pressed = pygame.key.get_pressed()
            dirs = set()
            if pressed[pygame.K_UP] or pressed[pygame.K_w]:
                dirs.add("up")
            if pressed[pygame.K_DOWN] or pressed[pygame.K_s]:
                dirs.add("down")
            if pressed[pygame.K_LEFT] or pressed[pygame.K_a]:
                dirs.add("left")
            if pressed[pygame.K_RIGHT] or pressed[pygame.K_d]:
                dirs.add("right")
            game.update_overworld(dirs, dt)

        # -- draw the current screen --
        if game.state == "TITLE":
            draw_title(screen, font_big, font)
        elif game.state == "STARTER":
            draw_starter(screen, game, font_big, font, font_small)
        elif game.state in ("OVERWORLD", "BUILD_PLACE"):
            draw_overworld(screen, game, font_big, font, font_small)
        elif game.state == "CRAFT":
            draw_craft(screen, game, font_big, font, font_small)
        elif game.state == "BUILD":
            draw_build(screen, game, font_big, font, font_small)
        elif game.state == "INVENTORY":
            draw_inventory(screen, game, font_big, font, font_small)
        elif game.state == "WORLDMAP":
            draw_worldmap(screen, font_big, font, font_small)
        elif game.state == "BATTLE":
            game.battle.draw(screen, sprites, font_big, font)
        elif game.state == "BESTIARY":
            draw_bestiary(screen, game, font_big, font, font_small)
        elif game.state == "VICTORY":
            draw_victory(screen, font_big, font)

        pygame.display.flip()

    pygame.quit()


# --------------------------------------------------------------- screens
def draw_title(screen, font_big, font):
    screen.fill((12, 14, 34))  # night sky
    # A row of the three starters for flavor.
    for i, key in enumerate(STARTER_KEYS):
        screen.blit(sprites.get_scaled(key, 4), (180 + i * 150, 150))
    title = font_big.render("STARBEASTS", True, (255, 220, 90))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
    sub = font.render("Catch all 8 Starbeasts!", True, (180, 200, 255))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 380))
    hint = font.render("ENTER: new game      L: load saved game",
                       True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 440))


def draw_starter(screen, game, font_big, font, font_small):
    screen.fill((12, 14, 34))
    title = font_big.render("Choose your partner!", True, (255, 220, 90))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))
    for i, key in enumerate(STARTER_KEYS):
        info = SPECIES[key]
        x = 44 + i * 240
        selected = (i == game.starter_cursor)
        color = (255, 220, 90) if selected else (90, 90, 120)
        pygame.draw.rect(screen, (24, 24, 40), (x, 120, 210, 330))
        pygame.draw.rect(screen, color, (x, 120, 210, 330), 4 if selected else 2)
        screen.blit(sprites.get_scaled(key, 4), (x + 73, 150))
        name = font.render(info["name"], True, (240, 240, 240))
        screen.blit(name, (x + 105 - name.get_width() // 2, 230))
        ctype = font_small.render(info["type"] + " type", True, (170, 200, 255))
        screen.blit(ctype, (x + 105 - ctype.get_width() // 2, 262))
        # Description wrapped to two short lines so it fits the card.
        for j, line in enumerate(_wrap(info["desc"], font_small, 190)):
            desc = font_small.render(line, True, (160, 160, 170))
            screen.blit(desc, (x + 105 - desc.get_width() // 2, 292 + j * 26))
        hp, atk, df, spd = info["base"]
        for j, line in enumerate((f"HP{hp}  ATK{atk}", f"DEF{df}  SPD{spd}")):
            stats = font_small.render(line, True, (160, 160, 170))
            screen.blit(stats, (x + 105 - stats.get_width() // 2, 352 + j * 26))
        if selected:
            # Little triangle marker under the selected card.
            cx = x + 105
            pygame.draw.polygon(screen, (255, 220, 90),
                                [(cx - 12, 418), (cx + 12, 418), (cx, 434)])
    hint = font.render("Left/Right: choose      ENTER: confirm",
                       True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 500))


def draw_overworld(screen, game, font_big, font, font_small):
    # Isometric render: the world draws ground + billboards + the player,
    # depth-sorted, with a camera that follows the player.
    game.world.draw(screen, sprites, game.player)

    # Top HUD: active creature + orbs.
    pygame.draw.rect(screen, (20, 20, 30), (0, 0, WIDTH, 44))
    active = game.party[game.first_healthy_index()] if game.party else None
    if active:
        hud = font.render(
            f"{active.name} Lv{active.level}  HP {active.hp}/{active.max_hp}"
            f"      Orbs: {game.orbs}"
            f"      Caught: {len(game.bestiary)}/8", True, (240, 240, 240))
        screen.blit(hud, (16, 10))

    # Toast message (fades after a few seconds).
    if game.toast:
        toast = font.render(game.toast, True, (255, 240, 180))
        bg = pygame.Surface((toast.get_width() + 24, 40))
        bg.fill((20, 20, 30))
        screen.blit(bg, (WIDTH // 2 - bg.get_width() // 2, HEIGHT - 110))
        screen.blit(toast, (WIDTH // 2 - toast.get_width() // 2, HEIGHT - 102))

    # Controls hint.
    hint = font_small.render(
        "Arrows/WASD: move   F: use   C: craft   V: build   I: bag   "
        "B: bestiary   M: map",
        True, (230, 230, 230))
    bg = pygame.Surface((WIDTH, 30))
    bg.fill((20, 20, 30))
    screen.blit(bg, (0, HEIGHT - 30))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 26))

    # "!" marker over the tent when standing on it.
    if game.on_tent_tile():
        _, psy = game.world.apply_camera(game.player.px, game.player.py)
        mark = font.render("ENTER: rest & save", True, (255, 220, 90))
        screen.blit(mark, (WIDTH // 2 - mark.get_width() // 2, psy - 34))

    # Build-mode ghost preview: a green diamond where the building CAN go,
    # red where it can't. Walk to aim it, F to place, ESC to cancel.
    if game.state == "BUILD_PLACE":
        tx, ty = game.faced_tile()
        if game.world.in_bounds(tx, ty):
            ok = game.build_spot_ok()
            sx, sy = tile_to_screen(tx, ty)
            dx, dy = game.world.apply_camera(sx, sy)
            pts = [(dx + x, dy + y) for x, y in DIAMOND]
            pygame.draw.polygon(screen,
                                (90, 255, 90) if ok else (255, 90, 90),
                                pts, 3)
            label = font_small.render(
                "F: place   ESC: cancel  (walk to aim)", True, (255, 255, 255))
            screen.blit(label, (WIDTH // 2 - label.get_width() // 2, 52))


# ------------------------------------------------- phase 2 screens
def _panel(screen, title, font_big, font):
    """Dark overlay panel shared by the CRAFT/BUILD/INVENTORY screens."""
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((10, 10, 18))
    screen.blit(overlay, (0, 0))
    pygame.draw.rect(screen, (30, 30, 46), (154, 90, 460, 400))
    pygame.draw.rect(screen, (255, 220, 90), (154, 90, 460, 400), 3)
    head = font_big.render(title, True, (255, 220, 90))
    screen.blit(head, (WIDTH // 2 - head.get_width() // 2, 110))


def draw_craft(screen, game, font_big, font, font_small):
    draw_overworld(screen, game, font_big, font, font_small)  # dim backdrop
    _panel(screen, "CRAFTING  (C)", font_big, font)
    for i, recipe in enumerate(RECIPES):
        y = 190 + i * 70
        ok = game.can_afford(recipe["cost"])
        color = (255, 220, 90) if i == game.craft_cursor else (210, 210, 210)
        if not ok:
            color = (110, 110, 120)  # grayed out: can't afford it
        prefix = "> " if i == game.craft_cursor else "  "
        name = font.render(prefix + recipe["name"], True, color)
        screen.blit(name, (200, y))
        cost = font_small.render(recipe["blurb"], True, (170, 190, 220))
        screen.blit(cost, (230, y + 32))
    hint = font_small.render("ENTER: craft   ESC: close", True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 440))


def draw_build(screen, game, font_big, font, font_small):
    draw_overworld(screen, game, font_big, font, font_small)
    _panel(screen, "BUILD  (V)", font_big, font)
    for i, opt in enumerate(BUILD_OPTIONS):
        y = 200 + i * 80
        color = (255, 220, 90) if i == game.build_cursor else (210, 210, 210)
        prefix = "> " if i == game.build_cursor else "  "
        name = font.render(prefix + opt["name"], True, color)
        screen.blit(name, (200, y))
        cost = font_small.render(opt["blurb"], True, (170, 190, 220))
        screen.blit(cost, (230, y + 32))
    hint = font_small.render("ENTER: choose, then F places it   ESC: close",
                             True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 440))


def draw_inventory(screen, game, font_big, font, font_small):
    draw_overworld(screen, game, font_big, font, font_small)
    _panel(screen, "BAG  (I)", font_big, font)
    rows = [("Wood", game.inv["wood"], "chop trees with F"),
            ("Seeds", game.inv["seeds"], "plant them in tilled soil"),
            ("Crops", game.inv["crops"], "harvested - craft super orbs"),
            ("Orbs", game.orbs, "catch wild starbeasts"),
            ("Super Orbs", game.inv["super_orbs"], "1.3x catch chance!"),
            ("Fence Kits", game.inv["fence_kits"], "V: build fences")]
    for i, (name, count, tip) in enumerate(rows):
        y = 180 + i * 44
        line = font.render(f"{name} x{count}", True, (240, 240, 240))
        screen.blit(line, (210, y))
        sub = font_small.render(tip, True, (150, 160, 180))
        screen.blit(sub, (420, y + 6))
    hint = font_small.render("I / ESC: close", True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 470))


def draw_worldmap(screen, font_big, font, font_small):
    """Fullscreen world-map overlay, opened with M in the overworld."""
    screen.fill((16, 13, 22))  # dark parchment night
    title = font_big.render("WORLD OF STARBEASTS", True, (255, 220, 90))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 8))

    img = get_world_map()
    top, bottom = 56, HEIGHT - 52  # room for the title bar + legend bar
    if img is None:
        msg = font.render("World map not found (world-map.png is missing).",
                          True, (220, 120, 120))
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2))
    else:
        # Scale the map to fit, keeping its aspect ratio, then center it.
        avail_w, avail_h = WIDTH - 40, bottom - top
        scale = min(avail_w / img.get_width(), avail_h / img.get_height())
        w, h = max(1, int(img.get_width() * scale)), \
            max(1, int(img.get_height() * scale))
        small = pygame.transform.smoothscale(img, (w, h))
        x, y = (WIDTH - w) // 2, top + (avail_h - h) // 2
        pygame.draw.rect(screen, (255, 220, 90),  # gold frame
                         (x - 4, y - 4, w + 8, h + 8), 3)
        screen.blit(small, (x, y))

    # Legend bar: what each mark on the map means.
    bar = pygame.Surface((WIDTH, 44))
    bar.set_alpha(180)
    bar.fill((10, 10, 16))
    screen.blit(bar, (0, HEIGHT - 52))
    legend = font_small.render(
        "Castle=Kingdom   Anchor=Port   Pick=Mine   Arch=Dungeon   "
        "House=Village   Star=Mark", True, (230, 220, 190))
    screen.blit(legend, (WIDTH // 2 - legend.get_width() // 2, HEIGHT - 46))
    hint = font_small.render("M / ESC: close", True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 24))


def draw_bestiary(screen, game, font_big, font, font_small):
    screen.fill((12, 14, 34))
    title = font_big.render(
        f"BESTIARY  {len(game.bestiary)}/{len(BESTIARY_ORDER)}",
        True, (255, 220, 90))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 24))
    for i, key in enumerate(BESTIARY_ORDER):
        info = SPECIES[key]
        col, row = i % 4, i // 4
        x, y = 24 + col * 186, 100 + row * 200
        pygame.draw.rect(screen, (24, 24, 40), (x, y, 170, 180))
        caught = key in game.bestiary
        sprite = sprites.get_scaled(key, 3)
        if caught:
            screen.blit(sprite, (x + 61, y + 16))
            name = font.render(info["name"], True, (240, 240, 240))
            screen.blit(name, (x + 85 - name.get_width() // 2, y + 80))
            ctype = font_small.render(info["type"], True, (170, 200, 255))
            screen.blit(ctype, (x + 85 - ctype.get_width() // 2, y + 112))
            rarity = font_small.render(info["rarity"], True, (150, 150, 160))
            screen.blit(rarity, (x + 85 - rarity.get_width() // 2, y + 138))
        else:
            screen.blit(make_silhouette(sprite), (x + 61, y + 16))
            name = font.render("???", True, (120, 120, 140))
            screen.blit(name, (x + 85 - name.get_width() // 2, y + 80))
            unknown = font_small.render("???", True, (100, 100, 115))
            screen.blit(unknown, (x + 85 - unknown.get_width() // 2, y + 112))
    hint = font.render("B / ESC: back", True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 50))


def draw_victory(screen, font_big, font):
    screen.fill((12, 14, 34))
    for i, key in enumerate(BESTIARY_ORDER):
        screen.blit(sprites.get_scaled(key, 3),
                    (60 + (i % 4) * 170, 200 + (i // 4) * 90))
    title = font_big.render("BESTIARY COMPLETE!", True, (255, 220, 90))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
    sub = font.render("You caught all 8 Starbeasts. You are a true",
                      True, (200, 220, 255))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 120))
    sub2 = font.render("Starbeast Master!", True, (200, 220, 255))
    screen.blit(sub2, (WIDTH // 2 - sub2.get_width() // 2, 155))
    hint = font.render("ENTER: keep exploring", True, (150, 150, 170))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 430))


if __name__ == "__main__":
    main()
