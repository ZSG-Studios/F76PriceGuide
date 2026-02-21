# F76 Price Guide (F76TradeGuide)

A Windows desktop app for **Fallout 76** that combines:

- **Legendary mod price guide** (community trade data → median/range/n in Leaders)
- **Trade post manager** (WTS / WTB lists → PNG + copy-ready text)
- **Collection sync + value estimate** (reads your in-game inventory and totals it using cached prices)
- **Optional Nexus mod installer** (installs the files needed to export your inventory)

> **Not affiliated with Bethesda / ZeniMax / Fallout 76.**  
> This is a fan-made tool for personal use.

---

## What it does

### 1) Reads your game data (no hardcoded mod list)
The app uses two files written to your game’s `Data\` folder by the **Invent-O-Matic Stash** mod:

- `LegendaryMods.ini` → master list of mod names + supported star tiers + learned (craftable) flags  
- `ItemsMod.ini` → your current inventory quantities per mod + star tier

### 2) Parses your trade archive and builds prices
You provide a **price-data archive** (default: `Data\ServerData.7z`) containing `.json` and/or `.txt` trade posts.  
The app extracts prices, rejects obvious junk/outliers, and saves the results to `Data\price_cache.json`.

- Prices are shown in **Leaders (L)**
- Caps are detected and converted using **1 Leader ≈ 1000 caps**
- If no real data exists for a mod, an estimated price is used (marked with `~` and `est`)

### 3) Generates WTS/WTB posts
- Build WTS (selling) and WTB (buying) lists
- Export **PNG images** for posting
- Copy **plain-text posts** to clipboard
- Backup/restore lists via JSON export/import

---

## Features

- Dashboard with live counters: **MODS / PRICES / COLLECTION / VALUE**
- Price Guide table with **search** + **Export TXT**
- WTS + WTB managers with:
  - auto price fill from median cache
  - “each” vs “all” pricing modes
  - WTT (trade-for-trade) field
  - optional “Buying Junk Mods” line
  - JSON backup/restore
- **Colour system** (White / Green / Orange) for craft status:
  - **White**: you own the card but cannot craft it
  - **Green**: learned → craftable (you provide modules; buyer brings the rest)
  - **Orange**: craftable but uses untradeable materials → special arrangement needed
- Settings for:
  - game paths, data paths
  - trade profile (IGN, junk prices, craft prices)
  - full PNG palette + legend text
  - cache management (clear/rebuild)
- Optional Nexus Mod Manager:
  - link Nexus API key
  - install/uninstall managed mods
  - updates `Fallout76Custom.ini` automatically for `.ba2` entries

---

## Quick start (end users)

### Step 1 — Install and run
- Use the installer (`F76TradeGuide_Installer.exe`) or run the portable exe (`F76PriceGuide.exe`).
- First run creates/uses:
  - `settings.json` (local settings)
  - `Data\` (app data + caches)
  - `Exports\` (default export location)

### Step 2 — Configure paths
Open **Settings** and verify:

- **Fallout 76 Game Root** → folder containing `Fallout76.exe`  
  (the app reads `Data\LegendaryMods.ini` + `Data\ItemsMod.ini` from here)
- **Fallout76Custom.ini** → usually:
  `C:\Users\<You>\Documents\My Games\Fallout 76\Fallout76Custom.ini`  
  (only needed if you use the in-app mod installer)
- **Data Folder** → default is `Data\` next to the exe
- **ServerData.7z Path** → default `Data\ServerData.7z`

### Step 3 — Install required game export mod (recommended)
To sync your collection, you need:

- **Invent-O-Matic Stash (Unofficial)**  
- **Script Functions Extender (SFE)**

You can install from **Settings → Nexus Mod Manager**, or install manually.

> After installing/updating Invent-O-Matic: **launch Fallout 76**, load a character once, then quit — it writes the INI files on game load.

### Step 4 — Load data
On **Dashboard**:

- **⟳ Load All Data** (first run or after updating ServerData.7z)
- **Load Collection Only** (fast refresh after playing)
- **Parse Price Data Only** (forces a full rebuild from the archive)

### Step 5 — Create posts
- Go to **Trade Post → WTS** and/or **WTB**
- Add items (or **⟳ Sync Collection** on WTS)
- Export a PNG or copy text to clipboard

---

## Repo layout

> Paths below are relative to the repo root / app directory.

```
F76PriceGuide.py            # main app (single-file)
F76PriceGuide.spec          # PyInstaller build spec (onefile, no console)
Pack.iss                    # Inno Setup installer script
#Run.bat                    # run from source (Windows)
#Pack.bat                   # clean + pip + pyinstaller + inno build script
app.ico                     # app icon for exe
gitignore                   # rename to .gitignore in your repo
Data/                       # runtime data (see notes)
Output/                     # Inno output (ignored)
dist/ build/                # PyInstaller artifacts (ignored)
Exports/                    # user exports (ignored)
settings.json               # user settings (ignored)
```

### About `Data\`
The installer (`Pack.iss`) includes **everything inside `Data\`**.  
Recommended repo contents:

- ✅ `Data\inventOmaticStashConfig.json` (safe default config)  
- ❓ `Data\ServerData.7z` (optional — **often private/large**, you may want it *excluded*)  
- ❌ `Data\price_cache.json` / `Data\raw_cache.json` (generated files; don’t commit)

---

## Building from source (developers)

### Run from source
Option A:
```bat
#Run.bat
```

Option B:
```bash
python F76PriceGuide.py
```

The app will auto-install these packages if missing:
- `customtkinter`, `pillow`, `rapidfuzz`, `py7zr`, `requests`

### Build the exe + installer (Windows)
Requirements:
- Python (the provided scripts assume `C:\Python314\python.exe`)
- PyInstaller
- Inno Setup 6 (default path: `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`)

Run:
```bat
#Pack.bat
```

Outputs:
- `dist\F76PriceGuide.exe`
- `Output\F76TradeGuide_Installer.exe`

---

## Troubleshooting (common)

- **“No mods loaded” / MODS = 0**  
  Your Game Root is wrong or you haven’t generated `LegendaryMods.ini` yet.
- **COLLECTION = 0**  
  Invent-O-Matic isn’t installed *or* you haven’t loaded a character since installing it.
- **All prices show `~` / `est`**  
  Your archive didn’t parse or contains no recognizable trade posts → Clear Caches, then Parse Price Data Only.
- **Prices look old**  
  Update your `ServerData.7z` with newer trade files and re-parse.

(For a full help guide, see the project Wiki.)

---

## Safety / privacy / TOS notes

- `settings.json` can contain a Nexus API key — **never commit it**.
- Only include trade data you have permission to use. **Don’t scrape private Discords or servers** without consent.
- This tool modifies game files when using the mod installer; always back up your `Fallout76Custom.ini` if you’re nervous.

---

## Credits

### Python libraries
- CustomTkinter (`customtkinter`)
- Pillow (`PIL`)
- RapidFuzz (`rapidfuzz`)
- py7zr (`py7zr`)
- Requests (`requests`)

### Managed mods
- Invent-O-Matic Stash (Unofficial) — by **Demorome**
- Script Functions Extender (SFE) — by **Keretus**
