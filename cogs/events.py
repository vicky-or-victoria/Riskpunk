# cogs/events.py
import discord
import random
import asyncio
from discord.ext import commands, tasks
from utils.database import (
    get_all_territories, log_event, update_player_credits, update_player_hp
)
from utils.game_data import RANDOM_EVENTS
from utils.styles import event_embed, NeonEmbed, NEON_RED
import os

GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
EVENT_CHANNEL_NAME = "city-events"  # The bot will try to post here


class EventsCog(commands.Cog, name="Events"):
    """Background random event system — fires every 30 minutes."""

    def __init__(self, bot):
        self.bot = bot
        self.event_loop.start()

    def cog_unload(self):
        self.event_loop.cancel()

    # ── Periodic event loop ──────────────────────────────────
    @tasks.loop(minutes=30)
    async def event_loop(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            # Try to fetch if not cached
            try:
                guild = await self.bot.fetch_guild(GUILD_ID)
            except Exception:
                return

        # Find or create the events channel
        channel = None
        for ch in guild.text_channels:
            if ch.name == EVENT_CHANNEL_NAME:
                channel = ch
                break
        if not channel:
            try:
                channel = await guild.create_text_channel(
                    EVENT_CHANNEL_NAME,
                    reason="NeonLedger event channel"
                )
            except Exception:
                return  # No permission

        # Pick a random event
        event = random.choice(RANDOM_EVENTS)
        await log_event(event["key"])

        # Post the embed
        embed = event_embed(event)
        await channel.send(embed=embed)

        # ── Apply mechanical effects ───────────────────────
        # Credit modifier to ALL players
        if event["credit_mod"] != 0:
            from utils.database import get_db
            async with await get_db() as db:
                # Fetch all players
                cur = await db.execute("SELECT discord_id FROM players")
                players = await cur.fetchall()
                for p in players:
                    await update_player_credits(p["discord_id"], event["credit_mod"])

        # Virus outbreak — damage HP
        if event["key"] == "virus_outbreak":
            from utils.database import get_db
            async with await get_db() as db:
                cur = await db.execute("SELECT discord_id, id FROM players")
                players = await cur.fetchall()
                for p in players:
                    # Check if they own a MedKit
                    cur2 = await db.execute(
                        "SELECT quantity FROM inventory WHERE player_id = ? AND item_name = 'MedKit'",
                        (p["id"],)
                    )
                    has_kit = await cur2.fetchone()
                    if not has_kit or has_kit["quantity"] <= 0:
                        await update_player_hp(p["discord_id"], -15)

        # Gang war — boost Void Street defense
        if event["key"] == "gang_war":
            from utils.database import get_db
            async with await get_db() as db:
                await db.execute(
                    "UPDATE territories SET defense = MIN(100, defense + 20) WHERE key = 'void_street'"
                )
                await db.commit()

    # ── Manual trigger (admin) ───────────────────────────────
    @discord.slash_command(name="trigger_event", description="[ADMIN] Manually trigger a random city event.")
    async def trigger_event(self, ctx: discord.ApplicationContext):
        # Simple admin check — only guild owner
        if ctx.guild and ctx.author.id != ctx.guild.owner_id:
            await ctx.respond(content="Admin only.", ephemeral=True)
            return
        event = random.choice(RANDOM_EVENTS)
        await log_event(event["key"])
        embed = event_embed(event)
        # Apply effects
        if event["credit_mod"] != 0:
            from utils.database import get_db
            async with await get_db() as db:
                cur = await db.execute("SELECT discord_id FROM players")
                players = await cur.fetchall()
                for p in players:
                    await update_player_credits(p["discord_id"], event["credit_mod"])
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(EventsCog(bot))
