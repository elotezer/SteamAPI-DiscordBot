import discord
from discord.ext import commands, tasks
from discord import app_commands
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

    @app_commands.command(name="game", description="Játék adatainak lekérése név vagy AppID alapján")
    @app_commands.describe(query="Add meg a játék nevét vagy AppID-ját")
    async def game_cmd(self, interaction: discord.Interaction, query: str):
        if not self.client:
            await interaction.response.send_message("A Steam kliens még nem készült el.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        if query.isdigit():
            appid = int(query)
        else:
            items = await self.client.search_app(query)
            if not items:
                await interaction.followup.send("Nincs találat erre a névre.")
                return
            appid = items[0].get("id")

        details = await self.client.get_app_details(int(appid))
        if not details:
            await interaction.followup.send("Nem sikerült lekérni az adatokat.")
            return

        name = details.get("name", "Ismeretlen")
        price_str = SteamStoreClient.format_price(details)
        release = details.get("release_date", {}).get("date", "Ismeretlen")
        publisher = ", ".join(details.get("publishers", [])) or "Ismeretlen"
        developer = ", ".join(details.get("developers", [])) or "Ismeretlen"
        categories = [c["description"] for c in details.get("categories", [])]
        multiplayer = "Igen" if any("Multiplayer" in c for c in categories) else "Nem"
        coop = "Igen" if any("Co-op" in c for c in categories) else "Nem"
        rating = details.get("metacritic", {}).get("score", "Ismeretlen")
        age = details.get("required_age", 0)
        age_str = f"{age}+" if age else "Nincs korhatár"

        embed = discord.Embed(
            title=name,
            url=f"https://store.steampowered.com/app/{appid}",
            description=details.get("short_description","")
        )
        header_image = details.get("header_image")
        if header_image:
            embed.set_image(url=header_image)
        embed.add_field(name="Ár", value=price_str, inline=True)
        embed.add_field(name="Megjelenés", value=release, inline=True)
        embed.add_field(name="Kiadó", value=publisher, inline=True)
        embed.add_field(name="Fejlesztő", value=developer, inline=True)
        embed.add_field(name="Multiplayer", value=multiplayer, inline=True)
        embed.add_field(name="Co-op", value=coop, inline=True)
        embed.add_field(name="Értékelés", value=str(rating), inline=True)
        embed.add_field(name="Korhatár", value=age_str, inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="watch", description="Játék figyelése név vagy AppID alapján")
    @app_commands.describe(query="Add meg a játék nevét vagy AppID-ját")
    async def watch_cmd(self, interaction: discord.Interaction, query: str):
        if not self.client:
            await interaction.response.send_message("A Steam kliens még nem készült el.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        if query.isdigit():
            appid = int(query)
            details = await self.client.get_app_details(appid)
            name = details.get("name", f"Ismeretlen ({appid})") if details else f"Ismeretlen ({appid})"
        else:
            items = await self.client.search_app(query)
            if not items:
                await interaction.followup.send(embed=discord.Embed(description="❌ Nincs találat erre a névre."))
                return
            appid = items[0]["id"]
            name = items[0]["name"]

        channel_id = str(interaction.channel.id)
        if channel_id not in self.state:
            self.state[channel_id] = []

        if any(game["appid"] == appid for game in self.state[channel_id]):
            await interaction.followup.send(embed=discord.Embed(description=f"❌ {name} már szerepel a figyelt listában."))
            return

        self.state[channel_id].append({"appid": appid, "name": name})
        _write_state(self.state)
        await interaction.followup.send(embed=discord.Embed(description=f"✅ {name} hozzáadva a figyeléshez."))

    @app_commands.command(name="unwatch", description="Eltávolít egy játékot a figyelésből")
    @app_commands.describe(appid="Add meg a játék AppID-ját")
    async def unwatch_cmd(self, interaction: discord.Interaction, appid: int):
        channel_id = str(interaction.channel.id)
        games = self.state.get(channel_id, [])
        for game in games:
            if game["appid"] == appid:
                games.remove(game)
                _write_state(self.state)
                await interaction.response.send_message(embed=discord.Embed(description=f"✅ {game['name']} eltávolítva a figyelt listából."))
                return
        await interaction.response.send_message(embed=discord.Embed(description=f"❌ A(z) {appid} nem szerepel a figyelt listában."))

    @app_commands.command(name="watchlist", description="Figyelt játékok listázása")
    async def watchlist_cmd(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)
        games = self.state.get(channel_id, [])
        if not games:
            await interaction.response.send_message("Nincs figyelt játék a csatornában.")
            return
        embed = discord.Embed(title="Watchlist", color=0x1b2838)
        for game in games:
            embed.add_field(name=f"{game['name']} ({game['appid']})", value=" ", inline=False)
        embed.set_footer(text="SteamAPI 5000")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="discount", description="Aktuális ár/leárazás megjelenítése")
    @app_commands.describe(query="Add meg a játék nevét vagy AppID-ját")
    async def discount_cmd(self, interaction: discord.Interaction, query: str):
        if not self.client:
            await interaction.response.send_message("A Steam kliens még nem készült el.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        if query.isdigit():
            appid = int(query)
        else:
            items = await self.client.search_app(query)
            if not items:
                await interaction.followup.send(embed=discord.Embed(description="❌ Nincs találat erre a névre."))
                return
            appid = items[0]["id"]

        details = await self.client.get_app_details(appid)
        if not details:
            await interaction.followup.send(embed=discord.Embed(description="❌ Nem sikerült lekérni az adatokat."))
            return

        price_str = SteamStoreClient.format_price(details)
        embed = discord.Embed(
            title=details.get("name", "Ismeretlen"),
            url=f"https://store.steampowered.com/app/{appid}",
            description="Ár ellenőrzés:"
        )
        header_image = details.get("header_image")
        if header_image:
            embed.set_image(url=header_image)
        embed.add_field(name="Jelenlegi ár", value=price_str, inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="randomgame", description="Véletlenszerű játék a Store-ból")
    async def randomgame_cmd(self, interaction: discord.Interaction):
        if not self.client:
            await interaction.response.send_message("A Steam kliens még nem készült el.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        import random
        items = await self.client.search_app("a")
        if not items:
            await interaction.followup.send(embed=discord.Embed(description="❌ Nem sikerült találni játékot."))
            return

        game = random.choice(items)
        details = await self.client.get_app_details(game["id"])
        if not details:
            await interaction.followup.send(embed=discord.Embed(description="❌ Nem sikerült lekérni az adatokat."))
            return

        price_str = SteamStoreClient.format_price(details)
        embed = discord.Embed(
            title=details.get("name","Ismeretlen"),
            url=f"https://store.steampowered.com/app/{game['id']}",
            description=details.get("short_description","")
        )
        header_image = details.get("header_image")
        if header_image:
            embed.set_image(url=header_image)
        embed.add_field(name="Ár", value=price_str, inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="status", description="Multiplayer/Co-op/Korhatár/Értékelés")
    @app_commands.describe(query="Add meg a játék nevét vagy AppID-ját")
    async def status_cmd(self, interaction: discord.Interaction, query: str):
        if not self.client:
            await interaction.response.send_message("A Steam kliens még nem készült el.")
            return
        await interaction.response.defer(thinking=True)

        if query.isdigit():
            appid = int(query)
        else:
            items = await self.client.search_app(query)
            if not items:
                await interaction.followup.send("Nincs találat erre a névre.")
                return
            appid = items[0]["id"]

        details = await self.client.get_app_details(appid)
        if not details:
            await interaction.followup.send("Nem sikerült lekérni az adatokat.")
            return

        categories = [c["description"] for c in details.get("categories", [])]
        multiplayer = "Igen" if any("Multiplayer" in c for c in categories) else "Nem"
        coop = "Igen" if any("Co-op" in c for c in categories) else "Nem"
        age = details.get("required_age", 0)
        age_str = f"{age}+" if age else "Nincs korhatár"
        rating = details.get("metacritic", {}).get("score")
        rating_str = str(rating) if rating else "Ismeretlen"

        embed = discord.Embed(
            title=details.get("name","Ismeretlen"),
            url=f"https://store.steampowered.com/app/{appid}",
            description=details.get("short_description","")
        )
        header_image = details.get("header_image")
        if header_image:
            embed.set_image(url=header_image)
        embed.add_field(name="Multiplayer", value=multiplayer, inline=True)
        embed.add_field(name="Co-op", value=coop, inline=True)
        embed.add_field(name="Korhatár", value=age_str, inline=True)
        embed.add_field(name="Értékelés", value=rating_str, inline=True)

        await interaction.followup.send(embed=embed)
    @app_commands.command(name="badge_tartas", description="Megtartja a fejlesztői badget")
    @app_commands.describe(query="/badge -> badge megtartva!")
    async def badge_tartas_cmd(self, interaction: discord.Interaction, query: str):
        await interaction.response.send_message("Badge meghosszabbítva még 1 hónapig :)")

    @app_commands.command(name="compare", description="Két játék összehasonlítása (vesszővel elválasztva)")
    @app_commands.describe(query="Pl.: Counter-Strike 2, Grand Theft Auto V")
    async def compare_cmd(self, interaction: discord.Interaction, query: str):
        if not self.client:
            await interaction.response.send_message("A Steam kliens még nem készült el.")
            return
        await interaction.response.defer(thinking=True)

        games = [q.strip() for q in query.split(",")]
        if len(games) != 2:
            await interaction.followup.send("Kérlek pontosan két játékot adj meg vesszővel elválasztva.")
            return

        results = []
        for game in games:
            if game.isdigit():
                appid = int(game)
            else:
                items = await self.client.search_app(game)
                if not items:
                    await interaction.followup.send(f"Nincs találat erre a névre: {game}")
                    return
                appid = items[0]["id"]
            details = await self.client.get_app_details(appid)
            if not details:
                await interaction.followup.send(f"Nem sikerült lekérni az adatokat: {game}")
                return
            results.append({"appid": appid, "name": details.get("name","Ismeretlen"), "details": details})

        def score(details):
            s = 0
            po = details.get("price_overview")
            price = po.get("final",0)/100 if po else 0
            s += max(0, 100 - price)
            release = details.get("release_date", {}).get("date", "1970-01-01")
            try:
                year = int(release.split("-")[0])
            except Exception:
                year = 0
            s += year
            rating = details.get("metacritic", {}).get("score") or 0
            s += rating
            return s

        score0 = score(results[0]["details"])
        score1 = score(results[1]["details"])

        winner = 0 if score0 >= score1 else 1
        loser = 1 - winner

        embed = discord.Embed(
            title="Játék összehasonlítás",
            description=f"{results[winner]['name']} ✅ vs {results[loser]['name']} ❌"
        )
        embed.add_field(
            name="Pontszámok (Ár + Megjelenés + Rating)",
            value=f"{results[0]['name']}: {score0}\n{results[1]['name']}: {score1}",
            inline=False
        )
        header_image = results[winner]['details'].get("header_image")
        if header_image:
            embed.set_image(url=header_image)

        await interaction.followup.send(embed=embed)

    @tasks.loop(minutes=10)
    async def discount_check(self):
        if not self.client:
            return
        for ch_id, apps in self.state.items():
            channel = self.bot.get_channel(int(ch_id))
            if not channel:
                continue
            for app in apps:
                appid = app["appid"] if isinstance(app, dict) else app
                details = await self.client.get_app_details(appid)
                if not details:
                    continue
                price_str = SteamStoreClient.format_price(details)
                await channel.send(f"Árfrissítés: {details.get('name','Ismeretlen')} — {price_str}")

    def cog_unload(self):
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())

async def setup(bot):
    cog = SteamCog(bot)
    await bot.add_cog(cog)
