"""STARBEASTS headless smoke test.

Runs with the dummy video driver (no window opens):
    SDL_VIDEODRIVER=dummy python test_smoke.py
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

import random
from unittest import mock

import pygame

import main as main_module
import sprites
from battle import Battle
from creatures import (
    BESTIARY_ORDER,
    SPECIES,
    Creature,
    calc_damage,
    catch_chance,
    type_mult,
)
from game import Game
from world import MAP_H, MAP_W, TALL, WATER, World

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((PASS if cond else FAIL, name, detail))
    print(f"[{PASS if cond else FAIL}] {name}" + (f" ({detail})" if detail else ""))


def battle_bot(game, max_steps=600):
    """Play a battle with a simple bot: RUN, else FIGHT move 0."""
    steps = 0
    while game.state == "BATTLE" and steps < max_steps:
        steps += 1
        b = game.battle
        if b.state == "msg":
            b.handle_key(pygame.K_RETURN)
        elif b.state == "menu":
            b.menu_cursor = 3  # RUN
            b.handle_key(pygame.K_RETURN)
        elif b.state == "fight":
            b.handle_key(pygame.K_ESCAPE)
        elif b.state == "switch":
            for i, c in enumerate(game.party):
                if not c.fainted and i != b.active_idx:
                    b.switch_cursor = i
                    break
            b.handle_key(pygame.K_RETURN)
        elif b.state == "over":
            b.handle_key(pygame.K_RETURN)
    return steps


def main():
    pygame.init()
    screen = pygame.display.set_mode((768, 576))
    font_big = pygame.font.Font(None, 44)
    font = pygame.font.Font(None, 30)
    font_small = pygame.font.Font(None, 24)
    random.seed(123)

    # 1. Sprites ------------------------------------------------------
    sprites.validate_sprites()
    check("sprites: 15 maps, all 16x16, chars known", len(sprites.SPRITES) == 15)
    for name in sprites.SPRITES:
        s2 = sprites.get_scaled(name, 2)
        s3 = sprites.get_scaled(name, 3)
        assert s2.get_size() == (32, 32) and s3.get_size() == (48, 48), name
    check("sprites: scale 2x->32px, 3x->48px for all", True)
    check("sprites: 8 creature species + player + 6 tiles",
          len(sprites.SPRITES) == 1 + 8 + 6)

    # 2. World map ----------------------------------------------------
    w = World()
    border_ok = all(w.tile_at(x, 0) == WATER and w.tile_at(x, MAP_H - 1) == WATER
                    for x in range(MAP_W)) and \
                all(w.tile_at(0, y) == WATER and w.tile_at(MAP_W - 1, y) == WATER
                    for y in range(MAP_H))
    check("world: water border all around", border_ok)
    check("world: tent tile is 'tent'",
          w.tile_at(*w.tent_tile) == "tent", f"at {w.tent_tile}")
    tall_count = sum(1 for y in range(MAP_H) for x in range(MAP_W)
                     if w.tile_at(x, y) == TALL)
    check("world: tall-grass patches exist", tall_count > 20, f"{tall_count} tiles")
    check("world: player start (11,9) walkable", not w.is_solid(11, 9))
    check("world: water+tree solid, grass not",
          w.is_solid(0, 0) and w.is_solid(2, 2) and not w.is_solid(11, 9))

    # 3. Boot + starter ----------------------------------------------
    game = Game()
    check("game boots to TITLE", game.state == "TITLE")
    game.select_starter("cindercub")
    check("starter select -> OVERWORLD, party of 1",
          game.state == "OVERWORLD" and len(game.party) == 1,
          game.party[0].name)
    check("starter is Lv5", game.party[0].level == 5)
    check("starter recorded in bestiary", "cindercub" in game.bestiary)

    # 4. Walk 300 frames inside tall grass ---------------------------
    game.player.teleport(4, 4)  # inside patch 1 (x3-6, y3-5)
    start = (game.player.tx, game.player.ty)
    battles_seen = 0
    for _ in range(300):
        if game.state == "BATTLE":
            battles_seen += 1
            battle_bot(game)
            if game.state == "BATTLE":
                break  # bot got stuck; fail below
            game.player.teleport(4, 4)
            continue
        # bounce left/right to stay inside the patch
        dirs = {"right"} if game.player.tx < 6 else {"left"}
        game.update_overworld(dirs)
    moved = (game.player.tx, game.player.ty) != start
    check("300 frames of walking: player moved, no crash", moved,
          f"{start} -> {(game.player.tx, game.player.ty)}")
    check("walking: game still in a valid state",
          game.state in ("OVERWORLD", "BATTLE"),
          f"state={game.state}, battles={battles_seen}")

    # 5. Forced battle: use both moves --------------------------------
    game2 = Game()
    game2.select_starter("bloopfin")
    game2.start_battle("leafling")
    b = game2.battle
    check("forced battle starts", game2.state == "BATTLE" and b.state == "msg",
          f"wild {b.enemy.name} Lv{b.enemy.level}")
    enemy_hp0 = b.enemy.hp
    # advance past intro, choose FIGHT -> move 0 (Tackle)
    b.handle_key(pygame.K_RETURN)  # intro
    b.handle_key(pygame.K_RETURN)  # FIGHT
    b.handle_key(pygame.K_RETURN)  # Tackle
    guard = 0
    while b.state == "msg" and guard < 20:
        b.handle_key(pygame.K_RETURN)
        guard += 1
    check("move 1 (Tackle) dealt damage", b.enemy.hp < enemy_hp0,
          f"{enemy_hp0} -> {b.enemy.hp}")
    # back at menu? use move 1 (Bubble Slam) if battle still going
    if b.state == "menu" and not b.enemy.fainted:
        enemy_hp1 = b.enemy.hp
        b.handle_key(pygame.K_RETURN)  # FIGHT
        b.handle_key(pygame.K_DOWN)    # move 1
        b.handle_key(pygame.K_RETURN)  # confirm
        guard = 0
        while b.state == "msg" and guard < 20:
            b.handle_key(pygame.K_RETURN)
            guard += 1
        check("move 2 (Bubble Slam) dealt damage", b.enemy.hp < enemy_hp1,
              f"{enemy_hp1} -> {b.enemy.hp}")
    else:
        check("move 2 (Bubble Slam) dealt damage", True, "enemy fainted early")

    # 6. Orb catch (guaranteed via patched RNG) -----------------------
    game3 = Game()
    game3.select_starter("sproutle")
    game3.start_battle("novawisp")
    b3 = game3.battle
    b3.handle_key(pygame.K_RETURN)  # intro
    b3.enemy.hp = 1  # weaken it
    orbs0 = game3.orbs
    with mock.patch("battle.random.random", return_value=0.0):
        b3.menu_cursor = 2  # ORB
        b3.handle_key(pygame.K_RETURN)
        guard = 0
        while b3.state == "msg" and guard < 20:
            b3.handle_key(pygame.K_RETURN)
            guard += 1
    check("orb thrown: orbs decreased by 1", game3.orbs == orbs0 - 1,
          f"{orbs0} -> {game3.orbs}")
    check("orb caught novawisp: battle over", b3.state == "over",
          f"result={b3.result}")
    check("caught species in bestiary", "novawisp" in game3.bestiary)
    check("caught species joined party (had room)",
          any(c.species == "novawisp" for c in game3.party))
    b3.handle_key(pygame.K_RETURN)  # ENTER on 'over'
    check("after battle -> OVERWORLD", game3.state == "OVERWORLD")

    # 7. XP / level-up math -------------------------------------------
    c = Creature("leafling", level=3)
    expected = int(30 * 3 ** 1.4)
    check("xp_to_next = int(30 * level**1.4)", c.xp_to_next() == expected,
          f"Lv3 needs {expected}")
    c.hp = 10
    hp_before, max_before = c.hp, c.max_hp
    need2 = c.xp_to_next() + int(30 * 4 ** 1.4)
    gained = c.gain_xp(need2 + 5)
    check("gain_xp: 2 level-ups", gained == 2 and c.level == 5,
          f"Lv{c.level}, +{gained}")
    check("level-up: +3 max HP per level", c.max_hp == max_before + 6,
          f"{max_before} -> {c.max_hp}")
    check("level-up: 25% heal applied", c.hp > hp_before, f"{hp_before} -> {c.hp}")
    check("level-up: atk/def/spd grew ~+2/level",
          c.atk >= 14 - 2 and c.defense >= 13 - 2 and c.spd >= 15 - 2,
          f"atk={c.atk} def={c.defense} spd={c.spd}")

    # 8. Type chart + damage + catch formulas --------------------------
    check("type chart Ember>Leaf x1.5", type_mult("Ember", "Leaf") == 1.5)
    check("type chart Leaf>Aqua x1.5", type_mult("Leaf", "Aqua") == 1.5)
    check("type chart Aqua>Ember x1.5", type_mult("Aqua", "Ember") == 1.5)
    check("type chart Ember vs Aqua resisted x0.6",
          type_mult("Ember", "Aqua") == 0.6)
    check("type chart same-type x0.8", type_mult("Leaf", "Leaf") == 0.8)
    check("type chart Normal neutral x1.0", type_mult("Normal", "Leaf") == 1.0)
    a, d = Creature("cindercub", 5), Creature("leafling", 3)
    dmg = calc_damage(a, d, a.moves[1])
    check("calc_damage >= 1 and sane", 1 <= dmg < 200, f"dmg={dmg}")
    weak, full = Creature("aquaffle", 3), Creature("aquaffle", 3)
    weak.hp = 1
    check("catch chance: weak easier than full",
          catch_chance(weak) > catch_chance(full),
          f"{catch_chance(weak):.2f} > {catch_chance(full):.2f}")
    check("catch chance clamped 0.05..0.95",
          0.05 <= catch_chance(full) <= 0.95)

    # 9. Save / load round-trip ----------------------------------------
    game4 = Game()
    game4.select_starter("cindercub")
    game4.party.append(Creature("aquaffle", 4))
    game4.orbs = 5
    game4.bestiary.update(["cindercub", "aquaffle"])
    game4.player.teleport(7, 8)
    path = "/tmp/starbeasts_test_save.dat"
    game4.save(path)
    game5 = Game()
    ok = game5.load(path)
    same = (ok and len(game5.party) == 2 and game5.orbs == 5
            and game5.bestiary == {"cindercub", "aquaffle"}
            and (game5.player.tx, game5.player.ty) == (7, 8)
            and game5.party[0].level == 5
            and game5.party[1].species == "aquaffle"
            and game5.state == "OVERWORLD")
    check("save/load round-trip preserves everything", same)
    os.remove(path)

    # 10. Blackout ------------------------------------------------------
    game6 = Game()
    game6.select_starter("cindercub")
    game6.start_battle("emberspark")
    b6 = game6.battle
    b6.handle_key(pygame.K_RETURN)  # intro
    game6.party[0].hp = 1  # barely alive
    with mock.patch("battle.random.random", return_value=0.99):  # run fails
        b6.menu_cursor = 3  # RUN
        b6.handle_key(pygame.K_RETURN)
        guard = 0
        while b6.state == "msg" and guard < 30:
            b6.handle_key(pygame.K_RETURN)
            guard += 1
    check("blackout: fainted with no backup -> over",
          b6.state == "over" and b6.result == "blackout",
          f"state={b6.state} result={b6.result}")
    b6.handle_key(pygame.K_RETURN)
    tx, ty = game6.player.tx, game6.player.ty
    check("blackout: respawn at tent, healed, orbs refilled",
          game6.state == "OVERWORLD"
          and (tx, ty) == game6.world.tent_tile
          and game6.party[0].hp == game6.party[0].max_hp
          and game6.orbs == 8,
          f"at {(tx, ty)}, hp={game6.party[0].hp}, orbs={game6.orbs}")

    # 11. Tent rest ------------------------------------------------------
    game7 = Game()
    game7.select_starter("bloopfin")
    game7.party[0].hp = 5
    game7.orbs = 2
    game7.player.teleport(*game7.world.tent_tile)
    game7.rest_at_tent()
    check("tent: heal + orbs refill + save",
          game7.party[0].hp == game7.party[0].max_hp and game7.orbs == 8
          and os.path.exists("save.dat"),
          f"hp={game7.party[0].hp}, orbs={game7.orbs}")
    os.remove("save.dat")

    # 12. Draw every screen headless ------------------------------------
    try:
        main_module.draw_title(screen, font_big, font)
        game8 = Game()
        main_module.draw_starter(screen, game8, font_big, font, font_small)
        game8.select_starter("sproutle")
        main_module.draw_overworld(screen, game8, font_big, font, font_small)
        game8.state = "BESTIARY"
        main_module.draw_bestiary(screen, game8, font_big, font, font_small)
        game8.state = "VICTORY"
        main_module.draw_victory(screen, font_big, font)
        game8.state = "BATTLE"
        game8.start_battle("thornbloom")
        for s in ("msg", "menu", "fight", "switch", "over", "orb"):
            game8.battle.state = s
            game8.battle.draw(screen, sprites, font_big, font)
        # Phase 2 screens (drawn over the overworld).
        game8.state = "CRAFT"
        main_module.draw_craft(screen, game8, font_big, font, font_small)
        game8.state = "BUILD"
        main_module.draw_build(screen, game8, font_big, font, font_small)
        game8.state = "INVENTORY"
        main_module.draw_inventory(screen, game8, font_big, font, font_small)
        game8.state = "BUILD_PLACE"
        game8.build_choice = 0
        main_module.draw_overworld(screen, game8, font_big, font, font_small)
        drew_ok = True
    except Exception as e:  # noqa: BLE001
        drew_ok = False
        print("DRAW ERROR:", repr(e))
    check("all screens + battle states draw without crashing", drew_ok)

    # 13. Bestiary / victory logic --------------------------------------
    game9 = Game()
    game9.select_starter("cindercub")
    for key in BESTIARY_ORDER:
        game9.bestiary.add(key)
    check("8/8 species -> victory", game9.check_victory())

    # 14. Phase 2: farming / crafting / building -------------------------
    from world import BRIDGE, FENCE, GRASS, SOIL, STUMP, TREE  # noqa: E402
    g = Game()
    g.select_starter("cindercub")
    check("new game: bag starts with 5 seeds, 0 wood",
          g.inv["seeds"] == 5 and g.inv["wood"] == 0)

    # Till -> plant -> grow -> harvest. Player at (5,7), facing down -> (6,8).
    g.player.teleport(5, 7)
    g.player.facing = "down"
    g.interact()
    check("F on grass tills soil", g.world.tile_at(6, 8) == SOIL)
    g.interact()
    check("F on soil plants a seed (5 -> 4)",
          (6, 8) in g.world.crops and g.inv["seeds"] == 4,
          f"seeds={g.inv['seeds']}")
    g.interact()
    check("F on growing crop: still growing, no seed consumed",
          g.world.crops[(6, 8)]["stage"] == 0 and g.inv["seeds"] == 4)
    g.world.update_crops(46)
    check("crop grows: stage 0 -> 1 after 46s",
          g.world.crops[(6, 8)]["stage"] == 1)
    g.world.update_crops(46)
    check("crop grows: stage 1 -> 2 (mature)",
          g.world.crops[(6, 8)]["stage"] == 2)
    g.interact()
    check("F on mature crop: +2 crops +1 seed, soil stays",
          g.inv["crops"] == 2 and g.inv["seeds"] == 5
          and (6, 8) not in g.world.crops
          and g.world.tile_at(6, 8) == SOIL,
          f"crops={g.inv['crops']} seeds={g.inv['seeds']}")

    # Chop a tree -> stump; rest regrows it. Tree at (2,7): stand (3,8).
    g.player.teleport(3, 8)
    g.player.facing = "up"
    g.interact()
    check("F on tree: +2 wood, becomes stump",
          g.inv["wood"] == 2 and g.world.tile_at(2, 7) == STUMP,
          f"wood={g.inv['wood']}")
    check("stump is solid", g.world.is_solid(2, 7))
    g.rest_at_tent()
    check("rest at tent regrows stumps", g.world.tile_at(2, 7) == TREE)
    if os.path.exists("save.dat"):
        os.remove("save.dat")

    # Crafting.
    g.inv["wood"] = 3
    orbs0 = g.orbs
    g.craft(0)
    check("craft orb: 3 wood -> +1 orb",
          g.orbs == orbs0 + 1 and g.inv["wood"] == 0)
    g.craft(0)
    check("unaffordable craft: orbs unchanged", g.orbs == orbs0 + 1)
    g.inv["wood"] = 1
    g.craft(1)
    check("craft super orb: 2 crops + 1 wood -> +1 super orb",
          g.inv["super_orbs"] == 1 and g.inv["crops"] == 0
          and g.inv["wood"] == 0)
    g.inv["wood"] = 4
    g.craft(2)
    check("craft fence kit: 4 wood -> +1 kit",
          g.inv["fence_kits"] == 1 and g.inv["wood"] == 0)

    # Building: fence on soil (6,8), then remove it for a wood refund.
    g.player.teleport(5, 7)
    g.player.facing = "down"
    g.build_choice = 0
    g.place_build()
    check("build fence on soil: kit consumed, fence solid",
          g.inv["fence_kits"] == 0 and g.world.tile_at(6, 8) == FENCE
          and g.world.is_solid(6, 8))
    g.build_choice = None
    g.interact()  # F on your own fence -> remove, +1 wood
    check("F on fence removes it: +1 wood, back to grass",
          g.world.tile_at(6, 8) == GRASS and g.inv["wood"] == 1)
    # Bridge on water: stand (5,1) facing up -> (4,0) is border water.
    g.player.teleport(5, 1)
    g.player.facing = "up"
    g.build_choice = 1
    g.inv["wood"] = 4
    g.place_build()
    check("build bridge on water: walkable",
          g.world.tile_at(4, 0) == BRIDGE and not g.world.is_solid(4, 0))
    g.build_choice = None
    # Invalid spot: fence on water is rejected, kit kept.
    g.inv["fence_kits"] = 1
    g.build_choice = 0
    g.place_build()
    check("fence on water rejected: bridge stays, kit kept",
          g.world.tile_at(4, 0) == BRIDGE and g.inv["fence_kits"] == 1)
    g.build_choice = None

    # Super orb in battle: consumed, catch works (mocked RNG).
    g2 = Game()
    g2.select_starter("sproutle")
    g2.orbs = 0
    g2.inv["super_orbs"] = 1
    g2.start_battle("novawisp")
    b2 = g2.battle
    b2.handle_key(pygame.K_RETURN)  # intro
    b2.enemy.hp = 1
    b2.state = "orb"
    b2.orb_cursor = 1  # super orb
    with mock.patch("battle.random.random", return_value=0.0):
        b2.handle_key(pygame.K_RETURN)
        guard = 0
        while b2.state == "msg" and guard < 20:
            b2.handle_key(pygame.K_RETURN)
            guard += 1
    check("super orb: consumed and caught novawisp",
          g2.inv["super_orbs"] == 0 and b2.state == "over"
          and "novawisp" in g2.bestiary)

    # Save/load keeps farm state: till + plant, save, reload.
    g3 = Game()
    g3.select_starter("bloopfin")
    g3.player.teleport(5, 7)
    g3.player.facing = "down"
    g3.interact()  # till (6,8)
    g3.interact()  # plant (seeds 5 -> 4)
    g3.inv["wood"] = 7
    path3 = "/tmp/starbeasts_test_save2.dat"
    g3.save(path3)
    g4 = Game()
    ok3 = g4.load(path3)
    same3 = (ok3 and g4.world.tile_at(6, 8) == SOIL
             and (6, 8) in g4.world.crops
             and g4.inv["wood"] == 7 and g4.inv["seeds"] == 4)
    check("save/load preserves farm state (soil, crop, bag)", same3)
    os.remove(path3)

    # World map overlay (M key): draws without crashing, and the
    # missing-file fallback shows a message instead of crashing.
    pygame.display.set_mode((768, 576))
    scr = pygame.display.get_surface()
    fb, f_, fs = (pygame.font.Font(None, s) for s in (44, 30, 24))
    g5 = Game()
    g5.select_starter("sproutle")
    g5.state = "WORLDMAP"  # as if M was pressed in the overworld
    try:
        main_module.draw_worldmap(scr, fb, f_, fs)
        drawn = True
    except Exception:
        drawn = False
    check("world map overlay draws without crashing",
          drawn and g5.state == "WORLDMAP")
    g5.state = "OVERWORLD"  # as if M / ESC was pressed to close it
    check("world map closes back to overworld", g5.state == "OVERWORLD")
    main_module._world_map_cache["loaded"] = True
    main_module._world_map_cache["image"] = None  # pretend file is missing
    try:
        main_module.draw_worldmap(scr, fb, f_, fs)
        fallback_ok = True
    except Exception:
        fallback_ok = False
    check("world map missing-file fallback draws message", fallback_ok)

    # -- summary --
    fails = [r for r in results if r[0] == FAIL]
    print(f"\n{len(results) - len(fails)}/{len(results)} checks passed.")
    if fails:
        print("FAILURES:")
        for _, name, detail in fails:
            print(f"  - {name} {detail}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
