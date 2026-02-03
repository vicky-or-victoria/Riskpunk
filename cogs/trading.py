# cogs/trading.py
import discord
from discord.ext import commands
from utils.database import (
    get_player, create_trade, get_open_trades, fulfill_trade, cancel_trade,
    add_item, remove_item, get_inventory, update_player_credits
)
from utils.game_data import ITEM_CATALOG
from utils.styles import trade_board_embed, NeonEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, THIN_LINE


class TradingCog(commands.Cog, name="Trading"):
    """Peer-to-peer Black Market trading board."""

    def __init__(self, bot):
        self.bot = bot

    trade_grp = discord.SlashCommandGroup("trade", "Black Market trading.")

    # ── /trade board ─────────────────────────────────────────
    @trade_grp.command(name="board", description="View all open trade listings.")
    async def trade_board(self, ctx: discord.ApplicationContext):
        trades = await get_open_trades()
        await ctx.respond(embed=trade_board_embed(trades))

    # ── /trade sell ──────────────────────────────────────────
    @trade_grp.command(name="sell", description="List an item for sale on the Black Market.")
    @discord.option("item_name", description="Item to sell")
    @discord.option("quantity",  description="How many",  type=int, min_value=1)
    @discord.option("price",     description="Total price in credits", type=float, min_value=1)
    async def trade_sell(self, ctx: discord.ApplicationContext, item_name: str, quantity: int, price: float):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        # Check inventory
        inv = await get_inventory(player["id"])
        owned = None
        for i in inv:
            if i["item_name"].lower() == item_name.lower():
                owned = i
                break
        if not owned or owned["quantity"] < quantity:
            await ctx.respond(
                embed=NeonEmbed(title="❌ Insufficient Stock", description=f"You don't have {quantity}x `{item_name}`.", color=NEON_RED),
                ephemeral=True
            )
            return
        # Deduct from inventory immediately (escrow)
        await remove_item(player["id"], owned["item_name"], quantity)
        listing = await create_trade(player["id"], owned["item_name"], quantity, price)
        embed = NeonEmbed(title="📦 Listing Created", color=NEON_GREEN)
        embed.description = (
            f"**{owned['item_name']}** × {quantity}\n"
            f"{THIN_LINE}\n"
            f"💰 Asking price: `{price:,.0f} ₵`\n"
            f"📋 Listing ID: `#{listing['id']}`\n"
            f"`Cancel anytime with /trade cancel {listing['id']}`"
        )
        await ctx.respond(embed=embed)

    # ── /trade buy ───────────────────────────────────────────
    @trade_grp.command(name="buy", description="Purchase an item from the Black Market.")
    @discord.option("listing_id", description="Listing ID from /trade board", type=int)
    async def trade_buy(self, ctx: discord.ApplicationContext, listing_id: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        # Fetch the listing
        from utils.database import get_db
        async with await get_db() as db:
            cur = await db.execute("SELECT * FROM trades WHERE id = ? AND status = 'open'", (listing_id,))
            listing = await cur.fetchone()
        if not listing:
            await ctx.respond(embed=NeonEmbed(title="❌ Listing Not Found", description="That listing doesn't exist or is already closed.", color=NEON_RED), ephemeral=True)
            return
        if listing["seller_id"] == player["id"]:
            await ctx.respond(content="You can't buy your own listing.", ephemeral=True)
            return
        if player["credits"] < listing["price"]:
            await ctx.respond(embed=NeonEmbed(title="💸 Can't Afford", description=f"Price: `{listing['price']:,.0f} ₵`  ┆  You have: `{player['credits']:,.0f} ₵`", color=NEON_RED), ephemeral=True)
            return
        # Transaction
        await update_player_credits(ctx.author.id, -listing["price"])         # buyer pays
        await update_player_credits(                                           # seller paid
            (await _discord_id_from_player_id(listing["seller_id"])),
            listing["price"]
        )
        await add_item(player["id"], listing["item_name"], listing["quantity"])  # buyer receives item
        await fulfill_trade(listing_id, player["id"])
        embed = NeonEmbed(title="✅ Purchase Complete", color=NEON_GREEN)
        embed.description = (
            f"Acquired **{listing['item_name']}** × {listing['quantity']}\n"
            f"{THIN_LINE}\n"
            f"💵 Paid `{listing['price']:,.0f} ₵`"
        )
        await ctx.respond(embed=embed)

    # ── /trade cancel ────────────────────────────────────────
    @trade_grp.command(name="cancel", description="Cancel your own listing (item returned).")
    @discord.option("listing_id", description="Listing ID", type=int)
    async def trade_cancel(self, ctx: discord.ApplicationContext, listing_id: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        from utils.database import get_db
        async with await get_db() as db:
            cur = await db.execute("SELECT * FROM trades WHERE id = ? AND status = 'open'", (listing_id,))
            listing = await cur.fetchone()
        if not listing or listing["seller_id"] != player["id"]:
            await ctx.respond(embed=NeonEmbed(title="❌ Not Your Listing", color=NEON_RED), ephemeral=True)
            return
        await cancel_trade(listing_id)
        await add_item(player["id"], listing["item_name"], listing["quantity"])  # return escrowed items
        embed = NeonEmbed(title="🗑️ Listing Cancelled", description=f"`{listing['item_name']}` × {listing['quantity']} returned to your inventory.", color=NEON_CYAN)
        await ctx.respond(embed=embed)

    # ── /inventory ───────────────────────────────────────────
    @discord.slash_command(description="View your item inventory.")
    async def inventory(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        inv = await get_inventory(player["id"])
        embed = NeonEmbed(title="🎒 Inventory", color=NEON_CYAN)
        if not inv:
            embed.description = "`Empty.  Nothing to show.`"
        else:
            lines = [f"  `{i['item_name']}` × {i['quantity']}" for i in inv]
            embed.description = "\n".join(lines)
        embed.add_field(
            name="📖 Catalog",
            value="Available items: " + ", ".join(f"`{k}`" for k in ITEM_CATALOG),
            inline=False
        )
        await ctx.respond(embed=embed)

    # ── /shop ────────────────────────────────────────────────
    @discord.slash_command(description="Buy items from the city shop.")
    async def shop(self, ctx: discord.ApplicationContext):
        embed = NeonEmbed(title="🏪 City Shop", color=NEON_GREEN)
        embed.description = "`Standard procurement.  No questions.`\n"
        for name, data in ITEM_CATALOG.items():
            embed.add_field(
                name=name,
                value=f"💰 `{data['base_price']:,} ₵`\n" +
                      (f"⚔️ ATK +{data.get('atk_bonus',0)}" if data.get("atk_bonus") else "") +
                      (f"🛡️ DEF +{data.get('def_bonus',0)}" if data.get("def_bonus") else "") +
                      (f"💨 SPD +{data.get('spd_bonus',0)}" if data.get("spd_bonus") else "") +
                      (f"❤️ Heals {data.get('heal',0)} HP" if data.get("heal") else "") +
                      (f"✨ {data.get('special','')}" if data.get("special") else ""),
                inline=True
            )
        embed.add_field(name="💡 Usage", value="Use `/shopbuy <item_name>` to purchase.", inline=False)
        await ctx.respond(embed=embed)

    @discord.slash_command(name="shopbuy", description="Buy an item from the city shop.")
    @discord.option("item_name", description="Item name from /shop")
    @discord.option("quantity", description="Quantity", type=int, min_value=1, default=1)
    async def shop_buy(self, ctx: discord.ApplicationContext, item_name: str, quantity: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        # Find item (case-insensitive)
        found_name = None
        for name in ITEM_CATALOG:
            if name.lower() == item_name.lower():
                found_name = name
                break
        if not found_name:
            await ctx.respond(embed=NeonEmbed(title="❌ Item Not Found", color=NEON_RED), ephemeral=True)
            return
        item = ITEM_CATALOG[found_name]
        total_cost = item["base_price"] * quantity
        if player["credits"] < total_cost:
            await ctx.respond(embed=NeonEmbed(title="💸 Can't Afford", description=f"Total: `{total_cost:,} ₵`", color=NEON_RED), ephemeral=True)
            return
        await update_player_credits(ctx.author.id, -total_cost)
        await add_item(player["id"], found_name, quantity)
        embed = NeonEmbed(title="✅ Purchased", color=NEON_GREEN)
        embed.description = f"**{found_name}** × {quantity}  ┆  `{total_cost:,} ₵` deducted."
        await ctx.respond(embed=embed)


# ── Helper ───────────────────────────────────────────────────────────────────
async def _discord_id_from_player_id(player_id: int) -> int:
    from utils.database import get_player_by_id
    p = await get_player_by_id(player_id)
    return p["discord_id"] if p else 0


def setup(bot):
    bot.add_cog(TradingCog(bot))
