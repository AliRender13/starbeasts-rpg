"""STARBEASTS game state: screens, party, bestiary, saving."""

import json
import os
import random

from battle import Battle
from creatures import BESTIARY_ORDER, SPECIES, Creature, roll_wild_species
from world import TALL, Player, World

SAVE_FILE = "save.dat"
ENCOUNTER_CHANCE = 0.12  # per step taken inside tall grass


class Game:
    """Owns everything: the world, the party, and which screen is showing.

    States: TITLE, STARTER, OVERWORLD, BATTLE, BESTIARY, VICTORY.
    """

    def __init__(self):
        self.state = "TITLE"
        self.world = World()
        self.player = Player(11, 9)  # start on the path
        self.party = []
        self.orbs = 8
        self.bestiary = set()
        self.battle = None
        self.starter_cursor = 0
        self.toast = ""
        self.toast_timer = 0

    # ------------------------------------------------------------ starters
    def select_starter(self, species_key):
        self.party = [Creature(species_key, level=5)]
        self.bestiary.add(species_key)
        self.state = "OVERWORLD"
        name = self.party[0].name
        self.set_toast(f"{name} joined your team! Find the tall grass...")

    # -------------------------------------------------------------- battle
    def first_healthy_index(self):
        for i, c in enumerate(self.party):
            if not c.fainted:
                return i
        return 0

    def start_battle(self, wild_key=None):
        """Begin a wild encounter (used by tall grass and by tests)."""
        self.battle = Battle(self, wild_key or roll_wild_species())
        self.state = "BATTLE"

    def on_battle_end(self, result):
        # The battle screen stays up ("press ENTER") until after_battle().
        self.battle_result = result

    def after_battle(self):
        if getattr(self, "battle_result", None) == "victory":
            self.state = "VICTORY"
        else:
            self.state = "OVERWORLD"
        self.battle = None

    def register_catch(self, species_key, level):
        self.bestiary.add(species_key)
        if len(self.party) < 4:
            self.party.append(Creature(species_key, level))
            self.set_toast(f"{SPECIES[species_key]['name']} joined your party!")
        else:
            self.set_toast(f"{SPECIES[species_key]['name']} was recorded "
                           f"(party full)!")

    def check_victory(self):
        return len(self.bestiary) >= len(BESTIARY_ORDER)

    def blackout(self):
        for c in self.party:
            c.heal_full()
        self.orbs = 8
        self.player.teleport(*self.world.tent_tile)
        self.state = "OVERWORLD"
        self.set_toast("You blacked out! The tent healer patched you up.")

    # ----------------------------------------------------------- overworld
    def update_overworld(self, dirs):
        """Move the player; maybe trigger a wild encounter."""
        stepped = self.player.update(dirs, self.world)
        if stepped == TALL and random.random() < ENCOUNTER_CHANCE:
            self.start_battle()

    def on_tent_tile(self):
        return (self.player.tx, self.player.ty) == self.world.tent_tile

    def rest_at_tent(self):
        for c in self.party:
            c.heal_full()
        self.orbs = 8
        self.save()
        self.set_toast("Rested! Party healed, orbs refilled, game saved.")

    # --------------------------------------------------------------- toast
    def set_toast(self, text, seconds=3.0):
        self.toast = text
        self.toast_timer = seconds

    def tick_toast(self, dt):
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast = ""

    # ------------------------------------------------------------ save/load
    def save(self, path=SAVE_FILE):
        data = {
            "party": [c.to_dict() for c in self.party],
            "orbs": self.orbs,
            "bestiary": sorted(self.bestiary),
            "player": [self.player.tx, self.player.ty],
            "state": "OVERWORLD" if self.state != "TITLE" else "TITLE",
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path=SAVE_FILE):
        if not os.path.exists(path):
            return False
        with open(path) as f:
            data = json.load(f)
        self.party = [Creature.from_dict(d) for d in data["party"]]
        self.orbs = data["orbs"]
        self.bestiary = set(data["bestiary"])
        self.player.teleport(*data["player"])
        self.state = "OVERWORLD"
        return True
