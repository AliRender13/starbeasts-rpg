"""STARBEASTS creatures: species data, type chart, moves, XP and battle math."""

import math
import random

# ------------------------------------------------------------------ types
# Ember beats Leaf, Leaf beats Aqua, Aqua beats Ember.
TYPES = ("Ember", "Aqua", "Leaf")

# (attacking type, defending type) -> damage multiplier.
# Anything not listed here does normal (x1.0) damage.
_TYPE_BONUS = {
    ("Ember", "Leaf"): 1.5,
    ("Leaf", "Aqua"): 1.5,
    ("Aqua", "Ember"): 1.5,
    ("Leaf", "Ember"): 0.6,
    ("Aqua", "Leaf"): 0.6,
    ("Ember", "Aqua"): 0.6,
}


def type_mult(attack_type, defend_type):
    """Damage multiplier for a move type against a creature type."""
    if attack_type == defend_type:
        return 0.8  # same-type moves are a bit weak
    return _TYPE_BONUS.get((attack_type, defend_type), 1.0)


# ------------------------------------------------------------------- data
# species_key -> everything about the species.
# base stats are (hp, atk, def, spd). rarity drives encounter weights.
SPECIES = {
    # -- starters (picked at the start of the game) --
    "cindercub": {
        "name": "Cindercub", "type": "Ember", "rarity": "starter",
        "desc": "A fire lion cub with a blazing mane.",
        "base": (45, 12, 10, 11),
    },
    "bloopfin": {
        "name": "Bloopfin", "type": "Aqua", "rarity": "starter",
        "desc": "A round water blob that loves to bounce.",
        "base": (48, 10, 12, 9),
    },
    "sproutle": {
        "name": "Sproutle", "type": "Leaf", "rarity": "starter",
        "desc": "A cheerful sprout buddy, always growing.",
        "base": (46, 11, 11, 10),
    },
    # -- wild creatures --
    "emberspark": {
        "name": "Emberspark", "type": "Ember", "rarity": "common",
        "desc": "A tiny living flame. Warm and curious.",
        "base": (40, 11, 9, 12),
    },
    "aquaffle": {
        "name": "Aquaffle", "type": "Aqua", "rarity": "common",
        "desc": "A playful fish-blob that blows bubbles.",
        "base": (44, 10, 11, 9),
    },
    "leafling": {
        "name": "Leafling", "type": "Leaf", "rarity": "common",
        "desc": "A quick little leaf that dances in the wind.",
        "base": (38, 10, 9, 11),
    },
    "thornbloom": {
        "name": "Thornbloom", "type": "Leaf", "rarity": "uncommon",
        "desc": "A proud flower. Do not touch the thorns.",
        "base": (47, 12, 11, 10),
    },
    "novawisp": {
        "name": "Novawisp", "type": "Ember", "rarity": "rare",
        "desc": "A mysterious ghost-flame. Very hard to find.",
        "base": (42, 13, 9, 14),
    },
}

# Encounter weights by rarity (higher = appears more often).
RARITY_WEIGHT = {"common": 40, "uncommon": 20, "rare": 5}

# Fixed order for the bestiary screen.
BESTIARY_ORDER = [
    "cindercub", "bloopfin", "sproutle",
    "emberspark", "aquaffle", "leafling",
    "thornbloom", "novawisp",
]

# The type-flavored move each type gets (plus Tackle for everyone).
TYPE_MOVES = {
    "Ember": ("Flare Bite", 55),
    "Aqua": ("Bubble Slam", 55),
    "Leaf": ("Vine Whip", 55),
}


class Move:
    """One battle move: name, type ('Normal' or a creature type), power."""

    def __init__(self, name, move_type, power):
        self.name = name
        self.type = move_type
        self.power = power


# ---------------------------------------------------------------- creature
class Creature:
    """One creature instance: species + level + current HP/XP."""

    def __init__(self, species_key, level=3):
        info = SPECIES[species_key]
        self.species = species_key
        self.name = info["name"]
        self.type = info["type"]
        self.level = level
        base_hp, base_atk, base_def, base_spd = info["base"]
        # Stats grow a little with every level past level 1.
        self.max_hp = base_hp + 3 * (level - 1)
        self.atk = base_atk + 2 * (level - 1)
        self.defense = base_def + 2 * (level - 1)
        self.spd = base_spd + 2 * (level - 1)
        self.hp = self.max_hp
        self.xp = 0
        move_name, move_power = TYPE_MOVES[self.type]
        self.moves = [
            Move("Tackle", "Normal", 35),
            Move(move_name, self.type, move_power),
        ]

    # -- state -----------------------------------------------------------
    @property
    def fainted(self):
        return self.hp <= 0

    def xp_to_next(self):
        """XP needed to go from the current level to the next one."""
        return int(30 * self.level ** 1.4)

    # -- progression -----------------------------------------------------
    def gain_xp(self, amount):
        """Add XP. Returns how many levels were gained (0 if none)."""
        self.xp += amount
        gained = 0
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self._level_up()
            gained += 1
        return gained

    def _level_up(self):
        self.level += 1
        self.max_hp += 3
        self.atk += 2 + random.randint(-1, 1)
        self.defense += 2 + random.randint(-1, 1)
        self.spd += 2 + random.randint(-1, 1)
        # Leveling up also restores 25% of max HP.
        self.hp = min(self.max_hp, self.hp + self.max_hp // 4)

    def heal_full(self):
        self.hp = self.max_hp

    # -- save/load --------------------------------------------------------
    def to_dict(self):
        return {
            "species": self.species,
            "level": self.level,
            "xp": self.xp,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "atk": self.atk,
            "def": self.defense,
            "spd": self.spd,
        }

    @classmethod
    def from_dict(cls, data):
        c = cls(data["species"], data["level"])
        c.xp = data["xp"]
        c.max_hp = data["max_hp"]
        c.atk = data["atk"]
        c.defense = data["def"]
        c.spd = data["spd"]
        c.hp = data["hp"]
        return c


# ------------------------------------------------------------- battle math
def calc_damage(attacker, defender, move):
    """Damage formula. Always does at least 1 damage."""
    mult = type_mult(move.type, defender.type)
    raw = (
        move.power
        * attacker.atk
        / (defender.defense + 10)
        * mult
        * (1 + attacker.level * 0.05)
        * random.uniform(0.85, 1.0)
    )
    return max(1, int(raw))


def catch_chance(creature):
    """Chance to catch with an orb. Weaker creature = easier catch."""
    missing = 1 - creature.hp / creature.max_hp
    return min(0.95, max(0.05, 0.25 + 0.65 * missing))


def roll_wild_species():
    """Pick a random wild species, weighted by rarity."""
    wild = [k for k, v in SPECIES.items() if v["rarity"] != "starter"]
    weights = [RARITY_WEIGHT[SPECIES[k]["rarity"]] for k in wild]
    return random.choices(wild, weights=weights, k=1)[0]


def wild_level():
    """Wild creatures are level 2-5."""
    return random.randint(2, 5)
