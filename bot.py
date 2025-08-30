import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
import asyncio
import threading

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.load_extension("steam_cog")  # cog betoltes

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
