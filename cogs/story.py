# cogs/story.py
import discord
from discord.ext import commands
from utils.database import (
    get_player, get_story_progress, set_story_progress,
    update_player_credits, update_player_xp
)
from utils.game_data import STORY_NODES
from utils.styles import NeonEmbed, NEON_CYAN, NEON_MAGENTA, NEON_GREEN, LINE, THIN_LINE


class StoryChoiceView(discord.ui.View):
    """Buttons for each narrative choice in a story node."""

    def __init__(self, player_id: int, choices: list, timeout=300):
        super().__init__(timeout=timeout)
        self.player_id = player_id
        self.choices = choices
        for i, choice in enumerate(choices):
            btn = discord.ui.Button(
                label=choice["label"][:80],
                style=discord.ButtonStyle.blurple if i == 0 else discord.ButtonStyle.secondary,
                custom_id=f"story_choice_{i}"
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, index):
        async def callback(self_view, interaction: discord.Interaction):
            # Only the player who started the story can choose
            if interaction.user.id != self_view.player_id:
                await interaction.response.send_message("This isn't your story, runner.", ephemeral=True)
                return
            choice = self_view.choices[index]
            next_node_key = choice["next"]
            next_node = STORY_NODES.get(next_node_key)
            if not next_node:
                await interaction.response.send_message("Story node missing — contact an admin.", ephemeral=True)
                return
            # Apply reward
            reward = choice.get("reward", {})
            if reward.get("credits"):
                await update_player_credits(interaction.user.id, reward["credits"])
            if reward.get("xp"):
                await update_player_xp(interaction.user.id, reward["xp"])
            # Save progress
            await set_story_progress(self_view.player_id, next_node["chapter"], next_node_key, choice["label"])
            # Build next embed
            embed = _story_node_embed(next_node, next_node_key)
            # Disable old buttons
            for item in self_view.children:
                item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self_view)
            # If next node has choices, send a new message with the new view
            if next_node["choices"]:
                from utils.database import get_player
                player = await get_player(interaction.user.id)
                new_view = StoryChoiceView(player["id"], next_node["choices"])
                await interaction.followup.send(embed=embed, view=new_view)
            else:
                # Ending — show a final "story complete" embed
                end_embed = NeonEmbed(title="📖 Story Complete", color=NEON_GREEN)
                end_embed.description = (
                    f"`You've reached an ending.`\n"
                    f"{THIN_LINE}\n"
                    f"Use `/story play` to restart or explore alternate paths."
                )
                await interaction.followup.send(embed=end_embed)

        # Bind self_view
        async def bound_callback(interaction):
            await callback(self, interaction)

        return bound_callback


def _story_node_embed(node: dict, node_key: str) -> NeonEmbed:
    """Build a styled embed for a story node."""
    chapter_colors = {1: NEON_CYAN, 2: NEON_MAGENTA, 3: 0xFF6B00}
    color = chapter_colors.get(node["chapter"], NEON_CYAN)
    embed = NeonEmbed(title=f"📖 Chapter {node['chapter']} — {node['title']}", color=color)
    embed.description = (
        f"{LINE}\n"
        f"{node['text']}\n"
        f"{LINE}"
    )
    if node["choices"]:
        embed.add_field(
            name="🔀 Choose Your Path",
            value="Select an option below…",
            inline=False
        )
    return embed


class StoryCog(commands.Cog, name="Story"):
    """Branching narrative story missions."""

    def __init__(self, bot):
        self.bot = bot

    story_grp = discord.SlashCommandGroup("story", "Story missions.")

    # ── /story status ────────────────────────────────────────
    @story_grp.command(name="status", description="Check your current story progress.")
    async def story_status(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        progress = await get_story_progress(player["id"])
        if not progress:
            embed = NeonEmbed(title="📖 Story Not Started", color=NEON_CYAN)
            embed.description = "Use `/story play` to begin your journey through Risk City."
            await ctx.respond(embed=embed)
            return
        node = STORY_NODES.get(progress["node"], {})
        embed = NeonEmbed(title="📖 Story Status", color=NEON_CYAN)
        embed.description = (
            f"Chapter **{progress['chapter']}**\n"
            f"Current Node: `{progress['node']}`\n"
            f"Title: **{node.get('title', '—')}**\n"
            f"{THIN_LINE}\n"
            f"Choices made: `{progress['choices'] or 'none'}`"
        )
        if not node.get("choices"):
            embed.add_field(name="📌 Status", value="You've reached an **ending**.  Run `/story play` to restart.", inline=False)
        else:
            embed.add_field(name="📌 Status", value="Run `/story play` to continue from this node.", inline=False)
        await ctx.respond(embed=embed)

    # ── /story play ──────────────────────────────────────────
    @story_grp.command(name="play", description="Continue (or start) your story.")
    async def story_play(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        progress = await get_story_progress(player["id"])
        # Determine which node to show
        if progress and STORY_NODES.get(progress["node"], {}).get("choices"):
            node_key = progress["node"]
        else:
            # Start fresh
            node_key = "start"
            await set_story_progress(player["id"], 1, "start")

        node = STORY_NODES[node_key]
        embed = _story_node_embed(node, node_key)

        if node["choices"]:
            view = StoryChoiceView(player["id"], node["choices"])
            await ctx.respond(embed=embed, view=view)
        else:
            # Ending node — no choices
            embed.add_field(name="📖 The End", value="Use `/story play` to restart.", inline=False)
            await ctx.respond(embed=embed)

    # ── /story restart ───────────────────────────────────────
    @story_grp.command(name="restart", description="Restart your story from the beginning.")
    async def story_restart(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        await set_story_progress(player["id"], 1, "start", "RESTART")
        embed = NeonEmbed(title="🔄 Story Restarted", color=NEON_CYAN)
        embed.description = "Your narrative has been rewound.  Use `/story play` to begin again."
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(StoryCog(bot))
