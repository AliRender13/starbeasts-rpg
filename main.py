"""STARBEASTS - a 2D pixel-creature RPG. Run this file to play."""

import pygame

import sprites
from creatures import BESTIARY_ORDER, SPECIES
from game import SAVE_FILE, Game
from world import TILE

WIDTH, HEIGHT = 768, 576
FPS = 60

STARTER_KEYS = ["cindercub", "bloopfin", "sproutle"]


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
                elif game.state == "BATTLE":
                    game.battle.handle_key(key)
                elif game.state == "BESTIARY":
                    if key in (pygame.K_b, pygame.K_ESCAPE, pygame.K_RETURN):
                        game.state = "OVERWORLD"
                elif game.state == "VICTORY":
                    if key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.state = "OVERWORLD"

        # Held-key movement only matters in the overworld.
        if game.state == "OVERWORLD":
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
            game.update_overworld(dirs)

        # -- draw the current screen --
        if game.state == "TITLE":
            draw_title(screen, font_big, font)
        elif game.state == "STARTER":
            draw_starter(screen, game, font_big, font, font_small)
        elif game.state == "OVERWORLD":
            draw_overworld(screen, game, font_big, font, font_small)
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
    game.world.draw(screen, sprites)
    game.player.draw(screen, sprites)

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
        "Arrows/WASD: move   ENTER: tent   B: bestiary   S: save",
        True, (230, 230, 230))
    bg = pygame.Surface((WIDTH, 30))
    bg.fill((20, 20, 30))
    screen.blit(bg, (0, HEIGHT - 30))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 26))

    # "!" marker over the tent when standing on it.
    if game.on_tent_tile():
        mark = font.render("ENTER: rest & save", True, (255, 220, 90))
        screen.blit(mark, (WIDTH // 2 - mark.get_width() // 2,
                           game.player.py - 30))


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
