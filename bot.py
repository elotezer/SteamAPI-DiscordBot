import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
import asyncio
import threading

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
GUILD_ID = os.getenv("GUILD_ID")  # opcionális: gyors, azonnali guild-sync

intents = discord.Intents.default()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.guild_id = int(GUILD_ID) if GUILD_ID and GUILD_ID.isdigit() else None

    async def setup_hook(self):
        await self.load_extension("steam_cog")
        if self.guild_id:
            guild_obj = discord.Object(id=self.guild_id)
            await self.tree.sync(guild=guild_obj)
            print(f"Slash parancsok szinkronizálva a guildre: {self.guild_id}")
        else:
            cmds = await self.tree.sync()
            print(f"Slash parancsok globálisan szinkronizálva: {len(cmds)} db")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bejelentkezve: {bot.user}")
    print("Bot online állapotban van!")

def console_listener(bot):
    while True:
        cmd = input()
        if cmd.lower() == "stop":
            print("Bot leállítása...")
            asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)
            break

threading.Thread(target=console_listener, args=(bot,), daemon=True).start()

bot.run(DISCORD_TOKEN)
