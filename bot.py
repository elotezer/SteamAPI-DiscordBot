import discord
from dotenv import load_dotenv
import os
import asyncio
from discord.ext import commands

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


async def main():
    async with bot:
        await bot.load_extension("steam_cog")
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

    
