"""STARBEASTS game state: screens, party, bestiary, saving.

Phase 2 adds a sandbox layer on top of the RPG: an inventory, farming
(till/plant/harvest), wood chopping, crafting, and building fences and
bridges. Press F to interact with the tile you face.
"""

import json
import os
import random

from battle import Battle
from creatures import BESTIARY_ORDER, SPECIES, Creature, roll_wild_species
from world import (
    BRIDGE, DIR_DELTAS, FENCE, GRASS, PATH, SOIL, STUMP, TALL, TENT, TREE,
    WATER, Player, World,
)

SAVE_FILE = "save.dat"
ENCOUNTER_CHANCE = 0.12  # per step taken inside tall grass

# Crafting recipes: name, cost (inventory items / "orbs"), and what you get.
# "orbs" is special: it means the game's orb count, not the inventory.
RECIPES = [
    {"name": "Carve Orb", "cost": {"wood": 3},
     "gives": {"orbs": 1}, "blurb": "3 wood -> 1 orb"},
    {"name": "Super Orb", "cost": {"crops": 2, "wood": 1},
     "gives": {"super_orbs": 1}, "blurb": "2 crops + 1 wood -> 1 super orb"},
    {"name": "Fence Kit", "cost": {"wood": 4},
     "gives": {"fence_kits": 1}, "blurb": "4 wood -> 1 fence kit"},
]

# Building options: name, cost, which tile it creates, and which tiles
# it may be placed on. (Crops block placement; the tent is never allowed.)
BUILD_OPTIONS = [
    {"name": "Fence", "cost": {"fence_kits": 1}, "tile": FENCE,
     "on": {GRASS, SOIL, PATH}, "blurb": "1 fence kit - blocks movement"},
    {"name": "Bridge", "cost": {"wood": 4}, "tile": BRIDGE,
     "on": {WATER}, "blurb": "4 wood - walk over water"},
]

# Fresh-inventory defaults (a new game starts with 5 seeds).
NEW_INVENTORY = {"wood": 0, "seeds": 5, "crops": 0,
                 "super_orbs": 0, "fence_kits": 0}


class Game:
    """Owns everything: the world, the party, and which screen is showing.

    States: TITLE, STARTER, OVERWORLD, BATTLE, BESTIARY, VICTORY,
    CRAFT, BUILD, BUILD_PLACE, INVENTORY, WORLDMAP.
    """

    def __init__(self):
        self.state = "TITLE"
        self.world = World()
        self.player = Player(11, 9)  # start on the path
        self.party = []
        self.orbs = 8
        # Phase 2: the player's bag. Orbs stay as self.orbs (older saves
        # and the battle code use that name); everything else lives here.
        self.inv = dict(NEW_INVENTORY)
        self.bestiary = set()
        self.battle = None
        self.starter_cursor = 0
        self.craft_cursor = 0
        self.build_cursor = 0
        self.build_choice = None  # index into BUILD_OPTIONS while placing
        self.toast = ""
        self.toast_timer = 0

    # ------------------------------------------------------------ starters
    def select_starter(self, species_key):
        self.party = [Creature(species_key, level=5)]
        self.bestiary.add(species_key)
        self.inv = dict(NEW_INVENTORY)  # fresh bag for a new journey
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
    def update_overworld(self, dirs, dt=0):
        """Move the player; grow crops; maybe trigger a wild encounter."""
        stepped = self.player.update(dirs, self.world)
        if dt > 0:
            # Crops grow in real time, even while you walk around.
            if self.world.update_crops(dt) > 0:
                self.set_toast("Your crops are ready to harvest!")
        if stepped == TALL and random.random() < ENCOUNTER_CHANCE:
            self.start_battle()

    def on_tent_tile(self):
        return (self.player.tx, self.player.ty) == self.world.tent_tile

    def rest_at_tent(self):
        for c in self.party:
            c.heal_full()
        self.orbs = 8
        self.world.regrow_stumps()  # chopped trees grow back overnight
        self.save()
        self.set_toast("Rested! Healed, orbs refilled, trees regrew, saved.")

    # --------------------------------------------- phase 2: interact (F)
    def faced_tile(self):
        """The grid tile directly in front of the player."""
        dx, dy = DIR_DELTAS[self.player.facing]
        return self.player.tx + dx, self.player.ty + dy

    def interact(self):
        """Use the tile you face: till, plant, harvest, chop, remove..."""
        tx, ty = self.faced_tile()
        if not self.world.in_bounds(tx, ty):
            return
        tile = self.world.tile_at(tx, ty)

        if tile == GRASS:
            # Till grass into plantable soil.
            self.world.set_tile(tx, ty, SOIL)
            self.set_toast("Tilled the soil! Press F again to plant.")
        elif tile == SOIL:
            crop = self.world.crops.get((tx, ty))
            if crop is None:
                if self.inv["seeds"] > 0:
                    self.inv["seeds"] -= 1
                    self.world.crops[(tx, ty)] = {
                        "stage": 0, "t": 0.0, "announced": False}
                    self.set_toast("Planted a seed! It grows in real time.")
                else:
                    self.set_toast("No seeds! Harvest crops to get more.")
            elif crop["stage"] >= 2:
                del self.world.crops[(tx, ty)]
                self.inv["crops"] += 2
                self.inv["seeds"] += 1
                self.set_toast("Harvested! +2 crops, +1 seed.")
            else:
                self.set_toast("Still growing... come back soon!")
        elif tile == TREE:
            self.world.set_tile(tx, ty, STUMP)
            self.inv["wood"] += 2
            self.set_toast("Chopped the tree! +2 wood.")
        elif tile == STUMP:
            self.set_toast("A stump. It regrows when you rest at the tent.")
        elif tile == FENCE:
            # Remove your own fence and get some wood back.
            self.world.set_tile(tx, ty, GRASS)
            self.inv["wood"] += 1
            self.set_toast("Removed the fence. +1 wood.")
        elif tile == TENT:
            self.rest_at_tent()
        else:
            self.set_toast("Nothing to do here.")

    # -------------------------------------------- phase 2: crafting (C)
    def can_afford(self, cost):
        for item, n in cost.items():
            have = self.orbs if item == "orbs" else self.inv.get(item, 0)
            if have < n:
                return False
        return True

    def _pay(self, cost):
        for item, n in cost.items():
            if item == "orbs":
                self.orbs -= n
            else:
                self.inv[item] -= n

    def _give(self, gives):
        for item, n in gives.items():
            if item == "orbs":
                self.orbs += n
            else:
                self.inv[item] = self.inv.get(item, 0) + n

    def craft(self, idx):
        """Craft one recipe (called from the CRAFT screen)."""
        recipe = RECIPES[idx]
        if self.can_afford(recipe["cost"]):
            self._pay(recipe["cost"])
            self._give(recipe["gives"])
            self.set_toast(f"Crafted: {recipe['name']}!")
        else:
            self.set_toast("Not enough materials!")

    # -------------------------------------------- phase 2: building (V)
    def place_build(self):
        """Place the chosen building on the faced tile (BUILD_PLACE mode)."""
        if self.build_choice is None:
            return
        opt = BUILD_OPTIONS[self.build_choice]
        tx, ty = self.faced_tile()
        if not self.world.in_bounds(tx, ty):
            self.set_toast("Can't build there.")
            return
        tile = self.world.tile_at(tx, ty)
        ok_spot = tile in opt["on"] and (tx, ty) not in self.world.crops
        if not ok_spot:
            self.set_toast("Can't build there.")
            return
        if not self.can_afford(opt["cost"]):
            self.set_toast("Not enough materials!")
            return
        self._pay(opt["cost"])
        self.world.set_tile(tx, ty, opt["tile"])
        self.set_toast(f"Built a {opt['name'].lower()}!")

    def build_spot_ok(self):
        """Is the faced tile a valid spot for the chosen building?
        Used for the green/red ghost preview."""
        if self.build_choice is None:
            return False
        opt = BUILD_OPTIONS[self.build_choice]
        tx, ty = self.faced_tile()
        return (self.world.in_bounds(tx, ty)
                and self.world.tile_at(tx, ty) in opt["on"]
                and (tx, ty) not in self.world.crops
                and self.can_afford(opt["cost"]))

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
            "inv": dict(self.inv),
            "bestiary": sorted(self.bestiary),
            "player": [self.player.tx, self.player.ty],
            # Only tiles the player changed (tilled/chopped/built)...
            "tiles": {f"{x},{y}": t
                      for (x, y), t in self.world.modified_tiles().items()},
            # ...and growing crops: "x,y" -> [stage, seconds_grown].
            "crops": {f"{x},{y}": [c["stage"], c["t"]]
                      for (x, y), c in self.world.crops.items()},
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
        # .get() with defaults keeps OLD saves (from before Phase 2) working.
        self.inv = dict(NEW_INVENTORY)
        self.inv.update(data.get("inv", {}))
        self.bestiary = set(data["bestiary"])
        for key, tile in data.get("tiles", {}).items():
            x, y = (int(n) for n in key.split(","))
            self.world.set_tile(x, y, tile)
        for key, (stage, t) in data.get("crops", {}).items():
            x, y = (int(n) for n in key.split(","))
            self.world.crops[(x, y)] = {
                "stage": stage, "t": t, "announced": stage >= 2}
        self.player.teleport(*data["player"])
        self.state = "OVERWORLD"
        return True
