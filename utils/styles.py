# utils/styles.py
import discord

# ── Cyberpunk Palette ────────────────────────────────────────────────────────
NEON_MAGENTA  = 0xFF00FF
NEON_CYAN     = 0x00FFFF
NEON_YELLOW   = 0xFFFF00
NEON_GREEN    = 0x39FF14
NEON_RED      = 0xFF073A
NEON_ORANGE   = 0xFF6B00
NEON_BLUE     = 0x4D4DFF
DARK_BG       = 0x0A0E1A   # deep navy used as base tint
FACTION_COLORS = {
    "omnicorp":   0x5B5EA6,
    "solarflare": 0xFF6B00,
    "netrunners": 0x00FFFF,
    "ironveil":   0xC0C0C0,
    "phantomcell": 0x9B59B6,
}

# ── Divider / border strings ─────────────────────────────────────────────────
LINE        = "━" * 40
THIN_LINE   = "─" * 40
DOUBLE_LINE = "═" * 40
GLOW_LINE   = "▬" * 38
DOTTED      = "┈" * 40

# ── Neon label wrappers ──────────────────────────────────────────────────────
def neon_title(text: str) -> str:
    return f"⚡ **{text}**"

def cyber_label(text: str) -> str:
    return f"▸ `{text}`"

def glitch(text: str) -> str:
    """Wrap text in a glitchy-feel code block."""
    return f"```ansi\n\033[2;31m{text}\033[0m```"

def mono(text: str) -> str:
    return f"```\n{text}```"

def inline_tag(tag: str) -> str:
    return f"`[{tag}]`"


# ── Core Embed Factory ───────────────────────────────────────────────────────
class RiskEmbed(discord.Embed):
    """Base embed with cyberpunk defaults."""
    def __init__(self, *, title="", description="", color=NEON_CYAN, **kwargs):
        super().__init__(
            title=f"⚡ {title}" if title else "",
            description=description,
            color=color,
            **kwargs
        )
        self.set_footer(text="━━━ RISKPUNK v1.0 ━━━  ┆  Risk City Underground", icon_url=None)


# ── Specialised Embed Builders ───────────────────────────────────────────────

def player_card(player, implants=None, faction_name: str = "None") -> RiskEmbed:
    """Full player status card."""
    hp_bar   = make_bar(player["hp"],     player["max_hp"],  12, "🟦", "⬜")
    xp_bar   = make_bar(player["xp"],     player["level"]*500, 12, "🟩", "⬛")

    embed = RiskEmbed(
        title=player["name"],
        description=f"{THIN_LINE}\n`Street identity registered in the city grid.`\n{THIN_LINE}",
        color=NEON_CYAN
    )
    embed.add_field(
        name="📊 Vitals",
        value=(
            f"❤️ HP  {hp_bar} `{player['hp']}/{player['max_hp']}`\n"
            f"✨ XP  {xp_bar} `{player['xp']}/{player['level']*500}`\n"
            f"📈 Level **{player['level']}**   ┆   ⭐ Rep `{player['rep']}`"
        ),
        inline=False
    )
    embed.add_field(
        name="💰 Economy",
        value=f"💵 Credits  `{player['credits']:,.2f} ₵`",
        inline=True
    )
    embed.add_field(
        name="🏢 Allegiance",
        value=f"`{faction_name}`",
        inline=True
    )
    embed.add_field(
        name="⚔️ Combat Stats",
        value=(
            f"🗡️ ATK `{player['atk']}`  ┆  "
            f"🛡️ DEF `{player['def']}`  ┆  "
            f"💨 SPD `{player['spd']}`"
        ),
        inline=False
    )
    if implants:
        implant_lines = "\n".join(
            f"  `{imp['slot'].upper()}` → {imp['implant_key']}"
            for imp in implants
        )
        embed.add_field(name="🔧 Active Implants", value=implant_lines or "— none —", inline=False)
    else:
        embed.add_field(name="🔧 Active Implants", value="— none installed —", inline=False)
    return embed


def faction_card(faction, members=None) -> RiskEmbed:
    col = FACTION_COLORS.get(faction["key"], NEON_MAGENTA)
    embed = RiskEmbed(title=faction["name"], color=col)
    embed.description = f"{LINE}\n{faction['description'] or 'No intel available.'}\n{LINE}"
    embed.add_field(name="🏢 Codename", value=f"`{faction['key'].upper()}`", inline=True)
    embed.add_field(name="⚡ Aggression", value=make_bar(faction["aggression"], 100, 10, "🟥", "⬜"), inline=True)
    if members:
        names = ", ".join(m["name"] for m in members[:15])
        embed.add_field(name=f"👥 Members ({len(members)})", value=names or "— empty —", inline=False)
    return embed


def territory_card(territory, faction_name: str = "Unclaimed") -> RiskEmbed:
    embed = RiskEmbed(title=f"🗺️ {territory['name']}", color=NEON_BLUE)
    embed.description = f"`{territory['description'] or 'No data.'}`"
    embed.add_field(name="🏢 Controller", value=f"`{faction_name}`", inline=True)
    embed.add_field(name="💰 Weekly Income", value=f"`{territory['income']:,.0f} ₵`", inline=True)
    embed.add_field(
        name="🛡️ Defense",
        value=make_bar(territory["defense"], 100, 12, "🟦", "⬜") + f"  `{territory['defense']}/100`",
        inline=False
    )
    return embed


def trade_board_embed(trades) -> RiskEmbed:
    embed = RiskEmbed(title="💱 Black Market Board", color=NEON_YELLOW)
    embed.description = f"`Open transactions on the neural net.`\n{THIN_LINE}"
    if not trades:
        embed.add_field(name="📭 No Listings", value="The board is dark. Check back later.", inline=False)
        return embed
    for t in trades[:12]:
        embed.add_field(
            name=f"#{t['id']}  {t['item_name']}",
            value=(
                f"Qty `{t['quantity']}`  ┆  Price `{t['price']:,.0f} ₵`\n"
                f"Listed by Player ID `{t['seller_id']}`"
            ),
            inline=True
        )
    return embed


def heist_card(heist) -> RiskEmbed:
    phase_colors = {"planning": NEON_BLUE, "active": NEON_ORANGE, "completed": NEON_GREEN, "failed": NEON_RED}
    embed = RiskEmbed(
        title=f"🚨 HEIST — {heist['target']}",
        color=phase_colors.get(heist["phase"], NEON_CYAN)
    )
    crew_ids = [x.strip() for x in heist["crew"].split(",") if x.strip()]
    embed.add_field(name="📌 Phase",      value=f"`{heist['phase'].upper()}`",        inline=True)
    embed.add_field(name="⚙️ Difficulty", value=make_bar(heist["difficulty"], 10, 10, "🟥", "⬜"), inline=True)
    embed.add_field(name="💰 Payout",     value=f"`{heist['reward']:,.0f} ₵`",        inline=True)
    embed.add_field(name="👥 Crew",       value=f"`{len(crew_ids)} members`",          inline=True)
    embed.add_field(name="📋 Status",     value=f"`{heist['status'].upper()}`",        inline=True)
    return embed


def event_embed(event: dict) -> RiskEmbed:
    """Render a random city event announcement."""
    embed = RiskEmbed(title=f"📢 CITY ALERT — {event['title']}", color=NEON_RED)
    embed.description = (
        f"{GLOW_LINE}\n"
        f"{event['description']}\n"
        f"{GLOW_LINE}"
    )
    if event.get("effect"):
        embed.add_field(name="⚡ Effect", value=f"`{event['effect']}`", inline=False)
    return embed


def pvp_result_embed(p1_name, p2_name, winner_name, rounds, log_text) -> RiskEmbed:
    embed = RiskEmbed(title="⚔️ PvP DUEL COMPLETE", color=NEON_GREEN if winner_name else NEON_RED)
    embed.description = (
        f"`{p1_name}` vs `{p2_name}`\n"
        f"{LINE}\n"
        f"🏆 Winner: **{winner_name or 'DRAW'}** after `{rounds}` rounds\n"
        f"{LINE}"
    )
    if log_text:
        embed.add_field(name="📜 Battle Log", value=f"```{log_text[:1500]}```", inline=False)
    return embed


def leaderboard_embed(players, sort_label: str = "Credits") -> RiskEmbed:
    embed = RiskEmbed(title="🏆 LEADERBOARD — Richest Runners", color=NEON_YELLOW)
    embed.description = f"`Top citizens ranked by {sort_label}`\n{LINE}"
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, p in enumerate(players):
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        if sort_label == "Credits":
            val = f"{p['credits']:,.0f} ₵"
        elif sort_label == "Level":
            val = f"Lvl {p['level']}"
        else:
            val = f"Rep {p['rep']}"
        lines.append(f"{medal}  **{p['name']}**  ┆  {val}")
    embed.add_field(name="", value="\n".join(lines), inline=False)
    return embed


def skill_tree_embed(player_name: str, skills: list) -> RiskEmbed:
    embed = RiskEmbed(title=f"🧬 Skill Tree — {player_name}", color=NEON_GREEN)
    embed.description = f"`Neural pathways mapped.`\n{THIN_LINE}"
    if not skills:
        embed.add_field(name="No skills unlocked", value="Visit `/skills learn` to begin.", inline=False)
    else:
        for s in skills:
            embed.add_field(
                name=f"  {s['skill_key'].replace('_', ' ').title()}",
                value=f"Level `{s['level']}` " + "█" * s["level"] + "░" * (5 - min(s["level"], 5)),
                inline=True
            )
    return embed


# ── Utility ──────────────────────────────────────────────────────────────────
def make_bar(current, maximum, length=10, filled="█", empty="░") -> str:
    ratio = max(0, min(1, current / maximum)) if maximum else 0
    n = int(ratio * length)
    return filled * n + empty * (length - n)
