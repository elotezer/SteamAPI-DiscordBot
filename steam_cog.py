import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json
import asyncio

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
            return "Ingyenes vagy nem elérhető az ár."
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

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
            self.client = SteamStoreClient(self.session, cc="hu", lang="hungarian")
        print(f"{self.bot.user} online állapotban!")

    @commands.command(name="game")
    async def game_cmd(self, ctx, *, query: str):
        if not self.client:
            await ctx.reply("A Steam kliens még nem készült el. Próbáld újra pár másodperc múlva.")
            return

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

        embed = discord.Embed(
            title=name,
            url=f"https://store.steampowered.com/app/{appid}",
            description=details.get("short_description","")
        )

        # thumbnail kep nagyobb
        header_image = details.get("header_image")
        if header_image:
            embed.set_image(url=header_image)

        embed.add_field(name="Ár", value=price_str, inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="watch")
    async def watch_cmd(self, ctx, query: str):
        if not self.client:
            await ctx.reply("A Steam kliens még nem készült el.", ephemeral=True)
            return

        if query.isdigit():
            appid = int(query)
            details = await self.client.get_app_details(appid)
            name = details.get("name", f"Ismeretlen ({appid})") if details else f"Ismeretlen ({appid})"
        else:
            items = await self.client.search_app(query)
            if not items:
                embed = discord.Embed(description="❌ Nincs találat erre a névre.")
                await ctx.reply(embed=embed)
                return
            appid = items[0]["id"]
            name = items[0]["name"]

        channel_id = str(ctx.channel.id)
        if channel_id not in self.state:
            self.state[channel_id] = []

        if any(game["appid"] == appid for game in self.state[channel_id]):
            embed = discord.Embed(description=f"❌ {name} már szerepel a figyelt listában.")
            await ctx.reply(embed=embed)
            return

        self.state[channel_id].append({"appid": appid, "name": name})
        _write_state(self.state)
        embed = discord.Embed(description=f"✅ {name} hozzáadva a figyeléshez.")
        await ctx.reply(embed=embed)

    @commands.command(name="unwatch")
    async def unwatch_cmd(self, ctx, appid: int):
        channel_id = str(ctx.channel.id)
        games = self.state.get(channel_id, [])
        for game in games:
            if game["appid"] == appid:
                games.remove(game)
                _write_state(self.state)
                embed = discord.Embed(description=f"✅ {game['name']} eltávolítva a figyelt listából.")
                await ctx.reply(embed=embed)
                return
        embed = discord.Embed(description=f"❌ A(z) {appid} nem szerepel a figyelt listában.")
        await ctx.reply(embed=embed)

    @commands.command(name="watchlist")  
    async def watchlist_cmd(self, ctx):  
        channel_id = str(ctx.channel.id)  
        games = self.state.get(channel_id, [])  
        if not games:  
            await ctx.reply("Nincs figyelt játék a csatornában.")  
            return  
        embed = discord.Embed(title="Watchlist", color=0x1b2838)  
        for game in games:  
            embed.add_field(name=f"{game['name']} ({game['appid']})", value=" ", inline=False)  
        embed.set_footer(text="SteamAPI 5000")  
        await ctx.reply(embed=embed)

    @tasks.loop(minutes=10)
    async def discount_check(self):
        if not self.client:
            return
        for ch_id, apps in self.state.items():
            channel = self.bot.get_channel(int(ch_id))
            if not channel:
                continue
            for appid in apps:
                details = await self.client.get_app_details(appid)
                if not details:
                    continue
                price_str = SteamStoreClient.format_price(details)
                await channel.send(f"Árfrissítés: {details.get('name','Ismeretlen')} — {price_str}")

    def cog_unload(self):
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())

async def setup(bot):
    await bot.add_cog(SteamCog(bot))