"""STARBEASTS battles: turn-based wild encounters.

The battle is player-paced: messages wait for ENTER. This keeps the code
simple (no timers) and easy to test.
"""

import random

import pygame

from creatures import (
    Creature, calc_damage, catch_chance, type_mult, wild_level,
)

MENU_OPTIONS = ["FIGHT", "SWITCH", "ORB", "RUN"]
RUN_CHANCE = 0.75


class Battle:
    """One wild encounter. States: msg / menu / fight / switch / over."""

    def __init__(self, game, wild_key):
        self.game = game
        self.enemy = Creature(wild_key, wild_level())
        self.active_idx = game.first_healthy_index()
        self.state = "msg"
        self.menu_cursor = 0
        self.move_cursor = 0
        self.switch_cursor = 0
        self.orb_cursor = 0
        self.forced_switch = False
        self.result = None
        # Message queue: list of (text, then_function_or_None).
        self._queue = []
        self.text = ""
        self._pending = None  # 'then' function waiting for ENTER
        self.state = None
        self.say(f"Wild {self.enemy.name} (Lv {self.enemy.level}) appeared!",
                 then=self._to_menu)

    # ------------------------------------------------------------ helpers
    def active(self):
        return self.game.party[self.active_idx]

    def say(self, text, then=None):
        """Queue a message. The first one shows right away."""
        self._queue.append((text, then))
        if self.state != "msg":
            self.state = "msg"
            self._show()

    def _show(self):
        """Display the next queued message (without running its 'then')."""
        if self._queue:
            self.text, self._pending = self._queue.pop(0)
        else:
            self._pending = None
            self._to_menu()

    def advance(self):
        """ENTER was pressed while a message is showing."""
        if self._pending is not None:
            pending, self._pending = self._pending, None
            pending()  # may queue more messages or change state
            if self.state == "msg":
                self._show()
        else:
            self._show()

    def _to_menu(self):
        self.state = "menu"
        self.menu_cursor = 0

    def _end(self, result):
        self.result = result
        self.state = "over"
        self.game.on_battle_end(result)

    @staticmethod
    def _effect_text(move_type, defend_type):
        mult = type_mult(move_type, defend_type)
        if mult > 1:
            return " It's super effective!"
        if mult < 1:
            return " It's not very effective..."
        return ""

    # -------------------------------------------------------------- input
    def handle_key(self, key):
        if self.state == "msg":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.advance()
        elif self.state == "menu":
            if key == pygame.K_UP:
                self.menu_cursor = (self.menu_cursor - 1) % 4
            elif key == pygame.K_DOWN:
                self.menu_cursor = (self.menu_cursor + 1) % 4
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._choose_menu(self.menu_cursor)
            # (no Esc on the main menu)
        elif self.state == "fight":
            if key == pygame.K_UP:
                self.move_cursor = (self.move_cursor - 1) % 2
            elif key == pygame.K_DOWN:
                self.move_cursor = (self.move_cursor + 1) % 2
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._player_attack(self.move_cursor)
            elif key == pygame.K_ESCAPE:
                self._to_menu()
        elif self.state == "switch":
            n = len(self.game.party)
            if key == pygame.K_UP:
                self.switch_cursor = (self.switch_cursor - 1) % n
            elif key == pygame.K_DOWN:
                self.switch_cursor = (self.switch_cursor + 1) % n
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._do_switch(self.switch_cursor)
            elif key == pygame.K_ESCAPE and not self.forced_switch:
                self._to_menu()
        elif self.state == "orb":
            # Phase 2: choose a normal orb or a super orb (1.3x catch!).
            if key == pygame.K_UP:
                self.orb_cursor = (self.orb_cursor - 1) % 2
            elif key == pygame.K_DOWN:
                self.orb_cursor = (self.orb_cursor + 1) % 2
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._throw_orb(super=(self.orb_cursor == 1))
            elif key == pygame.K_ESCAPE:
                self._to_menu()
        elif self.state == "over":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.game.after_battle()

    # ------------------------------------------------------------- actions
    def _choose_menu(self, idx):
        action = MENU_OPTIONS[idx]
        if action == "FIGHT":
            self.state = "fight"
            self.move_cursor = 0
        elif action == "SWITCH":
            self.forced_switch = False
            self.state = "switch"
            self.switch_cursor = self.active_idx
        elif action == "ORB":
            # Phase 2: if you carry BOTH orb types, pick which to throw.
            if self.game.orbs > 0 and self.game.inv["super_orbs"] > 0:
                self.state = "orb"
                self.orb_cursor = 0
            elif self.game.orbs > 0:
                self._throw_orb(super=False)
            elif self.game.inv["super_orbs"] > 0:
                self._throw_orb(super=True)
            else:
                self.say("No orbs left!", then=self._to_menu)
        elif action == "RUN":
            self._try_run()

    def _player_attack(self, move_idx):
        move = self.active().moves[move_idx]
        player, enemy = self.active(), self.enemy
        # Faster creature strikes first.
        if player.spd >= enemy.spd:
            self._hit(player, enemy, move,
                      then=self._after_player_hit)
        else:
            self._enemy_attack(then=self._after_enemy_hit_for_player_move,
                               saved_move=move)

    def _after_player_hit(self):
        """Continue the turn after the player's move landed."""
        if self.enemy.fainted:
            self._enemy_fainted()
        else:
            self._enemy_attack(then=self._after_enemy_hit)

    def _after_enemy_hit_for_player_move(self, move):
        if self.active().fainted:
            self._player_fainted()
        else:
            player, enemy = self.active(), self.enemy
            self._hit(player, enemy, move,
                      then=lambda: self._enemy_fainted()
                      if self.enemy.fainted else self._to_menu())

    def _after_enemy_hit(self):
        if self.active().fainted:
            self._player_fainted()
        else:
            self._to_menu()

    def _hit(self, attacker, defender, move, then=None):
        dmg = calc_damage(attacker, defender, move)
        defender.hp = max(0, defender.hp - dmg)
        eff = self._effect_text(move.type, defender.type)
        self.say(f"{attacker.name} used {move.name}!{eff}",
                 then=lambda: self.say(f"Dealt {dmg} damage!", then=then))

    def _enemy_attack(self, then=None, saved_move=None):
        enemy = self.enemy
        move = random.choice(enemy.moves)
        player = self.active()
        if saved_move is not None:
            # Enemy went first; player's move still to come.
            self._hit(enemy, player, move,
                      then=lambda: then(saved_move))
        else:
            self._hit(enemy, player, move, then=then)

    # ------------------------------------------------------------ outcomes
    def _enemy_fainted(self):
        enemy = self.enemy
        player = self.active()
        xp = 20 + 8 * enemy.level
        gained = player.gain_xp(xp)
        self.say(f"Wild {enemy.name} fainted!")
        if gained:
            self.say(
                f"{player.name} gained {xp} XP and grew to Lv {player.level}!",
                then=lambda: self._end("win"))
        else:
            self.say(f"{player.name} gained {xp} XP!",
                     then=lambda: self._end("win"))

    def _player_fainted(self):
        player = self.active()
        self.say(f"{player.name} fainted!")
        if all(c.fainted for c in self.game.party):
            self.say("All your creatures fainted...",
                     then=self._blackout)
        else:
            self.say("Choose your next creature!",
                     then=self._forced_switch_menu)

    def _forced_switch_menu(self):
        self.forced_switch = True
        self.state = "switch"
        self.switch_cursor = self.active_idx

    def _blackout(self):
        self.game.blackout()
        self._end("blackout")

    def _do_switch(self, idx):
        party = self.game.party
        if party[idx].fainted:
            self.say(f"{party[idx].name} is fainted!", then=self._reshow_switch)
            return
        if idx == self.active_idx and not self.forced_switch:
            self.say(f"{party[idx].name} is already out!", then=self._reshow_switch)
            return
        self.active_idx = idx
        newcomer = self.active()
        if self.forced_switch:
            self.forced_switch = False
            self.say(f"Go, {newcomer.name}!", then=self._to_menu)
        else:
            # Switching costs your turn: the enemy attacks.
            self.say(f"Go, {newcomer.name}!",
                     then=lambda: self._enemy_attack(then=self._after_enemy_hit))

    def _reshow_switch(self):
        self.state = "switch"

    def _throw_orb(self, super=False):
        """Throw an orb. Super orbs catch 1.3x better (craft them with C)."""
        if super:
            if self.game.inv["super_orbs"] <= 0:
                self.say("No super orbs left!", then=self._to_menu)
                return
            self.game.inv["super_orbs"] -= 1
            bonus = 1.3
            label = "a SUPER orb"
        else:
            if self.game.orbs <= 0:
                self.say("No orbs left!", then=self._to_menu)
                return
            self.game.orbs -= 1
            bonus = 1.0
            label = "an orb"
        enemy = self.enemy
        chance = min(0.95, catch_chance(enemy) * bonus)
        if random.random() < chance:
            self.say(f"You threw {label}... Gotcha! {enemy.name} was caught!",
                     then=self._caught)
        else:
            self.say(f"You threw {label}... {enemy.name} broke free!",
                     then=lambda: self._enemy_attack(then=self._after_enemy_hit))

    def _caught(self):
        enemy = self.enemy
        self.game.register_catch(enemy.species, enemy.level)
        if self.game.check_victory():
            self.say("BESTIARY COMPLETE!", then=lambda: self._end("victory"))
        else:
            self._end("caught")

    def _try_run(self):
        if random.random() < RUN_CHANCE:
            self.say("Got away safely!", then=lambda: self._end("ran"))
        else:
            self.say("Can't escape!",
                     then=lambda: self._enemy_attack(then=self._after_enemy_hit))

    # -------------------------------------------------------------- drawing
    def draw(self, surf, sprites, font_big, font):
        W, H = surf.get_size()
        surf.fill((36, 84, 46))  # grassy arena background
        # A lighter battle circle.
        pygame.draw.ellipse(surf, (52, 110, 62), (80, 40, W - 160, 340))

        # Enemy sprite (top right) + info box (top left).
        surf.blit(sprites.get_scaled(self.enemy.species, 3), (W - 200, 60))
        self._creature_card(surf, self.enemy, (24, 24), font_big, font,
                            is_enemy=True)

        # Player creature sprite (bottom left, flipped) + card (right).
        player_sprite = pygame.transform.flip(
            sprites.get_scaled(self.active().species, 3), True, False)
        surf.blit(player_sprite, (110, 220))
        self._creature_card(surf, self.active(), (W - 264, 250),
                            font_big, font, is_enemy=False)

        # Bottom panel.
        pygame.draw.rect(surf, (24, 24, 36), (0, 400, W, H - 400))
        pygame.draw.rect(surf, (90, 90, 120), (0, 400, W, 4))
        self._draw_panel(surf, font_big, font)

    def _creature_card(self, surf, creature, pos, font_big, font, is_enemy):
        x, y = pos
        pygame.draw.rect(surf, (24, 24, 36), (x, y, 240, 84))
        pygame.draw.rect(surf, (90, 90, 120), (x, y, 240, 84), 2)
        name = font.render(f"{creature.name}  Lv{creature.level}",
                          True, (240, 240, 240))
        surf.blit(name, (x + 10, y + 6))
        self._hp_bar(surf, creature, (x + 10, y + 36), 220)
        hp_text = font.render(f"{creature.hp}/{creature.max_hp} HP",
                              True, (200, 200, 200))
        surf.blit(hp_text, (x + 10, y + 56))
        if is_enemy:
            tag = font.render("WILD", True, (255, 120, 120))
            surf.blit(tag, (x + 190, y + 56))

    @staticmethod
    def _hp_bar(surf, creature, pos, width):
        x, y = pos
        frac = creature.hp / creature.max_hp if creature.max_hp else 0
        color = (80, 200, 80) if frac > 0.5 else (
            (240, 200, 60) if frac > 0.25 else (220, 70, 70))
        pygame.draw.rect(surf, (60, 60, 70), (x, y, width, 12))
        pygame.draw.rect(surf, color, (x, y, int(width * frac), 12))

    def _draw_panel(self, surf, font_big, font):
        W, H = surf.get_size()
        if self.state == "msg":
            lines = _wrap(self.text, font_big, W - 60)
            for i, line in enumerate(lines[:3]):
                surf.blit(font_big.render(line, True, (240, 240, 240)),
                          (30, 420 + i * 40))
            hint = font.render("ENTER: continue", True, (150, 150, 170))
            surf.blit(hint, (W - 200, H - 40))
        elif self.state == "menu":
            orb_label = f"ORB x{self.game.orbs}"
            if self.game.inv["super_orbs"]:
                orb_label += f" (+{self.game.inv['super_orbs']} super)"
            labels = ["FIGHT", "SWITCH", orb_label, "RUN"]
            for i, label in enumerate(labels):
                cx, cy = 190 + (i % 2) * 380, 450 + (i // 2) * 60
                color = (255, 220, 90) if i == self.menu_cursor else (200, 200, 200)
                prefix = "> " if i == self.menu_cursor else "  "
                surf.blit(font_big.render(prefix + label, True, color), (cx, cy))
        elif self.state == "orb":
            # Phase 2: pick which orb to throw.
            options = [f"Orb x{self.game.orbs}",
                       f"Super Orb x{self.game.inv['super_orbs']}  (1.3x catch!)"]
            for i, label in enumerate(options):
                color = (255, 220, 90) if i == self.orb_cursor else (200, 200, 200)
                prefix = "> " if i == self.orb_cursor else "  "
                surf.blit(font_big.render(prefix + label, True, color),
                          (60, 440 + i * 55))
            surf.blit(font.render("ESC: back", True, (150, 150, 170)),
                      (W - 140, H - 40))
        elif self.state == "fight":
            for i, move in enumerate(self.active().moves):
                color = (255, 220, 90) if i == self.move_cursor else (200, 200, 200)
                prefix = "> " if i == self.move_cursor else "  "
                label = f"{move.name}  ({move.type}, {move.power})"
                surf.blit(font_big.render(prefix + label, True, color),
                          (60, 440 + i * 55))
            surf.blit(font.render("ESC: back", True, (150, 150, 170)),
                      (W - 140, H - 40))
        elif self.state == "switch":
            title = "Choose! (fainted can't fight)" if self.forced_switch \
                else "Switch to? (uses your turn)"
            surf.blit(font.render(title, True, (150, 200, 255)), (30, 412))
            for i, c in enumerate(self.game.party):
                color = (255, 220, 90) if i == self.switch_cursor else (200, 200, 200)
                if c.fainted:
                    color = (110, 110, 120)
                prefix = "> " if i == self.switch_cursor else "  "
                label = f"{c.name} Lv{c.level}  {c.hp}/{c.max_hp}"
                if i == self.active_idx:
                    label += "  [OUT]"
                surf.blit(font_big.render(prefix + label, True, color),
                          (60, 445 + i * 32))
        elif self.state == "over":
            surf.blit(font_big.render("ENTER: continue", True, (240, 240, 240)),
                      (280, 470))


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
