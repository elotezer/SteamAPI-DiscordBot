import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
import json
from datetime import datetime

DATA_PATH = os.path.join("data", "watchlist.json")
os.makedirs("data", exist_ok=True)

def _read_state():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_state(state):
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)

class SteamStoreClient:
    BASE = "https://store.steampowered.com"

    def __init__(self, session, cc="hu", lang="hungarian"):
        self.session = session
        self.cc = cc
        self.lang = lang

    async def search_app(self, term):
        url = f"{self.BASE}/api/storesearch/"
        params = {"term": term, "cc": self.cc}
        async with self.session.get(url, params=params) as r:
            data = await r.json()
            return data.get("items", [])

    async def get_app_details(self, appid):
        url = f"{self.BASE}/api/appdetails"
        params = {"appids": str(appid), "cc": self.cc, "l": self.lang}
        async with self.session.get(url, params=params) as r:
            data = await r.json()
            block = data.get(str(appid))
            if not block or not block.get("success"):
                return None
            return block.get("data")

    @staticmethod
    def format_price(details):
        po = details.get("price_overview")
        if not po:
            return "Ingyenes vagy elérhető ár."
        initial = po.get("initial", 0) / 100
        final = po.get("final", 0) / 100
        discount = po.get("discount_percent", 0)
        currency = po.get("currency", "HUF")
        if discount and final < initial:
            return f"{final:.2f} {currency} (−{discount}% | korábban {initial:.2f} {currency})"
        return f"{final:.2f} {currency}"
    
class SteamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.client = None
        self.state = _read_state()
        self.check_discounts.start()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
            self.client = SteamStoreClient(self.session, cc="hu", lang="hungarian")

    @commands.command(name="game")
    async def game_cmd(self, ctx, *, query: str):
        appid = None
        if query.isdigit():
            appid = int(query)
        else:
            items = await self.client.search_app(query)
            if not items:
                await ctx.reply("Nincs találat.")
                return
            appid = items[0].get("id")
        details = await self.client.get_app_details(int(appid))
        if not details:
            await ctx.reply("Nem sikerült lekérni az adatokat.")
            return
        name = details.get("name", "Ismeretlen")
        price_str = SteamStoreClient.format_price(details)
        embed = discord.Embed(title=name, url=f"https://store.steampowered.com/app/{appid}", description=details.get("short_description",""))
        embed.add_field(name="Ár", value=price_str, inline=True)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(SteamCog(bot))