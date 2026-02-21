# F76 Price Guide — Wiki (Complete Guide)

This Wiki page mirrors the in-app **Help & Reference** tab and adds developer build/packaging notes.

---

## 🚀 First-Time Setup

Do this once before using the app:

1. Open the **Settings** tab.
2. Set **Fallout 76 Game Root** to the folder that contains `Fallout76.exe`.

   Common location:
   `C:\Program Files (x86)\Steam\steamapps\common\Fallout76`

   The app reads `LegendaryMods.ini` and `ItemsMod.ini` from the `Data\` subfolder automatically.
3. Set **Fallout76Custom.ini** to your personal INI file (only needed for the mod installer).

   Common location:
   `C:\Users\<You>\Documents\My Games\Fallout 76\Fallout76Custom.ini`
4. Check the **Data Folder** path under **Data Paths**.

   This defaults to the `Data\` folder next to the exe — where `ServerData.7z`, `price_cache.json`, and `inventOmaticStashConfig.json` live.
5. Set **ServerData.7z Path** to your price-data archive inside the Data folder.

   Loose `.json` and `.txt` trade files in the same folder are also loaded automatically.
6. Fill in your **Trade Post Profile** in Settings: IGN, junk prices, crafting prices, and PNG colours.
7. Click **💾 Save Settings**.
8. Switch to the **Dashboard** tab and click **⟳ Load All Data**.

Tips:
- The app auto-detects common Steam install paths on startup — confirm the Game Root field was filled correctly.
- After installing/updating **Invent-O-Matic Stash**, launch Fallout 76 once and load a character before clicking **Load All Data** so the mod can write fresh INI files.

---

## 🏠 Dashboard

The Dashboard is your home base.

### Stats Bar
Four counters update after every data load:

- **MODS** — total unique *(mod name + star tier)* entries found in `LegendaryMods.ini`
- **PRICES** — how many price entries are loaded into memory
- **COLLECTION** — how many *(mod, star-tier)* combinations you currently own
- **VALUE** — estimated total trade value of your collection in **Leaders**, based on cached median prices

### Load Buttons

- **⟳ Load All Data**  
  Full load — reads mods from `LegendaryMods.ini`, loads prices *(from cache if present, otherwise parses your archive)*, and scans your inventory. Use on first launch or after updating the archive.
- **Load Collection Only**  
  Re-reads only your in-game inventory without touching price data. Fast — use after playing when your stash has changed.
- **Parse Price Data Only**  
  Forces a complete re-parse of `ServerData.7z` *(and any loose files)* and rebuilds the price cache from scratch. Use when you have new trade data.

Tip:
- On startup the app automatically loads any existing `price_cache.json` so prices are ready immediately — the status bar shows **“Cache auto-loaded”** when this happens.

### Mod Installer Status
The bottom of the Dashboard shows whether **Invent-O-Matic Stash** and **SFE** are installed. Green ✓ means all files are present. If either shows ✗, go to **Settings → Nexus Mod Manager**.

---

## 💰 Price Guide Tab

A searchable table of every legendary mod with community-sourced trade prices.

### Table Columns

- **★** — star rating (1 through 4)
- **Mod Name** — canonical mod name exactly as it appears in `LegendaryMods.ini`
- **Price** — median trade price in **Leaders**. A tilde (`~`) means the price is estimated.
- **Range** — Low–High price band *(Q1 to Q3 — the middle 50% of real trades)*
- **n** — number of unique trade posts used (`est` = no real data)

### Price Markers

- `25L` → real price from trade posts
- `~9L` → estimated price (no data; uses star-tier average)
- `est` → shown in the **n** column for estimated entries

### Search & Filter
Type any part of a mod name in the Search box to filter in real time (case-insensitive, matches anywhere).

### Export TXT
Saves a formatted plain-text price guide to a file of your choice (you’ll be prompted for location).

---

## 🎨 The Colour System — White / Green / Orange

Every mod in your WTS list and generated PNG is colour-coded:

- **White** — you own the mod card but have **NOT** learned the recipe.  
  You are selling the physical card — once sold it is gone.
- **Green** — you have **LEARNED** the recipe.  
  You can craft this mod on demand. You provide Legendary Modules; the buyer brings the rest of the materials.
- **Orange** — you can craft the mod, but its materials cannot be traded  
  (e.g. Overeater's, Glutton, Polished, Propelling). A special in-game arrangement is needed.

⚠️ These hex codes and legend labels are fully customizable in **Settings → PNG Colours & Legend**.

---

## 📦 Trade Post — WTS (Want To Sell)

Build and manage your sell list, generate a PNG for posting, and copy plain text for chat.

### The WTS List (Left Panel)

- **+ Add** — opens Add Item dialog (price auto-filled from median cache)
- **✎ Edit** — edit selected item (double-click a row to edit)
- **✕ Del** — remove selected item (no confirmation)
- **⟳ Sync Collection** — reads `ItemsMod.ini` and auto-populates the WTS list with everything you own, quantities, and cached prices. Colour reflects craft status.

Sorting:
- star tier first (1★ → 4★), then alphabetically

### Add / Edit Item Dialog

- **Mod** — searchable dropdown of every valid mod/star combo
- **Qty / Mode** — `each` (price per piece) vs `all` (one price for the entire quantity)
- **Price (L)** — Leaders; auto-filled from cache (you can override)
- **WTT** — “want to trade” mod (optional)

Tip:
- Set Qty to **0** to mark “sold out” while keeping it visible on the PNG.

### Bottom Action Bar

- **💾 Save PNG** — saves the WTS image as PNG (prompts for location, default `Exports\`)
- **📋 Copy Text** — copies a plain-text WTS post to clipboard
- **↑ Export** — saves your WTS list as JSON backup
- **↓ Import** — loads a JSON list (replace or append)
- **Show Junk Mods** — toggles the “Buying Junk Mods” line (synced between WTS and WTB)

---

## 🛒 Trade Post — WTB (Want To Buy)

Build a Looking For list, generate a matching PNG, and copy a ready-to-post message.  
WTB is **free-form** (not limited to known mod names).

### The WTB List (Left Panel)

- **+ Add** — opens Add WTB dialog
- **✎ Edit** — edit selected item (or double-click)
- **✕ Del** — remove selected item
- **✕ Clear All** — remove all items (confirmation required)

### Add / Edit WTB Item Dialog

- **Looking For** — choose from dropdown **or** type free text
- **Qty / Mode** — how many you want; `each` vs `all`
- **Price (L)** — Leaders you pay; `0` = open offer (no price shown)
- **Notes** — optional detail shown in brackets
- **WTT Mod** — mod you offer in exchange
- **WTT Qty / Mode** — how many you offer + `ea`/`all`

### Bottom Action Bar

- **💾 Save PNG** — saves WTB image
- **📋 Copy Text** — copies formatted WTB post with “Looking For:” header
- **↑ Export / ↓ Import** — JSON backup/restore
- **Show Junk Mods** — synced with WTS

---

## ⚙️ Settings Tab

All configuration lives here. **💾 Save Settings** appears at both top and bottom.

### Game Paths

- **Fallout 76 Game Root** — folder containing `Fallout76.exe`  
  (INI files are read from `<GameRoot>\Data\`)
- **Fallout76Custom.ini** — only needed for the mod installer

Tip: the app scans common Steam install locations on startup and pre-fills when possible.

### Data Paths

- **Data Folder** — contains `ServerData.7z`, `inventOmaticStashConfig.json`, `price_cache.json`, `raw_cache.json`
- **ServerData.7z Path** — your price-data archive
- **Downloads Folder** — used by the mod installer to detect completed browser downloads

Tip: you can create your own `ServerData.7z` containing any mix of `.json` and `.txt` trade files.

### Trade Post Profile

Controls the look of your PNGs and text:

- IGN (In-Game Name)
- Junk mod buy prices per star tier
- Crafting service prices per star tier

### PNG Colours & Legend

Three colour rows (White / Green / Orange):

- Hex colour (`#RRGGBB`)
- Bold label
- Description text

“Other PNG Colours” lets you change:

- Background, Mod Card, IGN, Stars, Title Text, Notice Text, Buying Junk label, etc.

⚠️ Colour codes must be exactly `#RRGGBB` (7 chars). Invalid values revert to defaults on save.

### Reset to Defaults
Restores every profile field — IGN, prices, colours, labels, descriptions — to built-in defaults and refreshes all lists/previews.

### Nexus Mod Manager

Download and install managed mods directly from NexusMods.com.

- **Nexus API Key** — generate at NexusMods → Account → API Access  
  Stored only in `settings.json` on your PC.
- **Download & Install** — downloads latest Main file, extracts, copies `.dll`/`.ba2`, and updates `Fallout76Custom.ini`
- **Uninstall** — removes files + strips INI entry (confirmation required)

Managed mods:

- **Invent-O-Matic Stash (Unofficial)** — required; exports INI files used by this app
- **Script Functions Extender (SFE)** — required by Invent-O-Matic; installs as `dxgi.dll` in game root

⚠️ Free Nexus accounts may require “Slow Download” in browser. The installer watches your Downloads folder and installs automatically once the file finishes downloading.

### Cache Management
**🗑 Clear Caches** deletes `price_cache.json` and `raw_cache.json`. Next parse/load rebuilds them.

---

## 🎮 Game Data Files (Invent-O-Matic Stash Mod)

Invent-O-Matic writes these to your game’s `Data\` folder when you load a character:

- `<GameRoot>\Data\LegendaryMods.ini`  
  Master mod list + learned flags — the app’s master database (no CSV needed)
- `<GameRoot>\Data\ItemsMod.ini`  
  Your inventory quantities per mod/star tier

Notes:
- The app validates everything in `ItemsMod.ini` against `LegendaryMods.ini` and filters known bad entries.
- Multi-star mods are tracked independently (e.g., Anti-armor 2★ vs 3★ are separate entries).

---

## 📊 How Prices Are Calculated

Pipeline:

- **Source** — every `.json` and `.txt` in `ServerData.7z` (or loose in Data folder).  
  Leaders + caps detected; caps convert at **1 Leader ≈ 1000 caps**.
- **JSON format** — files with a `messages` key are parsed as structured exports.
- **TXT format** — split on blank lines; each block is a trade post.
- **Validation** — rejects out-of-range prices for the given star tier.
- **IQR outlier removal** — Tukey fence test (1.5 × IQR) removes extreme outliers.
- **Deduplication** — same `(source file, author, timestamp)` counted once.
- **Statistics** — Median / Q1 / Q3 + sample size `n`.
- **Estimated** — if no data exists, assigns star-tier median, marked `~` + `est`.
- **Caching** — saved to `Data\price_cache.json`.

Tip: more trade posts = more accurate prices.

---

## 🔧 Troubleshooting

- **“No mods loaded”**  
  Game Root path is wrong or the folder does not contain `Data\LegendaryMods.ini`. Browse to the folder containing `Fallout76.exe`.
- **“Game path not found”**  
  Saved path no longer exists — browse again and save.
- **“Auto-load failed” on startup**  
  `price_cache.json` is corrupt — Clear Caches and rebuild.
- **Collection shows 0**  
  Invent-O-Matic isn’t installed or you haven’t launched the game since installing it.
- **All prices estimated (`~`)**  
  Archive didn’t parse or has no recognizable trade posts — Clear Caches, Parse Price Data Only, check console output.
- **Prices look wrong/old**  
  Add newer trade files to `ServerData.7z` and re-parse.
- **PNG preview blank**  
  Add at least one item to WTS/WTB; preview renders only when there’s content.
- **Mod installer fails**  
  Ensure Fallout 76 is closed. If `Fallout76Custom.ini` doesn’t exist yet, launch the game once to generate it.
- **INI entry not removed on uninstall**  
  Verify the INI path is correct in Settings.
- **A mod missing from dropdown**  
  Some mods only exist at specific star tiers; the dropdown reflects valid combinations from `LegendaryMods.ini`.
- **Colour changes not updating**  
  You must **Save Settings** to refresh lists and previews.
- **TXT not parsed**  
  Ensure it’s inside `ServerData.7z` or loose in Data folder; separate posts by blank line and include prices like `5L` / `25 leaders`.

---

## 📁 File & Folder Reference

All paths relative to where the exe (or `F76PriceGuide.py`) lives:

- `settings.json` — all settings + Nexus key + profile (safe to back up; don’t commit)
- `Data\` — app data folder
  - `Data\ServerData.7z` — your price-data archive (you provide)
  - `Data\price_cache.json` — parsed prices (safe to delete)
  - `Data\raw_cache.json` — intermediate parse data (safe to delete)
  - `Data\inventOmaticStashConfig.json` — config for Invent-O-Matic (synced to game on install/start)
- `Exports\` — default save folder for PNG/TXT exports (created on first export)

Game files written by the mod:

- `<GameRoot>\Data\LegendaryMods.ini`
- `<GameRoot>\Data\ItemsMod.ini`
- `<GameRoot>\dxgi.dll` (SFE)

---

## ✨ Tips & Tricks

- Use **⟳ Sync Collection** on WTS after every play session to rebuild your sell list from current quantities.
- Use Mode = `all` for bulk pricing.
- Use WTT on both WTS and WTB for trade-for-trade deals on the PNG.
- Type partial names in dropdowns (e.g. `anti`) to filter instantly.
- Export WTS/WTB lists to JSON regularly.
- Pack multiple `.json` and `.txt` files into one `ServerData.7z` — the app parses them all in one pass.
- If a mod looks wrong, check for `~` and low `n` — low confidence from sparse data.

---

## Developer notes (build + release)

### Run from source
- `#Run.bat` (Windows), or run `python F76PriceGuide.py`
- The app auto-installs dependencies at runtime if missing.

### Build exe + installer (Windows)
Scripts included:

- `#Pack.bat` — cleans `build/ dist/ Output/`, installs/upgrades deps, runs PyInstaller, then Inno Setup
- `F76PriceGuide.spec` — onefile, windowed, icon `app.ico`
- `Pack.iss` — installer config

Expected outputs:

- `dist\F76PriceGuide.exe`
- `Output\F76TradeGuide_Installer.exe`

Paths in `#Pack.bat` are hardcoded (example):

- `C:\Python314\python.exe`
- `C:\Python314\Scripts\pyinstaller.exe`
- `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

Edit those paths if your system differs.
