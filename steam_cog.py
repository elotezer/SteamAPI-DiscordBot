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
            return "Ingyenes vagy nincs ár elérhető."
        initial = po.get("initial", 0) / 100
        final = po.get("final", 0) / 100
        discount = po.get("discount_percent", 0)
        currency = po.get("currency", "HUF")
        if discount and final < initial:
            return f"{final:.2f} {currency} (−{discount}% | korábban {initial:.2f} {currency})"
        return f"{final:.2f} {currency}"