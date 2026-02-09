# utils/game_data.py
# ─────────────────────────────────────────────────────────────────────────────
# All static / reference data for the game.  Nothing here touches the DB.
# ─────────────────────────────────────────────────────────────────────────────

# ── IMPLANTS ─────────────────────────────────────────────────────────────────
# Each implant: key, display name, slot, cost, and stat bonuses applied while
# installed (applied dynamically in combat / checks).
IMPLANTS = {
    # ── HEAD ─────────────────────────────────────────────────
    "neural_spike": {
        "name": "Neural Spike v3",
        "slot": "head",
        "cost": 12000,
        "description": "Overclocks synaptic throughput.  +5 SPD, +3 ATK.",
        "bonuses": {"spd": 5, "atk": 3},
    },
    "ghost_veil": {
        "name": "Ghost Veil",
        "slot": "head",
        "cost": 18000,
        "description": "Renders neural signature undetectable.  +8 SPD, +10 rep_bonus.",
        "bonuses": {"spd": 8},
    },
    "cortex_jammer": {
        "name": "Cortex Jammer",
        "slot": "head",
        "cost": 25000,
        "description": "Disrupts enemy cognitive loops.  +6 ATK, -2 DEF (overload risk).",
        "bonuses": {"atk": 6, "def": -2},
    },
    # ── EYES ─────────────────────────────────────────────────
    "chrome_optics": {
        "name": "Chrome Optics II",
        "slot": "eyes",
        "cost": 8000,
        "description": "Telescopic zoom + threat-overlay HUD.  +4 ATK.",
        "bonuses": {"atk": 4},
    },
    "predator_lens": {
        "name": "Predator Lens",
        "slot": "eyes",
        "cost": 15000,
        "description": "Marks targets for auto-aim.  +7 ATK.",
        "bonuses": {"atk": 7},
    },
    # ── ARM ──────────────────────────────────────────────────
    "blitz_arm": {
        "name": "Blitz Arm",
        "slot": "arm",
        "cost": 10000,
        "description": "Hydraulic-driven strike arm.  +6 ATK, +2 DEF.",
        "bonuses": {"atk": 6, "def": 2},
    },
    "titan_gauntlet": {
        "name": "Titan Gauntlet",
        "slot": "arm",
        "cost": 22000,
        "description": "Composite-alloy power fist.  +10 ATK.",
        "bonuses": {"atk": 10},
    },
    # ── TORSO ────────────────────────────────────────────────
    "sub_dermal_armour": {
        "name": "Sub-Dermal Armour",
        "slot": "torso",
        "cost": 14000,
        "description": "Mesh-woven ceramic plates.  +8 DEF.",
        "bonuses": {"def": 8},
    },
    "nano_regen": {
        "name": "Nano-Regen Suite",
        "slot": "torso",
        "cost": 30000,
        "description": "Swarms repair tissue in real time.  +15 max_hp.",
        "bonuses": {"max_hp": 15},
    },
    # ── LEGS ─────────────────────────────────────────────────
    "phantom_stride": {
        "name": "Phantom Stride",
        "slot": "legs",
        "cost": 9000,
        "description": "Silenced micro-actuators.  +6 SPD.",
        "bonuses": {"spd": 6},
    },
    "tank_legs": {
        "name": "Tank Legs",
        "slot": "legs",
        "cost": 16000,
        "description": "Braced shock-absorber legs.  +5 DEF, +3 HP.",
        "bonuses": {"def": 5, "max_hp": 3},
    },
}

IMPLANT_SLOTS = ["head", "eyes", "arm", "torso", "legs"]

# ── FACTIONS ─────────────────────────────────────────────────────────────────
# Seeded into the DB on first run.  id is positional (1-based).
FACTIONS_SEED = [
    {
        "key":         "omnicorp",
        "name":        "OmniCorp Industries",
        "description": "The megacorp that owns half the grid.  Cold.  Efficient.  Ruthless.",
        "color":       "#5B5EA6",
        "aggression":  60,
    },
    {
        "key":         "solarflare",
        "name":        "SolarFlare Syndicate",
        "description": "Arms dealers who ride the orbital supply chain.  Fire and profit.",
        "color":       "#FF6B00",
        "aggression":  75,
    },
    {
        "key":         "netrunners",
        "name":        "Netrunner Collective",
        "description": "Ghost hackers.  They own the data‑streams the city bleeds through.",
        "color":       "#00FFFF",
        "aggression":  45,
    },
    {
        "key":         "ironveil",
        "name":        "Iron Veil",
        "description": "Military‑grade mercenaries.  No flag.  No loyalty.  Just the contract.",
        "color":       "#C0C0C0",
        "aggression":  90,
    },
    {
        "key":         "phantomcell",
        "name":        "Phantom Cell",
        "description": "Underground resistance.  Small.  Quiet.  Deadly when cornered.",
        "color":       "#9B59B6",
        "aggression":  55,
    },
]

# ── TERRITORIES ──────────────────────────────────────────────────────────────
TERRITORIES_SEED = [
    {"key": "industrial_sector", "name": "Industrial Sector", "description": "Factory sprawl where the city's heavy machinery gets built. Constant smoke and grinding metal.", "income": 400, "defense": 50},
    {"key": "chrome_district",   "name": "Chrome District",   "description": "Heart of the commercial sprawl. Whoever controls the grid controls the cash flow.", "income": 500, "defense": 60},
    {"key": "downtown_core",     "name": "Downtown Core",     "description": "Corporate skyscrapers and neon billboards. The economic heart of Risk City.", "income": 700, "defense": 75},
    {"key": "port_authority",    "name": "Port Authority",    "description": "Shipping docks and smuggler's paradise. Everything flows through here eventually.", "income": 350, "defense": 55},
    {"key": "central_plaza",     "name": "Central Plaza",     "description": "The neutral ground where deals are made. Heavily monitored, rarely safe.", "income": 300, "defense": 40},
    {"key": "corp_towers",       "name": "Corp Towers",       "description": "Glass and steel monuments to corporate power. Heavily fortified.", "income": 900, "defense": 90},
    {"key": "undercity",         "name": "Undercity",         "description": "The forgotten underground. No cameras, no comms, no rules.", "income": 150, "defense": 30},
    {"key": "tech_quarter",      "name": "Tech Quarter",      "description": "Where the city's hackers and engineers congregate. Innovation and espionage.", "income": 600, "defense": 65},
    {"key": "skyline_heights",   "name": "Skyline Heights",   "description": "Luxury apartments in the clouds. The elite look down on everyone else.", "income": 800, "defense": 80},
]

# ── SKILL TREES ──────────────────────────────────────────────────────────────
# Three branches.  Each node has a parent (None = root), cost in credits,
# and the stat bonus unlocked at level 1 (cumulative on upgrade).
SKILL_TREE = {
    # ── COMBAT ───────────────────────────────────────────────
    "combat_basics": {
        "name":        "Combat Basics",
        "branch":      "combat",
        "parent":      None,
        "cost":        2000,
        "description": "Foundational streetfight training.",
        "bonus":       {"atk": 2},
    },
    "dual_strike": {
        "name":        "Dual Strike",
        "branch":      "combat",
        "parent":      "combat_basics",
        "cost":        5000,
        "description": "Two blows land before the opponent blinks.",
        "bonus":       {"atk": 4},
    },
    "killswitch": {
        "name":        "Killswitch",
        "branch":      "combat",
        "parent":      "dual_strike",
        "cost":        12000,
        "description": "A finishing move that ignores 30% DEF.",
        "bonus":       {"atk": 6},
    },
    # ── STEALTH ──────────────────────────────────────────────
    "shadow_step": {
        "name":        "Shadow Step",
        "branch":      "stealth",
        "parent":      None,
        "cost":        2000,
        "description": "Move without a trace.",
        "bonus":       {"spd": 3},
    },
    "ghost_protocol": {
        "name":        "Ghost Protocol",
        "branch":      "stealth",
        "parent":      "shadow_step",
        "cost":        6000,
        "description": "Evade detection systems.",
        "bonus":       {"spd": 5},
    },
    "phantom_strike": {
        "name":        "Phantom Strike",
        "branch":      "stealth",
        "parent":      "ghost_protocol",
        "cost":        14000,
        "description": "Strike from complete darkness.  +50% first-hit damage.",
        "bonus":       {"atk": 4, "spd": 3},
    },
    # ── TECH ─────────────────────────────────────────────────
    "hack_basics": {
        "name":        "Hack Basics",
        "branch":      "tech",
        "parent":      None,
        "cost":        2000,
        "description": "Crack simple encryption.",
        "bonus":       {},  # passive: heist success bonus
    },
    "deep_dive": {
        "name":        "Deep Dive",
        "branch":      "tech",
        "parent":      "hack_basics",
        "cost":        7000,
        "description": "Navigate hostile ICE without a scratch.",
        "bonus":       {},
    },
    "god_mode": {
        "name":        "God Mode",
        "branch":      "tech",
        "parent":      "deep_dive",
        "cost":        18000,
        "description": "You don't hack systems.  You ARE the system.",
        "bonus":       {"atk": 3, "spd": 3},
    },
}

SKILL_BRANCHES = ["combat", "stealth", "tech"]

# ── STORY NODES ──────────────────────────────────────────────────────────────
# Flat dict keyed by node ID.  Each node: text, chapter, choices [{label, next, reward}].
STORY_NODES = {
    # ───── CHAPTER 1 ─────────────────────────────────────────
    "start": {
        "chapter": 1,
        "title":   "Awakening",
        "text": (
            "You come to on a rain-slicked rooftop, a half-fried datashard still plugged "
            "into the port behind your ear.  The city hums below you — neon and smoke and ten million "
            "broken promises.  Your hand traces a scar you don't remember earning.\n\n"
            "A message flickers across your retinal HUD:\n"
            "  `> CONTACT: PHANTOM_7 — MEET ME AT THE SLAB, SUBLEVEL 9`"
        ),
        "choices": [
            {"label": "Head to The Slab",          "next": "slab_arrival",      "reward": {"xp": 50}},
            {"label": "Wipe the datashard first",  "next": "wipe_shard",        "reward": {"xp": 75, "credits": 200}},
        ],
    },
    "wipe_shard": {
        "chapter": 1,
        "title":   "Data Ghost",
        "text": (
            "You jack in.  The shard is corrupted — fragments of someone else's memories bleed through "
            "your cortex.  A woman's face.  A burning building.  Then silence.\n\n"
            "The shard wipes clean.  Something tells you that was never meant for you."
        ),
        "choices": [
            {"label": "Head to The Slab",  "next": "slab_arrival",  "reward": {"xp": 30}},
        ],
    },
    "slab_arrival": {
        "chapter": 1,
        "title":   "The Slab",
        "text": (
            "Sublevel 9 is a tomb of concrete and flickering strip‑lights.  A figure leans against "
            "a busted vending machine — Phantom_7.  They don't look at you.  They don't need to.\n\n"
            "`'You pulled the shard out of Kira's dead hand.  That makes you either very brave '`\n"
            "`'… or very stupid.  Either way — OmniCorp wants it back.'`"
        ),
        "choices": [
            {"label": "\"What's on the shard?\"",      "next": "shard_reveal",   "reward": {"xp": 40}},
            {"label": "\"I don't work for free.\"",    "next": "negotiate",      "reward": {"credits": 500, "xp": 30}},
        ],
    },
    "shard_reveal": {
        "chapter": 1,
        "title":   "The Truth Hurts",
        "text": (
            "Phantom_7 smirks.  `'Proof.  Proof that OmniCorp's orbital defence network has a backdoor — '`\n"
            "`'and they've been using it to skim tax revenue into a black fund for three years.'`\n\n"
            "The city could burn over this.  Or someone could get very, very rich."
        ),
        "choices": [
            {"label": "\"Let's burn OmniCorp.\"",       "next": "ch2_rebel",     "reward": {"xp": 100, "rep": 50}},
            {"label": "\"Who pays the most?\"",          "next": "ch2_broker",   "reward": {"xp": 80,  "credits": 1000}},
        ],
    },
    "negotiate": {
        "chapter": 1,
        "title":   "Brass Tacks",
        "text": (
            "Phantom_7 tilts their head.  A credit-chip slides across the floor to your feet.\n\n"
            "`'Five hundred up front.  Ten thousand if you see this through.'`\n"
            "You pocket the chip.  The clock starts now."
        ),
        "choices": [
            {"label": "\"Deal. Tell me everything.\"",   "next": "shard_reveal",  "reward": {"xp": 50}},
        ],
    },
    # ───── CHAPTER 2 ─────────────────────────────────────────
    "ch2_rebel": {
        "chapter": 2,
        "title":   "The Spark",
        "text": (
            "You broadcast the data on every open channel.  Within an hour the street erupts —  "
            "protests, riots, and three separate faction war‑rooms light up.\n\n"
            "Phantom_7 pings you:  `'Nice shot.  But OmniCorp has eyes everywhere.  "
            "We need the physical backdoor access point — it's inside Orbital Dock 7.'`"
        ),
        "choices": [
            {"label": "\"Infiltrate the Dock alone.\"",   "next": "ch2_solo",     "reward": {"xp": 120}},
            {"label": "\"Call in the crew.\"",             "next": "ch2_heist",    "reward": {"xp": 90, "credits": 500}},
        ],
    },
    "ch2_broker": {
        "chapter": 2,
        "title":   "Dirty Money",
        "text": (
            "You shop the data quietly.  SolarFlare bites first — double what Phantom offered.  "
            "But as the credits hit your account, a ping:  `'You just made very powerful enemies.'`\n\n"
            "SolarFlare wants one more favour.  Something inside Orbital Dock 7."
        ),
        "choices": [
            {"label": "\"Fine.  What's the job?\"",       "next": "ch2_heist",    "reward": {"xp": 80}},
            {"label": "\"I work alone.\"",                "next": "ch2_solo",     "reward": {"xp": 100, "credits": 800}},
        ],
    },
    "ch2_solo": {
        "chapter": 2,
        "title":   "Ghost Run",
        "text": (
            "Orbital Dock 7 at 03:00.  Skeleton crew.  You slip through a maintenance shaft, "
            "crack two ICE walls, and reach the access terminal.  Your fingers dance.  "
            "The backdoor is yours.\n\n"
            "`> CHAPTER 2 COMPLETE — FINAL CHOICE UNLOCKS IN CHAPTER 3`"
        ),
        "choices": [
            {"label": "Continue to Chapter 3",  "next": "ch3_finale",  "reward": {"xp": 200, "credits": 2000}},
        ],
    },
    "ch2_heist": {
        "chapter": 2,
        "title":   "The Job",
        "text": (
            "You hit up every contact in your book.  Three runners agree to run with you.  "
            "The plan is simple:  distraction at the main gate, you slip in through the cooling vents.\n\n"
            "Everything goes sideways at 02:47 — but you get the terminal.  Barely."
        ),
        "choices": [
            {"label": "Continue to Chapter 3",  "next": "ch3_finale",  "reward": {"xp": 250, "credits": 3000}},
        ],
    },
    # ───── CHAPTER 3 (FINALE) ────────────────────────────────
    "ch3_finale": {
        "chapter": 3,
        "title":   "Zero Hour",
        "text": (
            "The backdoor is open.  OmniCorp's orbital defence sits naked and waiting.  "
            "Every faction in the city is watching.\n\n"
            "This is the moment.  What do you do with that kind of power?"
        ),
        "choices": [
            {"label": "Destroy the network.",             "next": "ending_burn",    "reward": {"xp": 300, "rep": 200}},
            {"label": "Sell access to the highest bidder.","next": "ending_sell",  "reward": {"credits": 50000, "xp": 200}},
            {"label": "Keep it.  Use it yourself.",       "next": "ending_keep",   "reward": {"xp": 250, "rep": 100, "credits": 10000}},
        ],
    },
    # ── ENDINGS ──────────────────────────────────────────────
    "ending_burn": {
        "chapter": 3,
        "title":   "Ashes",
        "text": (
            "You burn it all.  The orbital net goes dark in a cascade of cascading failures.  "
            "OmniCorp's stock tanks.  The city breathes for the first time in a decade.\n\n"
            "Phantom_7 sends one last message:  `'You just changed everything.  "
            "Whether that's good — we'll find out.'`\n\n"
            "🏆 **ENDING: THE PHOENIX**"
        ),
        "choices": [],
    },
    "ending_sell": {
        "chapter": 3,
        "title":   "The Price of Power",
        "text": (
            "Six factions bid.  You play them against each other in a 72-hour auction.  "
            "The winner pays fifty thousand credits.  You vanish before the ink dries.\n\n"
            "The city doesn't change.  But you're richer than anyone who ever walked its streets.\n\n"
            "💰 **ENDING: THE KINGPIN**"
        ),
        "choices": [],
    },
    "ending_keep": {
        "chapter": 3,
        "title":   "The Throne",
        "text": (
            "You keep the backdoor.  Quietly.  No one bids.  No one knows.\n\n"
            "But you do.  And in this city, information is the only weapon that never runs out "
            "of ammunition.\n\n"
            "👑 **ENDING: THE SHADOW**"
        ),
        "choices": [],
    },
}

# ── RANDOM EVENTS ────────────────────────────────────────────────────────────
# Picked randomly every 30 min by the events cog.  effect is purely flavour;
# actual mechanical changes are applied in the cog after the embed posts.
RANDOM_EVENTS = [
    {
        "key":         "corp_raid",
        "title":       "CORPORATE RAID",
        "description": "OmniCorp strike teams flood the lower grid.  Street prices spike 40%.",
        "effect":      "All trade prices inflated ×1.4 for 1 hour.",
        "credit_mod":  0,
        "rep_mod":     -10,
    },
    {
        "key":         "blackout",
        "title":       "SECTOR BLACKOUT",
        "description": "A power surge kills the eastern grid.  Comms are down.  Nobody can see anything.",
        "effect":      "PvP accuracy reduced by 20% for 1 hour.",
        "credit_mod":  0,
        "rep_mod":     0,
    },
    {
        "key":         "data_leak",
        "title":       "MASSIVE DATA LEAK",
        "description": "Someone dumped fifty terabytes of corporate secrets onto every neural net.  "
                       "The netrunners are having a field day.",
        "effect":      "All players gain +200 ₵ as a finder's bonus.",
        "credit_mod":  200,
        "rep_mod":     0,
    },
    {
        "key":         "gang_war",
        "title":       "STREET GANG WAR",
        "description": "Two mid-tier gangs lock down Void Street.  Nobody gets in or out.",
        "effect":      "Void Street territory defense +20 for 2 hours.",
        "credit_mod":  0,
        "rep_mod":     0,
    },
    {
        "key":         "orbital_debris",
        "title":       "ORBITAL DEBRIS STRIKE",
        "description": "A chunk of decommissioned space station slams into the harbour.  "
                       "Salvagers are already circling.",
        "effect":      "Bonus salvage loot available via /heist for 2 hours.",
        "credit_mod":  0,
        "rep_mod":     5,
    },
    {
        "key":         "virus_outbreak",
        "title":       "BIO-VIRUS OUTBREAK",
        "description": "A rogue lab's creation escapes containment.  Street clinics are overwhelmed.",
        "effect":      "All players lose 15 HP unless they own a MedKit.",
        "credit_mod":  0,
        "rep_mod":     0,
    },
    {
        "key":         "arms_drop",
        "title":       "BLACK MARKET ARMS DROP",
        "description": "An unmarked container hit the docks with no manifest.  First come, first served.",
        "effect":      "One free weapon added to first 5 players who /claim.",
        "credit_mod":  0,
        "rep_mod":     0,
    },
    {
        "key":         "glitch_storm",
        "title":       "NEURAL GLITCH STORM",
        "description": "A rogue AI is pinging every neural implant in the metro.  Implant wearers feel… odd.",
        "effect":      "Implant bonuses randomly doubled or zeroed for 1 hour.",
        "credit_mod":  0,
        "rep_mod":     0,
    },
    {
        "key":         "tax_crackdown",
        "title":       "TAX CRACKDOWN",
        "description": "The city AI's fiscal subroutine wakes up.  Everyone owes back taxes.  Now.",
        "effect":      "All players lose 500 ₵.",
        "credit_mod":  -500,
        "rep_mod":     0,
    },
    {
        "key":         "festival",
        "title":       "NEON FESTIVAL",
        "description": "Once a year the city actually smiles.  Street vendors hand out freebies.",
        "effect":      "All players gain +100 ₵ and +30 XP.",
        "credit_mod":  100,
        "rep_mod":     0,
    },
]

# ── HEIST TARGETS ────────────────────────────────────────────────────────────
HEIST_TARGETS = [
    {"name": "OmniCorp Vault 9",          "reward": 25000, "difficulty": 8, "min_crew": 3},
    {"name": "SolarFlare Arms Cache",     "reward": 18000, "difficulty": 6, "min_crew": 2},
    {"name": "Orbital Dock 7 Cargo Hold", "reward": 30000, "difficulty": 9, "min_crew": 4},
    {"name": "Chrome Bazaar Vault",       "reward": 12000, "difficulty": 4, "min_crew": 2},
    {"name": "The Slab Casino",           "reward": 15000, "difficulty": 5, "min_crew": 2},
    {"name": "Ghost Quarter Safehouse",   "reward": 8000,  "difficulty": 3, "min_crew": 1},
    {"name": "Power Core Nexus",          "reward": 40000, "difficulty": 10,"min_crew": 5},
    {"name": "Black Harbour Smuggler HQ", "reward": 20000, "difficulty": 7, "min_crew": 3},
]

# ── TRADEABLE ITEMS ──────────────────────────────────────────────────────────
ITEM_CATALOG = {
    "Assault Rifle":     {"base_price": 3000,  "atk_bonus": 5},
    "Sniper Rifle":      {"base_price": 5000,  "atk_bonus": 8},
    "Combat Knife":      {"base_price": 800,   "atk_bonus": 3},
    "MedKit":            {"base_price": 1500,  "heal": 40},
    "EMP Grenade":       {"base_price": 2000,  "special": "nullify_implants"},
    "Hacking Rig":       {"base_price": 4000,  "special": "heist_hack_bonus"},
    "Stealth Suit":      {"base_price": 3500,  "spd_bonus": 4},
    "Armour Vest":       {"base_price": 2500,  "def_bonus": 5},
    "Data Shard":        {"base_price": 1000,  "special": "story_hint"},
    "Chrome Dye Pack":     {"base_price": 200,   "special": "cosmetic"},
}