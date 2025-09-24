# Steam Discord Bot

A Steam API-t használva valós idejű játékadatokat, árakat és leárazásokat jeleníthetsz meg a szervereden.

## Fő funkciók

- **Játék keresés**: `!game <név vagy AppID>`  
  Lekérheted a játék adatait, árát, leírását, megjelenését, kiadóját és korhatárt.

- **Watchlist**: `!watch <név vagy AppID>`  
  Hozzáadhatsz játékokat a figyeléshez. A bot a játék nevét és AppID-jét tárolja, értesít leárazásról.

- **Figyelés törlése**: `!unwatch <AppID>`  
  Eltávolítja a játékot a watchlistből.

- **Watchlist listázása**: `!watchlist`  
  Megjeleníti a figyelt játékokat `Név (AppID)` formátumban.

- **Játék státusz**: `!status <név vagy AppID>`  
  Megjeleníti a játék rövid leírását, multiplayer és co-op információt, valamint korhatárt és képet.

- **Összehasonlítás**: `!compare <játék1>, <játék2>`  
  Összehasonlítja két játék árát, megjelenését és ratingjét, a nyertes játék képe megjelenik az embedben.

- **Automatikus leárazás figyelés**  
  A bot ellenőrzi a watchlist-eden lévő játékok árait, és értesítést küld, ha leárazás történik.

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

3. Telepítsd a szükséges package-eket:

```bash
pip install -r requirements.txt
```

4. Indítsd el a botot:

```bash
python bot.py
```

- A konzolban a `stop` parancs leállítja a botot.

## Hogyan működik

- `!game <játék>`: a játék leírását és képét jeleníti meg
- `!watchlist`: a figyelt játékok listája
- Értesítés leárazáskor automatikusan

## Következő fejlesztések

- Több nyelv támogatása  
- Webhook alapú leárazás értesítés  
- Embed dizájn minden parancsnál

---

