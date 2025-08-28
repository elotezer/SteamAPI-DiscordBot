# Steam Discord Bot

A Steam API-t használva, valós idejű játékadatokat, árakat és leárazásokat jeleníthetsz meg a szervereden.

## Fő funkciók

- **Játék keresés**: `!game <név vagy AppID>`  
  Lekérheted a játék adatait, árát és leírását.

- **Figyelés (Watchlist)**: `!watch <név vagy AppID>`  
  Hozzáadhatsz játékokat a figyeléshez. A bot a játék nevét és AppID-jét tárolja.

- **Figyelés törlése**: `!unwatch <AppID>`  
  Eltávolítja a játékot a watchlistből.

- **Figyelt játékok listája**: `!watchlist`  
  Megjeleníti a figyelt játékokat `Név (AppID)` formátumban.

- **Automatikus leárazás figyelés**  
  A bot ellenőrzi a figyelt játékok árait, és értesítést küld, ha leárazás történik.

- **Stop parancs konzolon**  
  A botot a konzolból is leállíthatod a `stop` paranccsal.

## Telepítés

1. Clone:

```bash
git clone <repo_url>
cd SteamDiscordBot
```

2. Hozd létre a `.env` fájlt a következő tartalommal:

```env
DISCORD_TOKEN="ide_a_discord_tokened"
STEAM_API_KEY="ide_a_steam_api_kulcsod"
```

3. Telepítsd a requirement-eket:

```bash
pip install -r requirements.txt
```

4. Indítsd el a botot:

```bash
python bot.py
```

- A konzolban a `stop` parancs leállítja a botot.

## Hogyan működik

- `!game <játék>`: a játék leírását és nagy képét jeleníti meg
- `!watchlist`: a figyelt játékok listája
- Értesítés leárazáskor automatikusan

## Következő fejlesztések

- Több nyelv támogatása  
- Webhook alapú leárazás értesítés  
- Embed dizájn minden parancsnál

---

