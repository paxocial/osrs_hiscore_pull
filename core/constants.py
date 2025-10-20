"""Shared constants and enumerations for OSRS hiscore integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Gamemode:
    key: str
    path: str
    label: str


GAME_MODES: dict[str, Gamemode] = {
    "main": Gamemode("main", "hiscore_oldschool", "Regular"),
    "ironman": Gamemode("ironman", "hiscore_ironman", "Ironman"),
    "hardcore": Gamemode("hardcore", "hiscore_hardcore_ironman", "Hardcore Ironman"),
    "ultimate": Gamemode("ultimate", "hiscore_ultimate", "Ultimate Ironman"),
    "deadman": Gamemode("deadman", "hiscore_deadman", "Deadman Mode"),
    "tournament": Gamemode("tournament", "hiscore_tournament", "Tournament"),
    "seasonal": Gamemode("seasonal", "hiscore_seasonal", "Leagues"),
}

DEFAULT_MODE = "main"


SKILLS: tuple[str, ...] = (
    "overall",
    "attack",
    "defence",
    "strength",
    "hitpoints",
    "ranged",
    "prayer",
    "magic",
    "cooking",
    "woodcutting",
    "fletching",
    "fishing",
    "firemaking",
    "crafting",
    "smithing",
    "mining",
    "herblore",
    "agility",
    "thieving",
    "slayer",
    "farming",
    "runecraft",
    "hunter",
    "construction",
)


CLUE_ACTIVITIES: dict[str, str] = {
    "allClues": "Clue Scrolls (all)",
    "beginnerClues": "Clue Scrolls (beginner)",
    "easyClues": "Clue Scrolls (easy)",
    "mediumClues": "Clue Scrolls (medium)",
    "hardClues": "Clue Scrolls (hard)",
    "eliteClues": "Clue Scrolls (elite)",
    "masterClues": "Clue Scrolls (master)",
}

MINIGAME_ACTIVITIES: dict[str, str] = {
    "rogueBH": "Bounty Hunter (Legacy - Rogue)",
    "hunterBH": "Bounty Hunter (Legacy - Hunter)",
    "rogueBHV2": "Bounty Hunter (Rogue)",
    "hunterBHV2": "Bounty Hunter (Hunter)",
    "lastManStanding": "LMS - Rank",
    "pvpArena": "PvP Arena - Rank",
    "soulWarsZeal": "Soul Wars Zeal",
    "riftsClosed": "Rifts Closed",
    "colosseumGlory": "Colosseum Glory",
    "collectionsLogged": "Collections Logged",
}

POINT_ACTIVITIES: dict[str, str] = {
    "leaguePoints": "League Points",
    "deadmanPoints": "Deadman Points",
}

BOSS_ACTIVITIES: dict[str, str] = {
    "abyssalSire": "Abyssal Sire",
    "alchemicalHydra": "Alchemical Hydra",
    "amoxliatl": "Amoxliatl",
    "araxxor": "Araxxor",
    "artio": "Artio",
    "barrows": "Barrows Chests",
    "bryophyta": "Bryophyta",
    "callisto": "Callisto",
    "calvarion": "Calvar'ion",
    "cerberus": "Cerberus",
    "chambersOfXeric": "Chambers of Xeric",
    "chambersOfXericChallengeMode": "Chambers of Xeric: Challenge Mode",
    "chaosElemental": "Chaos Elemental",
    "chaosFanatic": "Chaos Fanatic",
    "commanderZilyana": "Commander Zilyana",
    "corporealBeast": "Corporeal Beast",
    "crazyArchaeologist": "Crazy Archaeologist",
    "dagannothPrime": "Dagannoth Prime",
    "dagannothRex": "Dagannoth Rex",
    "dagannothSupreme": "Dagannoth Supreme",
    "derangedArchaeologist": "Deranged Archaeologist",
    "doomOfMokhaiotl": "Doom of Mokhaiotl",
    "dukeSucellus": "Duke Sucellus",
    "generalGraardor": "General Graardor",
    "giantMole": "Giant Mole",
    "grotesqueGuardians": "Grotesque Guardians",
    "hespori": "Hespori",
    "kalphiteQueen": "Kalphite Queen",
    "kingBlackDragon": "King Black Dragon",
    "kraken": "Kraken",
    "kreeArra": "Kree'arra",
    "krilTsutsaroth": "K'ril Tsutsaroth",
    "lunarChests": "Lunar Chests",
    "mimic": "Mimic",
    "nex": "Nex",
    "nightmare": "The Nightmare",
    "phosanisNightmare": "Phosani's Nightmare",
    "obor": "Obor",
    "phantomMuspah": "Phantom Muspah",
    "sarachnis": "Sarachnis",
    "scorpia": "Scorpia",
    "scurrius": "Scurrius",
    "skotizo": "Skotizo",
    "solHeredit": "Sol Heredit",
    "spindel": "Spindel",
    "tempoross": "Tempoross",
    "gauntlet": "The Gauntlet",
    "corruptedGauntlet": "The Corrupted Gauntlet",
    "hueycoatl": "The Hueycoatl",
    "leviathan": "The Leviathan",
    "royalTitans": "The Royal Titans",
    "whisperer": "The Whisperer",
    "theatreOfBlood": "Theatre of Blood",
    "theatreOfBloodHardMode": "Theatre of Blood: Hard Mode",
    "thermonuclearSmokeDevil": "Thermonuclear Smoke Devil",
    "tombsOfAmascut": "Tombs of Amascut",
    "tombsOfAmascutExpertMode": "Tombs of Amascut: Expert Mode",
    "tzKalZuk": "TzKal-Zuk",
    "tzTokJad": "TzTok-Jad",
    "vardorvis": "Vardorvis",
    "venenatis": "Venenatis",
    "vetion": "Vet'ion",
    "vorkath": "Vorkath",
    "wintertodt": "Wintertodt",
    "yama": "Yama",
    "zalcano": "Zalcano",
    "zulrah": "Zulrah",
}


ACTIVITY_LOOKUP: dict[str, str] = {
    **CLUE_ACTIVITIES,
    **MINIGAME_ACTIVITIES,
    **POINT_ACTIVITIES,
    **BOSS_ACTIVITIES,
}

FORMATTED_BOSS_NAMES = BOSS_ACTIVITIES
FORMATTED_CLUE_NAMES = CLUE_ACTIVITIES
FORMATTED_MINIGAME_NAMES = MINIGAME_ACTIVITIES
FORMATTED_POINT_NAMES = POINT_ACTIVITIES

# Placeholder for activity table indexes (HTML leaderboard pages rely on numeric IDs).
ACTIVITY_TABLE_INDEX: dict[str, int] = {}


ACTIVITY_LOOKUP: dict[str, str] = {}
