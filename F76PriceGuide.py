#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F76 Price Guide - Fallout 76 Legendary Mod Price Guide
Single consolidated file with integrated parser

Run: python F76PriceGuide.py
Dependencies: pip install customtkinter pillow rapidfuzz py7zr
"""

import sys
import os
import re
import json
import glob
import math
import threading
import tkinter as tk
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import tempfile
import zipfile
import shutil
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Set

# ============================================================================
# AUTO-INSTALL DEPENDENCIES
# ============================================================================

def _auto_install(package: str, import_name: str = None) -> None:
    """Install a package via pip if it is not already importable."""
    import importlib
    import subprocess
    name = import_name or package
    try:
        importlib.import_module(name)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package, "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"  {package} installed.")

# Ensure all required packages are present before importing them
_auto_install("customtkinter")
_auto_install("pillow", "PIL")
_auto_install("rapidfuzz")
_auto_install("py7zr")
_auto_install("requests")

# Fix user-site path so freshly installed packages are importable immediately
import site
user_site = site.USER_SITE
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

# ============================================================================
# THIRD-PARTY IMPORTS (all guaranteed present after auto-install above)
# ============================================================================

import customtkinter as ctk
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

from PIL import Image, ImageDraw, ImageFont, ImageTk

from rapidfuzz import fuzz, process
FUZZY = True

import py7zr
PY7ZR = True

# ============================================================================
# CONFIG
# ============================================================================

def winpath(p) -> str:
    """Always return a Windows-style backslash path string."""
    return str(Path(p)).replace("/", "\\")

def get_app_dir() -> Path:
    """Return the directory that contains the running script or exe.
    Used only for locating bundled assets (icons, etc.) — NOT for user data."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent.resolve()
    else:
        return Path(__file__).parent.resolve()

APP_DIR = get_app_dir()   # directory containing the exe / script

# ── Trade Post Profile defaults ───────────────────────────────────────────────
PROFILE_DEFAULTS = {
    "ign":            "UserName",
    # Junk mod prices per star tier
    "junk_1star":     "1",
    "junk_2star":     "2",
    "junk_3star":     "5",
    "junk_4star":     "10",
    # Crafting service prices per star tier
    "craft_1star":    "5",
    "craft_2star":    "10",
    "craft_3star":    "15",
    "craft_4star":    "20",
    # Legend label names (customizable)
    "label_white":    "Cannot Craft",
    "label_green":    "Can Craft",
    "label_orange":   "Can Craft",
    # Legend description text (the body text after the label)
    "desc_white":     "I have this mod — cannot craft tho",
    "desc_green":     "Can Craft — I provide the Legendary Modules, you bring the rest of the materials",
    "desc_orange":    "Can Craft at a premium! — all materials are untradeable",
    "color_bg":       "#373737",
    "color_card":     "#4B4B4B",
    "color_gold":     "#FFD700",
    "color_green":    "#64DC64",
    "color_orange":   "#FFA500",
    "color_accent":   "#FFFFFF",
    # Additional PNG colours (all fully editable)
    "color_stars":    "#FFD700",   # star icons on cards and price lines
    "color_title":    "#FFFFFF",   # big "Want To Sell / Want To Buy" header
    "color_notice":   "#DC2828",   # "Read the color guide" notice line
    "color_junk_label": "#FFD700", # "Buying Junk Mods" line text
}
# Settings and exports live alongside the exe/script.
# DATA_DIR is the user's chosen Data folder — defaults to APP_DIR/Data on first run
# but is overridden at startup once settings are loaded (see _load_settings).
SETTINGS_FILE = APP_DIR / "settings.json"
EXPORT_DIR    = APP_DIR / "Exports"
DATA_DIR      = APP_DIR / "Data"   # overwritten at runtime by _apply_data_dir()

# ── Nexus Mod Catalog ─────────────────────────────────────────────────────────
# Each entry describes one mod the app can manage via the Nexus API.
# mod_id and file_id are from the Nexus mod page URL and Files tab.
# These are NOT shipped with the app — the user downloads from Nexus directly.
NEXUS_GAME = "fallout76"
NEXUS_APP_NAME = "F76PriceGuide"
NEXUS_APP_VERSION = "1.0"
NXM_LISTENER_PORT = 52990   # local port we listen on for nxm:// callbacks

NEXUS_MODS = [
    {
        "key":          "inventomatic",
        "name":         "Invent-O-Matic Stash (Unofficial)",
        "author":       "Demorome",
        "mod_id":       698,          # nexusmods.com/fallout76/mods/698
        "nexus_url":    "https://www.nexusmods.com/fallout76/mods/698",
        "description":  "Exports your legendary mod inventory to JSON files so this app can read your collection. Required for Sync Collection and Value estimation.",
        "install_files": [],
        "detect_files": [
            "Data/InventOmaticStash.ba2",
            "Data/inventOmaticStashConfig.json",
        ],
        "ini_ba2":      "InventOmaticStash.ba2",
    },
    {
        "key":          "sfe",
        "name":         "Script Functions Extender (SFE)",
        "author":       "Keretus",
        "mod_id":       106,          # nexusmods.com/fallout76/mods/106
        "nexus_url":    "https://www.nexusmods.com/fallout76/mods/106",
        "description":  "Script extender required by several Fallout 76 mods. Installs as a DLL hook — no ba2 file needed.",
        "detect_files": [
            "dxgi.dll",       # SFE installs dxgi.dll at the game root
        ],
        "ini_ba2":      None,         # SFE doesn't need an INI ba2 entry
        # Direct download of raw dxgi.dll — bypasses Nexus API while restricted
        "direct_url":      "https://drive.google.com/uc?export=download&id=1Z6f8Lum1rcF8eyQ03_MeAgTaRLusLSSf",
        "direct_filename": "dxgi.dll",
        "direct_is_dll":   True,       # raw DLL, no archive extraction needed
    },
]

# ── Bundled inventOmaticStashConfig.json ──────────────────────────────────────
# This config tells InventOmatic where to write LegendaryMods.ini / ItemsMod.ini.
# Outputs go to the game's Data folder (same place the app reads them from).
# This is written to Data/ on every mod install so the mod works out of the box.
INVENTOMATIC_CONFIG = {
    "outputDirectory": "Data",
    "outputLegendaryModsFilename": "LegendaryMods.ini",
    "outputItemsModFilename": "ItemsMod.ini",
    "enabledForCharacters": [],
    "outputAllCharacters": True,
    "prettyPrint": True,
    "version": 1
}

# Default game paths
DEFAULT_GAME_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Fallout76"
DEFAULT_GAME_PATH = DEFAULT_GAME_ROOT + r"\Data"

def detect_game_root():
    """Auto-detect Fallout 76 game root directory across all drives and common library paths."""
    import string
    steam_subpaths = [
        "Steam\\steamapps\\common\\Fallout76",
        "SteamLibrary\\steamapps\\common\\Fallout76",
        "Games\\Steam\\steamapps\\common\\Fallout76",
        "Games\\steamapps\\common\\Fallout76",
        "Program Files (x86)\\Steam\\steamapps\\common\\Fallout76",
        "Program Files\\Steam\\steamapps\\common\\Fallout76",
    ]
    # Check all available drive letters
    for drive in string.ascii_uppercase:
        root = f"{drive}:\\"
        if not Path(root).exists():
            continue
        for sub in steam_subpaths:
            candidate = Path(root) / sub
            if (candidate / "Fallout76.exe").exists():
                return winpath(str(candidate))
    return winpath(DEFAULT_GAME_ROOT)

def detect_ini_path():
    """Auto-detect Fallout76Custom.ini path for current Windows user"""
    user_profile = os.environ.get('USERPROFILE', '')
    if user_profile:
        ini_path = Path(user_profile) / "Documents" / "My Games" / "Fallout 76" / "Fallout76Custom.ini"
        if ini_path.exists():
            return winpath(ini_path)
        # Return default path even if doesn't exist yet
        return winpath(ini_path)
    return ""

def detect_downloads_path() -> str:
    """Detect the system Downloads folder (%%USERPROFILE%%\\Downloads)."""
    user_profile = os.environ.get('USERPROFILE', '')
    if user_profile:
        return winpath(Path(user_profile) / "Downloads")
    return winpath(Path.home() / "Downloads")

# ============================================================================
# NXM PROTOCOL HANDLER  (nxm:// links from nexusmods.com)
# ============================================================================

def nxm_register_handler():
    """Register nxm:// as a Windows URI scheme handled by this script.
    Writes to HKCU so no admin rights required."""
    try:
        import winreg
        script = str(Path(sys.executable).resolve())
        app    = str(Path(__file__).resolve())
        cmd    = f'"{script}" "{app}" "%1"'
        base   = r"Software\Classes\nxm"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as k:
            winreg.SetValueEx(k, "",            0, winreg.REG_SZ, "URL:NXM Protocol")
            winreg.SetValueEx(k, "URL Protocol",0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)
        print("NXM handler registered in HKCU.")
    except Exception as e:
        print(f"NXM register failed (non-Windows?): {e}")

def nxm_parse(nxm_url: str) -> dict:
    """Parse nxm://game/mods/modid/files/fileid?key=K&expires=E&user_id=U
    Returns dict with game, mod_id, file_id, key, expires, user_id."""
    try:
        p = urllib.parse.urlparse(nxm_url)
        # path: /mods/<mod_id>/files/<file_id>
        parts = [x for x in p.path.split("/") if x]
        params = dict(urllib.parse.parse_qsl(p.query))
        return {
            "game":    p.netloc,
            "mod_id":  int(parts[1]) if len(parts) > 1 else 0,
            "file_id": int(parts[3]) if len(parts) > 3 else 0,
            "key":     params.get("key", ""),
            "expires": params.get("expires", ""),
            "user_id": params.get("user_id", ""),
        }
    except Exception as e:
        print(f"NXM parse error: {e}")
        return {}

def nxm_build_download_url(parsed: dict, api_key: str) -> str:
    """Build the CDN download URL using the nxm key/expires params."""
    game    = parsed["game"]
    mod_id  = parsed["mod_id"]
    file_id = parsed["file_id"]
    key     = parsed["key"]
    expires = parsed["expires"]
    url = (f"https://api.nexusmods.com/v1/games/{game}"
           f"/mods/{mod_id}/files/{file_id}/download_link.json"
           f"?key={key}&expires={expires}")
    return url

def nxm_start_listener(callback):
    """Listen on localhost:NXM_LISTENER_PORT for nxm:// URLs sent by a second instance.
    Calls callback(nxm_url) on the main thread when a link arrives.
    Returns the server socket (caller should close on exit)."""
    import socket, threading
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", NXM_LISTENER_PORT))
        srv.listen(5)
        srv.settimeout(1.0)
        def _serve():
            while True:
                try:
                    conn, _ = srv.accept()
                    data = conn.recv(4096).decode("utf-8", errors="replace").strip()
                    conn.close()
                    if data.startswith("nxm://"):
                        callback(data)
                except socket.timeout:
                    continue
                except OSError:
                    break
        threading.Thread(target=_serve, daemon=True).start()
        return srv
    except Exception as e:
        print(f"NXM listener failed: {e}")
        return None

def nxm_forward_to_running_instance(nxm_url: str) -> bool:
    """If another instance is already running, forward the nxm:// URL to it and return True."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", NXM_LISTENER_PORT))
        s.sendall(nxm_url.encode("utf-8"))
        s.close()
        return True
    except Exception:
        return False



def hex_to_rgb(h: str) -> tuple:
    """Convert #RRGGBB hex string to (R,G,B) tuple."""
    h = h.lstrip("#")
    if len(h) != 6:
        return (255, 255, 255)
    try:
        return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))
    except ValueError:
        return (255, 255, 255)


# ============================================================================
# STARS
# ============================================================================

def stars(n: int) -> str:
    """Return star string for PNG/text (asterisks)"""
    if n <= 0:
        return ""
    return " * " * n

def stars_unicode(n: int) -> str:
    """Unicode stars for GUI display"""
    return "★" * n if n > 0 else ""

def draw_star(draw, cx, cy, size, fill_color):
    """Draw a 5-pointed star at center (cx, cy) with given size"""
    points = []
    for i in range(5):
        # Outer point
        angle_outer = math.pi / 2 + i * 2 * math.pi / 5
        ox = cx + size * math.cos(angle_outer)
        oy = cy - size * math.sin(angle_outer)
        points.append((ox, oy))
        # Inner point
        angle_inner = angle_outer + math.pi / 5
        ix = cx + (size * 0.4) * math.cos(angle_inner)
        iy = cy - (size * 0.4) * math.sin(angle_inner)
        points.append((ix, iy))
    draw.polygon(points, fill=fill_color)

# ============================================================================
# DATA CLASSES
# ============================================================================

# Mods that can be crafted but require materials that CANNOT be traded.
# These show orange in the UI/PNG instead of green.
UNTRADEABLE_MATERIAL_MODS: set = {
    "Overeater's",
    "Glutton",
    "Polished",
    "Propelling",
}

@dataclass
class PriceData:
    name: str
    star: int
    median: float = 0
    low: float = 0
    high: float = 0
    n: int = 0
    estimated: bool = False

@dataclass
class CollItem:
    name: str
    star: int
    qty: int = 0
    learned: bool = False

@dataclass
class TradeItem:
    stars: int
    name: str
    qty: int = 1
    price: int = 0
    mode: str = "each"
    wtt: str = ""
    can_craft: bool = False  # True = learned mod, name shown in green
    craft_untradeable: bool = False  # True = can craft but materials can't be traded, shown in orange

@dataclass
class WTBItem:
    """Want To Buy item"""
    text: str           # Mod name (WTB)
    stars: int = 1      # Star tier (1-4) for WTB mod
    qty: int = 1        # How many wanting to buy
    mode: str = "each"  # "each" = price per mod, "all" = price for whole lot
    price: int = 0      # Price willing to pay
    notes: str = ""     # Optional notes
    wtt: str = ""       # WTT mod name
    wtt_stars: int = 1  # Star tier of WTT mod
    wtt_qty: int = 1    # How many offering in trade
    wtt_mode: str = "each"  # "each" or "all" for WTT quantity

# ============================================================================
# MODS LOADER - Uses LegendaryMods.ini as CANONICAL SOURCE (no external CSV needed)
# ============================================================================

# Known bad entries in LegendaryMods.ini - erroneous data from the game itself.
# Format: {name: {stars_to_exclude}}
INI_BAD_ENTRIES: Dict[str, Set[int]] = {
    "Barbarian": {4},  # Barbarian only goes up to 3* - 4* is a game data error
}

def load_mods_from_ini(game_path: str) -> Tuple[Dict[str, List[int]], Dict[str, str], int]:
    """
    Load the master mod list from LegendaryMods.ini - the CANONICAL SOURCE of truth.
    LegendaryMods.ini contains ALL mods in the game (owned or not) with star tiers.
    Bad entries listed in INI_BAD_ENTRIES are silently filtered out.

    Returns: (mods_dict, name_lookup, total_entries)
    - mods_dict:     {canonical_name: [star1, star2, ...]}  sorted ascending
    - name_lookup:   {normalized_name -> canonical_name}
    - total_entries: count of unique (name, star) pairs
    """
    leg_ini = Path(game_path) / "LegendaryMods.ini"
    mods = defaultdict(set)   # use set to auto-deduplicate same star appearing twice
    name_lookup = {}

    if not leg_ini.exists():
        print(f"LegendaryMods.ini not found at {leg_ini}")
        return {}, {}, 0

    try:
        with open(leg_ini, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for char, cdata in data.get('characterInventories', {}).items():
            for mod in cdata.get('legendaryMods', []):
                name = mod.get('name', '').strip()
                star = mod.get('stars', 0)
                if not name or not (1 <= star <= 4):
                    continue
                # Filter known bad game data entries
                if star in INI_BAD_ENTRIES.get(name, set()):
                    print(f"  Filtered bad INI entry: {name} {star}*")
                    continue
                mods[name].add(star)

        # Convert sets to sorted lists and build lookup
        mods_sorted = {}
        total_entries = 0
        for name, star_set in mods.items():
            star_list = sorted(star_set)
            mods_sorted[name] = star_list
            total_entries += len(star_list)
            normalized = normalize_mod_name(name)
            name_lookup[normalized] = name

        print(f"Loaded {total_entries} mod entries from LegendaryMods.ini ({len(mods_sorted)} unique names)")
        print(f"  Star distribution: 1*={sum(1 for s in mods_sorted.values() if 1 in s)}, "
              f"2*={sum(1 for s in mods_sorted.values() if 2 in s)}, "
              f"3*={sum(1 for s in mods_sorted.values() if 3 in s)}, "
              f"4*={sum(1 for s in mods_sorted.values() if 4 in s)}")

        return mods_sorted, name_lookup, total_entries

    except Exception as e:
        print(f"Error loading LegendaryMods.ini as mod source: {e}")
        return {}, {}, 0

def normalize_mod_name(name: str) -> str:
    """Normalize a mod name for matching - removes all variance"""
    if not name:
        return ""
    # Lowercase, remove apostrophes, dashes, spaces
    n = name.lower().strip()
    n = n.replace("'", "").replace("-", "").replace(" ", "")
    # Strip trailing 's' only for longer names to avoid mangling short ones
    # (e.g. "Stalkers" -> "stalker" is fine; "Mass" -> "Mas" is wrong)
    if n.endswith("s") and len(n) > 5:
        n = n[:-1]
    return n

# Known name variations that map to canonical names in mods.csv
# Format: {normalized_ini_name: canonical_mods_csv_name}
NAME_VARIATIONS = {
    # V.A.T.S. variations
    "vatsenhanced": "V.A.T.S. Enhanced",
    "vatsoptimized": "V.A.T.S. Optimized",
    "vats enhanced": "V.A.T.S. Enhanced",
    "vats optimized": "V.A.T.S. Optimized",
    # Common variations
    "antiarmor": "Anti-armor",
    "ghoulslayers": "Ghoul Slayer's",
    "ghoulslayer": "Ghoul Slayer's",
    "mutantslayers": "Mutant Slayer's",
    "mutantslayer": "Mutant Slayer's",
    "troubleshooters": "Troubleshooter's",
    "zealots": "Zealot's",
    "vampires": "Vampire's",
    "hunters": "Hunter's",
    "aristocrats": "Aristocrat's",
    "berserkers": "Berserker's",
    "executioners": "Executioner's",
    "exterminators": "Exterminator's",
    "medics": "Medic's",
    "snipers": "Sniper's",
    "stalkers": "Stalker's",
    "suppressors": "Suppressor's",
    "vanguards": "Vanguard's",
    # Name corrections for price cache backward compatibility
    "lucky": "Lucky Hit",  # Old price cache uses "Lucky", new mods.csv uses "Lucky Hit"
}

# Price cache name corrections (old_name -> new_canonical_name)
PRICE_NAME_CORRECTIONS = {
    "Lucky": "Lucky Hit",
}

def match_ini_name_to_canonical(ini_name: str, name_lookup: Dict[str, str], mods: Dict[str, List[int]]) -> Optional[str]:
    """
    Match an INI item name to canonical mod name - NEVER FAIL
    Returns canonical name or None if truly not found
    """
    if not ini_name or not name_lookup:
        return None
    
    # Try exact match first
    if ini_name in mods:
        return ini_name
    
    # Try NAME_VARIATIONS lookup
    ini_lower = ini_name.lower().strip()
    ini_normalized = normalize_mod_name(ini_name)
    if ini_normalized in NAME_VARIATIONS:
        canonical = NAME_VARIATIONS[ini_normalized]
        if canonical in mods:
            return canonical
    if ini_lower in NAME_VARIATIONS:
        canonical = NAME_VARIATIONS[ini_lower]
        if canonical in mods:
            return canonical
    
    # Try normalized match
    if ini_normalized in name_lookup:
        return name_lookup[ini_normalized]
    
    # Try case-insensitive match
    for canonical in mods.keys():
        if canonical.lower() == ini_lower:
            return canonical
    
    # Try without apostrophes and dashes
    ini_no_apos = ini_lower.replace("'", "").replace("-", " ").strip()
    for canonical in mods.keys():
        canon_clean = canonical.lower().replace("'", "").replace("-", " ").strip()
        if ini_no_apos == canon_clean:
            return canonical
    
    # Fuzzy match as last resort
    if FUZZY:
        try:
            mod_names = list(mods.keys())
            result = process.extractOne(ini_lower, mod_names, scorer=fuzz.ratio)
            if result and result[1] >= 75:
                return result[0]
        except Exception as e:
            print(f"Warning: fuzzy match error: {e}")
    
    return None

def load_mods_from_ini_simple(game_path: str) -> Dict[str, List[int]]:
    """Load mods from LegendaryMods.ini - returns {canonical_name: [star1, star2, ...]}"""
    mods_dict, _, _ = load_mods_from_ini(game_path)
    return mods_dict

def load_prices_and_match_to_mods(data_dir: Path, mods: Dict[str, List[int]]) -> Dict[str, Dict]:
    """
    Load price_cache.json and match to canonical mods.
    Returns prices dict with keys matching canonical mod names.
    """
    price_cache_path = data_dir / "price_cache.json"
    prices = {}
    
    if not price_cache_path.exists():
        print(f"price_cache.json not found at {price_cache_path}")
        return prices
    
    try:
        with open(price_cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        raw_prices = cache.get("prices", {})
        
        matched = 0
        unmatched = 0
        
        for key, data in raw_prices.items():
            price_name = data.get("name", "")
            price_star = data.get("star", 0)
            
            # Apply name corrections first (for backward compatibility)
            if price_name in PRICE_NAME_CORRECTIONS:
                price_name = PRICE_NAME_CORRECTIONS[price_name]
                data = data.copy()  # Don't modify original
                data["name"] = price_name
            
            # Try to match price name to canonical mod
            canonical = None
            
            # Exact match
            if price_name in mods:
                canonical = price_name
            else:
                # Try normalized match
                normalized = normalize_mod_name(price_name)
                for mod_name in mods.keys():
                    if normalize_mod_name(mod_name) == normalized:
                        canonical = mod_name
                        break
                
                # Try case-insensitive
                if not canonical:
                    for mod_name in mods.keys():
                        if mod_name.lower() == price_name.lower():
                            canonical = mod_name
                            break
            
            if canonical and price_star in mods.get(canonical, []):
                # Use canonical key
                canonical_key = f"{canonical}_{price_star}"
                prices[canonical_key] = data
                matched += 1
            else:
                # Keep original key but log warning
                prices[key] = data
                unmatched += 1
                if unmatched <= 5:
                    print(f"  Warning: Price '{price_name}' star {price_star} not matched to a known mod")
        
        print(f"Loaded {len(prices)} prices: {matched} matched, {unmatched} unmatched")
        
    except Exception as e:
        print(f"Error loading price_cache.json: {e}")
    
    return prices

def build_fuzzy_index(mods: Dict[str, List[int]]) -> Dict[str, Tuple[str, int]]:
    """Build fuzzy matching index"""
    index = {}
    for name, star_list in mods.items():
        variations = [
            name.lower(),
            name.lower().replace("'", ""),
            name.lower().replace("'", "s"),
            name.lower().replace("-", " "),
            name.lower().replace("-", ""),
            name.lower().replace(" ", ""),
        ]
        base = name.lower().rstrip("'s").rstrip("s")
        if base and len(base) >= 3:
            variations.extend([base, base + "s", base + "'s"])
        
        for v in variations:
            if v and len(v) >= 3 and v not in index:
                index[v] = (name, min(star_list))
    return index

def build_valid_mods_set(mods: Dict) -> set:
    """Build set of (name, star) tuples for validation - handles multi-star format"""
    valid = set()
    for name, star_list in mods.items():
        if isinstance(star_list, list):
            for star in star_list:
                valid.add((name, star))
        else:
            # Legacy format: (name, star) tuple
            valid.add((name, star_list))
    return valid

def get_mod_stars(name: str, mods: Dict) -> List[int]:
    """Get all star ratings for a mod name (multi-star format)"""
    if not name or not mods:
        return [1]
    
    # Check if mods is in multi-star format {name: [stars]}
    if name in mods:
        star_list = mods[name]
        return star_list if isinstance(star_list, list) else [star_list]
    
    # Try exact match by name (case-insensitive)
    for mod_name, star_list in mods.items():
        if mod_name.lower() == name.lower():
            return star_list if isinstance(star_list, list) else [star_list]
    
    return [1]

def get_mod_star(name: str, mods: Dict) -> int:
    """Get default (minimum) star rating for a mod name"""
    star_list = get_mod_stars(name, mods)
    return min(star_list) if star_list else 1

def fuzzy_match(name: str, mods: Dict) -> Optional[Tuple[str, int]]:
    """Fuzzy match name to mods database - returns (canonical_name, default_star)"""
    if not name or not mods:
        return None
    
    clean = name.lower().strip()
    
    # Check for exact match by name (multi-star format: {name: [stars]})
    if clean in mods:
        star_list = mods[clean]
        default_star = min(star_list) if isinstance(star_list, list) else star_list
        return (clean, default_star)
    
    # Case-insensitive match
    for mod_name, star_list in mods.items():
        if mod_name.lower() == clean:
            default_star = min(star_list) if isinstance(star_list, list) else star_list
            return (mod_name, default_star)
    
    variants = [
        clean,
        clean.replace("'", ""),
        clean.replace("'", "s"),
        clean.replace("-", " "),
        clean.replace("-", ""),
        clean.replace("'s", "s"),
        clean.replace("'s", ""),
        clean.replace(" ", ""),
        clean.replace(" ", "-"),
    ]
    
    for v in variants:
        v = v.strip()
        for mod_name, star_list in mods.items():
            if mod_name.lower() == v:
                default_star = min(star_list) if isinstance(star_list, list) else star_list
                return (mod_name, default_star)
    
    for key in mods.keys():
        key_lower = key.lower()
        if clean in key_lower and len(clean) >= 4:
            stars = mods[key]
            default_star = min(stars) if isinstance(stars, list) else stars
            return (key, default_star)
        if key_lower in clean and len(key) >= 4:
            stars = mods[key]
            default_star = min(stars) if isinstance(stars, list) else stars
            return (key, default_star)
    
    if FUZZY:
        try:
            result = process.extractOne(clean, list(mods.keys()), scorer=fuzz.partial_ratio)
            if result and result[1] >= 70:
                mod_name = result[0]
                stars = mods[mod_name]
                default_star = min(stars) if isinstance(stars, list) else stars
                return (mod_name, default_star)
        except Exception as e:
            print(f"Warning: mod lookup error: {e}")
    
    return None

# ============================================================================
# PRICE DATA PARSER — reads .json and .txt trade files from ServerData.7z
# ============================================================================

TIER_BOUNDS = {
    1: {"min": 1, "max": 150},
    2: {"min": 2, "max": 250},
    3: {"min": 5, "max": 400},
    4: {"min": 10, "max": 600},
}

def extract_stars_from_text(text: str) -> Optional[int]:
    """Extract star rating from message text"""
    unicode_stars = len(re.findall(r'★', text))
    if unicode_stars > 0 and unicode_stars <= 4:
        star_match = re.search(r'★{1,4}', text)
        if star_match:
            return len(star_match.group(0))
    
    ast_match = re.search(r'\*{1,4}(?!\*)', text)
    if ast_match:
        return len(ast_match.group(0))
    
    num_star_patterns = [
        r'(\d)\s*\*', r'(\d)\s*★', r'(\d)\s*star',
        r'(\d)\s*-\s*star', r'(\d)s?\s*tar',
    ]
    for pattern in num_star_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            star = int(match.group(1))
            if 1 <= star <= 4:
                return star
    return None

def extract_stars_near_mod(text: str, mod_pos: int, window: int = 50) -> Optional[int]:
    start = max(0, mod_pos - window)
    end = min(len(text), mod_pos + window)
    nearby = text[start:end]
    return extract_stars_from_text(nearby)

def extract_section_star(text: str, mod_pos: int) -> Optional[int]:
    before = text[:mod_pos]
    patterns = [
        r'(?:^|\n)\s*(\d)\s*\*\s*(?:$|\n)',
        r'\*\*\*\s+',
        r'\((\d)\s*star\)',
        r'(\d)\s*star\)',
        r'__\s*(\d)\s*[Ss]tar\s*__',
        r'\n\s*\*\*\*\s+',
    ]
    
    last_star = None
    last_pos = -1
    
    for pattern in patterns[:5]:
        for match in re.finditer(pattern, before, re.IGNORECASE | re.MULTILINE):
            if match.start() > last_pos:
                last_pos = match.start()
                if match.groups():
                    last_star = int(match.group(1))
                else:
                    last_star = 3
    
    for match in re.finditer(r'(?:^|\n|\s)\*{3,4}(?:\s|$)', before):
        if match.start() > last_pos:
            last_pos = match.start()
            star_count = len(match.group(0).strip())
            if 1 <= star_count <= 4:
                last_star = star_count
    
    return last_star

def extract_prices(text: str) -> List[Tuple[int, int, str]]:
    prices = []
    for match in re.finditer(r'(\d+)\s*[Ll](?:eaders?)?\b', text):
        try:
            price = int(match.group(1))
            if 1 <= price <= 10000:
                prices.append((price, match.start(), 'leaders'))
        except Exception as e:
            print(f"Warning: price parse error (leaders): {e}")
    
    for match in re.finditer(r'(\d+)k?\s*caps?\b', text, re.IGNORECASE):
        try:
            price = int(match.group(1))
            if 'k' in text[match.start():match.end()].lower():
                price *= 1000
            leader_equiv = max(1, price // 1000)
            prices.append((leader_equiv, match.start(), 'caps'))
        except Exception as e:
            print(f"Warning: price parse error (caps): {e}")
    return prices

def extract_mod_candidates(text: str, mods_index: Dict[str, Tuple[str, int]]) -> List[Tuple[str, int, int, Optional[int]]]:
    candidates = []
    text_lower = text.lower()
    
    for key, (canonical, default_star) in mods_index.items():
        if len(key) < 3:
            continue
        
        for match in re.finditer(re.escape(key), text_lower):
            pos = match.start()
            qty = 1
            extracted_star = extract_stars_near_mod(text, pos, 30)
            
            prefix = text[max(0, pos-15):pos]
            qty_match = re.search(r'[xX]?(\d+)[xX]?\s*$', prefix)
            if qty_match:
                qty = int(qty_match.group(1))
            
            candidates.append((canonical, pos, qty, extracted_star))
    
    return candidates

def is_listing_message(content: str) -> bool:
    content_lower = content.lower()
    trade_tags = ['wts', 'wtb', 'wtt', 'h:', 'w:', 'lf ', 'looking for', 
                  'selling', 'buying', 'offer', 'trade', 'have:', 'want:']
    for tag in trade_tags:
        if tag in content_lower:
            return True
    if re.search(r'\d+\s*[Ll]', content):
        return True
    if re.search(r'★{1,4}\s*\w', content):
        return True
    return False

def is_plan_price_pair(content: str, price_pos: int, mod_pos: int) -> bool:
    """
    Return True if the price at price_pos is associated with a "Plan:" item
    rather than a legendary mod.  We check the same line as the price for
    "plan:" prefix, which catches "Plan: Steady Handle - 300L" being
    mistakenly attributed to the mod "Steady".
    """
    # Find the line that contains the price
    line_start = content.rfind('\n', 0, price_pos)
    line_start = 0 if line_start == -1 else line_start + 1
    line_end = content.find('\n', price_pos)
    line_end = len(content) if line_end == -1 else line_end
    line = content[line_start:line_end].lower()
    return 'plan:' in line or line.strip().startswith('plan ')


def is_junk_message(content: str) -> Tuple[bool, str]:
    content_lower = content.lower().strip()
    
    if re.match(r'^(sold|done|traded|closed|taken|gone)\s*$', content_lower):
        return True, "sold/done"

    # Strikethrough check: Discord wraps struck-out text with ~~...~~
    # Match both messages that start with ~~ and ones that are fully struck-through
    if re.search(r'~~.+~~', content, re.DOTALL):
        return True, "strikethrough"
    
    crafting_patterns = [
        r'crafting\s*service', r'free\s*craft', r'craft\s*for\s*you',
        r'you\s*provide\s*(materials?|mats)', r'your\s*(materials?|mats)',
    ]
    for pattern in crafting_patterns:
        if re.search(pattern, content_lower):
            return True, "crafting"
    
    if re.match(r'^(bump|up|\^|\.)\s*$', content_lower):
        return True, "bump"
    
    return False, ""

def parse_message(content: str, mods_index: Dict[str, Tuple[str, int]], 
                  source_file: str = "", author: str = "", timestamp: str = "") -> List[Dict]:
    entries = []
    
    is_junk, reason = is_junk_message(content)
    if is_junk:
        return entries
    
    if not is_listing_message(content):
        return entries
    
    prices = extract_prices(content)
    if not prices:
        return entries
    
    candidates = extract_mod_candidates(content, mods_index)
    if not candidates:
        return entries
    
    for price, price_pos, price_type in prices:
        best_candidate = None
        best_dist = float('inf')
        
        for mod_name, mod_pos, qty, extracted_star in candidates:
            dist = abs(mod_pos - price_pos)
            if dist < best_dist:
                best_dist = dist
                best_candidate = (mod_name, mod_pos, qty, extracted_star)
        
        if best_candidate and best_dist < 200:
            mod_name, mod_pos, qty, extracted_star = best_candidate

            # Skip this price if it lives on a "Plan: ..." line — those are
            # weapon/armour plan prices, not legendary mod prices.
            if is_plan_price_pair(content, price_pos, mod_pos):
                continue

            star = extracted_star
            if not star:
                section_star = extract_section_star(content, mod_pos)
                if section_star:
                    star = section_star
            if not star:
                key = mod_name.lower().replace("'", "").replace("-", " ")
                if key in mods_index:
                    star = mods_index[key][1]
                else:
                    star = 1
            
            bounds = TIER_BOUNDS.get(star, TIER_BOUNDS[1])
            # Allow up to 1.5× the tier ceiling (not 3×) before hard-rejecting;
            # IQR cleaning later will handle any remaining stragglers.
            if not (bounds["min"] <= price <= bounds["max"] * 1.5):
                continue
            
            entries.append({
                "raw_name": mod_name,
                "raw_star": star,
                "price": price,
                "quantity": qty,
                "price_type": price_type,
                "source_message": content[:300],
                "source_file": source_file,
                "author": author,
                "timestamp": timestamp,
            })
    
    return entries

def _parse_json_data(data: dict, source_name: str, mods_index: Dict[str, Tuple[str, int]],
                     all_entries: list, stats: dict) -> None:
    """Parse a single JSON data dict and extend all_entries in-place."""
    messages = data.get('messages', [])
    stats["messages"] += len(messages)
    for msg in messages:
        content = msg.get('content', '')
        author_data = msg.get('author', {})
        author = author_data.get('name', 'Unknown') if isinstance(author_data, dict) else str(author_data)
        timestamp = msg.get('timestamp', '')
        entries = parse_message(content, mods_index, source_name, author, timestamp)
        all_entries.extend(entries)
        stats["entries"] += len(entries)


def _parse_txt_data(text: str, source_name: str, mods_index: Dict[str, Tuple[str, int]],
                    all_entries: list, stats: dict) -> None:
    """Parse a plain-text trade file (one message per line or free-form blocks)."""
    # Split on blank lines — each block is treated as one 'message'
    blocks = re.split(r'\n{2,}', text.strip())
    if len(blocks) <= 1:
        # No blank-line separators — treat each non-empty line as a message
        blocks = [ln for ln in text.splitlines() if ln.strip()]
    stats["messages"] += len(blocks)
    for block in blocks:
        entries = parse_message(block.strip(), mods_index, source_name, "", "")
        all_entries.extend(entries)
        stats["entries"] += len(entries)


def parse_all_jsons(archive_path: Path, mods_index: Dict[str, Tuple[str, int]],
                    progress_cb=None) -> List[Dict]:
    """Parse all trade data files from ServerData.7z (or loose files in the same folder).

    Supported file types inside the archive or folder:
      • serverdata_*.json  — structured message exports
      • *.txt              — plain-text trade listings (one post per block)
      • *.json             — any JSON with a 'messages' key

    Priority:
      1. archive_path (.7z file) if it exists — extracts to temp dir, reads, auto-cleans
      2. Loose matching files in archive_path.parent — fallback
    """
    all_entries = []
    stats = {"files": 0, "messages": 0, "entries": 0}

    def _cb(done, total, label=""):
        if progress_cb and total > 0:
            progress_cb(done / total, label)

    def _process_file(file_path: Path, source_name: str):
        """Process a single file (json or txt) and add entries to all_entries."""
        suffix = file_path.suffix.lower()
        stats["files"] += 1
        try:
            if suffix == ".json":
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                _parse_json_data(data, source_name, mods_index, all_entries, stats)
            elif suffix == ".txt":
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text = f.read()
                _parse_txt_data(text, source_name, mods_index, all_entries, stats)
        except Exception as e:
            print(f"  Error parsing {source_name}: {e}")

    # --- Try 7z archive first ---
    if archive_path.exists():
        print(f"Reading from archive: {archive_path.name}")
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                    all_names = archive.getnames()
                    # Accept both JSON and TXT files
                    target_names = [
                        n for n in all_names
                        if re.search(r'\.(json|txt)$', n, re.IGNORECASE)
                    ]
                    if not target_names:
                        print("  WARNING: No .json or .txt files found inside", archive_path.name)
                    else:
                        archive.extract(path=tmp_dir, targets=target_names)

                total = len(target_names)
                for idx, name in enumerate(target_names):
                    extracted = tmp_path / name
                    short_name = Path(name).name
                    _cb(idx, total, f"Parsing {short_name}...")
                    if not extracted.exists():
                        print(f"  WARNING: {name} not extracted, skipping")
                        continue
                    print(f"  Parsing {short_name} (from archive)...")
                    _process_file(extracted, short_name)
                _cb(total, total, "Archive parsed")

            print(f"Archive stats: {stats['files']} files, {stats['messages']} messages, {stats['entries']} entries")
            return all_entries

        except Exception as e:
            print(f"  Error reading {archive_path.name}: {e}")
            print("  Falling back to loose files...")
            all_entries.clear()
            stats = {"files": 0, "messages": 0, "entries": 0}

    # --- Fallback: loose JSON and TXT files in same folder as archive ---
    data_dir = archive_path.parent
    loose_files = sorted(
        list(data_dir.glob("*.json")) + list(data_dir.glob("*.txt"))
    )
    # Exclude our own cache files
    cache_names = {"price_cache.json", "raw_cache.json"}
    loose_files = [f for f in loose_files if f.name not in cache_names]

    if not loose_files:
        print(f"No {archive_path.name} found and no .json/.txt files found in {data_dir}")
    else:
        print(f"Reading {len(loose_files)} loose file(s) from {data_dir}")
        total = len(loose_files)
        for idx, data_file in enumerate(loose_files):
            _cb(idx, total, f"Parsing {data_file.name}...")
            print(f"  Parsing {data_file.name}...")
            _process_file(data_file, data_file.name)
        _cb(total, total, "Files parsed")

    print(f"Stats: {stats['files']} files, {stats['messages']} messages, {stats['entries']} entries")
    return all_entries

def fuzzy_match_mod(raw_name: str, mods: Dict[str, List[int]], target_star: int) -> Tuple[str, int]:
    if raw_name in mods:
        stars = mods[raw_name]
        if target_star in stars:
            return raw_name, target_star
        else:
            return raw_name, min(stars, key=lambda s: abs(s - target_star))
    
    raw_lower = raw_name.lower().replace("'", "").replace("-", " ").strip()
    
    for canonical, star_list in mods.items():
        canon_lower = canonical.lower().replace("'", "").replace("-", " ").strip()
        if raw_lower == canon_lower:
            if target_star in star_list:
                return canonical, target_star
            else:
                return canonical, min(star_list, key=lambda s: abs(s - target_star))
    
    if FUZZY:
        try:
            mod_names = list(mods.keys())
            result = process.extractOne(raw_lower, mod_names, scorer=fuzz.ratio)
            if result and result[1] >= 70:
                canonical = result[0]
                stars = mods[canonical]
                if target_star in stars:
                    return canonical, target_star
                else:
                    return canonical, min(stars, key=lambda s: abs(s - target_star))
        except Exception as e:
            print(f"Warning: canonical resolution error: {e}")
    
    return raw_name, target_star

def _iqr_filter(prices: List[float]) -> List[float]:
    """
    Remove outliers using Tukey fences (1.5 × IQR rule).
    Requires at least 4 data points to apply; returns original list otherwise.
    Always returns at least 1 value (the median of the original if everything
    would be filtered out).
    """
    if len(prices) < 4:
        return prices
    prices = sorted(prices)
    n = len(prices)
    q1 = prices[n // 4]
    q3 = prices[(3 * n) // 4]
    iqr = q3 - q1
    if iqr == 0:
        # All values identical or no spread — nothing to filter
        return prices
    lo_fence = q1 - 1.5 * iqr
    hi_fence = q3 + 1.5 * iqr
    filtered = [p for p in prices if lo_fence <= p <= hi_fence]
    return filtered if filtered else prices


def unify_entries(raw_entries: List[Dict], mods: Dict[str, List[int]]) -> Dict[str, Dict]:
    by_mod: Dict[str, Dict] = {}   # key -> {canonical, star, entries[]}

    for entry in raw_entries:
        raw_name = entry["raw_name"]
        raw_star = entry["raw_star"]
        canonical, star = fuzzy_match_mod(raw_name, mods, raw_star)
        key = f"{canonical}_{star}"
        if key not in by_mod:
            by_mod[key] = {"canonical": canonical, "star": star, "entries": []}
        by_mod[key]["entries"].append({
            "price": entry["price"],
            "quantity": entry["quantity"],
            "source": entry["source_file"],
            "_dedup": f"{entry.get('source_file','')}__{entry.get('author','')}__{entry.get('timestamp','')}",
        })

    prices = {}
    for key, bucket in by_mod.items():
        canonical = bucket["canonical"]
        star = bucket["star"]
        entries = bucket["entries"]

        # Deduplicate: same (source_file, author, timestamp) = same Discord post
        seen_dedup: set = set()
        unique_entries = []
        for e in entries:
            dk = e["_dedup"]
            if dk not in seen_dedup:
                seen_dedup.add(dk)
                unique_entries.append(e)

        raw_prices = [e["price"] for e in unique_entries]
        if not raw_prices:
            continue

        clean_prices = _iqr_filter(sorted(raw_prices))
        n_raw = len(raw_prices)
        n = len(clean_prices)

        if n == 0:
            continue

        median = clean_prices[n // 2]
        mean = sum(clean_prices) / n

        if n >= 4:
            q1 = clean_prices[n // 4]
            q3 = clean_prices[(3 * n) // 4]
            low, high = q1, q3
        elif n >= 2:
            low, high = clean_prices[0], clean_prices[-1]
        else:
            low = high = median

        prices[key] = {
            "name": canonical,   # always the canonical name, never rsplit-derived
            "star": star,
            "median": round(median, 1),
            "mean": round(mean, 1),
            "low": round(low, 1),
            "high": round(high, 1),
            "min": round(min(clean_prices), 1),
            "max": round(max(clean_prices), 1),
            "n": n,
            "n_raw": n_raw,
        }

    return prices

def estimate_missing_prices(prices: Dict[str, Dict], mods: Dict[str, List[int]]) -> Dict[str, Dict]:
    """Estimate prices for mods with no data based on star-tier averages"""
    tier_prices = defaultdict(list)
    for key, data in prices.items():
        if data["n"] > 0:
            tier_prices[data["star"]].append(data["median"])
    
    tier_stats = {}
    for star, price_list in tier_prices.items():
        if price_list:
            price_list.sort()
            n = len(price_list)
            q1 = price_list[n // 4] if n >= 4 else price_list[0]
            q3 = price_list[(3 * n) // 4] if n >= 4 else price_list[-1]
            tier_stats[star] = {
                "avg": round(sum(price_list) / n, 1),
                "median": price_list[n // 2],
                "q1": q1,
                "q3": q3,
                "min": min(price_list),
                "max": max(price_list),
                "count": n,
            }
    
    print(f"\nTier statistics for estimation:")
    for star, stats in sorted(tier_stats.items()):
        print(f"  {star}*: avg={stats['avg']}L, median={stats['median']}L (from {stats['count']} mods)")
    
    estimated_count = 0
    for name, star_list in mods.items():
        for star in star_list:
            key = f"{name}_{star}"
            
            if key not in prices:
                stats = tier_stats.get(star, {"avg": 5, "median": 5, "q1": 2, "q3": 10, "count": 0})
                prices[key] = {
                    "name": name,
                    "star": star,
                    "median": stats["median"],
                    "mean": stats["avg"],
                    "low": stats["q1"],
                    "high": stats["q3"],
                    "min": stats["q1"],
                    "max": stats["q3"],
                    "n": 0,
                    "estimated": True,
                    "estimate_method": "tier_average",
                }
                estimated_count += 1
            elif prices[key]["n"] == 0:
                stats = tier_stats.get(star, {"avg": 5, "median": 5, "q1": 2, "q3": 10, "count": 0})
                prices[key]["median"] = stats["median"]
                prices[key]["mean"] = stats["avg"]
                prices[key]["low"] = stats["q1"]
                prices[key]["high"] = stats["q3"]
                prices[key]["min"] = stats["q1"]
                prices[key]["max"] = stats["q3"]
                prices[key]["estimated"] = True
                prices[key]["estimate_method"] = "tier_average"
                estimated_count += 1
    
    print(f"\nEstimated prices for {estimated_count} mods with no data")
    return prices

def run_parser(data_dir: Path, game_path: str, force_parse: bool = False,
               archive_path: Path = None, progress_cb=None) -> Dict[str, Dict]:
    """Run the full parser and return prices dict. If cache exists and force_parse=False, load from cache."""
    print("=" * 60)
    print("PRICE DATA PARSER")
    print("=" * 60)

    def _cb(val, label=""):
        if progress_cb: progress_cb(val, label)

    if archive_path is None:
        archive_path = data_dir / "ServerData.7z"

    price_cache_path = data_dir / "price_cache.json"

    if not force_parse and price_cache_path.exists():
        try:
            _cb(0.1, "Loading prices from cache...")
            print("\nLoading prices from cache...")
            with open(price_cache_path, 'r', encoding='utf-8') as f:
                price_cache = json.load(f)
            prices = price_cache.get("prices", {})
            print(f"Loaded {len(prices)} prices from cache")
            _cb(1.0, "Cache loaded")
            return prices
        except Exception as e:
            print(f"Error loading cache: {e}")
            print("Will parse trade data instead...")

    _cb(0.05, "Loading mods index...")
    print("\nLoading mods from LegendaryMods.ini...")
    mods = load_mods_from_ini_simple(game_path)
    mods_index = build_fuzzy_index(mods)
    print(f"Built fuzzy index with {len(mods_index)} keys")

    # Parse JSONs — progress_cb receives 0..1 within this phase, mapped to 0.1..0.7
    def parse_cb(val, label=""):
        _cb(0.1 + val * 0.6, label)

    _cb(0.1, "Parsing trade data...")
    print("\nParsing trade data files...")
    raw_entries = parse_all_jsons(archive_path, mods_index, progress_cb=parse_cb)

    _cb(0.72, f"Saving raw cache ({len(raw_entries)} entries)...")
    raw_cache_path = data_dir / "raw_cache.json"
    print(f"\nSaving raw_cache.json ({len(raw_entries)} entries)...")
    raw_cache = {
        "generated": datetime.now().isoformat(),
        "total_entries": len(raw_entries),
        "entries": raw_entries,
    }
    try:
        with open(raw_cache_path, 'w', encoding='utf-8') as f:
            json.dump(raw_cache, f, indent=2)
    except Exception as e:
        print(f"Warning: could not write raw_cache.json: {e}")

    _cb(0.80, "Unifying to canonical names...")
    print("\nUnifying to canonical names...")
    prices = unify_entries(raw_entries, mods)

    _cb(0.90, "Estimating missing prices...")
    print("\nEstimating prices for missing mods...")
    prices = estimate_missing_prices(prices, mods)

    by_star = defaultdict(int)
    for p in prices.values():
        by_star[p["star"]] += 1

    _cb(0.96, "Saving price cache...")
    print(f"\nSaving price_cache.json ({len(prices)} entries)...")
    price_cache = {
        "generated": datetime.now().isoformat(),
        "stats": {
            "total_entries": len(raw_entries),
            "unique_mods": len(prices),
            "by_star": dict(by_star),
        },
        "prices": prices,
    }
    try:
        with open(price_cache_path, 'w', encoding='utf-8') as f:
            json.dump(price_cache, f, indent=2)
    except Exception as e:
        print(f"Warning: could not write price_cache.json: {e}")

    print(f"\nParsed {len(prices)} mods: 1*={by_star[1]}, 2*={by_star[2]}, 3*={by_star[3]}, 4*={by_star[4]}")
    _cb(1.0, f"Done — {len(prices)} mods parsed")
    return prices

def clear_caches(data_dir: Path) -> bool:
    """Clear price and raw cache files."""
    cleared = []
    errors = []

    for cache_name in ["price_cache.json", "raw_cache.json"]:
        cache_path = data_dir / cache_name
        if cache_path.exists():
            try:
                cache_path.unlink()
                cleared.append(cache_name)
            except Exception as e:
                errors.append(f"{cache_name}: {e}")
        else:
            errors.append(f"{cache_name}: not found")

    if cleared:
        print(f"Cleared caches: {', '.join(cleared)}")
    if errors:
        for err in errors:
            if "not found" not in err:
                print(f"Error clearing cache: {err}")
    return len(cleared) > 0

# ============================================================================
# COLLECTION LOADER - Uses CANONICAL matching
# ============================================================================

def load_collection_with_canonical(mods: Dict[str, List[int]], name_lookup: Dict[str, str], game_path: str) -> List[CollItem]:
    """
    Load collection from game INI files using CANONICAL mod names.
    Star tier is read from the ¬ prefix count on each item's text field.
    Quantities are tracked per (canonical_name, star) — never merged across tiers.
    """
    game_dir = Path(game_path)
    items_ini = game_dir / "ItemsMod.ini"
    leg_ini = game_dir / "LegendaryMods.ini"

    LEGENDARY_MOD_FILTER = 16384
    unmatched_items = []

    def parse_star_and_name(raw_text: str):
        """Count leading ¬ chars for star tier, return (star, clean_name)."""
        star_count = 0
        i = 0
        while i < len(raw_text) and raw_text[i] == '¬':
            star_count += 1
            i += 1
        clean = raw_text[i:].strip()
        return (star_count if star_count > 0 else 1), clean

    # ── Load learned mods from LegendaryMods.ini ────────────────────────────
    learned_mods_raw = set()
    if leg_ini.exists():
        try:
            with open(leg_ini, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for char, cdata in data.get('characterInventories', {}).items():
                for mod in cdata.get('legendaryMods', []):
                    name = mod.get('name', '').strip()
                    if mod.get('isLearned', False):
                        learned_mods_raw.add(name)
            print(f"Loaded {len(learned_mods_raw)} learned mods from LegendaryMods.ini")
        except Exception as e:
            print(f"Error loading LegendaryMods.ini: {e}")
    else:
        print(f"LegendaryMods.ini not found at {leg_ini}")

    # ── Process physical mod cards from ItemsMod.ini ─────────────────────────
    # Key: (canonical_name, star)  →  {'qty': int, 'is_learned': bool}
    card_totals: Dict[tuple, dict] = {}

    if items_ini.exists():
        try:
            with open(items_ini, 'r', encoding='utf-8') as f:
                data = json.load(f)
            raw_item_count = 0
            for char, cdata in data.get('characterInventories', {}).items():
                for itype in ['playerInventory', 'stashInventory']:
                    for item in cdata.get(itype, []):
                        raw_text = item.get('text', '')
                        qty = item.get('count', 0)
                        filter_flag = item.get('filterFlag', 0)
                        is_leg_mod = filter_flag == LEGENDARY_MOD_FILTER

                        if not is_leg_mod or not raw_text:
                            continue

                        raw_item_count += 1

                        # Parse star tier from ¬ prefix — DO NOT strip before reading
                        card_star, clean_name = parse_star_and_name(raw_text)

                        if not clean_name:
                            continue

                        canonical = match_ini_name_to_canonical(clean_name, name_lookup, mods)
                        if not canonical:
                            unmatched_items.append(f"{raw_text!r} (star={card_star})")
                            continue

                        # Validate star against known tiers for this mod
                        supported_stars = mods.get(canonical, [])
                        if supported_stars and card_star not in supported_stars:
                            print(f"  WARNING: {canonical} {card_star}★ not in supported tiers {supported_stars} — skipping")
                            unmatched_items.append(f"{clean_name} ({card_star}★ invalid)")
                            continue

                        # Key on (name, star) so 2★ Luck and 3★ Luck are NEVER merged
                        key = (canonical, card_star)
                        is_learned = canonical.lower() in {m.lower() for m in learned_mods_raw}

                        if key not in card_totals:
                            card_totals[key] = {'qty': 0, 'is_learned': is_learned}
                        card_totals[key]['qty'] += qty
                        if is_learned:
                            card_totals[key]['is_learned'] = True

            print(f"Loaded {raw_item_count} legendary mod cards from ItemsMod.ini")
        except Exception as e:
            print(f"Error loading ItemsMod.ini: {e}")
    else:
        print(f"ItemsMod.ini not found at {items_ini}")

    if unmatched_items:
        print(f"  WARNING: {len(unmatched_items)} items could not be matched:")
        for item in unmatched_items[:5]:
            print(f"    - {item}")

    # ── Build CollItem list from physical cards ──────────────────────────────
    seen_items: set = set()
    coll: List[CollItem] = []

    for (canonical_name, star), info in card_totals.items():
        key = (canonical_name, star)
        seen_items.add(key)
        coll.append(CollItem(canonical_name, star, info['qty'], info['is_learned']))

    # ── Add learned-only entries (no physical cards for that star tier) ───────
    for learned_name in learned_mods_raw:
        canonical = match_ini_name_to_canonical(learned_name, name_lookup, mods)
        if not canonical:
            continue
        for star in mods.get(canonical, []):
            key = (canonical, star)
            if key not in seen_items:
                seen_items.add(key)
                coll.append(CollItem(canonical, star, 0, True))

    print(f"Loaded {len(coll)} collection items (CANONICAL, per-tier)")

    # Debug: show any multi-star mods so we can confirm split is correct
    by_name = defaultdict(list)
    for c in coll:
        by_name[c.name].append((c.star, c.qty, c.learned))
    multi = {k: v for k, v in by_name.items() if len(v) > 1}
    if multi:
        print("  Multi-tier mods (qty per star):")
        for name, tiers in sorted(multi.items()):
            tier_str = ", ".join(f"{s}★:{q}{'(L)' if l else ''}" for s, q, l in sorted(tiers))
            print(f"    {name}: {tier_str}")

    return coll



# ============================================================================
# PNG GENERATOR
# ============================================================================



def gen_text_preview(items: List[TradeItem], profile: dict = None) -> str:
    """Generate text version of the trade post (for copy/debug)."""
    if profile is None:
        profile = PROFILE_DEFAULTS
    ign = profile.get("ign", PROFILE_DEFAULTS["ign"])
    j1  = profile.get("junk_1star", PROFILE_DEFAULTS["junk_1star"])
    j2  = profile.get("junk_2star", PROFILE_DEFAULTS["junk_2star"])
    j3  = profile.get("junk_3star", PROFILE_DEFAULTS["junk_3star"])
    j4  = profile.get("junk_4star", PROFILE_DEFAULTS["junk_4star"])
    c1  = profile.get("craft_1star", PROFILE_DEFAULTS["craft_1star"])
    c2  = profile.get("craft_2star", PROFILE_DEFAULTS["craft_2star"])
    c3  = profile.get("craft_3star", PROFILE_DEFAULTS["craft_3star"])
    c4  = profile.get("craft_4star", PROFILE_DEFAULTS["craft_4star"])
    lines = []
    if ign:
        lines.append(f"IGN: {ign}")
    lines.append(f"Buying Junk Mods (★|{j1}L, ★★|{j2}L, ★★★|{j3}L, ★★★★|{j4}L)")
    lines.append("")

    sorted_items = sorted(items, key=lambda x: (x.stars, x.name.lower()))

    if not sorted_items:
        lines.append("(No items in trade list)")
    else:
        for item in sorted_items:
            s = stars(item.stars)
            name = item.name
            if len(name) > 18:
                name = name[:16] + ".."

            if item.qty == 0:
                qty_str = f"x0|0L ea"
            elif item.mode == "all":
                qty_str = f"x{item.qty}|{item.price}L all"
            else:
                qty_str = f"x{item.qty}|{item.price}L ea"
            txt = f"{s} {name} {qty_str}"

            if item.wtt:
                txt += f"  WTT| {item.wtt}"
            lines.append(txt)

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"White = I have this mod — cannot craft tho  |  Green = Can Craft (1*|{c1}L  2*|{c2}L  3*|{c3}L  4*|{c4}L)  |  Orange = Can Craft but materials cannot be traded")

    return "\n".join(lines)



def draw_stars_row(draw, x, y, count, size, fill_color, spacing):
    """Draw a row of stars centered at x, vertically at y."""
    if count <= 0:
        return
    start_x = x - (count * spacing) // 2
    for i in range(count):
        draw_star(draw, start_x + i * spacing, y, size, fill_color)


def gen_png(items: List[TradeItem], path: str, width: int = 2600, include_junk_mods: bool = True, profile: dict = None) -> Tuple[bool, str]:
    """Generate WTS PNG — fully dynamic layout, consistent pad throughout."""
    if not Image:
        return False, "Pillow not installed"
    if profile is None:
        profile = PROFILE_DEFAULTS
    try:
        # ── Palette (from profile) ────────────────────────────────────────────
        bg          = hex_to_rgb(profile.get("color_bg",     PROFILE_DEFAULTS["color_bg"]))
        _cbr        = hex_to_rgb(profile.get("color_card",   PROFILE_DEFAULTS["color_card"]))
        card_bg     = _cbr
        _br         = tuple(min(255, c + 35) for c in bg)
        border      = _br
        card_border = tuple(min(255, c + 15) for c in _cbr)
        text_color  = hex_to_rgb(profile.get("color_accent", PROFILE_DEFAULTS["color_accent"]))
        gold        = hex_to_rgb(profile.get("color_gold",   PROFILE_DEFAULTS["color_gold"]))
        green_col   = hex_to_rgb(profile.get("color_green",  PROFILE_DEFAULTS["color_green"]))
        orange_col  = hex_to_rgb(profile.get("color_orange", PROFILE_DEFAULTS["color_orange"]))
        dim_white   = text_color
        star_col    = hex_to_rgb(profile.get("color_stars",  PROFILE_DEFAULTS["color_stars"]))
        title_col   = hex_to_rgb(profile.get("color_title",  PROFILE_DEFAULTS["color_title"]))
        notice_col  = hex_to_rgb(profile.get("color_notice", PROFILE_DEFAULTS["color_notice"]))
        junk_col    = hex_to_rgb(profile.get("color_junk_label", PROFILE_DEFAULTS["color_junk_label"]))

        pad           = 50   # ONE padding constant used everywhere
        line_h        = 45
        wtt_h         = 28
        star_size     = 8
        star_spacing  = 18
        star_text_gap = 4

        # ── Fonts ─────────────────────────────────────────────────────────────
        try:
            font           = ImageFont.truetype("arial.ttf",   26)
            font_h         = ImageFont.truetype("arialbd.ttf", 28)
            font_notice    = ImageFont.truetype("arialbd.ttf", 38)
            font_small     = ImageFont.truetype("arial.ttf",   17)
            font_legend    = ImageFont.truetype("arialbd.ttf", 26)
            font_legend_d  = ImageFont.truetype("arial.ttf",   28)
            font_legend_pr = ImageFont.truetype("arialbd.ttf", 28)
        except Exception as e:
            print(f"Font error: {e}")
            font = font_h = font_notice = font_small = font_legend = font_legend_d = font_legend_pr = ImageFont.load_default()

        # ── Pre-measure legend box heights (needs a throw-away draw) ──────────
        _tmp = Image.new('RGB', (100, 100))
        _d   = ImageDraw.Draw(_tmp)
        def _th(txt, f):
            tb = _d.textbbox((0,0), txt, f); return tb[3]-tb[1], tb[1]

        lbl_h,  lbl_off  = _th("Wg", font_legend)
        desc_h, desc_off = _th("Wg", font_legend_d)
        pr_h,   pr_off   = _th("Wg", font_legend_pr)
        row_h    = max(lbl_h, desc_h)

        box_py       = 16
        box_gap      = 10
        sw           = 22
        sw_gap       = 14
        box_h_single = row_h  + box_py * 2
        box_h_green  = row_h  + box_py + 12 + pr_h + box_py
        legend_h     = pad + box_h_single + box_h_green + box_h_single + box_gap * 2 + pad

        # ── Card layout — auto pick cols to make image most square ─────────
        sorted_items = sorted(items, key=lambda x: (x.stars, x.name.lower()))
        num_items    = len(sorted_items)

        card_margin  = 10
        card_h       = line_h + 22      # main content row height
        card_h_fixed = card_h           # single row — WTT not used on WTS cards

        # Header section: pad + WTS title(60) + notice(50) + title(55) + [junk(90)] + separator(1) + pad/2 gap
        header_h  = pad + 60 + 50 + 55
        if include_junk_mods:
            header_h += 90
        header_h += pad // 2   # gap between separator and first card row

        num_cols     = 4
        rows_per_col = math.ceil(num_items / num_cols) if num_items > 0 else 0
        col_w        = (width - pad * 2) // num_cols
        card_w       = col_w
        start_y      = header_h

        if num_items == 0:
            max_content_height = 0
        else:
            rows = math.ceil(num_items / num_cols)
            max_content_height = rows * (card_h_fixed + card_margin)

        # Total height = header + cards + gap before legend + legend
        height = start_y + max_content_height + pad // 2 + legend_h
        height = max(height, 400)

        img  = Image.new('RGB', (width, height), bg)
        draw = ImageDraw.Draw(img)

        # ── Outer border (double line) ─────────────────────────────────────────
        draw.rectangle([0, 0, width-1, height-1], outline=border, width=4)
        draw.rectangle([6, 6, width-7, height-7], outline=(70, 70, 70), width=1)

        # ── Want To Sell title (big white) ───────────────────────────────────
        y = pad
        wts_title = "Want To Sell"
        wts_tb = draw.textbbox((0, 0), wts_title, font=font_notice)
        wts_tw = wts_tb[2] - wts_tb[0]
        draw.text(((width - wts_tw) // 2, y - wts_tb[1]), wts_title, fill=title_col, font=font_notice)
        y += 60

        # ── Read-the-bottom notice (big red + drawn triangles) ──────────────
        notice_txt = "Read the color guide at the bottom"
        ntb = draw.textbbox((0,0), notice_txt, font=font_notice)
        nw  = ntb[2] - ntb[0]
        nh  = ntb[3] - ntb[1]
        nx  = (width - nw) // 2
        ny  = y - ntb[1]
        draw.text((nx, ny), notice_txt, fill=notice_col, font=font_notice)
        tri_size = 14
        tri_cx_l = nx - tri_size * 3
        tri_cx_r = nx + nw + tri_size * 3
        tri_cy   = ny + nh // 2
        draw.polygon([
            (tri_cx_l - tri_size, tri_cy - tri_size),
            (tri_cx_l + tri_size, tri_cy - tri_size),
            (tri_cx_l,            tri_cy + tri_size),
        ], fill=notice_col)
        draw.polygon([
            (tri_cx_r - tri_size, tri_cy - tri_size),
            (tri_cx_r + tri_size, tri_cy - tri_size),
            (tri_cx_r,            tri_cy + tri_size),
        ], fill=notice_col)
        y += 50

        # ── Header ────────────────────────────────────────────────────────────
        ign = profile.get("ign", PROFILE_DEFAULTS["ign"])
        header = f"IGN: {ign}" if ign else ""
        if header:
            tw = draw.textbbox((0,0), header, font=font_h)[2]
            draw.text(((width-tw)//2, y), header, fill=gold, font=font_h)
        y += 55

        # ── Junk Mods line ────────────────────────────────────────────────────
        if include_junk_mods:
            junk_tiers = [
                (1, profile.get("junk_1star", PROFILE_DEFAULTS["junk_1star"]) + "L"),
                (2, profile.get("junk_2star", PROFILE_DEFAULTS["junk_2star"]) + "L"),
                (3, profile.get("junk_3star", PROFILE_DEFAULTS["junk_3star"]) + "L"),
                (4, profile.get("junk_4star", PROFILE_DEFAULTS["junk_4star"]) + "L"),
            ]
            # Line 1 — "Buying Junk Mods" centred, no brackets
            jlabel = "Buying Junk Mods"
            jlw = draw.textbbox((0, 0), jlabel, font=font_h)[2]
            draw.text(((width - jlw) // 2, y), jlabel, fill=junk_col, font=font_h)
            y += 40
            # Line 2 — star/price tiers centred below
            tw2 = 0
            for i,(sc,pt) in enumerate(junk_tiers):
                tw2 += sc*star_spacing + draw.textbbox((0,0),"|"+pt,font=font_h)[2]
                if i < len(junk_tiers)-1:
                    tw2 += draw.textbbox((0,0),", ",font=font_h)[2]
            cx = (width - tw2) // 2
            for i,(sc,pt) in enumerate(junk_tiers):
                for s in range(sc):
                    draw_star(draw, cx+star_spacing//2+s*star_spacing, y+14, star_size+1, star_col)
                cx += sc*star_spacing
                sep = "|"+pt
                draw.text((cx,y), "|", fill=junk_col, font=font_h); pipe_w = draw.textbbox((0,0),"|",font=font_h)[2]; cx += pipe_w
                draw.text((cx,y), pt, fill=text_color, font=font_h); cx += draw.textbbox((0,0),pt,font=font_h)[2]
                if i < len(junk_tiers)-1:
                    draw.text((cx,y),", ",fill=junk_col,font=font_h); cx += draw.textbbox((0,0),", ",font=font_h)[2]
            y += 50

        # Separator sits right after header content, cards start pad//2 below it
        draw.line([(pad, y), (width-pad, y)], fill=border, width=2)

        # ── Mod cards ─────────────────────────────────────────────────────────
        col_y = [start_y] * num_cols

        for i, item in enumerate(sorted_items):
            col = min(i // rows_per_col if rows_per_col > 0 else 0, num_cols-1)
            cy  = col_y[col]
            cx  = pad + col * col_w + card_margin

            draw.rectangle([cx, cy, cx+card_w, cy+card_h_fixed],
                           fill=card_bg, outline=card_border, width=2)

            name = item.name
            display_name = name if len(name) <= 20 else name[:18]+".."
            # Always show qty and price
            qty_str = f"x{item.qty}|0L ea" if item.qty == 0 else (f"x{item.qty}|{item.price}L all" if item.mode=="all" else f"x{item.qty}|{item.price}L ea")
            txt = f"{display_name} {qty_str}".strip()

            star_count = item.stars
            stars_px   = star_count * star_spacing
            gap        = star_text_gap if star_count > 0 else 0
            txt_w      = draw.textbbox((0,0), txt, font=font)[2]
            total_w    = stars_px + gap + sw + sw_gap + txt_w

            # Clamp to card width
            while total_w > card_w - 12 and len(display_name) > 6:
                display_name = display_name[:-3]+".."
                qty_str = f"x{item.qty}|0L ea" if item.qty == 0 else (f"x{item.qty}|{item.price}L all" if item.mode=="all" else f"x{item.qty}|{item.price}L ea")
                txt     = f"{display_name} {qty_str}".strip()
                txt_w   = draw.textbbox((0,0), txt, font=font)[2]
                total_w = stars_px + gap + sw + sw_gap + txt_w

            txt_bbox  = draw.textbbox((0,0), txt, font=font)
            text_h    = txt_bbox[3] - txt_bbox[1]
            content_x = cx + (card_w - total_w) // 2
            # Centre text + stars within the main row (card_h), not the full fixed card
            content_y = cy + (card_h - text_h) // 2 - txt_bbox[1]
            star_mid_y = cy + card_h // 2

            if star_count > 0:
                draw_stars_row(draw, content_x + stars_px//2, star_mid_y,
                               star_count, star_size, star_col, star_spacing)

            if item.craft_untradeable:
                indicator_col = orange_col
            elif item.can_craft:
                indicator_col = green_col
            else:
                indicator_col = text_color

            tx    = content_x + stars_px + gap
            sq_y  = cy + (card_h - sw) // 2
            draw.rectangle([tx, sq_y, tx + sw, sq_y + sw], fill=indicator_col)
            tx += sw + sw_gap

            name_end_idx = len(display_name)
            name_part    = txt[:name_end_idx]
            rest_part    = txt[name_end_idx:]
            if rest_part:
                np_w = draw.textbbox((0,0), name_part, font=font)[2]
                draw.text((tx,      content_y), name_part, fill=text_color, font=font)
                draw.text((tx+np_w, content_y), rest_part, fill=gold,       font=font)
            else:
                draw.text((tx, content_y), txt, fill=text_color, font=font)

            # WTT sits in the lower strip — always reserved, only drawn if present
            if item.wtt:
                wtt_txt = f"WTT| {item.wtt}"
                if len(wtt_txt) > 30: wtt_txt = wtt_txt[:27]+".."
                ww = draw.textbbox((0,0), wtt_txt, font=font_small)[2]
                draw.text((cx+(card_w-ww)//2, cy + card_h + (wtt_h - 17)//2),
                          wtt_txt, fill=(160,160,160), font=font_small)

            col_y[col] = cy + card_h_fixed + card_margin

        # ── Legend — 3 full-width bordered boxes, placed immediately after cards ──
        # Separator sits pad//2 below the tallest column
        grid_bottom = max(col_y)  # actual bottom of card grid
        sep_y       = grid_bottom + pad // 2
        draw.line([(pad, sep_y), (width-pad, sep_y)], fill=border, width=2)

        bx    = pad
        bw    = width - pad * 2
        box_x = bx
        box_px = 30

        lbl_white  = profile.get("label_white",  PROFILE_DEFAULTS["label_white"])
        lbl_green  = profile.get("label_green",  PROFILE_DEFAULTS["label_green"])
        lbl_orange = profile.get("label_orange", PROFILE_DEFAULTS["label_orange"])

        def th(txt, f):
            tb = draw.textbbox((0,0), txt, f)
            return tb[3]-tb[1], tb[1]

        def draw_box_row(by, bh, box_col, label, desc, desc_col):
            draw.rectangle([box_x, by, box_x+bw, by+bh], fill=card_bg, outline=box_col, width=3)
            lbl_h2, lbl_off2 = th("Wg", font_legend)
            content_y = by + (bh - max(lbl_h2, desc_h)) // 2 - lbl_off2
            swatch_y  = by + (bh - sw) // 2 - 2
            lbl_t = label + ":  "
            lbl_w = draw.textbbox((0,0), lbl_t, font=font_legend)[2]
            dw    = draw.textbbox((0,0), desc,  font=font_legend_d)[2]
            total_w2 = sw + sw_gap + lbl_w + dw
            tx = box_x + (bw - total_w2) // 2
            draw.rectangle([tx, swatch_y, tx+sw, swatch_y+sw], fill=box_col)
            tx += sw + sw_gap
            draw.text((tx,       content_y), lbl_t, fill=box_col,  font=font_legend)
            draw.text((tx+lbl_w, content_y), desc,  fill=desc_col, font=font_legend_d)

        # White box
        wy = sep_y + pad // 2
        draw_box_row(wy, box_h_single, text_color,
                     lbl_white, profile.get("desc_white", PROFILE_DEFAULTS["desc_white"]), dim_white)

        # Green box (taller)
        gy = wy + box_h_single + box_gap
        draw.rectangle([box_x, gy, box_x+bw, gy+box_h_green], fill=card_bg, outline=green_col, width=3)

        lbl_h2, lbl_off2 = th("Wg", font_legend)
        line1_y   = gy + box_py - lbl_off2
        lbl_t     = lbl_green + ":  "
        lbl_w     = draw.textbbox((0,0), lbl_t, font=font_legend)[2]
        desc1     = profile.get("desc_green", PROFILE_DEFAULTS["desc_green"])
        desc1_w   = draw.textbbox((0,0), desc1, font=font_legend_d)[2]
        total1_w  = sw + sw_gap + lbl_w + desc1_w
        tx        = box_x + (bw - total1_w) // 2
        swatch1_y = gy + box_py + (row_h - sw) // 2 - 2
        draw.rectangle([tx, swatch1_y, tx+sw, swatch1_y+sw], fill=green_col)
        tx += sw + sw_gap
        draw.text((tx,       line1_y), lbl_t,  fill=green_col, font=font_legend)
        draw.text((tx+lbl_w, line1_y), desc1,  fill=text_color, font=font_legend_d)

        # Price sub-line centered in green box
        star_tiers = [
            (1, profile.get("craft_1star", PROFILE_DEFAULTS["craft_1star"]) + "L"),
            (2, profile.get("craft_2star", PROFILE_DEFAULTS["craft_2star"]) + "L"),
            (3, profile.get("craft_3star", PROFILE_DEFAULTS["craft_3star"]) + "L"),
            (4, profile.get("craft_4star", PROFILE_DEFAULTS["craft_4star"]) + "L"),
        ]
        sep_txts   = ["|"+pt+(", " if i<len(star_tiers)-1 else "") for i,(sc,pt) in enumerate(star_tiers)]
        sub_w = sum(sc*star_spacing + draw.textbbox((0,0),sep_txts[i],font=font_legend_pr)[2]
                    for i,(sc,pt) in enumerate(star_tiers))
        slx        = box_x + (bw - sub_w) // 2
        line2_base = gy + box_py + row_h + 12 - pr_off
        star_cy    = line2_base + pr_h // 2
        for i,(sc,pt) in enumerate(star_tiers):
            for s in range(sc):
                draw_star(draw, slx+star_spacing//2+s*star_spacing, star_cy, star_size+2, star_col)
            slx += sc*star_spacing
            draw.text((slx, line2_base), sep_txts[i], fill=text_color, font=font_legend_pr)
            slx += draw.textbbox((0,0), sep_txts[i], font=font_legend_pr)[2]

        # Orange box
        oy = gy + box_h_green + box_gap
        draw_box_row(oy, box_h_single, orange_col,
                     lbl_orange, profile.get("desc_orange", PROFILE_DEFAULTS["desc_orange"]), dim_white)

        img.save(path, 'PNG')
        return True, path
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)


def gen_wtb_png(items: List[WTBItem], path: str, width: int = 2600, include_junk_mods: bool = True, profile: dict = None) -> Tuple[bool, str]:
    """Generate WTB PNG — styled to match WTS PNG layout."""
    if not Image:
        return False, "Pillow not installed"
    if profile is None:
        profile = PROFILE_DEFAULTS
    try:
        # ── Palette (from profile) ────────────────────────────────────────────
        bg          = hex_to_rgb(profile.get("color_bg",   PROFILE_DEFAULTS["color_bg"]))
        _cbr        = hex_to_rgb(profile.get("color_card", PROFILE_DEFAULTS["color_card"]))
        card_bg     = _cbr
        _br         = tuple(min(255, c + 35) for c in bg)
        border      = _br
        card_border = tuple(min(255, c + 15) for c in _cbr)
        text_color  = hex_to_rgb(profile.get("color_accent",     PROFILE_DEFAULTS["color_accent"]))
        gold        = hex_to_rgb(profile.get("color_gold",       PROFILE_DEFAULTS["color_gold"]))
        star_col    = hex_to_rgb(profile.get("color_stars",      PROFILE_DEFAULTS["color_stars"]))
        title_col   = hex_to_rgb(profile.get("color_title",      PROFILE_DEFAULTS["color_title"]))
        notice_col  = hex_to_rgb(profile.get("color_notice",     PROFILE_DEFAULTS["color_notice"]))
        junk_col    = hex_to_rgb(profile.get("color_junk_label", PROFILE_DEFAULTS["color_junk_label"]))

        pad           = 50
        line_h        = 45
        note_h        = 40          # sized for main font (26pt) — same as main row
        star_size     = 8
        star_spacing  = 18

        # ── Fonts ─────────────────────────────────────────────────────────────
        try:
            font        = ImageFont.truetype("arial.ttf",   26)
            font_h      = ImageFont.truetype("arialbd.ttf", 28)
            font_notice = ImageFont.truetype("arialbd.ttf", 38)
            font_small  = ImageFont.truetype("arial.ttf",   17)
        except Exception as e:
            print(f"Font error: {e}")
            font = font_h = font_notice = font_small = ImageFont.load_default()

        # ── Layout — auto pick cols to make image most square ────────────────
        num_items    = len(items)

        card_margin  = 10
        card_h       = line_h + 22      # main row
        # Determine if any items have notes or WTT so we can size cards correctly
        any_notes = any(bool(it.notes) for it in items)
        any_wtt   = any(bool(it.wtt)   for it in items)
        # Fixed card height: main row + optional note/WTT rows (only if used)
        card_h_fixed = card_h + (note_h if any_notes else 0) + (note_h if any_wtt else 0)
        # notice(50) + title(55) + [junk(90)] + subheader(50) + sep gap
        header_h = pad + 60 + 50 + 55
        if include_junk_mods:
            header_h += 90
        header_h += pad // 2

        legend_h = 80

        num_cols     = 4
        rows_per_col = math.ceil(num_items / num_cols) if num_items > 0 else 0
        col_w        = (width - pad * 2) // num_cols
        card_w       = col_w
        start_y      = header_h

        if num_items == 0:
            max_content_height = 0
        else:
            rows = math.ceil(num_items / num_cols)
            max_content_height = rows * (card_h_fixed + card_margin)

        height = max(start_y + max_content_height + pad // 2 + legend_h, 400)

        img  = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(img)

        # ── Outer border (double line, grey) ──────────────────────────────────
        draw.rectangle([0, 0, width-1, height-1], outline=border, width=4)
        draw.rectangle([6, 6, width-7, height-7], outline=(70, 70, 70), width=1)

        # ── Want To Buy title (big white) ────────────────────────────────────
        y = pad
        wtb_title = "Want To Buy"
        wtb_tb = draw.textbbox((0, 0), wtb_title, font=font_notice)
        wtb_tw = wtb_tb[2] - wtb_tb[0]
        draw.text(((width - wtb_tw) // 2, y - wtb_tb[1]), wtb_title, fill=title_col, font=font_notice)
        y += 60

        # ── Read-the-bottom notice (big red + drawn triangles) ────────────────
        notice_txt = "Read the color guide at the bottom"
        ntb = draw.textbbox((0, 0), notice_txt, font=font_notice)
        nw  = ntb[2] - ntb[0]
        nh  = ntb[3] - ntb[1]
        nx  = (width - nw) // 2
        ny  = y - ntb[1]
        draw.text((nx, ny), notice_txt, fill=notice_col, font=font_notice)
        tri_size = 14
        tri_cx_l = nx - tri_size * 3
        tri_cx_r = nx + nw + tri_size * 3
        tri_cy   = ny + nh // 2
        draw.polygon([
            (tri_cx_l - tri_size, tri_cy - tri_size),
            (tri_cx_l + tri_size, tri_cy - tri_size),
            (tri_cx_l,            tri_cy + tri_size),
        ], fill=notice_col)
        draw.polygon([
            (tri_cx_r - tri_size, tri_cy - tri_size),
            (tri_cx_r + tri_size, tri_cy - tri_size),
            (tri_cx_r,            tri_cy + tri_size),
        ], fill=notice_col)
        y += 50

        # ── Header ────────────────────────────────────────────────────────────
        ign = profile.get("ign", PROFILE_DEFAULTS["ign"])
        header = f"IGN: {ign}" if ign else ""
        if header:
            tw = draw.textbbox((0, 0), header, font=font_h)[2]
            draw.text(((width - tw) // 2, y), header, fill=gold, font=font_h)
        y += 55

        # ── Junk Mods line ────────────────────────────────────────────────────
        if include_junk_mods:
            junk_tiers = [
                (1, profile.get("junk_1star", PROFILE_DEFAULTS["junk_1star"]) + "L"),
                (2, profile.get("junk_2star", PROFILE_DEFAULTS["junk_2star"]) + "L"),
                (3, profile.get("junk_3star", PROFILE_DEFAULTS["junk_3star"]) + "L"),
                (4, profile.get("junk_4star", PROFILE_DEFAULTS["junk_4star"]) + "L"),
            ]
            # Line 1 — "Buying Junk Mods" centred, no brackets
            jlabel = "Buying Junk Mods"
            jlw = draw.textbbox((0, 0), jlabel, font=font_h)[2]
            draw.text(((width - jlw) // 2, y), jlabel, fill=junk_col, font=font_h)
            y += 40
            # Line 2 — star/price tiers centred below
            tw2 = 0
            for i, (sc, pt) in enumerate(junk_tiers):
                tw2 += sc * star_spacing + draw.textbbox((0, 0), "|" + pt, font=font_h)[2]
                if i < len(junk_tiers) - 1:
                    tw2 += draw.textbbox((0, 0), ", ", font=font_h)[2]
            cx = (width - tw2) // 2
            for i, (sc, pt) in enumerate(junk_tiers):
                for s in range(sc):
                    draw_star(draw, cx + star_spacing // 2 + s * star_spacing, y + 14, star_size + 1, star_col)
                cx += sc * star_spacing
                sep = "|" + pt
                draw.text((cx, y), "|", fill=junk_col, font=font_h); pipe_w = draw.textbbox((0, 0), "|", font=font_h)[2]; cx += pipe_w
                draw.text((cx, y), pt, fill=text_color, font=font_h); cx += draw.textbbox((0, 0), pt, font=font_h)[2]
                if i < len(junk_tiers) - 1:
                    draw.text((cx, y), ", ", fill=junk_col, font=font_h); cx += draw.textbbox((0, 0), ", ", font=font_h)[2]
            y += 50

        draw.line([(pad, y), (width - pad, y)], fill=border, width=2)

        # ── WTB cards ─────────────────────────────────────────────────────────
        col_y = [start_y] * num_cols
        star_text_gap = 4

        for i, item in enumerate(items):
            col = min(i // rows_per_col if rows_per_col > 0 else 0, num_cols - 1)
            cy  = col_y[col]
            cx  = pad + col * col_w + card_margin

            draw.rectangle([cx, cy, cx + card_w, cy + card_h_fixed],
                           fill=card_bg, outline=card_border, width=2)

            # ── Build main-row text: name + qty|price ──────────────────────────
            item_name = item.text
            if item.price > 0:
                qty_str = f"x{item.qty}|{item.price}L all" if item.mode == "all" else f"x{item.qty}|{item.price}L ea"
            else:
                qty_str = f"x{item.qty} all" if item.mode == "all" else f"x{item.qty} ea"
            display_name = item_name if len(item_name) <= 20 else item_name[:18] + ".."
            txt          = f"{display_name} {qty_str}".strip()

            star_count = item.stars
            stars_px   = star_count * star_spacing
            gap        = star_text_gap if star_count > 0 else 0
            txt_w      = draw.textbbox((0, 0), txt, font=font)[2]
            total_w    = stars_px + gap + txt_w

            while total_w > card_w - 12 and len(display_name) > 6:
                display_name = display_name[:-3] + ".."
                txt          = f"{display_name} {qty_str}".strip()
                txt_w        = draw.textbbox((0, 0), txt, font=font)[2]
                total_w      = stars_px + gap + txt_w

            # ── Calculate actual content block height to centre it ─────────────
            has_notes = bool(item.notes)
            has_wtt   = bool(item.wtt)
            block_h   = card_h + (note_h if has_notes else 0) + (note_h if has_wtt else 0)
            block_top = cy + (card_h_fixed - block_h) // 2

            # ── Main row ──────────────────────────────────────────────────────
            txt_bbox  = draw.textbbox((0, 0), txt, font=font)
            text_h    = txt_bbox[3] - txt_bbox[1]
            content_x = cx + (card_w - total_w) // 2
            content_y = block_top + (card_h - text_h) // 2 - txt_bbox[1]

            if star_count > 0:
                draw_stars_row(draw, content_x + stars_px // 2, block_top + card_h // 2,
                               star_count, star_size, star_col, star_spacing)

            tx = content_x + stars_px + gap

            name_part = txt[:len(display_name)]
            rest_part = txt[len(display_name):]
            if rest_part:
                np_w = draw.textbbox((0, 0), name_part, font=font)[2]
                draw.text((tx,        content_y), name_part, fill=text_color, font=font)
                draw.text((tx + np_w, content_y), rest_part, fill=gold,       font=font)
            else:
                draw.text((tx, content_y), txt, fill=text_color, font=font)

            # ── Notes sub-row — same font as main row ─────────────────────────
            sub_y = block_top + card_h
            if has_notes:
                nt  = f"({item.notes})"
                if len(nt) > 28: nt = nt[:25] + ".."
                nw2   = draw.textbbox((0, 0), nt, font=font)[2]
                ntb2  = draw.textbbox((0, 0), nt, font=font)
                nt_h  = ntb2[3] - ntb2[1]
                draw.text((cx + (card_w - nw2) // 2, sub_y + (note_h - nt_h) // 2 - ntb2[1]),
                          nt, fill=(160, 160, 160), font=font)
                sub_y += note_h

            # ── WTT sub-row — same font as main row ───────────────────────────
            if has_wtt:
                wtt_sc      = item.wtt_stars
                wtt_spx     = wtt_sc * star_spacing
                # Always leave a gap after stars so name doesn't collide
                wtt_star_gap = star_text_gap + 4 if wtt_sc > 0 else 0
                wtt_qty_str = f"x{item.wtt_qty} all" if item.wtt_mode == "all" else f"x{item.wtt_qty} ea"
                wtt_prefix  = "WTT| "
                wtt_suffix  = f"{item.wtt} {wtt_qty_str}".strip()
                if len(wtt_prefix + wtt_suffix) > 28:
                    wtt_suffix = wtt_suffix[:25 - len(wtt_prefix)] + ".."
                wtt_pfx_w    = draw.textbbox((0, 0), wtt_prefix, font=font)[2]
                wtt_pre_gap  = 6 if wtt_sc > 0 else 0   # space between "WTT| " text and first star
                wtt_suf_b    = draw.textbbox((0, 0), wtt_suffix, font=font)
                wtt_suf_w    = wtt_suf_b[2]
                wtt_suf_h    = wtt_suf_b[3] - wtt_suf_b[1]
                wtt_total_w  = wtt_pfx_w + wtt_pre_gap + wtt_spx + wtt_star_gap + wtt_suf_w
                wtt_cx       = cx + (card_w - wtt_total_w) // 2
                wtt_row_y    = sub_y + (note_h - wtt_suf_h) // 2 - wtt_suf_b[1]
                # Draw "WTT| " prefix
                draw.text((wtt_cx, wtt_row_y), wtt_prefix, fill=(160, 200, 160), font=font)
                wtt_cx += wtt_pfx_w + wtt_pre_gap
                # Draw stars (with gap before them), then gap after, then mod name
                if wtt_sc > 0:
                    draw_stars_row(draw, wtt_cx + wtt_spx // 2,
                                   sub_y + note_h // 2 - 4,
                                   wtt_sc, star_size, star_col, star_spacing)
                wtt_cx += wtt_spx + wtt_star_gap
                # Draw mod name + qty
                draw.text((wtt_cx, wtt_row_y), wtt_suffix, fill=(160, 200, 160), font=font)

            col_y[col] = cy + card_h_fixed + card_margin

        # ── Footer ────────────────────────────────────────────────────────────
        grid_bottom = max(col_y)
        sep_y = grid_bottom + pad // 2
        draw.line([(pad, sep_y), (width - pad, sep_y)], fill=border, width=2)
        msg = "DM me if you have any of these items!"
        mw  = draw.textbbox((0, 0), msg, font=font)[2]
        draw.text(((width - mw) // 2, sep_y + 20), msg, fill=text_color, font=font)

        img.save(path, "PNG")
        return True, path
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)


# ============================================================================
# DROPDOWN VALUE BUILDER
# ============================================================================

def build_starred_values(mods: dict) -> list:
    """
    Returns a flat sorted list of "★★★ ModName" strings — one per name×star combo.
    Sorted by star tier first (1★ → 4★), then alphabetically within each tier.
    """
    entries = []
    # Collect all (star, name) pairs first so we can sort by star then name
    pairs = []
    for name, star_list in mods.items():
        stars = star_list if isinstance(star_list, list) else [star_list]
        for s in stars:
            pairs.append((s, name))
    pairs.sort(key=lambda x: (x[0], x[1].lower()))
    for s, name in pairs:
        entries.append(f"{'★' * s} {name}")
    return entries

def parse_starred_value(val: str):
    """
    Parse "★★★ ModName" or legacy "ModName ★★★" → (name, stars).
    Falls back to (val, 1) if no stars found.
    """
    val = val.strip()
    # Stars-first format: "★★ ModName"
    if val and val[0] == '★':
        parts = val.split(" ", 1)
        if len(parts) == 2 and all(c == '★' for c in parts[0]):
            return parts[1], len(parts[0])
    # Stars-last format (legacy): "ModName ★★"
    parts = val.rsplit(" ", 1)
    if len(parts) == 2 and all(c == '★' for c in parts[1]):
        return parts[0], len(parts[1])
    return val, 1

# ============================================================================
# SEARCHABLE DROPDOWN WIDGET
# ============================================================================

class SearchableDropdown(ctk.CTkFrame):
    """
    A search-as-you-type dropdown.
    Shows a CTkEntry; as the user types, a Listbox pops up below showing up to
    12 matching options.  Clicking an option or pressing Enter commits it.
    on_select(value) is called whenever the value changes.
    """
    def __init__(self, master, values: list, on_select=None,
                 font=("", 14), entry_height=38, colors: dict = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._all_values  = list(values)
        self._on_select   = on_select
        self._font        = font
        self._listbox_open = False
        self._colors      = colors or {}  # {value: fg_color}

        # ── Entry ─────────────────────────────────────────────────────────────
        self._var = tk.StringVar()
        self._var.trace_add("write", self._on_type)

        self.entry = ctk.CTkEntry(self, textvariable=self._var,
                                   font=font, height=entry_height)
        self.entry.pack(fill="x")

        # ── Listbox (lives in a Toplevel so it overlays other widgets) ─────────
        self._popup     = None
        self._listbox   = None

        self.entry.bind("<Down>",        self._focus_list)
        self.entry.bind("<Return>",      self._on_entry_return)
        self.entry.bind("<Escape>",      lambda e: self._close_popup())
        self.entry.bind("<FocusOut>",    self._on_focus_out)
        self.entry.bind("<FocusIn>",     self._on_focus_in)
        # Also open on click even when the entry is already focused
        self.entry.bind("<Button-1>",    self._on_click)

    # ── Public API ────────────────────────────────────────────────────────────
    def get(self) -> str:
        return self._var.get()

    def set(self, value: str):
        self._var.set(value)
        self._close_popup()

    # ── Internal ──────────────────────────────────────────────────────────────
    def _filtered(self) -> list:
        q = self._var.get().lower()
        if not q:
            return self._all_values  # show every mod when field is empty
        return [v for v in self._all_values if q in v.lower()]

    def _on_type(self, *_):
        matches = self._filtered()
        if matches:
            self._open_popup(matches)
        else:
            self._close_popup()

    def _open_popup(self, matches: list):
        self.entry.update_idletasks()
        ex = self.entry.winfo_rootx()
        ey = self.entry.winfo_rooty() + self.entry.winfo_height()
        ew = max(self.entry.winfo_width(), 500)   # at least 500px wide

        visible = min(12, len(matches))
        row_h   = 26
        lb_h    = visible * row_h + 4

        if self._popup is None:
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            self._popup.configure(bg="#2b2b2b")
            self._listbox = tk.Listbox(
                self._popup,
                font=self._font,
                bg="#2b2b2b", fg="white",
                selectbackground="#5865F2", selectforeground="white",
                activestyle="none",
                relief="flat", bd=0,
                highlightthickness=1, highlightbackground="#555",
            )
            self._listbox.pack(fill="both", expand=True)
            self._listbox.bind("<ButtonRelease-1>", self._on_listbox_click)
            self._listbox.bind("<Return>",          self._on_listbox_return)
            self._listbox.bind("<Escape>",          lambda e: self._close_popup())
            self._listbox.bind("<FocusOut>",        self._on_focus_out)
            self._listbox_open = True

        self._popup.geometry(f"{ew}x{lb_h}+{ex}+{ey}")
        self._popup.lift()

        self._listbox.delete(0, tk.END)
        for m in matches[:200]:
            self._listbox.insert(tk.END, m)
            if self._colors:
                # Strip leading stars to look up by mod name
                key = m
                color = self._colors.get(key, "white")
                self._listbox.itemconfig(tk.END, foreground=color)

    def _close_popup(self):
        if self._popup:
            self._popup.destroy()
            self._popup   = None
            self._listbox = None
            self._listbox_open = False

    def _commit(self, value: str):
        self._var.set(value)
        self._close_popup()
        if self._on_select:
            self._on_select(value)

    def _focus_list(self, event=None):
        if self._listbox:
            self._listbox.focus_set()
            if self._listbox.size() > 0:
                self._listbox.selection_set(0)
                self._listbox.activate(0)

    def _on_entry_return(self, event=None):
        matches = self._filtered()
        if matches:
            self._commit(matches[0])

    def _on_listbox_click(self, event=None):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel:
                self._commit(self._listbox.get(sel[0]))

    def _on_listbox_return(self, event=None):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel:
                self._commit(self._listbox.get(sel[0]))

    def _on_focus_in(self, event=None):
        # Select all text so typing immediately replaces it
        def _sel():
            try:
                self.entry._entry.select_range(0, "end")
                self.entry._entry.icursor("end")
            except Exception:
                pass
        self.entry.after(10, _sel)
        # Always open with the full list immediately on focus
        self._open_popup(self._all_values)

    def _on_click(self, event=None):
        """Re-open dropdown when clicking an already-focused entry."""
        def _do():
            try:
                self.entry._entry.select_range(0, "end")
                self.entry._entry.icursor("end")
            except Exception:
                pass
            self._open_popup(self._all_values)
        self.entry.after(10, _do)

    def _on_focus_out(self, event=None):
        # Delay so a click on the listbox isn't swallowed
        self.after(150, self._check_focus)

    def _check_focus(self):
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        if self._listbox and focused == self._listbox:
            return
        self._close_popup()


# ============================================================================
# DIALOG
# ============================================================================

class WTBDialog(ctk.CTkToplevel):
    """Dialog for adding/editing Want To Buy items — compact, starred dropdowns."""
    def __init__(self, parent, item=None, coll=None, mods=None, profile=None):
        super().__init__(parent)

        self.result = None
        self.mods   = mods or {}

        self.title("Add WTB Item" if not item else "Edit WTB Item")
        self.geometry("680x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-680)//2}+{(sh-500)//2}")

        # Starred dropdown lists for both WTB and WTT
        starred = build_starred_values(self.mods) if self.mods else []

        # Build color lookup matching WTS color scheme
        p = profile or {}
        col_green  = p.get("color_green",  "#64DC64")
        col_orange = p.get("color_orange", "#FFA500")
        col_white  = p.get("color_accent", "#FFFFFF")
        learned = {c.name for c in (coll or []) if c.learned}
        mod_colors = {}
        for name, star_list in self.mods.items():
            stars = star_list if isinstance(star_list, list) else [star_list]
            for s in sorted(stars):
                key = f"{'★' * s} {name}"
                if name in UNTRADEABLE_MATERIAL_MODS:
                    mod_colors[key] = col_orange
                elif name in learned:
                    mod_colors[key] = col_green
                else:
                    mod_colors[key] = col_white

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=28, pady=18)

        ctk.CTkLabel(outer,
            text="Add WTB Item" if not item else "Edit WTB Item",
            font=("", 20, "bold")).pack(anchor="w", pady=(0, 10))

        grid = ctk.CTkFrame(outer, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=0, minsize=148)
        grid.columnconfigure(1, weight=1)

        def lbl(row, text):
            ctk.CTkLabel(grid, text=text, font=("", 14), anchor="e",
                         width=148).grid(row=row, column=0, sticky="e", padx=(0, 12), pady=5)

        # ── Looking For (starred dropdown + optional free-text) ───────────────
        lbl(0, "Looking For:")
        lf_frame = ctk.CTkFrame(grid, fg_color="transparent")
        lf_frame.grid(row=0, column=1, sticky="ew", pady=5)
        lf_frame.columnconfigure(0, weight=1)
        initial_wtb = f"{'\u2605' * item.stars} {item.text}" if item else ""
        self.text_search = SearchableDropdown(
            lf_frame, values=starred, font=("Consolas", 14), entry_height=36,
            on_select=lambda v: None, colors=mod_colors)
        self.text_search.set(initial_wtb)
        self.text_search.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(lf_frame, text="or:", font=("", 11), text_color="gray").grid(row=0, column=1, padx=(0, 4))
        self.text_custom = ctk.CTkEntry(lf_frame, font=("", 14), height=36, width=130,
                                         placeholder_text="free text…")
        self.text_custom.grid(row=0, column=2)

        # ── Qty / Mode / Price ────────────────────────────────────────────────
        lbl(1, "Qty / Mode:")
        qm_row = ctk.CTkFrame(grid, fg_color="transparent")
        qm_row.grid(row=1, column=1, sticky="w", pady=5)
        self.qty_entry = ctk.CTkEntry(qm_row, font=("", 14), height=34, width=70)
        self.qty_entry.insert(0, str(item.qty) if item else "1")
        self.qty_entry.pack(side="left", padx=(0, 6))
        self.mode_combo = ctk.CTkComboBox(qm_row, values=["each", "all"],
                                           font=("", 14), height=34, width=95, state="readonly")
        self.mode_combo.set(item.mode if item else "each")
        self.mode_combo.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(qm_row, text="Price (L):", font=("", 13)).pack(side="left", padx=(0, 6))
        self.price_entry = ctk.CTkEntry(qm_row, font=("", 14), height=34, width=100)
        self.price_entry.insert(0, str(item.price) if item else "0")
        self.price_entry.pack(side="left")

        # ── Notes ─────────────────────────────────────────────────────────────
        lbl(2, "Notes:")
        self.notes_entry = ctk.CTkEntry(grid, font=("", 14), height=34)
        self.notes_entry.insert(0, item.notes if item else "")
        self.notes_entry.grid(row=2, column=1, sticky="ew", pady=5)

        # ── WTT Section ───────────────────────────────────────────────────────
        ctk.CTkFrame(grid, height=2, fg_color="#555555").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 2))
        ctk.CTkLabel(grid, text="Want To Trade  (optional)", font=("", 12, "bold"),
                     text_color="#AAAAAA").grid(row=4, column=0, columnspan=2, pady=(0, 2))

        lbl(5, "WTT Mod:")
        initial_wtt = f"{'★' * item.wtt_stars} {item.wtt}" if (item and item.wtt) else ""
        self.wtt_search = SearchableDropdown(
            grid, values=starred, font=("Consolas", 13), entry_height=34,
            on_select=lambda v: None, colors=mod_colors)
        self.wtt_search.set(initial_wtt)
        self.wtt_search.grid(row=5, column=1, sticky="ew", pady=5)

        lbl(6, "WTT Qty / Mode:")
        wtt_qm_row = ctk.CTkFrame(grid, fg_color="transparent")
        wtt_qm_row.grid(row=6, column=1, sticky="w", pady=5)
        self.wtt_qty_entry = ctk.CTkEntry(wtt_qm_row, font=("", 14), height=34, width=70)
        self.wtt_qty_entry.insert(0, str(item.wtt_qty) if item else "1")
        self.wtt_qty_entry.pack(side="left", padx=(0, 6))
        self.wtt_mode_combo = ctk.CTkComboBox(wtt_qm_row, values=["each", "all"],
                                               font=("", 14), height=34, width=95, state="readonly")
        self.wtt_mode_combo.set(item.wtt_mode if item else "each")
        self.wtt_mode_combo.pack(side="left")

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(pady=(14, 0))
        ctk.CTkButton(btn_row, text="✔  Save", command=self._ok,
                      width=150, height=42, font=("", 15, "bold"),
                      fg_color="#5865F2", hover_color="#4752C4").pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="✖  Cancel", command=self._cancel,
                      width=150, height=42, font=("", 15),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=10)

        self.text_search.entry.focus()
        self.wait_window()

    def _ok(self):
        try:
            # Looking For: parse starred dropdown first, fall back to free text
            raw = self.text_custom.get().strip() or self.text_search.get().strip()
            if not raw:
                messagebox.showerror("Error", "Please enter what you're looking for.", parent=self)
                return
            text, stars = parse_starred_value(raw)

            # WTT: parse starred dropdown
            wtt_raw  = self.wtt_search.get().strip()
            wtt, wtt_stars = parse_starred_value(wtt_raw) if wtt_raw else ("", 1)

            self.result = WTBItem(
                text=text,
                stars=stars,
                qty=int(self.qty_entry.get().strip() or 1),
                mode=self.mode_combo.get(),
                price=int(self.price_entry.get().strip() or 0),
                notes=self.notes_entry.get().strip(),
                wtt=wtt,
                wtt_stars=wtt_stars,
                wtt_qty=int(self.wtt_qty_entry.get().strip() or 1),
                wtt_mode=self.wtt_mode_combo.get(),
            )
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}", parent=self)

    def _cancel(self):
        self.result = None
        self.destroy()


class ItemDialog(ctk.CTkToplevel):
    """WTS Add/Edit dialog — mod+stars combined in dropdown, compact."""
    def __init__(self, parent, mods, prices, item=None, coll=None, profile=None):
        super().__init__(parent)

        self.result    = None
        self.mods      = mods
        self.prices    = prices
        self.item_star = item.stars if item else 1
        self.item_name = item.name  if item else ""

        # Build color lookup: {★★ ModName -> color} matching WTS list colors
        p = profile or {}
        col_green  = p.get("color_green",  "#64DC64")
        col_orange = p.get("color_orange", "#FFA500")
        col_white  = p.get("color_accent", "#FFFFFF")
        learned = {c.name for c in (coll or []) if c.learned}
        self._mod_colors = {}
        for name, star_list in (mods or {}).items():
            stars = star_list if isinstance(star_list, list) else [star_list]
            for s in sorted(stars):
                key = f"{'★' * s} {name}"
                if name in UNTRADEABLE_MATERIAL_MODS:
                    self._mod_colors[key] = col_orange
                elif name in learned:
                    self._mod_colors[key] = col_green
                else:
                    self._mod_colors[key] = col_white

        self.title("Add WTS Item" if not item else "Edit WTS Item")
        self.geometry("620x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-620)//2}+{(sh-320)//2}")

        # Dropdown values: "ModName ★★★" — one entry per name×star tier
        starred_values = build_starred_values(mods) if mods else []
        # Pre-select the current item's combo
        initial = f"{'★' * item.stars} {item.name}" if item else (starred_values[0] if starred_values else "")

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=28, pady=20)

        ctk.CTkLabel(outer,
            text="Add WTS Item" if not item else "Edit WTS Item",
            font=("", 20, "bold")).pack(anchor="w", pady=(0, 12))

        grid = ctk.CTkFrame(outer, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=0, minsize=110)
        grid.columnconfigure(1, weight=1)

        def lbl(row, text):
            ctk.CTkLabel(grid, text=text, font=("", 14), anchor="e",
                         width=110).grid(row=row, column=0, sticky="e", padx=(0, 12), pady=6)

        # Mod + Stars — single starred dropdown
        lbl(0, "Mod:")
        self.name_search = SearchableDropdown(
            grid, values=starred_values, on_select=self._on_mod_change,
            font=("Consolas", 14), entry_height=36, colors=self._mod_colors)
        self.name_search.set(initial)
        self.name_search.grid(row=0, column=1, sticky="ew", pady=6)

        # Qty + Mode + Price on one compact row
        lbl(1, "Qty / Mode:")
        qrow = ctk.CTkFrame(grid, fg_color="transparent")
        qrow.grid(row=1, column=1, sticky="w", pady=6)
        self.qty_entry = ctk.CTkEntry(qrow, font=("", 14), height=34, width=70)
        self.qty_entry.insert(0, str(item.qty) if item else "1")
        self.qty_entry.pack(side="left", padx=(0, 6))
        self.mode_combo = ctk.CTkComboBox(qrow, values=["each", "all"],
                                           font=("", 14), height=34, width=95, state="readonly")
        self.mode_combo.set(item.mode if item else "each")
        self.mode_combo.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(qrow, text="Price (L):", font=("", 13)).pack(side="left", padx=(0, 6))
        self.price_entry = ctk.CTkEntry(qrow, font=("", 14), height=34, width=100)
        self.price_entry.insert(0, str(item.price) if item else "0")
        self.price_entry.pack(side="left", padx=(0, 8))
        self.price_hint = ctk.CTkLabel(qrow, text="", font=("", 11), text_color="#64DC64")
        self.price_hint.pack(side="left")

        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(pady=(16, 0))
        ctk.CTkButton(btn_row, text="✔  Save", command=self._ok,
                      width=150, height=42, font=("", 15, "bold"),
                      fg_color="#5865F2", hover_color="#4752C4").pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="✖  Cancel", command=self._cancel,
                      width=150, height=42, font=("", 15),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=10)

        self._on_mod_change(initial)
        self.name_search.entry.focus()
        self.wait_window()

    def _on_mod_change(self, val):
        name, stars = parse_starred_value(val)
        self.item_name = name
        self.item_star = stars
        self._suggest_price()

    def _suggest_price(self):
        key = f"{self.item_name}_{self.item_star}"
        pd  = self.prices.get(key)
        if pd and pd.median > 0 and not pd.estimated:
            self.price_entry.delete(0, "end")
            self.price_entry.insert(0, str(int(pd.median)))
            self.price_hint.configure(text=f"≈{int(pd.median)}L")
        else:
            self.price_hint.configure(text="")

    def _ok(self):
        try:
            raw = self.name_search.get().strip()
            name, stars = parse_starred_value(raw)
            if not name:
                messagebox.showerror("Error", "Please select a mod.", parent=self)
                return
            self.result = TradeItem(
                stars=stars,
                name=name,
                qty=int(self.qty_entry.get().strip() or 1),
                price=int(self.price_entry.get().strip() or 0),
                mode=self.mode_combo.get(),
                wtt="",
                craft_untradeable=name in UNTRADEABLE_MATERIAL_MODS
            )
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}", parent=self)

    def _cancel(self):
        self.result = None
        self.destroy()

# ============================================================================
# MAIN APP
# ============================================================================

class App(ctk.CTk):
    def __init__(self, pending_nxm=None):
        super().__init__()
        
        self.settings = self._load_settings()
        self._apply_data_dir()   # update DATA_DIR global from settings immediately
        self.mods = {}
        self.prices = {}
        self.coll = []
        self.wts = []  # Want To Sell items
        self.wtb = []  # Want To Buy items
        self._nexus_mod_widgets = {}  # populated by _build_settings → must exist before _build_dash
        self._nxm_pending_mod   = {}  # mod_def waiting for NXM link keyed by mod_id

        # Toggle for showing "Buying Junk Mods" line (default True)
        self.show_junk_mods = self.settings.get("show_junk_mods", True)
        
        self.title("F76 Price Guide")
        self.geometry("1500x950")
        
        self._build_ui()

        # Register nxm:// protocol handler in Windows registry (silent, no admin needed)
        threading.Thread(target=nxm_register_handler, daemon=True).start()

        # Start local NXM listener so browser-triggered downloads reach us
        self._nxm_server = nxm_start_listener(self._on_nxm_received)

        # Process any NXM link passed on the command line (rare — usually forwarded)
        for url in (pending_nxm or []):
            self.after(500, lambda u=url: self._on_nxm_received(u))

        # Bootstrap inventOmaticStashConfig.json if needed
        self.after(100, self._bootstrap_inventomatic_config)
        # Auto-load price cache on startup if it exists
        self.after(200, self._try_load_cache_on_startup)
    
    def _bootstrap_inventomatic_config(self):
        """On startup: if InventOmatic ba2 is installed but config is missing, write it.
        Also syncs inventOmaticStashConfig.json from the Data folder if present.
        This is silent — no dialogs, just ensures the config is always present."""
        game_root = Path(self.settings.get("game_root", detect_game_root()))
        if not game_root or not game_root.exists():
            return  # game root not configured yet — skip silently during init
        config_dst = game_root / "Data" / "inventOmaticStashConfig.json"
        ba2_present = (game_root / "Data" / "InventOmaticStash.ba2").exists()

        # On startup, always sync inventOmaticStashConfig.json from the install
        # Data folder so any changes made there take effect immediately.
        if ba2_present:
            src_cfg = DATA_DIR / "inventOmaticStashConfig.json"
            if src_cfg.exists() and src_cfg.resolve() != config_dst.resolve():
                try:
                    shutil.copy2(src_cfg, config_dst)
                    print(f"Bootstrap: synced config from Data folder → {config_dst}")
                except Exception as e:
                    print(f"Bootstrap: config sync failed: {e}")
            elif not config_dst.exists():
                try:
                    self._write_inventomatic_config(config_dst, game_root)
                    print(f"Bootstrap: wrote inventOmaticStashConfig.json → {config_dst}")
                except Exception as e:
                    print(f"Bootstrap config write failed: {e}")

    def _try_load_cache_on_startup(self):
        """Auto-load price cache on startup if it already exists — no button click needed."""
        cache_path = DATA_DIR / "price_cache.json"
        if not cache_path.exists():
            return  # Nothing cached yet, user must load manually

        self.status.configure(text="Auto-loading cached prices…")
        self._show_progress()
        self._set_progress(0.05, "Reading price cache…")

        def task():
            try:
                game_path = self.settings.get("game_path",
                    str(Path(self.settings.get("game_root", DEFAULT_GAME_ROOT)) / "Data"))

                # Load mods
                self.after(0, lambda: self._set_progress(0.15, "Loading mods…"))
                mods, name_lookup, total = load_mods_from_ini(game_path)
                self.mods = mods
                self.name_lookup = name_lookup
                self.mod_total_entries = total

                # Load prices from cache (fast path — no parsing)
                self.after(0, lambda: self._set_progress(0.45, "Loading cached prices…"))
                raw_prices = load_prices_and_match_to_mods(DATA_DIR, self.mods)
                valid_mods = build_valid_mods_set(self.mods)
                processed = {}
                for key, val in raw_prices.items():
                    name = val.get("name", "")
                    star = val.get("star", 0)
                    if not name or not star:
                        parts = key.rsplit("_", 1)
                        name = name or parts[0]
                        try:
                            star = star or int(parts[1])
                        except (IndexError, ValueError):
                            star = star or 1
                    if (name, star) in valid_mods:
                        processed[f"{name}_{star}"] = PriceData(
                            name=name, star=star,
                            median=val.get("median", 0), low=val.get("low", 0),
                            high=val.get("high", 0), n=val.get("n", 0),
                            estimated=val.get("estimated", False)
                        )
                self.prices = processed

                # Load collection
                self.after(0, lambda: self._set_progress(0.75, "Loading collection…"))
                self.coll = load_collection_with_canonical(self.mods, self.name_lookup, game_path)

                self.after(0, self._update_ui)
                self.after(0, lambda: self.status.configure(text=f"Cache auto-loaded — {len(self.prices)} prices ready"))
            except Exception as e:
                self.after(0, lambda: self.status.configure(text=f"Auto-load failed: {e}"))
                self.after(0, self._hide_progress)

        threading.Thread(target=task, daemon=True).start()

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Migrate old game_path to game_root if needed
                    if "game_path" in settings and "game_root" not in settings:
                        old_path = settings["game_path"]
                        # If it ends with /Data, use parent as root
                        if old_path.replace("\\", "/").endswith("/Data"):
                            settings["game_root"] = winpath(Path(old_path).parent)
                        else:
                            settings["game_root"] = winpath(old_path)
                    # Migrate old json_path (folder) to archive_path (direct .7z file)
                    if "json_path" in settings and "archive_path" not in settings:
                        old_json = settings.pop("json_path")
                        settings["archive_path"] = winpath(Path(old_json) / "ServerData.7z")
                    return settings
        except Exception as e:
            print(f"Warning: failed to load settings ({e}); using defaults")
        # Auto-detect paths on first run
        detected_root = detect_game_root()
        detected_ini = detect_ini_path()
        return {
            "data_dir":      winpath(APP_DIR / "Data"),
            "archive_path":  winpath(APP_DIR / "Data" / "ServerData.7z"),
            "game_root":     detected_root,
            "ini_path":      detected_ini,
            "downloads_path": detect_downloads_path(),
        }
    
    def _save_settings(self):
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            tmp.replace(SETTINGS_FILE)   # atomic on Windows — prevents corruption on crash
        except Exception as e:
            print(f"Warning: failed to save settings: {e}")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _apply_data_dir(self):
        """Update the module-level DATA_DIR global from the current settings.
        Called on startup and whenever settings are saved so all code that
        references DATA_DIR picks up the user's chosen folder immediately."""
        import __main__ as _main_mod
        import sys as _sys
        chosen = self.settings.get("data_dir", "").strip()
        new_dir = Path(chosen) if chosen else APP_DIR / "Data"
        new_dir.mkdir(parents=True, exist_ok=True)
        # Update the global in this module's namespace
        globals()["DATA_DIR"] = new_dir
        # Also update archive_path default if it still points at the old DATA_DIR
        current_archive = self.settings.get("archive_path", "")
        if not current_archive or not Path(current_archive).exists():
            self.settings["archive_path"] = winpath(new_dir / "ServerData.7z")
        print(f"DATA_DIR → {new_dir}")

    def _get_profile(self) -> dict:
        """Return current trade post profile merged with defaults."""
        p = dict(PROFILE_DEFAULTS)
        p.update(self.settings.get("profile", {}))
        return p
    
    def _build_ui(self):
        self.main = ctk.CTkFrame(self)
        self.main.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tabs = ctk.CTkTabview(self.main)
        self.tabs.pack(fill="both", expand=True)
        
        self.tab_dash = self.tabs.add("Dashboard")
        self.tab_prices = self.tabs.add("Price Guide")
        self.tab_trade = self.tabs.add("Trade Post")
        self.tab_settings = self.tabs.add("Settings")
        self.tab_help = self.tabs.add("Help")
        
        self._build_dash()
        self._build_prices()
        self._build_trade()
        self._build_settings()
        self._build_help()
    
    def _build_dash(self):
        f = self.tab_dash

        # Center column
        center = ctk.CTkFrame(f, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # ── Page title ────────────────────────────────────────────────────────
        ctk.CTkLabel(center, text="F76 Price Guide", font=("", 30, "bold")).pack(pady=(0, 4))
        ctk.CTkLabel(center, text="Fallout 76 Legendary Mod Price Guide & Trade Post Manager",
                     font=("", 13), text_color="gray").pack(pady=(0, 18))

        # ── Stats card ────────────────────────────────────────────────────────
        stats_card = ctk.CTkFrame(center, width=860)
        stats_card.pack(pady=(0, 18))
        stats_card.grid_columnconfigure((0,1,2,3), weight=1, minsize=210)

        def stat_cell(col, label_ref):
            cell = ctk.CTkFrame(stats_card, fg_color="transparent")
            cell.grid(row=0, column=col, padx=14, pady=10, sticky="nsew")
            lbl = ctk.CTkLabel(cell, text="—", font=("", 20, "bold"), anchor="center")
            lbl.pack(anchor="center", pady=(8, 1))
            ctk.CTkLabel(cell, text=label_ref, font=("", 11),
                         text_color="gray", anchor="center").pack(anchor="center", pady=(0, 8))
            return lbl

        self.stat_mods   = stat_cell(0, "MODS")
        self.stat_prices = stat_cell(1, "PRICES")
        self.stat_coll   = stat_cell(2, "COLLECTION")
        self.stat_val    = stat_cell(3, "VALUE")

        # ── Load buttons ──────────────────────────────────────────────────────
        ctk.CTkButton(center, text="⟳  Load All Data", command=self._load_all,
                      width=280, height=52, font=("", 18, "bold")).pack(pady=(0, 10))

        row2 = ctk.CTkFrame(center, fg_color="transparent")
        row2.pack()
        ctk.CTkButton(row2, text="Load Collection Only",
                      command=self._load_collection_only,
                      width=196, height=38, font=("", 13)).pack(side="left", padx=6)
        ctk.CTkButton(row2, text="Parse Price Data Only",
                      command=self._parse_discord_only,
                      width=210, height=38, font=("", 13)).pack(side="left", padx=6)

        # ── Status / progress — container always holds space, bar appears inside ──
        ctk.CTkFrame(center, height=16, fg_color="transparent").pack()

        self.status = ctk.CTkLabel(center, text="Click 'Load All Data' to start",
                                   font=("", 14), text_color="gray")
        self.status.pack(pady=(0, 6))

        # Fixed-height container — never changes size, so layout never shifts
        self._prog_container = ctk.CTkFrame(center, fg_color="transparent", height=44, width=520)
        self._prog_container.pack(pady=(0, 6))
        self._prog_container.pack_propagate(False)

        self.progress_pct = ctk.CTkLabel(self._prog_container, text="", font=("", 12), text_color="gray")
        self.progress = ctk.CTkProgressBar(self._prog_container, width=520, height=14)
        self.progress.set(0)
        # Don't pack them yet — they appear on demand

        ctk.CTkFrame(center, height=16, fg_color="transparent").pack()

        # ── Mod installer status card ─────────────────────────────────────────
        mod_card = ctk.CTkFrame(center)
        mod_card.pack(pady=(16, 0), fill="x", padx=160)
        ctk.CTkLabel(mod_card, text="Mod Status",
                     font=("", 13, "bold")).pack(pady=(10, 2))
        self.dash_install_status = ctk.CTkLabel(mod_card, text="",
                                                font=("", 12), text_color="gray")
        self.dash_install_status.pack(pady=(0, 2))
        ctk.CTkLabel(mod_card, text="Manage mods in the Settings tab",
                     font=("", 11), text_color="gray").pack(pady=(0, 10))
        self._refresh_dash_install_status()

    
    def _build_prices(self):
        f = self.tab_prices

        # ── Header bar ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(f)
        hdr.pack(fill="x", padx=14, pady=(14, 6))

        ctk.CTkLabel(hdr, text="Price Guide", font=("", 18, "bold")).pack(side="left", padx=(14, 20), pady=10)

        ctk.CTkLabel(hdr, text="Search:", font=("", 14), text_color="gray").pack(side="left", padx=(0, 6), pady=10)
        self.search = ctk.CTkEntry(hdr, width=260, height=36, font=("", 14),
                                    placeholder_text="Filter by mod name…")
        self.search.pack(side="left", pady=10)
        self.search.bind("<KeyRelease>", self._filter)

        ctk.CTkButton(hdr, text="Export TXT", command=self._export_txt,
                      width=110, height=36, font=("", 13)).pack(side="right", padx=14, pady=10)

        # ── Treeview ──────────────────────────────────────────────────────────
        tf = ctk.CTkFrame(f)
        tf.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#2b2b2b", foreground="white",
                        fieldbackground="#2b2b2b", rowheight=32, font=("", 13))
        style.configure("Treeview.Heading", background="#3b3b3b", foreground="white",
                        font=("", 13, "bold"))
        style.map("Treeview", background=[('selected', '#5865F2')])
        style.configure("TCombobox", fieldbackground="#2b2b2b", background="#3b3b3b",
                        foreground="white", arrowcolor="white")
        style.map("TCombobox", fieldbackground=[('readonly', '#2b2b2b')],
                  background=[('readonly', '#3b3b3b')])

        cols = ("star", "name", "price", "range", "n")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=30)

        self.tree.heading("star",  text="★")
        self.tree.heading("name",  text="Mod Name")
        self.tree.heading("price", text="Price")
        self.tree.heading("range", text="Range")
        self.tree.heading("n",     text="n")

        self.tree.column("star",  width=80,  anchor="center")
        self.tree.column("name",  width=400, anchor="center")
        self.tree.column("price", width=120, anchor="center")
        self.tree.column("range", width=140, anchor="center")
        self.tree.column("n",     width=60,  anchor="center")

        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    
    def _build_trade(self):
        """Build Trade Post tab with WTS/WTB sub-tabs"""
        f = self.tab_trade
        
        # Create sub-tab switcher
        self.trade_tabs = ctk.CTkTabview(f)
        self.trade_tabs.pack(fill="both", expand=True)
        
        self.tab_wts = self.trade_tabs.add("WTS (Selling)")
        self.tab_wtb = self.trade_tabs.add("WTB (Buying)")
        
        # Build WTS tab
        self._build_wts_tab()
        
        # Build WTB tab
        self._build_wtb_tab()
    
    def _build_wts_tab(self):
        """Build WTS (Want To Sell) sub-tab"""
        f = self.tab_wts

        split = ctk.CTkFrame(f, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=12, pady=12)

        # ── Left panel ────────────────────────────────────────────────────────
        left = ctk.CTkFrame(split, width=290)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Want To Sell", font=("", 16, "bold")).pack(
            pady=(14, 8), padx=14, anchor="w")

        # Action buttons — centered so they sit above Sync Collection
        btn_container_wts = ctk.CTkFrame(left, fg_color="transparent")
        btn_container_wts.pack(fill="x", padx=10, pady=(0, 6))
        btn_row = ctk.CTkFrame(btn_container_wts, fg_color="transparent")
        btn_row.pack(anchor="center")
        ctk.CTkButton(btn_row, text="+ Add",  command=self._add_wts,
                      width=82, height=36, font=("", 13)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="✎ Edit", command=self._edit_wts,
                      width=82, height=36, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="✕ Del",  command=self._remove_wts,
                      width=82, height=36, font=("", 13),
                      fg_color="#6b2020", hover_color="#8b2020").pack(side="left")

        ctk.CTkButton(left, text="⟳  Sync Collection", command=self._sync,
                      width=260, height=36, font=("", 13)).pack(padx=10, pady=(0, 8))

        # Listbox
        lb_frame = ctk.CTkFrame(left)
        lb_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.wts_list = tk.Listbox(lb_frame, bg="#1e1e1e", fg="white",
                                    selectbackground="#5865F2", selectforeground="white",
                                    font=("Consolas", 11), bd=0, highlightthickness=0,
                                    activestyle="none")
        sb_wts = ttk.Scrollbar(lb_frame, orient="vertical", command=self.wts_list.yview)
        self.wts_list.configure(yscrollcommand=sb_wts.set)
        self.wts_list.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb_wts.pack(side="right", fill="y", pady=6)
        self.wts_list.bind("<Double-Button-1>", lambda e: self._edit_wts())

        # ── Right panel (preview) ─────────────────────────────────────────────
        right = ctk.CTkFrame(split)
        right.pack(side="left", fill="both", expand=True)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(hdr, text="PNG Preview", font=("", 15, "bold")).pack(side="left")
        ctk.CTkButton(hdr, text="⟳ Refresh", command=self._refresh_wts_preview,
                      width=100, height=32, font=("", 12)).pack(side="right")

        self.wts_preview_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.wts_preview_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.wts_preview_label = tk.Label(self.wts_preview_frame, bg="#1e1e1e")
        self.wts_preview_label.pack(fill="both", expand=True)
        self._wts_resize_job = None
        def _wts_on_configure(e):
            if self._wts_resize_job:
                self.after_cancel(self._wts_resize_job)
            self._wts_resize_job = self.after(300, self._refresh_wts_preview)
        self.wts_preview_frame.bind("<Configure>", _wts_on_configure)

        # ── Bottom action bar ─────────────────────────────────────────────────
        bot = ctk.CTkFrame(f, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(bot, text="💾 Save PNG",   command=self._save_wts_png,
                      width=120, height=38, font=("", 13)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot, text="📋 Copy Text",  command=self._copy_wts,
                      width=120, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot, text="↑ Export",      command=self._export_wts,
                      width=90, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot, text="↓ Import",      command=self._import_wts,
                      width=90, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left")

        self.junk_mods_checkbox_wts = ctk.CTkCheckBox(
            bot, text="Show 'Buying Junk Mods'",
            variable=tk.BooleanVar(value=self.show_junk_mods),
            command=self._on_junk_mods_toggle_wts, font=("", 13))
        self.junk_mods_checkbox_wts.pack(side="right", padx=10)

    
    def _on_junk_mods_toggle_wts(self):
        """Handle toggle of junk mods display for WTS"""
        self.show_junk_mods = self.junk_mods_checkbox_wts.get()
        self.settings["show_junk_mods"] = self.show_junk_mods
        self._save_settings()
        # Update WTB checkbox to match
        self.junk_mods_checkbox_wtb.deselect() if not self.show_junk_mods else self.junk_mods_checkbox_wtb.select()
        self._refresh_wts_preview()
    
    def _build_wtb_tab(self):
        """Build WTB (Want To Buy) sub-tab"""
        f = self.tab_wtb

        split = ctk.CTkFrame(f, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=12, pady=12)

        # ── Left panel ────────────────────────────────────────────────────────
        left = ctk.CTkFrame(split, width=290)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Want To Buy", font=("", 16, "bold")).pack(
            pady=(14, 8), padx=14, anchor="w")

        btn_container_wtb = ctk.CTkFrame(left, fg_color="transparent")
        btn_container_wtb.pack(fill="x", padx=10, pady=(0, 6))
        btn_row = ctk.CTkFrame(btn_container_wtb, fg_color="transparent")
        btn_row.pack(anchor="center")
        ctk.CTkButton(btn_row, text="+ Add",  command=self._add_wtb,
                      width=82, height=36, font=("", 13)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="✎ Edit", command=self._edit_wtb,
                      width=82, height=36, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="✕ Del",  command=self._remove_wtb,
                      width=82, height=36, font=("", 13),
                      fg_color="#6b2020", hover_color="#8b2020").pack(side="left")

        ctk.CTkButton(left, text="✕  Clear All", command=self._clear_wtb,
                      width=260, height=36, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(padx=10, pady=(0, 8))

        lb_frame = ctk.CTkFrame(left)
        lb_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.wtb_list = tk.Listbox(lb_frame, bg="#1e1e1e", fg="white",
                                    selectbackground="#5865F2", selectforeground="white",
                                    font=("Consolas", 11), bd=0, highlightthickness=0,
                                    activestyle="none")
        sb_wtb = ttk.Scrollbar(lb_frame, orient="vertical", command=self.wtb_list.yview)
        self.wtb_list.configure(yscrollcommand=sb_wtb.set)
        self.wtb_list.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb_wtb.pack(side="right", fill="y", pady=6)
        self.wtb_list.bind("<Double-Button-1>", lambda e: self._edit_wtb())

        # ── Right panel (preview) ─────────────────────────────────────────────
        right = ctk.CTkFrame(split)
        right.pack(side="left", fill="both", expand=True)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(hdr, text="PNG Preview", font=("", 15, "bold")).pack(side="left")
        ctk.CTkButton(hdr, text="⟳ Refresh", command=self._refresh_wtb_preview,
                      width=100, height=32, font=("", 12)).pack(side="right")

        self.wtb_preview_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.wtb_preview_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.wtb_preview_label = tk.Label(self.wtb_preview_frame, bg="#1e1e1e")
        self.wtb_preview_label.pack(fill="both", expand=True)
        self._wtb_resize_job = None
        def _wtb_on_configure(e):
            if self._wtb_resize_job:
                self.after_cancel(self._wtb_resize_job)
            self._wtb_resize_job = self.after(300, self._refresh_wtb_preview)
        self.wtb_preview_frame.bind("<Configure>", _wtb_on_configure)

        # ── Bottom action bar ─────────────────────────────────────────────────
        bot = ctk.CTkFrame(f, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(bot, text="💾 Save PNG",   command=self._save_wtb_png,
                      width=120, height=38, font=("", 13)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot, text="📋 Copy Text",  command=self._copy_wtb,
                      width=120, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot, text="↑ Export",      command=self._export_wtb,
                      width=90, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot, text="↓ Import",      command=self._import_wtb,
                      width=90, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left")

        self.junk_mods_checkbox_wtb = ctk.CTkCheckBox(
            bot, text="Show 'Buying Junk Mods'",
            variable=tk.BooleanVar(value=self.show_junk_mods),
            command=self._on_junk_mods_toggle_wtb, font=("", 13))
        self.junk_mods_checkbox_wtb.pack(side="right", padx=10)

    
    def _on_junk_mods_toggle_wtb(self):
        """Handle toggle of junk mods display for WTB"""
        self.show_junk_mods = self.junk_mods_checkbox_wtb.get()
        self.settings["show_junk_mods"] = self.show_junk_mods
        self._save_settings()
        # Update WTS checkbox to match
        self.junk_mods_checkbox_wts.deselect() if not self.show_junk_mods else self.junk_mods_checkbox_wts.select()
        self._refresh_wtb_preview()
    
    # ==================== WTS Methods ====================
    
    def _add_wts(self):
        dlg = ItemDialog(self, self.mods, self.prices, coll=self.coll, profile=self._get_profile())
        if dlg.result:
            self.wts.append(dlg.result)
            self._refresh_wts()
    
    def _edit_wts(self):
        sel = self.wts_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if not hasattr(self, '_wts_sorted') or idx >= len(self._wts_sorted):
            return
        target = self._wts_sorted[idx]
        # Find the actual index in self.wts by identity
        wts_idx = next((i for i, item in enumerate(self.wts) if item is target), None)
        if wts_idx is None:
            return
        dlg = ItemDialog(self, self.mods, self.prices, self.wts[wts_idx], coll=self.coll, profile=self._get_profile())
        if dlg.result:
            self.wts[wts_idx] = dlg.result
            self._refresh_wts()
    
    def _remove_wts(self):
        sel = self.wts_list.curselection()
        if not sel:
            return
        idx = sel[0]
        # _wts_sorted mirrors the Listbox order exactly — use identity (id) to
        # find and remove the correct item from the unsorted self.wts list.
        if not hasattr(self, '_wts_sorted') or idx >= len(self._wts_sorted):
            return
        target = self._wts_sorted[idx]
        # Remove by object identity — safe even if two items share the same name/star
        for i, item in enumerate(self.wts):
            if item is target:
                del self.wts[i]
                break
        self._refresh_wts()
    
    def _refresh_wts(self):
        self.wts_list.delete(0, tk.END)
        # Build sorted view but keep a parallel list so remove uses same order
        self._wts_sorted = sorted(self.wts, key=lambda x: (x.stars, x.name.lower()))

        p = self._get_profile()
        col_green  = p.get("color_green",  "#64DC64")
        col_orange = p.get("color_orange", "#FFA500")
        col_white  = p.get("color_accent", "#FFFFFF")

        for item in self._wts_sorted:
            s = stars_unicode(item.stars)
            if item.qty == 0:
                qty_str = f"x0|0L ea"
            elif item.mode == "all":
                qty_str = f"x{item.qty}|{item.price}L all"
            else:
                qty_str = f"x{item.qty}|{item.price}L ea"
            txt = f"{s} {item.name} {qty_str}"

            self.wts_list.insert(tk.END, txt)
            if item.craft_untradeable:
                self.wts_list.itemconfig(tk.END, foreground=col_orange)
            elif item.can_craft:
                self.wts_list.itemconfig(tk.END, foreground=col_green)
            else:
                self.wts_list.itemconfig(tk.END, foreground=col_white)

        self._refresh_wts_preview()
    
    def _refresh_wts_preview(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        tmp = EXPORT_DIR / "_wts_preview.png"
        ok, msg = gen_png(self.wts, str(tmp), 2600, self.show_junk_mods, profile=self._get_profile())
        if ok:
            try:
                img = Image.open(tmp)
                self.wts_preview_frame.update_idletasks()
                avail_w = self.wts_preview_frame.winfo_width() - 8
                avail_h = self.wts_preview_frame.winfo_height() - 8
                if avail_w < 100: avail_w = 900
                if avail_h < 100: avail_h = 600
                ratio = min(avail_w / img.width, avail_h / img.height)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.wts_preview_label.configure(image=photo, text="")
                self.wts_preview_label.image = photo
            except Exception as e:
                self.wts_preview_label.configure(image="", text=f"Preview error: {e}")
        else:
            self.wts_preview_label.configure(image="", text=f"Error: {msg}")
    
    def _save_wts_png(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
            initialdir=str(EXPORT_DIR),
            initialfile=f"wts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            title="Save WTS PNG"
        )
        if not path:
            return
        ok, msg = gen_png(self.wts, str(path), 2600, self.show_junk_mods, profile=self._get_profile())
        if ok:
            messagebox.showinfo("Saved", f"Saved: {path}")
        else:
            messagebox.showerror("Error", msg)
    
    def _copy_wts(self):
        p = self._get_profile()
        ign = p.get("ign", PROFILE_DEFAULTS["ign"])
        lines = [f"IGN: {ign}"] if ign else []
        lines.append(f"Buying Junk Mods (★|{p['junk_1star']}L, ★★|{p['junk_2star']}L, ★★★|{p['junk_3star']}L, ★★★★|{p['junk_4star']}L)")
        lines.append("")
        for item in sorted(self.wts, key=lambda x: (x.stars, x.name.lower())):
            s = stars_unicode(item.stars)
            if item.qty == 0:
                qty_str = f"x0|0L ea"
            elif item.mode == "all":
                qty_str = f"x{item.qty}|{item.price}L all"
            else:
                qty_str = f"x{item.qty}|{item.price}L ea"
            txt = f"{s} {item.name} {qty_str}"
            lines.append(txt)
        lines.append("")
        lines.append(f"White = I have this mod — cannot craft tho  |  Green = Can Craft (1*|{p['craft_1star']}L  2*|{p['craft_2star']}L  3*|{p['craft_3star']}L  4*|{p['craft_4star']}L)  |  Orange = Can Craft but materials cannot be traded")
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        messagebox.showinfo("Copied", "WTS text copied!")
    
    # ==================== WTB Methods ====================
    
    def _add_wtb(self):
        dlg = WTBDialog(self, coll=self.coll, mods=self.mods, profile=self._get_profile())
        if dlg.result:
            self.wtb.append(dlg.result)
            self._refresh_wtb()
    
    def _edit_wtb(self):
        sel = self.wtb_list.curselection()
        if not sel:
            return
        idx = sel[0]
        dlg = WTBDialog(self, item=self.wtb[idx], coll=self.coll, mods=self.mods, profile=self._get_profile())
        if dlg.result:
            self.wtb[idx] = dlg.result
            self._refresh_wtb()
    
    def _remove_wtb(self):
        sel = self.wtb_list.curselection()
        if sel:
            del self.wtb[sel[0]]
            self._refresh_wtb()
    
    def _clear_wtb(self):
        if messagebox.askyesno("Clear All", "Clear all WTB items?"):
            self.wtb = []
            self._refresh_wtb()
    
    def _refresh_wtb(self):
        self.wtb_list.delete(0, tk.END)
        for item in self.wtb:
            s = stars_unicode(item.stars)
            # Truncate name for list readability
            name = item.text[:20] + ".." if len(item.text) > 20 else item.text
            # Mode at end (match WTS style)
            if item.price > 0:
                qty_str = f"x{item.qty}|{item.price}L all" if item.mode == "all" else f"x{item.qty}|{item.price}L ea"
            else:
                qty_str = f"x{item.qty} all" if item.mode == "all" else f"x{item.qty} ea"
            txt = f"{s} {name} {qty_str}".strip()
            if item.notes:
                note_short = item.notes[:15] + ".." if len(item.notes) > 15 else item.notes
                txt += f" ({note_short})"
            if item.wtt:
                wtt_s   = stars_unicode(item.wtt_stars)
                wtt_name = item.wtt[:12] + ".." if len(item.wtt) > 12 else item.wtt
                wtt_qty_s = "all" if item.wtt_mode == "all" else "ea"
                txt += f"  WTT| {wtt_s} {wtt_name} x{item.wtt_qty} {wtt_qty_s}"
            self.wtb_list.insert(tk.END, txt)
        self._refresh_wtb_preview()
    
    def _refresh_wtb_preview(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        tmp = EXPORT_DIR / "_wtb_preview.png"
        ok, msg = gen_wtb_png(self.wtb, str(tmp), 2600, self.show_junk_mods, profile=self._get_profile())
        if ok:
            try:
                img = Image.open(tmp)
                self.wtb_preview_frame.update_idletasks()
                avail_w = self.wtb_preview_frame.winfo_width() - 8
                avail_h = self.wtb_preview_frame.winfo_height() - 8
                if avail_w < 100: avail_w = 900
                if avail_h < 100: avail_h = 600
                ratio = min(avail_w / img.width, avail_h / img.height)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.wtb_preview_label.configure(image=photo, text="")
                self.wtb_preview_label.image = photo
            except Exception as e:
                self.wtb_preview_label.configure(image="", text=f"Preview error: {e}")
        else:
            self.wtb_preview_label.configure(image="", text=f"Error: {msg}")
    
    def _save_wtb_png(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
            initialdir=str(EXPORT_DIR),
            initialfile=f"wtb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            title="Save WTB PNG"
        )
        if not path:
            return
        ok, msg = gen_wtb_png(self.wtb, str(path), 2600, self.show_junk_mods, profile=self._get_profile())
        if ok:
            messagebox.showinfo("Saved", f"Saved: {path}")
        else:
            messagebox.showerror("Error", msg)
    
    def _copy_wtb(self):
        p = self._get_profile()
        ign = p.get("ign", PROFILE_DEFAULTS["ign"])
        lines = [f"IGN: {ign}"] if ign else []
        lines.append(f"Buying Junk Mods (★|{p['junk_1star']}L, ★★|{p['junk_2star']}L, ★★★|{p['junk_3star']}L, ★★★★|{p['junk_4star']}L)")
        lines.append("")
        lines.append("Looking For:")
        lines.append("")
        for item in self.wtb:
            s = "★" * item.stars
            if item.price > 0:
                qty_str = f"x{item.qty}|{item.price}L all" if item.mode == "all" else f"x{item.qty}|{item.price}L ea"
            else:
                qty_str = f"x{item.qty} all" if item.mode == "all" else f"x{item.qty} ea"
            txt = f"• {s} {item.text} {qty_str}".strip()
            if item.notes:
                txt += f" ({item.notes})"
            if item.wtt:
                wtt_s = "★" * item.wtt_stars
                wtt_qty = f"x{item.wtt_qty} all" if item.wtt_mode == "all" else f"x{item.wtt_qty} ea"
                txt += f"  WTT| {wtt_s} {item.wtt} {wtt_qty}"
            lines.append(txt)
        lines.append("")
        lines.append("DM me if you have any of these!")
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        messagebox.showinfo("Copied", "WTB text copied!")
    
    # ==================== Export/Import Methods ====================
    
    def _export_wts(self):
        """Export WTS list to JSON file"""
        if not self.wts:
            messagebox.showwarning("Warning", "No WTS items to export")
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(EXPORT_DIR),
            initialfile=f"wts_list_{datetime.now().strftime('%Y%m%d')}.json",
            title="Export WTS List"
        )
        
        if not path:
            return
        
        try:
            data = {
                "type": "wts_list",
                "exported": datetime.now().isoformat(),
                "items": [
                    {
                        "stars": item.stars,
                        "name": item.name,
                        "qty": item.qty,
                        "price": item.price,
                        "mode": item.mode,
                        "wtt": item.wtt,
                        "can_craft": item.can_craft
                    }
                    for item in self.wts
                ]
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            messagebox.showinfo("Exported", f"Exported {len(self.wts)} WTS items to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
    
    def _import_wts(self):
        """Import WTS list from JSON file"""
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import WTS List"
        )
        
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("type") != "wts_list":
                messagebox.showerror("Error", "Invalid file format. Expected WTS list.")
                return
            
            items = data.get("items", [])
            if not items:
                messagebox.showwarning("Warning", "No items found in file")
                return
            
            # Ask whether to replace or append
            if self.wts:
                result = messagebox.askyesnocancel("Import", 
                    f"You have {len(self.wts)} existing WTS items.\n\n"
                    "Yes = Replace existing list\n"
                    "No = Append to existing list\n"
                    "Cancel = Abort import")
                
                if result is None:  # Cancel
                    return
                elif result:  # Yes - Replace
                    self.wts = []
            
            count = 0
            for item_data in items:
                try:
                    item = TradeItem(
                        stars=item_data.get("stars", 1),
                        name=item_data.get("name", ""),
                        qty=item_data.get("qty", 1),
                        price=item_data.get("price", 0),
                        mode=item_data.get("mode", "each"),
                        wtt=item_data.get("wtt", ""),
                        can_craft=item_data.get("can_craft", item_data.get("byom", False)),
                        craft_untradeable=item_data.get("name", "") in UNTRADEABLE_MATERIAL_MODS
                    )
                    self.wts.append(item)
                    count += 1
                except Exception as e:
                    print(f"Error importing item: {e}")
            
            self._refresh_wts()
            messagebox.showinfo("Imported", f"Imported {count} WTS items")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {e}")
    
    def _export_wtb(self):
        """Export WTB list to JSON file"""
        if not self.wtb:
            messagebox.showwarning("Warning", "No WTB items to export")
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(EXPORT_DIR),
            initialfile=f"wtb_list_{datetime.now().strftime('%Y%m%d')}.json",
            title="Export WTB List"
        )
        
        if not path:
            return
        
        try:
            data = {
                "type": "wtb_list",
                "exported": datetime.now().isoformat(),
                "items": [
                    {
                        "text": item.text,
                        "stars": item.stars,
                        "qty": item.qty,
                        "mode": item.mode,
                        "price": item.price,
                        "notes": item.notes,
                        "wtt": item.wtt,
                        "wtt_stars": item.wtt_stars,
                        "wtt_qty": item.wtt_qty,
                        "wtt_mode": item.wtt_mode,
                    }
                    for item in self.wtb
                ]
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            messagebox.showinfo("Exported", f"Exported {len(self.wtb)} WTB items to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
    
    def _import_wtb(self):
        """Import WTB list from JSON file"""
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import WTB List"
        )
        
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("type") != "wtb_list":
                messagebox.showerror("Error", "Invalid file format. Expected WTB list.")
                return
            
            items = data.get("items", [])
            if not items:
                messagebox.showwarning("Warning", "No items found in file")
                return
            
            # Ask whether to replace or append
            if self.wtb:
                result = messagebox.askyesnocancel("Import", 
                    f"You have {len(self.wtb)} existing WTB items.\n\n"
                    "Yes = Replace existing list\n"
                    "No = Append to existing list\n"
                    "Cancel = Abort import")
                
                if result is None:  # Cancel
                    return
                elif result:  # Yes - Replace
                    self.wtb = []
            
            count = 0
            for item_data in items:
                try:
                    item = WTBItem(
                        text=item_data.get("text", ""),
                        stars=item_data.get("stars", 1),
                        qty=item_data.get("qty", 1),
                        mode=item_data.get("mode", "each"),
                        price=item_data.get("price", 0),
                        notes=item_data.get("notes", ""),
                        wtt=item_data.get("wtt", ""),
                        wtt_stars=item_data.get("wtt_stars", 1),
                        wtt_qty=item_data.get("wtt_qty", 1),
                        wtt_mode=item_data.get("wtt_mode", "each"),
                    )
                    self.wtb.append(item)
                    count += 1
                except Exception as e:
                    print(f"Error importing item: {e}")
            
            self._refresh_wtb()
            messagebox.showinfo("Imported", f"Imported {count} WTB items")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {e}")
    
    def _build_settings(self):
        f = self.tab_settings

        scroll = ctk.CTkScrollableFrame(f)
        scroll.pack(fill="both", expand=True)
        f = scroll

        def section_header(parent, title, subtitle=None):
            ctk.CTkLabel(parent, text=title, font=("", 17, "bold")).pack(
                anchor="w", padx=18, pady=(16, 0))
            if subtitle:
                ctk.CTkLabel(parent, text=subtitle, font=("", 12),
                             text_color="gray").pack(anchor="w", padx=18, pady=(2, 6))

        def field_row(parent, label, widget_factory):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=5)
            ctk.CTkLabel(row, text=label, font=("", 13), width=200,
                         anchor="w").pack(side="left")
            widget_factory(row)

        ctk.CTkLabel(f, text="Settings", font=("", 26, "bold")).pack(
            pady=(22, 4), anchor="center")
        ctk.CTkLabel(f, text="Configure paths, profile and mod installer.",
                     font=("", 13), text_color="gray").pack(
            anchor="center", pady=(0, 8))
        ctk.CTkButton(f, text="💾  Save Settings", command=self._save,
                      width=220, height=44, font=("", 14, "bold")).pack(pady=(0, 16))

        # ── Game Paths ────────────────────────────────────────────────────────
        pf = ctk.CTkFrame(f)
        pf.pack(fill="x", padx=14, pady=(0, 10))
        section_header(pf, "Game Paths")

        def path_row(parent, label, entry_attr, browse_key):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=5)
            ctk.CTkLabel(row, text=label, font=("", 13), width=200,
                         anchor="w").pack(side="left")
            e = ctk.CTkEntry(row, width=460, height=34, font=("", 13))
            e.pack(side="left", padx=(0, 8))
            ctk.CTkButton(row, text="Browse", width=80, height=34, font=("", 12),
                          fg_color="#4E5058", hover_color="#3a3b40",
                          command=lambda k=browse_key: self._browse(k)).pack(side="left")
            setattr(self, entry_attr, e)
            return e

        er = path_row(pf, "Fallout 76 Game Root:", "game_root_entry", "game_root")
        er.insert(0, winpath(self.settings.get("game_root", detect_game_root())))
        ei = path_row(pf, "Fallout76Custom.ini:", "ini_entry", "ini")
        ei.insert(0, winpath(self.settings.get("ini_path", detect_ini_path())))

        ctk.CTkFrame(pf, height=10, fg_color="transparent").pack()

        # ── Data Paths ────────────────────────────────────────────────────────
        sf = ctk.CTkFrame(f)
        sf.pack(fill="x", padx=14, pady=(0, 10))
        section_header(sf, "Data Paths")

        edd = path_row(sf, "Data Folder:", "data_dir_entry", "data_dir")
        edd.insert(0, self.settings.get("data_dir", winpath(APP_DIR / "Data")))

        ea = path_row(sf, "ServerData.7z Path:", "json_entry", "archive")
        ea.insert(0, self.settings.get("archive_path", winpath(DATA_DIR / "ServerData.7z")))

        edl = path_row(sf, "Downloads Folder:", "downloads_entry", "downloads")
        edl.insert(0, self.settings.get("downloads_path", detect_downloads_path()))

        ctk.CTkFrame(sf, height=10, fg_color="transparent").pack()

        # ── Nexus Mod Manager ─────────────────────────────────────────────────
        nf = ctk.CTkFrame(f)
        nf.pack(fill="x", padx=14, pady=(0, 10))
        section_header(nf, "Nexus Mod Manager",
                       "Download and install mods directly from NexusMods.com. Link your account to enable auto-download.")

        # Account link row
        acct_row = ctk.CTkFrame(nf, fg_color="transparent")
        acct_row.pack(fill="x", padx=18, pady=(6, 2))

        saved_key = self.settings.get("nexus_api_key", "")
        self._nexus_linked = bool(saved_key)

        self.nexus_status_lbl = ctk.CTkLabel(
            acct_row,
            text="✅ Account Linked" if self._nexus_linked else "❌ Not Linked",
            font=("", 13, "bold"),
            text_color="#3ba55c" if self._nexus_linked else "#ed4245"
        )
        self.nexus_status_lbl.pack(side="left", padx=(0, 16))

        ctk.CTkButton(acct_row, text="🔑  Enter API Key", width=170, height=34,
                      font=("", 12), fg_color="#5865F2", hover_color="#3b47b5",
                      command=self._nexus_link_account).pack(side="left", padx=(0, 8))

        if saved_key:
            ctk.CTkButton(acct_row, text="Unlink Account", width=130, height=34,
                          font=("", 12), fg_color="#4E5058", hover_color="#3a3b40",
                          command=self._nexus_unlink_account).pack(side="left")

        # Hidden entry still stored so _nexus_headers() can read it
        self.nexus_api_entry = ctk.CTkEntry(nf, width=0, height=0)
        if saved_key:
            self.nexus_api_entry.insert(0, saved_key)

        hint_row = ctk.CTkFrame(nf, fg_color="transparent")
        hint_row.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkLabel(hint_row,
            text="Click 'Enter API Key' — your browser will open the NexusMods API Access page. "
                 "Generate a Personal API Key there, copy it, and paste it into the dialog. "
                 "Your key is stored only in settings.json on this PC.",
            font=("", 11), text_color="gray", anchor="w", wraplength=780, justify="left").pack(anchor="w")

        # Mod cards
        self._nexus_mod_widgets = {}
        for mod_def in NEXUS_MODS:
            self._build_nexus_mod_card(nf, mod_def)

        ctk.CTkFrame(nf, height=8, fg_color="transparent").pack()

        # ── Cache Management ──────────────────────────────────────────────────
        cf = ctk.CTkFrame(f)
        cf.pack(fill="x", padx=14, pady=(0, 10))
        section_header(cf, "Cache Management",
                       "Clear the price cache to force a fresh parse of your trade data.")
        ctk.CTkButton(cf, text="🗑  Clear Caches", command=self._clear_caches,
                      width=160, height=40, font=("", 13),
                      fg_color="#ed4245", hover_color="#bd2e31").pack(pady=(4, 14))

        # ── Trade Post Profile ────────────────────────────────────────────────
        prf = ctk.CTkFrame(f)
        prf.pack(fill="x", padx=14, pady=(0, 10))
        section_header(prf, "Trade Post Profile",
                       "Customize your IGN, junk prices, crafting prices and PNG colours.")

        p = self._get_profile()

        # IGN
        ign_row = ctk.CTkFrame(prf, fg_color="transparent")
        ign_row.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(ign_row, text="In-Game Name (IGN):", font=("", 13),
                     width=200, anchor="w").pack(side="left")
        self.prof_ign = ctk.CTkEntry(ign_row, width=280, height=34, font=("", 13),
                                      placeholder_text="Your IGN")
        self.prof_ign.insert(0, p.get("ign", ""))
        self.prof_ign.pack(side="left")

        def price_tier_section(parent, title, title_color, keys_labels, store_attr, star_hex=None):
            hdr = ctk.CTkFrame(parent, fg_color="transparent")
            hdr.pack(anchor="w", padx=18, pady=(12, 4))
            ctk.CTkLabel(hdr, text=title, font=("", 13, "bold"),
                         text_color=title_color).pack(side="left")
            tier_row = ctk.CTkFrame(parent, fg_color="transparent")
            tier_row.pack(fill="x", padx=18, pady=(0, 6))
            store = {}
            for key, star_n in keys_labels:
                cell = ctk.CTkFrame(tier_row)
                cell.pack(side="left", padx=6)
                # Star label colored by star_hex (or gray if not set)
                star_str = "★" * star_n
                star_color = star_hex if star_hex else "gray"
                ctk.CTkLabel(cell, text=star_str, font=("", 13),
                             text_color=star_color).pack(pady=(8, 2))
                e = ctk.CTkEntry(cell, width=76, height=32, font=("", 13), justify="center")
                e.insert(0, p.get(key, PROFILE_DEFAULTS[key]))
                e.pack(pady=(0, 2))
                ctk.CTkLabel(cell, text="Leaders", font=("", 10),
                             text_color="gray").pack(pady=(0, 8))
                store[key] = e
            setattr(self, store_attr, store)

        star_hex = p.get("color_stars", PROFILE_DEFAULTS["color_stars"])

        price_tier_section(prf, "Junk Mod Buy Prices", "gray",
            [("junk_1star", 1), ("junk_2star", 2),
             ("junk_3star", 3), ("junk_4star", 4)],
            "prof_junk", star_hex=star_hex)

        price_tier_section(prf, "Crafting Service Prices", p.get("color_green", PROFILE_DEFAULTS["color_green"]),
            [("craft_1star", 1), ("craft_2star", 2),
             ("craft_3star", 3), ("craft_4star", 4)],
            "prof_craft", star_hex=star_hex)

        # ── PNG Colour Palette + Legend Labels (compact grid) ────────────────
        ctk.CTkLabel(prf, text="PNG Colours & Legend",
                     font=("", 13, "bold"), text_color="gray").pack(
            anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(prf,
                     text="Hex colour  ·  Short label shown in bold  ·  Description text after the label",
                     font=("", 11), text_color="gray").pack(anchor="w", padx=18, pady=(0, 6))

        # ── helper: a tiny colour-swatch ──────────────────────────────────────
        def make_color_row(parent, row_idx, color_key, label_key, desc_key,
                           row_label, row_color):
            """Add one legend row (colour + label + description) to parent grid."""
            # row label (e.g. "Color 1 (White)")
            ctk.CTkLabel(parent, text=row_label, font=("", 11), text_color=row_color,
                         width=110, anchor="w").grid(
                row=row_idx, column=0, padx=(8, 4), pady=4, sticky="w")
            # hex entry + swatch
            hex_frame = ctk.CTkFrame(parent, fg_color="transparent")
            hex_frame.grid(row=row_idx, column=1, padx=4, pady=4, sticky="w")
            ce = ctk.CTkEntry(hex_frame, width=84, height=30, font=("", 12), justify="center")
            ce.insert(0, p.get(color_key, PROFILE_DEFAULTS[color_key]))
            ce.pack(side="left", padx=(0, 3))
            swatch = tk.Label(hex_frame, width=2, height=1, relief="flat",
                              bg=p.get(color_key, PROFILE_DEFAULTS[color_key]))
            swatch.pack(side="left")
            self.prof_swatches[color_key] = swatch
            def _upd(event, sw=swatch, en=ce):
                try: sw.configure(bg=en.get().strip())
                except Exception: pass
            ce.bind("<KeyRelease>", _upd)
            self.prof_colors[color_key] = ce
            # label entry
            if label_key:
                le = ctk.CTkEntry(parent, width=120, height=30, font=("", 12))
                le.insert(0, p.get(label_key, PROFILE_DEFAULTS[label_key]))
                le.grid(row=row_idx, column=2, padx=4, pady=4, sticky="w")
                self.prof_labels[label_key] = le
            else:
                ctk.CTkLabel(parent, text="—", font=("", 11),
                             text_color="gray").grid(row=row_idx, column=2, padx=4)
            # description entry
            if desc_key:
                de = ctk.CTkEntry(parent, width=340, height=30, font=("", 11))
                de.insert(0, p.get(desc_key, PROFILE_DEFAULTS[desc_key]))
                de.grid(row=row_idx, column=3, padx=(4, 8), pady=4, sticky="ew")
                self.prof_descs[desc_key] = de
            else:
                ctk.CTkLabel(parent, text="—", font=("", 11),
                             text_color="gray").grid(row=row_idx, column=3, padx=4)

        self.prof_colors   = {}
        self.prof_labels   = {}
        self.prof_descs    = {}
        self.prof_swatches = {}  # {color_key: tk.Label swatch}

        grid = ctk.CTkFrame(prf)
        grid.pack(fill="x", padx=18, pady=(0, 4))
        grid.columnconfigure(3, weight=1)

        # Header labels for columns
        for col, hdr in enumerate(["Legend Row", "Hex Colour", "Bold Label", "Description Text"]):
            ctk.CTkLabel(grid, text=hdr, font=("", 10, "bold"),
                         text_color="gray").grid(row=0, column=col, padx=(8 if col==0 else 4, 4),
                                                  pady=(4, 0), sticky="w")

        # Row 1 – White (Color 1)
        make_color_row(grid, 1, "color_accent", "label_white", "desc_white",
                       "Color 1", "#DDDDDD")
        # Row 2 – Green (Color 2)
        make_color_row(grid, 2, "color_green",  "label_green",  "desc_green",
                       "Color 2", "#DDDDDD")
        # Row 3 – Orange (Color 3)
        make_color_row(grid, 3, "color_orange", "label_orange", "desc_orange",
                       "Color 3", "#DDDDDD")

        # Remaining palette-only colours (no label/desc)
        ctk.CTkLabel(prf, text="Other PNG Colours",
                     font=("", 12, "bold"), text_color="gray").pack(
            anchor="w", padx=18, pady=(10, 4))
        OTHER_COLOR_FIELDS = [
            ("color_bg",         "Background"),
            ("color_card",       "Mod Card"),
            ("color_gold",       "IGN"),
            ("color_stars",      "Stars"),
            ("color_title",      "Title Text"),
            ("color_notice",     "Notice Text"),
            ("color_junk_label", "Buying Junk"),
        ]
        oc_row = ctk.CTkFrame(prf, fg_color="transparent")
        oc_row.pack(fill="x", padx=18, pady=(0, 8))
        for key, label in OTHER_COLOR_FIELDS:
            cell = ctk.CTkFrame(oc_row)
            cell.pack(side="left", padx=4)
            ctk.CTkLabel(cell, text=label, font=("", 11)).pack(pady=(6, 2))
            inner = ctk.CTkFrame(cell, fg_color="transparent")
            inner.pack(pady=(0, 6))
            e = ctk.CTkEntry(inner, width=84, height=30, font=("", 12), justify="center")
            e.insert(0, p.get(key, PROFILE_DEFAULTS[key]))
            e.pack(side="left", padx=(4, 2))
            swatch = tk.Label(inner, width=2, height=1, relief="flat",
                              bg=p.get(key, PROFILE_DEFAULTS[key]))
            swatch.pack(side="left")
            self.prof_swatches[key] = swatch
            def _update_swatch(event, sw=swatch, entry=e):
                try: sw.configure(bg=entry.get().strip())
                except Exception: pass
            e.bind("<KeyRelease>", _update_swatch)
            self.prof_colors[key] = e

        # Reset + Save
        def _reset_profile():
            self.prof_ign.delete(0, "end")
            self.prof_ign.insert(0, PROFILE_DEFAULTS["ign"])
            for key, e in self.prof_junk.items():
                e.delete(0, "end"); e.insert(0, PROFILE_DEFAULTS[key])
            for key, e in self.prof_craft.items():
                e.delete(0, "end"); e.insert(0, PROFILE_DEFAULTS[key])
            for key, e in self.prof_colors.items():
                e.delete(0, "end"); e.insert(0, PROFILE_DEFAULTS[key])
                # Update the colour swatch immediately
                sw = self.prof_swatches.get(key)
                if sw:
                    try: sw.configure(bg=PROFILE_DEFAULTS[key])
                    except Exception: pass
            for key, e in self.prof_labels.items():
                e.delete(0, "end"); e.insert(0, PROFILE_DEFAULTS[key])
            for key, e in self.prof_descs.items():
                e.delete(0, "end"); e.insert(0, PROFILE_DEFAULTS[key])
            # Persist to disk and refresh all live UI immediately
            self._save()

        action_row = ctk.CTkFrame(prf, fg_color="transparent")
        action_row.pack(pady=(10, 16))
        ctk.CTkButton(action_row, text="Reset to Defaults", command=_reset_profile,
                      width=160, height=38, font=("", 13),
                      fg_color="#4E5058", hover_color="#3a3b40").pack(side="left", padx=8)

        ctk.CTkButton(f, text="💾  Save Settings", command=self._save,
                      width=220, height=48, font=("", 15, "bold")).pack(pady=(6, 24))


    # ══════════════════════════════════════════════════════════════════════════
    # NEXUS MOD MANAGER
    # ══════════════════════════════════════════════════════════════════════════

    def _nexus_link_account(self):
        """Link NexusMods account. Tries WebSocket SSO AND shows manual paste — both work."""
        import uuid as _uuid_mod

        sso_id   = str(_uuid_mod.uuid4())
        app_slug = NEXUS_APP_NAME.lower().replace(" ", "-")
        _sso_cancelled = [False]

        # ── Main dialog ───────────────────────────────────────────────────────
        dlg = ctk.CTkToplevel(self)
        dlg.title("Link NexusMods Account")
        dlg.geometry("580x400")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.update_idletasks()
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"+{(sw-580)//2}+{(sh-400)//2}")

        # ── SSO section ───────────────────────────────────────────────────────
        sso_frame = ctk.CTkFrame(dlg, fg_color="#2b2d31", corner_radius=8)
        sso_frame.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(sso_frame, text="Option 1 — Auto Link (SSO)",
                     font=("", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(sso_frame,
            text="Opens nexusmods.com in your browser. Approve there and the key saves automatically.\n"
                 "Note: requires a registered app slug. Email support@nexusmods.com to request one for F76PriceGuide.",
            font=("", 11), text_color="gray", wraplength=530,
            justify="left").pack(anchor="w", padx=14, pady=(0, 6))

        sso_status = ctk.CTkLabel(sso_frame, text="", font=("", 11), text_color="gray")
        sso_status.pack(anchor="w", padx=14)

        sso_btn_row = ctk.CTkFrame(sso_frame, fg_color="transparent")
        sso_btn_row.pack(anchor="w", padx=14, pady=(4, 12))
        sso_btn = ctk.CTkButton(sso_btn_row, text="🔗  Auto Link via Browser",
                                width=210, height=34, font=("", 12),
                                fg_color="#5865F2", hover_color="#3b47b5")
        sso_btn.pack(side="left", padx=(0, 8))

        # ── Manual section ────────────────────────────────────────────────────
        man_frame = ctk.CTkFrame(dlg, fg_color="#2b2d31", corner_radius=8)
        man_frame.pack(fill="x", padx=18, pady=(0, 8))

        ctk.CTkLabel(man_frame, text="Option 2 — Paste API Key (always works)",
                     font=("", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(man_frame,
            text="nexusmods.com → click your avatar → API Keys → copy Personal API Key",
            font=("", 11), text_color="gray").pack(anchor="w", padx=14, pady=(0, 6))

        key_row = ctk.CTkFrame(man_frame, fg_color="transparent")
        key_row.pack(fill="x", padx=14, pady=(0, 12))
        key_entry = ctk.CTkEntry(key_row, height=36, font=("", 12),
                                 show="•", placeholder_text="Paste Personal API Key here…")
        key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(key_row, text="📋 Paste", width=70, height=36, font=("", 11),
                      fg_color="#4E5058", hover_color="#3a3b40",
                      command=lambda: (key_entry.delete(0, "end"),
                                       key_entry.insert(0, self.clipboard_get()))
                      ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(key_row, text="↗ Open Page", width=100, height=36, font=("", 11),
                      fg_color="#4E5058", hover_color="#3a3b40",
                      command=lambda: webbrowser.open(
                          "https://www.nexusmods.com/users/myaccount?tab=api+access")
                      ).pack(side="left")

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(pady=(0, 14))

        def _save_manual():
            k = key_entry.get().strip()
            if not k:
                messagebox.showwarning("No Key", "Please paste your API key first.", parent=dlg)
                return
            _sso_cancelled[0] = True
            self._apply_nexus_key(k, dlg)

        ctk.CTkButton(btn_row, text="✔  Save Key", width=140, height=36,
                      font=("", 13, "bold"), fg_color="#3ba55c", hover_color="#2d8049",
                      command=_save_manual).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Cancel", width=100, height=36,
                      font=("", 12), fg_color="#4E5058", hover_color="#3a3b40",
                      command=lambda: [dlg.destroy(), _sso_cancelled.__setitem__(0, True)]
                      ).pack(side="left", padx=6)

        # ── SSO thread ────────────────────────────────────────────────────────
        def _run_sso():
            # Install websocket-client if needed
            try:
                import importlib
                ws_mod = importlib.import_module("websocket")
            except ImportError:
                self.after(0, lambda: sso_status.configure(
                    text="Installing websocket-client…", text_color="gray"))
                try:
                    import subprocess as _sp
                    _sp.check_call([sys.executable, "-m", "pip", "install",
                                    "websocket-client", "--quiet"],
                                   stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                    import importlib
                    ws_mod = importlib.import_module("websocket")
                except Exception:
                    self.after(0, lambda: sso_status.configure(
                        text="⚠ websocket-client unavailable — use Option 2.",
                        text_color="#f0a500"))
                    return

            received = []

            def on_open(ws):
                self.after(0, lambda: sso_status.configure(
                    text="Connected — opening browser…", text_color="gray"))
                # Correct Nexus SSO payload: id + appid (registered slug required)
                ws.send(json.dumps({"id": sso_id, "appid": app_slug}))
                # Open browser immediately after sending — server handles the rest
                url = f"https://www.nexusmods.com/sso?id={sso_id}&application={app_slug}"
                webbrowser.open(url)
                self.after(0, lambda: sso_status.configure(
                    text="Browser opened — approve on nexusmods.com…", text_color="gray"))

            def on_message(ws, msg):
                try:
                    data = json.loads(msg)
                    if data.get("success"):
                        inner = data.get("data") or {}
                        if isinstance(inner, dict):
                            if "connection_token" in inner:
                                # Server acknowledged — waiting for user to approve
                                self.after(0, lambda: sso_status.configure(
                                    text="Waiting for you to approve in browser…",
                                    text_color="gray"))
                            elif "api_key" in inner:
                                received.append(inner["api_key"])
                                ws.close()
                except json.JSONDecodeError:
                    # Plain-text API key response
                    key = msg.strip()
                    if key and len(key) > 8:
                        received.append(key)
                        ws.close()

            def on_error(ws, err):
                self.after(0, lambda e=str(err): sso_status.configure(
                    text=f"SSO error — use Option 2. ({e[:60]})",
                    text_color="#ed4245"))

            def on_close(ws, *a):
                pass

            try:
                ws = ws_mod.WebSocketApp("wss://sso.nexusmods.com",
                    on_open=on_open, on_message=on_message,
                    on_error=on_error, on_close=on_close)
                ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                self.after(0, lambda e=str(e): sso_status.configure(
                    text=f"SSO unavailable — use Option 2.", text_color="#ed4245"))

            if received and not _sso_cancelled[0]:
                self.after(0, lambda k=received[0]: self._apply_nexus_key(k, dlg))

        sso_btn.configure(
            command=lambda: threading.Thread(target=_run_sso, daemon=True).start())

        key_entry.focus()

    def _apply_nexus_key(self, api_key: str, dlg=None):
        """Save API key to settings and update all UI."""
        self.settings["nexus_api_key"] = api_key
        self._save_settings()
        try:
            if self.nexus_api_entry.winfo_exists():
                self.nexus_api_entry.delete(0, "end")
                self.nexus_api_entry.insert(0, api_key)
            if self.nexus_status_lbl.winfo_exists():
                self.nexus_status_lbl.configure(text="✅ Account Linked", text_color="#3ba55c")
        except Exception as e:
            print(f"Warning: could not update Nexus UI after linking: {e}")
        if dlg:
            try:
                if dlg.winfo_exists():
                    dlg.destroy()
            except Exception:
                pass
        self._refresh_dash_install_status()
        messagebox.showinfo("Account Linked",
            "NexusMods API key saved!\n\nYou can now use 'Download & Install' on mod cards.")

    def _nexus_sso_fallback(self, wait_win=None):
        """Legacy stub."""
        try:
            if wait_win and wait_win.winfo_exists():
                wait_win.destroy()
        except Exception:
            pass
        self._nexus_link_account()



    def _nexus_unlink_account(self):
        """Remove stored Nexus API key."""
        if messagebox.askyesno("Unlink Account",
                "This will remove your stored NexusMods API key.\nContinue?"):
            self.settings.pop("nexus_api_key", None)
            self._save_settings()
            self.nexus_api_entry.delete(0, "end")
            self.nexus_status_lbl.configure(text="❌ Not Linked", text_color="#ed4245")

    def _nexus_headers(self) -> dict:
        """Return standard Nexus API request headers per their AUP."""
        key = self.settings.get("nexus_api_key", "").strip()
        return {
            "apikey":     key,
            "User-Agent": f"{NEXUS_APP_NAME}/{NEXUS_APP_VERSION} (github; contact via nexus mod page)",
            "Accept":     "application/json",
        }

    def _on_nxm_received(self, nxm_url: str):
        """Called (on main thread via after()) when an nxm:// link arrives.
        Parses the URL, matches it to a pending mod, downloads and installs."""
        print(f"NXM received: {nxm_url}")
        parsed = nxm_parse(nxm_url)
        if not parsed:
            messagebox.showerror("NXM Error", f"Could not parse NXM link:\n{nxm_url}")
            return

        mod_id  = parsed.get("mod_id", 0)
        file_id = parsed.get("file_id", 0)

        # Match to pending mod
        pending = self._nxm_pending_mod.pop(mod_id, None)
        if not pending:
            # Try matching any known mod by mod_id
            mod_def = next((m for m in NEXUS_MODS if m["mod_id"] == mod_id), None)
            if not mod_def:
                messagebox.showwarning("NXM",
                    f"Received download for unknown mod ID {mod_id}.\n"
                    f"Full link: {nxm_url}")
                return
            # Create a dummy pending entry — no live status/progress labels
            pending = {
                "mod_def": mod_def, "status_lbl": None,
                "progress_lbl": None, "refresh_cb": None,
                "file_id": file_id, "file_name": "",
            }

        mod_def     = pending["mod_def"]
        status_lbl  = pending.get("status_lbl")
        progress_lbl= pending.get("progress_lbl")
        refresh_cb  = pending.get("refresh_cb")

        def _update(text, color="gray"):
            if progress_lbl:
                self.after(0, lambda t=text, c=color:
                    progress_lbl.configure(text=t, text_color=c))

        api_key = self.settings.get("nexus_api_key", "").strip()
        game_root = Path(self.settings.get("game_root", detect_game_root()))
        if not game_root or not game_root.exists():
            messagebox.showerror("Game Root Not Found",
                f"Set a valid Fallout 76 Game Root path in Settings first.\n\n{game_root}")
            return

        def task():
            try:
                _update("Getting download link…")

                # Build download URL using the nxm key/expires
                dl_api_url = nxm_build_download_url(parsed, api_key)
                req = urllib.request.Request(dl_api_url, headers=self._nexus_headers())
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read().decode()
                try:
                    links = json.loads(raw)
                except json.JSONDecodeError:
                    _update("Invalid response from Nexus (not JSON)", "#ed4245")
                    self.after(0, lambda: messagebox.showerror("Nexus Error",
                        "Nexus returned an unexpected response (not JSON).\n"
                        "This usually means you're being rate-limited or Nexus is down.\n"
                        "Wait a minute and try again."))
                    return

                if not links:
                    _update("No download link in NXM response", "#ed4245")
                    return

                dl_link   = links[0].get("URI", "")
                file_name = pending.get("file_name") or f"mod_{mod_id}_{file_id}.zip"

                if not dl_link:
                    _update("Empty download URI", "#ed4245")
                    return

                _update(f"Downloading {file_name}…")
                with tempfile.TemporaryDirectory() as tmp:
                    archive = Path(tmp) / file_name

                    def _hook(count, block, total):
                        if total > 0:
                            pct = min(100, int(count * block * 100 / total))
                            _update(f"Downloading… {pct}%")

                    urllib.request.urlretrieve(dl_link, archive, reporthook=_hook)
                    _update("Installing…")
                    self._nexus_install_archive(archive, mod_def, game_root)

                _update("✓ Installed!", "#3ba55c")
                self.after(0, self._refresh_dash_install_status)
                if refresh_cb:
                    self.after(0, refresh_cb)
                self.after(0, lambda: messagebox.showinfo("Installed",
                    f"{mod_def['name']} installed successfully!\n\n"
                    "Launch Fallout 76, load your character, then quit to export your inventory.\n\n"
                    f"Credit: {mod_def['author']} — {mod_def['nexus_url']}"))
            except Exception as ex:
                import traceback; traceback.print_exc()
                _update(f"Error: {ex}", "#ed4245")
                self.after(0, lambda e=str(ex): messagebox.showerror(
                    "NXM Install Failed", f"{e}\n\nTry 'Install from File…' instead."))

        threading.Thread(target=task, daemon=True).start()

    def _build_nexus_mod_card(self, parent, mod_def: dict):
        """Build one mod card with fully dynamic install/uninstall buttons."""
        card = ctk.CTkFrame(parent, fg_color="#2b2d31", corner_radius=10)
        card.pack(fill="x", padx=18, pady=(4, 8))

        # ── Header row ─────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 2))

        ctk.CTkLabel(hdr, text=mod_def["name"], font=("", 14, "bold"),
                     anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text=f"by {mod_def['author']}", font=("", 11),
                     text_color="gray", anchor="w").pack(side="left", padx=(8, 0))

        right_hdr = ctk.CTkFrame(hdr, fg_color="transparent")
        right_hdr.pack(side="right")
        status_lbl = ctk.CTkLabel(right_hdr, text="", font=("", 12))
        status_lbl.pack(side="left", padx=(0, 10))
        ctk.CTkButton(right_hdr, text="↗ Nexus Page", width=110, height=28, font=("", 11),
                      fg_color="#4E5058", hover_color="#3a3b40",
                      command=lambda u=mod_def["nexus_url"]: webbrowser.open(u)).pack(side="left")

        # ── Description ────────────────────────────────────────────────────
        ctk.CTkLabel(card, text=mod_def["description"], font=("", 12),
                     text_color="gray", anchor="w", justify="left",
                     wraplength=760).pack(anchor="w", padx=14, pady=(2, 8))

        # ── Action row — rebuilt whenever install state changes ─────────────
        act = ctk.CTkFrame(card, fg_color="transparent")
        act.pack(fill="x", padx=14, pady=(0, 12))

        progress_lbl = ctk.CTkLabel(act, text="", font=("", 11), text_color="gray")
        progress_lbl.pack(side="right", padx=(8, 0))

        btn_frame = ctk.CTkFrame(act, fg_color="transparent")
        btn_frame.pack(side="left")

        def _refresh_buttons():
            """Destroy and rebuild action buttons based on current install state."""
            for w in btn_frame.winfo_children():
                w.destroy()
            game_root = self.settings.get("game_root", detect_game_root())
            installed = self._nexus_mod_installed(mod_def, game_root)

            # Update status label
            if installed:
                status_lbl.configure(text="🟢 Installed", text_color="#3ba55c")
            else:
                status_lbl.configure(text="⚫ Not installed", text_color="gray")

            if not installed:
                ctk.CTkButton(btn_frame, text="⬇  Download & Install",
                              width=190, height=36, font=("", 13),
                              fg_color="#3ba55c", hover_color="#2d8049",
                              command=lambda: self._nexus_download_mod(
                                  mod_def, status_lbl, progress_lbl, _refresh_buttons)
                              ).pack(side="left", padx=(0, 8))
                ctk.CTkButton(btn_frame, text="📁  Install from File…",
                              width=170, height=36, font=("", 13),
                              fg_color="#4E5058", hover_color="#3a3b40",
                              command=lambda: self._nexus_install_from_file_dialog(
                                  mod_def, status_lbl, progress_lbl, _refresh_buttons)
                              ).pack(side="left", padx=(0, 8))
            else:
                ctk.CTkButton(btn_frame, text="📁  Re-install from File…",
                              width=185, height=36, font=("", 13),
                              fg_color="#4E5058", hover_color="#3a3b40",
                              command=lambda: self._nexus_install_from_file_dialog(
                                  mod_def, status_lbl, progress_lbl, _refresh_buttons)
                              ).pack(side="left", padx=(0, 8))
                ctk.CTkButton(btn_frame, text="✕  Uninstall",
                              width=130, height=36, font=("", 13),
                              fg_color="#ed4245", hover_color="#bd2e31",
                              command=lambda: self._nexus_uninstall(
                                  mod_def, status_lbl, progress_lbl, _refresh_buttons)
                              ).pack(side="left", padx=(0, 8))

        # Initial draw
        _refresh_buttons()

        # Store references for external refresh calls
        self._nexus_mod_widgets[mod_def["key"]] = {
            "card":           card,
            "status_lbl":     status_lbl,
            "progress_lbl":   progress_lbl,
            "refresh_buttons": _refresh_buttons,
        }

    def _nexus_mod_installed(self, mod_def: dict, game_root: str) -> bool:
        """Return True if the mod appears to be installed in game_root.
        For inventomatic: requires the ba2 OR the config JSON.
        For sfe: requires dxgi.dll at the game root.
        """
        root = Path(game_root)
        detect = mod_def.get("detect_files", [])
        if not detect:
            return False
        found = [f for f in detect if (root / f).exists()]
        return len(found) > 0

    def _nexus_download_mod(self, mod_def: dict, status_lbl, progress_lbl, refresh_cb=None):
        """Fetch download link from Nexus API, download archive, then install."""
        api_key = self.settings.get("nexus_api_key", "").strip()
        if not api_key:
            messagebox.showerror("Account Not Linked",
                "Please link your NexusMods account first.\n\n"
                "Go to Settings → Nexus Mod Manager → 'Link Nexus Account'.")
            return

        game_root = self.settings.get("game_root", detect_game_root())
        if not Path(game_root).exists():
            messagebox.showerror("Game Root Not Found",
                f"Set a valid Fallout 76 Game Root path in Settings first.\n\n{game_root}")
            return

        def _update(text, color="gray"):
            self.after(0, lambda t=text, c=color:
                progress_lbl.configure(text=t, text_color=c))

        def _set_status(text, color):
            self.after(0, lambda t=text, c=color:
                status_lbl.configure(text=t, text_color=c))

        def task():
            try:
                # ── Direct URL override (bypasses Nexus API) ──────────────
                if mod_def.get("direct_url"):
                    file_name = mod_def.get("direct_filename", "mod_download.zip")
                    dl_link   = mod_def["direct_url"]
                    is_dll    = mod_def.get("direct_is_dll", False)
                    _update(f"Downloading {file_name}…")

                    # Use requests — handles Google Drive redirect/cookie flow
                    import requests
                    session = requests.Session()
                    session.headers.update({"User-Agent": "Mozilla/5.0"})

                    # Extract file ID from the drive URL
                    import re as _re
                    fid_m = _re.search(r'id=([^&"]+)', dl_link)
                    fid   = fid_m.group(1) if fid_m else ""

                    # Use the modern usercontent.google.com endpoint (confirm= param
                    # was deprecated by Google in 2023; this URL bypasses the warning page)
                    if fid:
                        direct = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
                    else:
                        direct = dl_link
                    _update(f"Downloading {file_name}…")
                    resp = session.get(direct, stream=True, timeout=120)

                    # Stream file to disk
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    with tempfile.TemporaryDirectory() as tmp:
                        dest = Path(tmp) / file_name
                        with open(dest, "wb") as fout:
                            for chunk in resp.iter_content(chunk_size=65536):
                                if chunk:
                                    fout.write(chunk)
                                    downloaded += len(chunk)
                                    if total > 0:
                                        pct = min(100, int(downloaded * 100 / total))
                                        _update(f"Downloading… {pct}%")

                        # Sanity check — did Drive return an HTML page?
                        with open(dest, "rb") as f:
                            magic = f.read(9)
                        if magic[:5] in (b"<!DOC", b"<html", b"<HTML"):
                            raise RuntimeError(
                                "Google Drive returned an HTML page instead of the file.\n"
                                "The share link may have expired or the file requires sign-in.")

                        _update("Installing…")
                        if is_dll:
                            # Raw DLL — copy directly to game root
                            game_root_path = Path(game_root)
                            dst = game_root_path / file_name
                            shutil.copy2(dest, dst)
                        else:
                            self._nexus_install_archive(dest, mod_def, Path(game_root))

                    _update("✓ Installed!", "#3ba55c")
                    self.after(0, self._refresh_dash_install_status)
                    if refresh_cb:
                        self.after(0, refresh_cb)
                    self.after(0, lambda: messagebox.showinfo("Installed",
                        f"{mod_def['name']} installed successfully!\n\n"
                        f"Launch Fallout 76, load your character, then quit to let the mod write your inventory files.\n\n"
                        f"Credit: {mod_def['author']} — {mod_def['nexus_url']}"))
                    return

                _update("Querying Nexus API…")
                mod_id = mod_def["mod_id"]

                # ── Step 1: get file list ─────────────────────────────────
                files_url = (f"https://api.nexusmods.com/v1/games/{NEXUS_GAME}"
                             f"/mods/{mod_id}/files.json")
                req = urllib.request.Request(files_url, headers=self._nexus_headers())
                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        files_data = json.loads(resp.read().decode())
                except urllib.error.HTTPError as e:
                    if e.code in (401, 403):
                        self.after(0, lambda code=e.code: messagebox.showerror("API Key Invalid",
                            f"The Nexus API returned {code}.\n\n"
                            "Check that your API key is correct and hasn't expired.\n\n"
                            "Go to Settings → Nexus Mod Manager → 'Link Nexus Account' "
                            "and re-paste your API key."))
                        _update("Auth failed", "#ed4245")
                        return
                    raise

                # Pick the most recent 'Main' file
                all_files = files_data.get("files", [])
                main_files = [f for f in all_files if f.get("category_name") == "MAIN"]
                if not main_files:
                    main_files = all_files  # fall back to any file
                if not main_files:
                    _update("No files found on Nexus", "#ed4245")
                    return
                # Sort by uploaded time descending, pick latest
                main_files.sort(key=lambda x: x.get("uploaded_timestamp", 0), reverse=True)
                file_info = main_files[0]
                file_id   = file_info["file_id"]
                file_name = file_info["file_name"]

                _update(f"Found: {file_name}")

                # ── Step 2: get download link ─────────────────────────────
                dl_url = (f"https://api.nexusmods.com/v1/games/{NEXUS_GAME}"
                          f"/mods/{mod_id}/files/{file_id}/download_link.json")
                req2 = urllib.request.Request(dl_url, headers=self._nexus_headers())
                try:
                    with urllib.request.urlopen(req2, timeout=15) as resp2:
                        links = json.loads(resp2.read().decode())
                except urllib.error.HTTPError as e:
                    if e.code == 403:
                        # Free account — API won't give direct link.
                        # Open the Nexus slow-download page and watch the Downloads
                        # folder for the file to appear, then auto-install it.
                        dl_page = (f"https://www.nexusmods.com/{NEXUS_GAME}"
                                   f"/mods/{mod_id}?tab=files&file_id={file_id}")
                        self.after(0, lambda: webbrowser.open(dl_page))
                        _update("Waiting for download…", "#f0a500")
                        self.after(0, lambda fn=file_name: messagebox.showinfo(
                            "One More Click Required",
                            f"Your browser opened the Nexus page for:\n  {fn}\n\n"
                            "Click the  ⬇ Slow Download  button.\n\n"
                            "F76 Price Guide is watching your Downloads folder and will "
                            "install the file automatically once it finishes — "
                            "no file picker needed!"))
                        # Watch downloads folder for the file
                        dl_folder = Path(self.settings.get("downloads_path", "") or detect_downloads_path())
                        base_name = Path(file_name).stem.lower()
                        found = self._wait_for_download(
                            dl_folder, base_name, _update, timeout=300)
                        if found:
                            _update("Installing…")
                            self._nexus_install_archive(found, mod_def, Path(game_root))
                            _update("✓ Installed!", "#3ba55c")
                            self.after(0, self._refresh_dash_install_status)
                            if refresh_cb:
                                self.after(0, refresh_cb)
                            self.after(0, lambda: messagebox.showinfo("Installed",
                                f"{mod_def['name']} installed successfully!\n\n"
                                "Launch Fallout 76, load your character, then quit to "
                                "export your inventory.\n\n"
                                f"Credit: {mod_def['author']} — {mod_def['nexus_url']}"))
                        else:
                            _update("Timed out — use 'Install from File…'", "#ed4245")
                        return
                    raise

                if not links:
                    _update("No download links returned", "#ed4245")
                    return

                # Pick the CDN link (first entry is usually the preferred CDN)
                dl_link = links[0].get("URI", "")
                if not dl_link:
                    _update("Empty download URI", "#ed4245")
                    return

                # ── Step 3: download ──────────────────────────────────────
                _update(f"Downloading {file_name}…")
                with tempfile.TemporaryDirectory() as tmp:
                    archive = Path(tmp) / file_name

                    def _reporthook(count, block, total):
                        if total > 0:
                            pct = min(100, int(count * block * 100 / total))
                            _update(f"Downloading… {pct}%")

                    urllib.request.urlretrieve(dl_link, archive, reporthook=_reporthook)
                    _update("Installing…")
                    self._nexus_install_archive(archive, mod_def, Path(game_root))

                _update("✓ Installed!", "#3ba55c")
                self.after(0, self._refresh_dash_install_status)
                if refresh_cb:
                    self.after(0, refresh_cb)
                self.after(0, lambda: messagebox.showinfo("Installed",
                    f"{mod_def['name']} installed successfully!\n\n"
                    f"Launch Fallout 76, load your character, then quit to let the mod write your inventory files.\n\n"
                    f"Credit: {mod_def['author']} — {mod_def['nexus_url']}"))

            except Exception as ex:
                print(f"Nexus install error: {ex}")
                import traceback; traceback.print_exc()
                _update(f"Error: {ex}", "#ed4245")
                self.after(0, lambda e=str(ex): messagebox.showerror("Download Failed",
                    f"Could not download {mod_def['name']}:\n\n{e}\n\n"
                    f"You can download it manually from:\n{mod_def['nexus_url']}"))

        threading.Thread(target=task, daemon=True).start()

    def _wait_for_download(self, folder: Path, base_name: str, update_cb, timeout: int = 300) -> Path | None:
        """Poll the Downloads folder until a file matching base_name appears and
        stops growing (download complete). Returns the Path or None on timeout.
        base_name is the stem (no extension), matched case-insensitively."""
        import time
        extensions = {".zip", ".7z", ".rar", ".fomod"}
        deadline = time.time() + timeout
        last_size = {}
        stable_since = {}
        consecutive_errors = 0

        update_cb("Waiting for download to start…", "#f0a500")

        while time.time() < deadline:
            candidates = []
            try:
                for f in folder.iterdir():
                    if f.suffix.lower() not in extensions:
                        continue
                    stem = f.stem.lower()
                    # Match: file stem contains the base_name, or base_name contains stem
                    if base_name in stem or stem in base_name or self._name_similarity(base_name, stem) > 0.6:
                        candidates.append(f)
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                print(f"Warning: _wait_for_download folder scan error ({consecutive_errors}): {e}")
                if consecutive_errors >= 3:
                    print("Error: download folder inaccessible after 3 attempts, aborting wait")
                    update_cb("Error: download folder inaccessible", "#ed4245")
                    return None

            for f in candidates:
                try:
                    sz = f.stat().st_size
                except OSError:
                    continue
                prev = last_size.get(f)
                if prev is None:
                    last_size[f] = sz
                    stable_since[f] = time.time()
                    update_cb(f"Downloading {f.name}…", "#f0a500")
                elif sz == prev:
                    # File hasn't grown — check if stable for 3 seconds
                    if time.time() - stable_since[f] >= 3 and sz > 1024:
                        update_cb(f"Download complete: {f.name}", "gray")
                        return f
                else:
                    last_size[f] = sz
                    stable_since[f] = time.time()
                    kb = sz // 1024
                    update_cb(f"Downloading {f.name} ({kb:,} KB)…", "#f0a500")

            time.sleep(1)

        return None

    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        """Simple character-overlap similarity ratio between two strings."""
        if not a or not b:
            return 0.0
        set_a, set_b = set(a), set(b)
        return len(set_a & set_b) / len(set_a | set_b)

    def _nexus_install_archive(self, archive_path: Path, mod_def: dict, game_root: Path):
        """Extract a downloaded mod archive and install files to game_root."""
        suffix = archive_path.suffix.lower()
        game_root.mkdir(exist_ok=True)
        data_dir = game_root / "Data"
        data_dir.mkdir(exist_ok=True)

        with tempfile.TemporaryDirectory() as extract_dir:
            ep = Path(extract_dir)

            # Extract the archive
            if suffix in (".zip", ".7z") or archive_path.name.endswith(".7z"):
                try:
                    if suffix == ".zip":
                        with zipfile.ZipFile(archive_path, 'r') as z:
                            z.extractall(ep)
                    else:
                        with py7zr.SevenZipFile(archive_path, mode='r') as z:
                            z.extractall(ep)
                except Exception as e:
                    raise RuntimeError(f"Could not extract archive ({suffix}): {e}")
            else:
                # Treat as zip anyway (Nexus often sends .zip regardless of extension)
                try:
                    with zipfile.ZipFile(archive_path, 'r') as z:
                        z.extractall(ep)
                except Exception:
                    with py7zr.SevenZipFile(archive_path, mode='r') as z:
                        z.extractall(ep)

            # Auto-detect and copy files
            copied = []
            for src in ep.rglob("*"):
                if not src.is_file():
                    continue
                name_low = src.name.lower()

                # DLL → game root
                if name_low.endswith(".dll") and ("dxgi" in name_low or "f4se" in name_low or "asi" in name_low):
                    dst = game_root / src.name
                    shutil.copy2(src, dst)
                    copied.append(str(dst))

                # BA2 → Data folder
                elif name_low.endswith(".ba2"):
                    dst = data_dir / src.name
                    shutil.copy2(src, dst)
                    copied.append(str(dst))

                # JSON config from archive (may be overridden below by bundled config)
                elif name_low.endswith(".json") and "config" in name_low:
                    dst = data_dir / src.name
                    shutil.copy2(src, dst)
                    copied.append(str(dst))

                # f4se / SFE executables / extra DLLs
                elif name_low.endswith(".exe") and "loader" in name_low:
                    dst = game_root / src.name
                    shutil.copy2(src, dst)
                    copied.append(str(dst))

            # ── Always write the bundled inventOmaticStashConfig.json ──────────
            # This is the authoritative config that ensures the mod outputs to the
            # right location. It overrides whatever may have been in the archive.
            if mod_def.get("key") == "inventomatic":
                config_dst = data_dir / "inventOmaticStashConfig.json"
                self._write_inventomatic_config(config_dst, game_root)
                if str(config_dst) not in copied:
                    copied.append(str(config_dst))

            if not copied:
                raise RuntimeError(
                    "No recognizable mod files (.dll, .ba2, .json config, .exe) found in archive.\n"
                    "Please install this mod manually from the Nexus page.")

            print(f"Installed {len(copied)} file(s): {copied}")

            # Update INI if needed
            ini_ba2 = mod_def.get("ini_ba2")
            if ini_ba2:
                ini_path = self.settings.get("ini_path", detect_ini_path())
                ini_file = Path(ini_path)
                if ini_file.exists():
                    try:
                        self._update_ini_for_mod(ini_file)
                    except Exception as e:
                        print(f"Warning: INI update failed (mod files installed successfully): {e}")
                else:
                    print(f"  INI not found at {ini_file} — skipping INI update")

    def _write_inventomatic_config(self, config_dst: Path, game_root: Path):
        """Write the inventOmaticStashConfig.json to the game's Data folder.

        Priority order (highest first):
          1. Data folder (DATA_DIR / inventOmaticStashConfig.json)
             — the user's live config; always used if present (overwrites destination)
          2. Bundled default config (outputs LegendaryMods.ini / ItemsMod.ini to Data/)
        """
        config_dst.parent.mkdir(parents=True, exist_ok=True)

        # ── 1. App Data folder — highest priority, always wins ────────────────
        # DATA_DIR is the user-configured Data folder (Settings > Data Paths).
        src_config = DATA_DIR / "inventOmaticStashConfig.json"
        if src_config.exists() and src_config.resolve() != config_dst.resolve():
            try:
                shutil.copy2(src_config, config_dst)
                print(f"  ✓ Restored config from Data folder: {src_config}")
                return
            except Exception as e:
                print(f"  Warning: could not copy Data folder config ({e}), trying fallbacks…")

        # ── 2. App's own Data folder ───────────────────────────────────────────
        app_config = APP_DIR / "Data" / "inventOmaticStashConfig.json"
        if app_config.exists() and app_config.resolve() != config_dst.resolve():
            try:
                shutil.copy2(app_config, config_dst)
                print(f"  Copied app-local config from: {app_config}")
                return
            except Exception as e:
                print(f"  Warning: could not copy app config ({e}), using built-in default…")

        # ── 3. Bundled default — last resort ───────────────────────────────────
        config = dict(INVENTOMATIC_CONFIG)
        with open(config_dst, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"  Wrote bundled default inventOmaticStashConfig.json → {config_dst}")

    def _nexus_install_from_file_dialog(self, mod_def: dict, status_lbl, progress_lbl, refresh_cb=None):
        """Let user pick a manually-downloaded archive to install."""
        path = filedialog.askopenfilename(
            title=f"Select downloaded archive for {mod_def['name']}",
            filetypes=[
                ("Archives", "*.zip *.7z"),
                ("All files", "*.*"),
            ])
        if not path:
            return
        archive = Path(path)
        game_root = Path(self.settings.get("game_root", detect_game_root()))
        if not game_root or not game_root.exists():
            messagebox.showerror("Game Root Not Found",
                f"Set a valid Fallout 76 Game Root path in Settings first.\n\n{game_root}")
            return

        def _update(text, color="gray"):
            self.after(0, lambda t=text, c=color:
                progress_lbl.configure(text=t, text_color=c))

        def task():
            try:
                _update("Installing from file…")
                self._nexus_install_archive(archive, mod_def, game_root)
                _update("✓ Installed!", "#3ba55c")
                self.after(0, self._refresh_dash_install_status)
                if refresh_cb:
                    self.after(0, refresh_cb)
                self.after(0, lambda: messagebox.showinfo("Installed",
                    f"{mod_def['name']} installed successfully!\n\n"
                    f"Credit: {mod_def['author']} — {mod_def['nexus_url']}"))
            except Exception as ex:
                _update(f"Error: {ex}", "#ed4245")
                self.after(0, lambda e=str(ex): messagebox.showerror("Install Failed", e))

        threading.Thread(target=task, daemon=True).start()

    def _nexus_uninstall(self, mod_def: dict, status_lbl, progress_lbl, refresh_cb=None):
        """Uninstall a mod managed by the Nexus Mod Manager."""
        game_root = Path(self.settings.get("game_root", detect_game_root()))
        ini_path  = Path(self.settings.get("ini_path", detect_ini_path()))
        if not game_root or not game_root.exists():
            messagebox.showerror("Game Root Not Found",
                f"Set a valid Fallout 76 Game Root path in Settings first.\n\n{game_root}")
            return

        # Build list of files to remove
        candidates = []
        for rel in mod_def.get("detect_files", []):
            p = game_root / rel
            if p.exists():
                candidates.append(p)
        # Also try to find the INI ba2 name in Data/
        ini_ba2 = mod_def.get("ini_ba2")
        if ini_ba2:
            p = game_root / "Data" / ini_ba2
            if p.exists() and p not in candidates:
                candidates.append(p)
        # For inventomatic: also remove the config JSON
        if mod_def.get("key") == "inventomatic":
            cfg = game_root / "Data" / "inventOmaticStashConfig.json"
            if cfg.exists() and cfg not in candidates:
                candidates.append(cfg)

        if not candidates:
            messagebox.showinfo("Not Installed",
                f"{mod_def['name']} does not appear to be installed.")
            return

        file_list = "\n".join(f"  • {f.name}" for f in candidates)
        if not messagebox.askyesno("Confirm Uninstall",
                f"This will remove from your game directory:\n\n{file_list}\n\n"
                "It will also remove the mod entry from Fallout76Custom.ini.\n\nContinue?"):
            return

        # BUG-02 fix: run all file I/O and INI updates on a background thread
        _candidates = list(candidates)
        _ini_ba2    = ini_ba2  # None for SFE, "InventOmaticStash.ba2" for inventomatic

        def task():
            removed = []
            errors  = []
            for p in _candidates:
                try:
                    p.unlink()
                    removed.append(p.name)
                except Exception as e:
                    errors.append(f"{p.name}: {e}")

            # Strip ba2 entry from INI — always attempt if there's a ba2 to remove
            if _ini_ba2:
                try:
                    self._remove_mod_from_ini(ini_path, ba2_name=_ini_ba2)
                except Exception as e:
                    errors.append(f"INI update: {e}")

            if removed:
                self.after(0, self._refresh_dash_install_status)
                if refresh_cb:
                    self.after(0, refresh_cb)
                else:
                    self.after(0, lambda: progress_lbl.configure(text="", text_color="gray"))
                mod_name = mod_def['name']
                msg = f"Uninstalled {mod_name}.\n\nRemoved:\n" + "\n".join(f"  • {n}" for n in removed)
                if errors:
                    msg += "\n\nWarnings:\n" + "\n".join(errors)
                self.after(0, lambda: messagebox.showinfo("Uninstalled", msg))
            else:
                err_text = "\n".join(errors)
                self.after(0, lambda: messagebox.showerror("Error", f"Could not remove files:\n{err_text}"))

        threading.Thread(target=task, daemon=True).start()

    def _check_install_status(self):
        """Check install status for the Dashboard mod status card."""
        game_root = self.settings.get("game_root", detect_game_root())
        # Primary check: InventOmatic (the one this app needs most)
        inv_def = next((m for m in NEXUS_MODS if m["key"] == "inventomatic"), None)
        if inv_def and self._nexus_mod_installed(inv_def, game_root):
            if hasattr(self, 'install_status'):
                self.install_status.configure(text="✓ InventOmatic installed", text_color="#3ba55c")
        else:
            if hasattr(self, 'install_status'):
                self.install_status.configure(text="InventOmatic not installed", text_color="gray")

    def _install_mod(self):
        """Legacy stub — redirects to Nexus Mod Manager. Use the Settings tab to install mods."""
        print("Warning: _install_mod() called — this is a legacy stub. Use the Nexus Mod Manager in Settings.")
        messagebox.showinfo("Use Mod Manager",
            "Please use the Mod Manager in the Settings tab to install mods.")



    def _refresh_dash_install_status(self):
        """Update the install status label on the Dashboard — shows both mods.
        Also refreshes all mod card buttons so they stay in sync with actual disk state."""
        # BUG-05 fix: widget may not exist yet if called before _build_ui completes
        if not hasattr(self, 'dash_install_status'):
            return
        game_root = self.settings.get("game_root", detect_game_root())
        inv_def = next((m for m in NEXUS_MODS if m["key"] == "inventomatic"), None)
        sfe_def = next((m for m in NEXUS_MODS if m["key"] == "sfe"), None)

        inv_ok  = inv_def and self._nexus_mod_installed(inv_def, game_root)
        sfe_ok  = sfe_def and self._nexus_mod_installed(sfe_def, game_root)

        inv_sym = "✓" if inv_ok else "✗"
        sfe_sym = "✓" if sfe_ok else "✗"

        status_text = f"{inv_sym} InventOmatic    {sfe_sym} SFE (Script Extender)"
        overall_color = "#3ba55c" if (inv_ok and sfe_ok) else ("#f0a500" if (inv_ok or sfe_ok) else "#ed4245")
        self.dash_install_status.configure(text=status_text, text_color=overall_color)

        # Refresh each mod card's buttons so they always match actual disk state
        for key, widgets in self._nexus_mod_widgets.items():
            cb = widgets.get("refresh_buttons")
            if cb:
                try:
                    cb()
                except Exception as e:
                    print(f"Warning: mod card refresh error for '{key}': {e}")

    def _uninstall_mod(self):
        """Properly uninstall the InventOmatic Stash mod and clean up INI."""
        game_root = self.settings.get("game_root", detect_game_root())
        ini_path  = self.settings.get("ini_path", detect_ini_path())

        if not game_root or not Path(game_root).exists():
            messagebox.showerror("Game Root Not Found",
                f"Set a valid Fallout 76 Game Root path in Settings first.\n\n{game_root}")
            return

        game_root_path = Path(game_root)
        ini_file       = Path(ini_path)

        # Files to remove — BUG-03 fix: dxgi.dll belongs to SFE, not InventOmatic
        files_to_remove = [
            game_root_path / "Data" / "InventOmaticStash.ba2",
            game_root_path / "Data" / "inventOmaticStashConfig.json",
            game_root_path / "Data" / "LegendaryMods.ini",
            game_root_path / "Data" / "ItemsMod.ini",
        ]

        # Check if anything is actually installed
        present = [f for f in files_to_remove if f.exists()]
        if not present:
            messagebox.showinfo("Uninstall", "Mod files not found — nothing to uninstall.")
            if hasattr(self, 'install_status'):
                self.install_status.configure(text="Mod not installed", text_color="gray")
            return

        # Confirm before doing anything destructive
        file_list = "\n".join(f"  \u2022 {f.name}" for f in present)
        if not messagebox.askyesno("Confirm Uninstall",
                f"This will remove the following files from your game directory:\n\n{file_list}\n\n"
                "It will also remove the mod entry from Fallout76Custom.ini.\n\nContinue?"):
            return

        # BUG-01 fix: run all file I/O on a background thread so the UI never freezes
        def task():
            removed = []
            errors  = []

            for f in files_to_remove:
                if f.exists():
                    try:
                        f.unlink()
                        removed.append(f.name)
                    except Exception as e:
                        errors.append(f"{f.name}: {e}")

            # Strip mod entry from INI
            if ini_file.exists():
                try:
                    self._remove_mod_from_ini(ini_file)
                except Exception as e:
                    errors.append(f"INI update failed: {e}")

            # Marshal all UI updates back to the main thread
            if removed:
                msg = "Uninstalled successfully!\n\nRemoved:\n" + "\n".join(f"  \u2022 {n}" for n in removed)
                if errors:
                    msg += "\n\nWarnings:\n" + "\n".join(errors)
                self.after(0, lambda: messagebox.showinfo("Uninstalled", msg))
                if hasattr(self, 'install_status'):
                    self.after(0, lambda: self.install_status.configure(
                        text="\u2717 Mod uninstalled", text_color="#ed4245"))
                self.after(0, self._refresh_dash_install_status)
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Error", "Could not remove files:\n" + "\n".join(errors)))

        threading.Thread(target=task, daemon=True).start()

    def _remove_mod_from_ini(self, ini_file: Path, ba2_name: str = "InventOmaticStash.ba2"):
        """Remove a specific ba2 entry from sResourceArchive2List in Fallout76Custom.ini.

        Surgical removal — only strips the named ba2, leaves all other entries untouched.
        If removing the entry would leave sResourceArchive2List empty, the entire line is
        removed rather than leaving a dangling 'sResourceArchive2List=' behind.
        Uses an atomic tmp-then-replace write to prevent INI corruption on crash/power loss.

        Args:
            ini_file: Path to Fallout76Custom.ini
            ba2_name: Exact filename to remove (case-insensitive match). Default: InventOmaticStash.ba2
        """
        remove_lower = ba2_name.lower()

        # Log the exact path being used so mismatches are immediately visible
        print(f"  INI removal targeting: {ini_file}")

        # Verify the file actually exists and is readable before doing anything
        if not ini_file.exists():
            print(f"  INI removal FAILED — file not found: {ini_file}")
            print(f"  Tip: check the 'Fallout76Custom.ini' path in Settings")
            raise FileNotFoundError(f"INI not found: {ini_file}")

        try:
            with open(ini_file, 'r', encoding='utf-8') as f:
                raw = f.read()
        except Exception as e:
            print(f"Could not read INI for removal: {e}")
            raise

        lines     = raw.split('\n')
        new_lines = []
        modified  = False

        for line in lines:
            stripped_lower = line.strip().lower()
            if stripped_lower.startswith('sresourcearchive2list='):
                parts = line.split('=', 1)
                if len(parts) == 2:
                    values   = [v.strip() for v in parts[1].split(',') if v.strip()]
                    filtered = [v for v in values if v.lower() != remove_lower]
                    if len(filtered) != len(values):
                        modified = True
                        if filtered:
                            # Keep the line, just without this ba2
                            line = parts[0] + '=' + ', '.join(filtered)
                        else:
                            # List is now empty — drop the whole line instead of
                            # leaving 'sResourceArchive2List=' which confuses the game
                            print(f"  sResourceArchive2List is now empty — removing line entirely")
                            continue   # skip appending this line
            new_lines.append(line)

        if modified:
            try:
                tmp = ini_file.with_suffix('.tmp')
                with open(tmp, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                tmp.replace(ini_file)
                print(f"  Removed {ba2_name} from INI: {ini_file}")
            except Exception as e:
                print(f"Error writing INI after removal: {e}")
                raise
        else:
            print(f"  {ba2_name} not found in INI (nothing to remove): {ini_file}")

    def _update_ini_for_mod(self, ini_file: Path):
        """Update Fallout76Custom.ini to include InventOmaticStash.ba2 in the correct load order.

        Target position: AFTER BetterInventory (if present), BEFORE FastPip (if present).
        If neither anchor is found, appends to the end of the archive list.
        Only touches sResourceArchive2List - nothing else in the INI is modified.
        Creates the [Archive] section + key if the INI has neither.
        """
        try:
            with open(ini_file, 'r', encoding='utf-8') as f:
                content = f.read()

            NEW_MOD     = "InventOmaticStash.ba2"
            OLD_PATTERN = "inventomaticstash"   # catches any old/misnamed variant

            lines     = content.split('\n')
            new_lines = []
            modified  = False
            inserted  = False

            for line in lines:
                stripped = line.strip()
                if stripped.lower().startswith('sresourcearchive2list='):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key    = parts[0] + '='
                        values = [v.strip() for v in parts[1].split(',') if v.strip()]

                        # 1. Remove stale/duplicate InventOmaticStash entries
                        values = [v for v in values if OLD_PATTERN not in v.lower()]

                        # 2. Find anchor positions (case-insensitive)
                        lower_vals  = [v.lower() for v in values]
                        better_idx  = next((i for i, v in enumerate(lower_vals) if 'betterinventory' in v), -1)
                        fastpip_idx = next((i for i, v in enumerate(lower_vals) if 'fastpip' in v), -1)

                        # 3. Insert at correct position:
                        #    After BetterInventory > Before FastPip > End of list
                        if better_idx >= 0:
                            insert_at = better_idx + 1
                        elif fastpip_idx >= 0:
                            insert_at = fastpip_idx
                        else:
                            insert_at = len(values)

                        values.insert(insert_at, NEW_MOD)
                        inserted = True
                        line     = key + ', '.join(values)
                        modified = True

                new_lines.append(line)

            # sResourceArchive2List line didn't exist - create it under [Archive]
            if not inserted:
                final_lines  = []
                arch_section = False
                for line in new_lines:
                    final_lines.append(line)
                    if line.strip().lower() == '[archive]':
                        arch_section = True
                        final_lines.append(f'sResourceArchive2List={NEW_MOD}')
                        modified = True
                if not arch_section:
                    final_lines.append('')
                    final_lines.append('[Archive]')
                    final_lines.append(f'sResourceArchive2List={NEW_MOD}')
                    modified = True
                new_lines = final_lines

            if modified:
                tmp = ini_file.with_suffix('.tmp')
                with open(tmp, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                tmp.replace(ini_file)
                print(f"Updated INI file: {ini_file}")

        except Exception as e:
            print(f"Error updating INI: {e}")
            raise
    
    def _build_help(self):
        self._build_help_ui(self.tab_help)

    def _build_help_ui(self, f):
        """Help tab — fully reflects current app features and settings."""
        scroll = ctk.CTkScrollableFrame(f)
        scroll.pack(fill="both", expand=True)
        S = scroll

        TITLE_FONT  = ("", 26, "bold")
        SEC_FONT    = ("", 16, "bold")
        SUB_FONT    = ("", 14, "bold")
        BODY_FONT   = ("", 13)
        LABEL_FONT  = ("", 13, "bold")
        SMALL_FONT  = ("", 12)
        GRAY        = "gray"
        ACCENT      = "#5865F2"
        GREEN       = "#64DC64"
        ORANGE      = "#FFA500"
        GOLD        = "#FFD700"
        PAD_X       = 28
        WRAP        = 860

        def divider():
            ctk.CTkFrame(S, height=1, fg_color="#3a3a3a").pack(
                fill="x", padx=PAD_X, pady=(6, 16))

        def section(icon, title):
            divider()
            ctk.CTkLabel(S, text=f"{icon}  {title}", font=SEC_FONT).pack(
                anchor="w", padx=PAD_X, pady=(0, 6))

        def subsection(title):
            ctk.CTkLabel(S, text=title, font=SUB_FONT, text_color=ACCENT).pack(
                anchor="w", padx=PAD_X + 8, pady=(10, 3))

        def body(text, color=None):
            if not text:
                ctk.CTkFrame(S, height=6, fg_color="transparent").pack()
                return
            ctk.CTkLabel(S, text=text, font=BODY_FONT,
                         text_color=color or "white",
                         anchor="w", justify="left", wraplength=WRAP).pack(
                anchor="w", padx=PAD_X + 8, pady=2)

        def tip(text):
            box = ctk.CTkFrame(S, fg_color="#1e2a1e", corner_radius=8)
            box.pack(fill="x", padx=PAD_X + 8, pady=(4, 6))
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=6)
            ctk.CTkLabel(row, text="💡", font=("", 15)).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=text, font=SMALL_FONT, text_color=GREEN,
                         anchor="w", justify="left", wraplength=WRAP - 40).pack(side="left")

        def warn(text):
            box = ctk.CTkFrame(S, fg_color="#2a1e1e", corner_radius=8)
            box.pack(fill="x", padx=PAD_X + 8, pady=(4, 6))
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=6)
            ctk.CTkLabel(row, text="⚠️", font=("", 14)).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=text, font=SMALL_FONT, text_color=ORANGE,
                         anchor="w", justify="left", wraplength=WRAP - 40).pack(side="left")

        def kv(key, value, key_color=None, key_width=210):
            row = ctk.CTkFrame(S, fg_color="transparent")
            row.pack(anchor="w", padx=PAD_X + 8, pady=2)
            ctk.CTkLabel(row, text=key, font=LABEL_FONT,
                         text_color=key_color or ACCENT, width=key_width,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, font=BODY_FONT,
                         anchor="w", justify="left",
                         wraplength=WRAP - key_width).pack(side="left")

        def step(num, text):
            row = ctk.CTkFrame(S, fg_color="transparent")
            row.pack(anchor="w", padx=PAD_X + 8, pady=3)
            ctk.CTkLabel(row, text=f"  {num}.", font=LABEL_FONT,
                         text_color=ACCENT, width=30).pack(side="left", anchor="n")
            ctk.CTkLabel(row, text=text, font=BODY_FONT,
                         anchor="w", justify="left", wraplength=WRAP - 40).pack(side="left")

        def color_row(swatch_color, label, desc):
            row = ctk.CTkFrame(S, fg_color="transparent")
            row.pack(anchor="w", padx=PAD_X + 8, pady=4)
            tk.Label(row, width=3, height=1, bg=swatch_color,
                     relief="flat").pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=label, font=LABEL_FONT,
                         text_color=swatch_color, width=90,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=BODY_FONT,
                         anchor="w", justify="left",
                         wraplength=WRAP - 130).pack(side="left")

        # ── Header ────────────────────────────────────────────────────────────
        ctk.CTkLabel(S, text="Help & Reference", font=TITLE_FONT,
                     anchor="center").pack(anchor="center", padx=PAD_X, pady=(22, 2))
        ctk.CTkLabel(S,
            text="A complete guide to every feature in the F76 Price Guide app.",
            font=BODY_FONT, text_color=GRAY, anchor="center").pack(
            anchor="center", padx=PAD_X, pady=(0, 18))

        # ── First-Time Setup ──────────────────────────────────────────────────
        section("🚀", "First-Time Setup")
        body("Do this once before using the app:")
        body("")
        step(1, "Open the Settings tab.")
        step(2, 'Set "Fallout 76 Game Root" to the folder that contains Fallout76.exe.\n'
                r"Common location:  C:\Program Files (x86)\Steam\steamapps\common\Fallout76"
                "\nThe app reads LegendaryMods.ini and ItemsMod.ini from the Data subfolder automatically.")
        step(3, 'Set "Fallout76Custom.ini" to your personal INI file.\n'
                r"Common location:  C:\Users\YourName\Documents\My Games\Fallout 76\Fallout76Custom.ini"
                "\nOnly needed for the mod installer — skip if installing mods manually.")
        step(4, 'Check the "Data Folder" path under Data Paths.\n'
                "This defaults to the Data folder next to the exe — where ServerData.7z, price_cache.json, and inventOmaticStashConfig.json live.\n"
                "If your data files are somewhere else, browse to that folder and save.")
        step(5, 'Set "ServerData.7z Path" to your price-data archive inside the Data folder.\n'
                "Loose .json and .txt trade files in the same folder are also loaded automatically.")
        step(6, "Fill in your Trade Post Profile in Settings: IGN, junk prices, crafting prices, and PNG colours.")
        step(7, "Click  💾 Save Settings.")
        step(8, "Switch to the Dashboard tab and click  ⟳ Load All Data.")
        body("")
        tip("The app auto-detects common Steam install paths on startup — check the Game Root field was pre-filled correctly.")
        tip("After installing or updating the InventOmatic Stash mod, launch Fallout 76 once and load a character before clicking Load All Data so the mod can write fresh INI files.")

        # ── Dashboard ─────────────────────────────────────────────────────────
        section("🏠", "Dashboard")
        body("The Dashboard is your home base. Everything starts here.")
        body("")
        subsection("Stats Bar")
        body("Four counters update automatically after every data load:")
        kv("MODS",       "Total unique (mod name + star tier) entries found in LegendaryMods.ini.")
        kv("PRICES",     "How many price entries are currently loaded into memory.")
        kv("COLLECTION", "How many (mod, star-tier) combinations are in your in-game inventory right now.")
        kv("VALUE",      "Estimated total trade value of your collection in Leaders, based on cached median prices.")
        body("")
        subsection("Load Buttons")
        kv("⟳ Load All Data",
           "Full load — reads mods from LegendaryMods.ini, loads prices (from cache if present, otherwise parses your archive), and scans your inventory. Use on first launch or after updating the archive.")
        kv("Load Collection Only",
           "Re-reads only your in-game inventory without touching price data. Fast — use this after playing when your stash has changed.")
        kv("Parse Price Data Only",
           "Forces a complete re-parse of ServerData.7z (and any loose files) and rebuilds the price cache from scratch. Use this when you have new trade data.")
        body("")
        tip("On startup the app automatically loads any existing price_cache.json so prices are ready immediately — no button click needed. The status bar says 'Cache auto-loaded' when this happens.")
        body("")
        subsection("Mod Installer Status")
        body("The bottom of the Dashboard shows whether the InventOmatic Stash mod and SFE are installed. Green ✓ means all files are present. If either shows ✗, go to Settings → Nexus Mod Manager.")

        # ── Price Guide ───────────────────────────────────────────────────────
        section("💰", "Price Guide Tab")
        body("A searchable table of every legendary mod with community-sourced trade prices.")
        body("")
        subsection("Table Columns")
        kv("★",         "Star rating of the mod (1 through 4).")
        kv("Mod Name",  "Canonical mod name exactly as it appears in LegendaryMods.ini.")
        kv("Price",     "Median trade price in Leaders. A tilde (~) means the price is estimated.")
        kv("Range",     "Low–High price band (Q1 to Q3 — the middle 50% of real trades).")
        kv("n",         "Number of unique trade posts used. 'est' = no real data found.")
        body("")
        subsection("Price Markers")
        kv("25L",  "Real price from actual trade posts — reliable.", key_width=60)
        kv("~9L",  "Estimated — no trade data found, uses the star-tier average. Treat as a rough guide.", key_width=60)
        kv("est",  "Shown in the n column for estimated entries.", key_width=60)
        body("")
        subsection("Search & Filter")
        body("Type any part of a mod name in the Search box to filter in real time. Case-insensitive, matches anywhere in the name.")
        body("")
        subsection("Export TXT")
        body("Saves a formatted plain-text price guide to a file of your choice. You are always prompted for a save location.")

        # ── Colour System ─────────────────────────────────────────────────────
        section("🎨", "The Colour System — White / Green / Orange")
        body("Every mod in your WTS list and generated PNG is colour-coded to tell buyers what they are getting.")
        body("")
        color_row("#FFFFFF", "White",  "You own the mod card but have NOT learned the recipe. You are selling the physical card — once sold it is gone.")
        color_row("#64DC64", "Green",  "You have LEARNED the recipe. You can craft this mod on demand. You provide Legendary Modules; the buyer brings the rest of the materials.")
        color_row("#FFA500", "Orange", "You can craft the mod BUT its materials cannot be traded (e.g. Overeater's, Glutton, Polished, Propelling). A special in-game arrangement is needed.")
        body("")
        warn("White / Green / Orange hex codes are fully customisable in Settings → PNG Colours & Legend. Save Settings after any change to refresh all lists and previews instantly.")

        # ── WTS ───────────────────────────────────────────────────────────────
        section("📦", "Trade Post — WTS (Want To Sell)")
        body("Build and manage your sell list, generate a PNG for posting, and copy plain text for chat.")
        body("")
        subsection("The WTS List (Left Panel)")
        kv("+ Add",             "Opens the Add Item dialog. Price is auto-filled from the median in your price cache.")
        kv("✎ Edit",            "Edit the selected item. Double-click any row to open the edit dialog.")
        kv("✕ Del",             "Remove the selected item from the list (no confirmation).")
        kv("⟳ Sync Collection", "Reads ItemsMod.ini and auto-populates the WTS list with everything you own, quantities and cached prices included. Colour reflects craft status.")
        body("")
        body("Items are sorted by star tier (1★ first) then alphabetically. Row colour follows the White / Green / Orange system.")
        body("")
        subsection("Add / Edit Item Dialog")
        kv("Mod",        "Searchable dropdown — every mod from LegendaryMods.ini, sorted star-first. Type any part of the name to filter instantly.")
        kv("Qty / Mode", "'each' = price per individual mod. 'all' = one price for the entire quantity.")
        kv("Price (L)",  "Price in Leaders. Auto-filled from the cache — adjust freely. Green hint shows the cached median.")
        kv("WTT",        "Want To Trade — the mod you want in exchange (optional). Appears on the PNG card.")
        body("")
        tip("Setting Qty to 0 marks the item as 'sold out' — it still appears on the PNG so buyers know you stock it.")
        body("")
        subsection("Bottom Action Bar")
        kv("💾 Save PNG",   "Saves the WTS image as a PNG. Always prompts for save location (default: Exports folder).")
        kv("📋 Copy Text", "Copies a plain-text WTS post to clipboard.")
        kv("↑ Export",     "Saves your WTS item list as a JSON backup file.")
        kv("↓ Import",     "Loads a previously exported JSON list. Choose to replace or append to your current list.")
        kv("Show Junk Mods","Toggle the 'Buying Junk Mods' price line in the PNG and text. Synced between WTS and WTB tabs.")
        body("")
        tip("Export your WTS list to JSON regularly — restoring takes one click.")

        # ── WTB ───────────────────────────────────────────────────────────────
        section("🛒", "Trade Post — WTB (Want To Buy)")
        body("Build a Looking For list, generate a matching PNG, and copy a ready-to-post message. WTB is free-form — not limited to known mod names.")
        body("")
        subsection("The WTB List (Left Panel)")
        kv("+ Add",       "Opens the Add WTB Item dialog.")
        kv("✎ Edit",      "Edit the selected item (or double-click it).")
        kv("✕ Del",       "Remove the selected item.")
        kv("✕ Clear All", "Remove every item from the WTB list. A confirmation dialog appears first.")
        body("")
        subsection("Add / Edit WTB Item Dialog")
        kv("Looking For",    "Choose from the mod dropdown (stars-first, searchable) OR type any free text.")
        kv("Qty / Mode",     "How many you want. 'each' = price per piece. 'all' = one price for the whole lot.")
        kv("Price (L)",      "Leaders you are willing to pay. 0 = open offer with no price shown.")
        kv("Notes",          "Optional extra detail shown in brackets on the PNG card.")
        kv("WTT Mod",        "Want To Trade — mod you are offering in exchange.")
        kv("WTT Qty / Mode", "How many WTT mods you offer, and whether 'ea' or 'all'.")
        body("")
        subsection("Bottom Action Bar")
        kv("💾 Save PNG",          "Saves the WTB image as a PNG. Always prompts for save location.")
        kv("📋 Copy Text",         "Copies a formatted WTB post with 'Looking For:' header.")
        kv("↑ Export / ↓ Import", "Backup and restore your WTB list as JSON — same as WTS.")
        kv("Show Junk Mods",       "Synced with the WTS tab.")

        # ── Settings ──────────────────────────────────────────────────────────
        section("⚙️", "Settings Tab")
        body("All configuration lives here. 💾 Save Settings buttons appear at both the top and bottom of the page.")
        body("")
        subsection("Game Paths")
        kv("Fallout 76 Game Root",
           "Folder containing Fallout76.exe. LegendaryMods.ini and ItemsMod.ini are read from the Data subfolder automatically. Click Browse to pick the folder.")
        kv("Fallout76Custom.ini",
           "Your personal INI file. Only needed by the mod installer. Click Browse to locate it.")
        tip("The app scans common Steam install locations on startup and pre-fills these where possible. Double-check before your first Load All Data.")
        body("")
        subsection("Data Paths")
        kv("Data Folder",
           "The folder that contains all app data — ServerData.7z, inventOmaticStashConfig.json, price_cache.json, and raw_cache.json. Defaults to the Data folder next to the exe. Browse to change it.")
        kv("ServerData.7z Path",
           "Full path to your price-data archive inside the Data folder. Loose .json and .txt files in the same folder are also picked up automatically as a fallback.")
        kv("Downloads Folder",
           "Where your browser saves downloaded files. Used by the mod installer to auto-detect a mod archive after a Nexus slow-download completes.")
        body("")
        tip("You can 7-Zip your own mix of .json and .txt trade files into ServerData.7z. The app accepts both formats and processes them together in one pass.")
        body("")
        subsection("Trade Post Profile")
        body("Controls how your trade post images and text look. Changes take effect after saving.")
        kv("In-Game Name (IGN)",       "Shown in gold on every PNG and at the top of copied text posts.")
        kv("Junk Mod Buy Prices",      "Leaders you pay per star tier for junk mods. Appears in the 'Buying Junk Mods' line.")
        kv("Crafting Service Prices",  "What you charge per star tier for crafting a mod. Shown in the Green legend box on WTS PNGs.")
        body("")
        subsection("PNG Colours & Legend")
        body("Three colour rows (White / Green / Orange) each have:")
        kv("Hex Colour",       "#RRGGBB code. A live swatch updates as you type.")
        kv("Bold Label",       "Short bold heading in the legend box (e.g. 'Cannot Craft', 'Can Craft').")
        kv("Description Text", "Longer explanation shown after the label in the legend box.")
        body("")
        body("'Other PNG Colours' section lets you change:")
        kv("Background",   "Overall image background colour.")
        kv("Mod Card",     "Fill colour of each individual mod card.")
        kv("IGN",          "IGN text colour at the top of the image.")
        kv("Stars",        "Star icon colour on cards and the craft price sub-line.")
        kv("Title Text",   "Large 'Want To Sell / Want To Buy' header colour.")
        kv("Notice Text",  "'Read the colour guide' banner text and triangle colour.")
        kv("Buying Junk",  "'Buying Junk Mods' label text colour.")
        body("")
        tip("Every colour field has a live swatch beside it — you see the colour before you save.")
        warn("Colour codes must be exactly 7 characters in the format #RRGGBB (e.g. #FF6600). Invalid codes are replaced with the default when you save.")
        body("")
        subsection("Reset to Defaults")
        body("Instantly restores every profile field — IGN, prices, colours, labels, and descriptions — to the built-in defaults. Saves to disk and refreshes all lists and previews immediately.")
        body("")
        subsection("Nexus Mod Manager")
        body("Download and install mods directly from NexusMods.com — no manual file-copying required.")
        body("")
        kv("Nexus API Key",
           "Generate a free Personal API Key at nexusmods.com → Account → API Access. Paste it and save. Stored only in settings.json on your PC — sent only to api.nexusmods.com.")
        kv("↗ Nexus Page",
           "Opens the official mod page in your browser.")
        kv("⬇ Download & Install",
           "Queries the Nexus API for the latest Main file, downloads it, extracts the archive, copies .dll and .ba2 files to your game directory, and updates Fallout76Custom.ini automatically.")
        kv("✕ Uninstall",
           "Removes the mod files from your game directory and strips the ba2 entry from Fallout76Custom.ini. Asks for confirmation first. Runs in the background — the UI stays responsive.")
        body("")
        body("Currently managed mods:")
        kv("Invent-O-Matic Stash (Unofficial)",
           "Required — exports your legendary mod inventory to LegendaryMods.ini and ItemsMod.ini so the app can read your collection. By Demorome.")
        kv("Script Functions Extender (SFE)",
           "Required by InventOmatic — DLL-based script extender. By Keretus. Installs as dxgi.dll in your game root.")
        body("")
        warn("Free Nexus accounts cannot get direct download links via the API. If you see a 'One More Click Required' message, click 'Slow Download' in the browser — the installer watches your Downloads folder and installs the file automatically when it finishes.")
        tip("After installing InventOmatic Stash: launch Fallout 76, load any character, then quit. The mod writes INI files on game load. Then click 'Load Collection Only' on the Dashboard.")
        body("")
        subsection("Cache Management")
        kv("🗑 Clear Caches", "Deletes price_cache.json and raw_cache.json from the Data folder. The next 'Load All Data' or 'Parse Price Data Only' will rebuild them from scratch. Use after receiving updated trade data files.")

        # ── Game Data Files ───────────────────────────────────────────────────
        section("🎮", "Game Data Files (InventOmatic Stash Mod)")
        body("The InventOmatic Stash mod writes two INI files to your game's Data folder when you load a character in-game. You never need to edit them by hand.")
        body("")
        kv("LegendaryMods.ini",
           "The canonical list of every legendary mod in the game, with supported star tiers and which ones your characters have learned (can craft). The app uses this as its master mod database — no external CSV or hardcoded list needed.")
        kv("ItemsMod.ini",
           "Your actual inventory: every legendary mod card in your stash and on your characters, with quantities. Cross-referenced against LegendaryMods.ini to determine what you own and at what star tier.")
        body("")
        body("The app validates every entry from ItemsMod.ini against LegendaryMods.ini. Known bad game data entries (e.g. Barbarian 4★) are silently filtered out.")
        tip("Multi-star mods are tracked independently — Anti-armor 2★ × 3 and Anti-armor 3★ × 1 appear as two separate entries with separate quantities and prices.")

        # ── How Prices Work ───────────────────────────────────────────────────
        section("📊", "How Prices Are Calculated")
        body("Prices come from trade messages in your data archive. Here is the full pipeline:")
        body("")
        kv("Source",              "Every .json and .txt file in ServerData.7z (or loose in the Data folder). Both Leaders and caps prices are detected; caps convert at 1 Leader ≈ 1000 caps.")
        kv("JSON format",         "Files with a 'messages' key are parsed as structured message exports.")
        kv("TXT format",          "Plain-text files are split on blank lines — each block is one trade post.")
        kv("Validation",          "Each detected price is checked against the expected range for its star tier. Out-of-range prices are rejected immediately.")
        kv("IQR Outlier Removal", "Extreme outliers are removed using the Tukey fence test (1.5 × IQR above Q3 and below Q1). Stops a few wildly overpriced posts from skewing results.")
        kv("Deduplication",       "Posts with the same (source file, author, timestamp) triplet are counted only once. Prevents copy-paste spam from inflating the sample size.")
        kv("Statistics",          "Median = middle value (best reference),  Low = Q1 (25th percentile),  High = Q3 (75th percentile),  n = unique posts used.")
        kv("Estimated",           "If a mod has no real data, an estimated price is assigned equal to the median of all real prices for that star tier. Marked with ~ and 'est'.")
        kv("Caching",             r"After parsing, results are saved to Data\price_cache.json. Subsequent loads read the cache instantly. Use Clear Caches to force a rebuild.")
        body("")
        tip("The more trade posts your archive contains, the more accurate the prices. Add more .json or .txt files to your ServerData.7z and re-parse to improve results.")

        # ── Troubleshooting ───────────────────────────────────────────────────
        section("🔧", "Troubleshooting")
        body("Work through the symptom that matches your problem:")
        body("")
        kv('"No mods loaded"',
           r"Game Root path is wrong or the folder does not contain Data\LegendaryMods.ini. Go to Settings and browse to the folder containing Fallout76.exe.",
           "orange")
        kv('"Game path not found"',
           "The path saved in Settings does not exist on disk — check the drive and folder. Browse again and save.",
           "orange")
        kv('"Auto-load failed" on startup',
           "price_cache.json is present but corrupt. Go to Settings → Clear Caches, then click Load All Data to rebuild it.",
           "orange")
        kv("Collection shows 0",
           "InventOmatic Stash mod is not installed, or you have not launched the game since installing it. Install the mod (Settings → Nexus Mod Manager), launch Fallout 76, load a character, quit, then click Load Collection Only.",
           "orange")
        kv("All prices show as estimated (~)",
           "The archive was not parsed successfully or contains no recognisable trade posts. Go to Settings → Clear Caches, then Parse Price Data Only and check the console output for errors.",
           "orange")
        kv("Prices look wrong or very old",
           "You need newer trade data. Add updated .json or .txt files to ServerData.7z, then click Parse Price Data Only on the Dashboard.",
           "orange")
        kv("PNG preview is blank",
           "Add at least one item to the WTS or WTB list first — the preview only renders when there is something to show. If items are present but preview is blank, click ⟳ Refresh.",
           "orange")
        kv("Mod installer fails",
           r"Make sure Fallout 76 is completely closed before installing. If Fallout76Custom.ini does not exist yet, launch the game once to generate it, then try again. If the Nexus API key is invalid, re-generate it at nexusmods.com → Account → API Access.",
           "orange")
        kv("INI entry not removed on uninstall",
           "Check that the Fallout76Custom.ini path in Settings points to the correct file. The uninstall runs in the background — any errors appear in the result dialog.",
           "orange")
        kv("A mod is missing from the dropdown",
           "Some mods only exist at specific star tiers. The dropdown shows every valid combination from LegendaryMods.ini. If a whole mod is missing, it may not be in your game data yet.",
           "orange")
        kv("Colour changes not updating",
           "Click 💾 Save Settings after every colour change. Saving triggers an immediate refresh of the WTS list, WTB list, and both PNG previews.",
           "orange")
        kv("TXT file not parsed",
           r"Make sure the .txt file is inside ServerData.7z (or loose in the Data folder). Each trade post should be separated by a blank line and contain price values like '5L' or '25 leaders' next to mod names.",
           "orange")

        # ── File Reference ────────────────────────────────────────────────────
        section("📁", "File & Folder Reference")
        body("All paths relative to the folder where the exe (or F76PriceGuide.py) lives:")
        body("")
        kv("settings.json",                        "All your settings, Nexus API key, and Trade Post Profile. Safe to back up.", key_width=280)
        kv("Data\\",                             "Your data folder (configurable in Settings > Data Paths). Default: Data\\ next to the exe.", key_width=280)
        kv("Data\\ServerData.7z",                "Your price-data archive. Pack .json and/or .txt trade files inside. You provide this.", key_width=280)
        kv("Data\\price_cache.json",             "Parsed price data. Rebuilt automatically on parse. Safe to delete.", key_width=280)
        kv("Data\\raw_cache.json",               "Intermediate parse data. Always safe to delete.", key_width=280)
        kv("Data\\inventOmaticStashConfig.json", "Config for the InventOmatic mod. Synced to your game's Data folder on install and startup.", key_width=280)
        kv("Exports\\",                          "Default save folder for PNGs and TXT exports. Created automatically on first export.", key_width=280)
        body("")
        body("Game files written by the mod (in your Fallout 76 Data folder):")
        kv("<GameRoot>\\Data\\LegendaryMods.ini", "Master mod list + learned recipe flags.", key_width=320)
        kv("<GameRoot>\\Data\\ItemsMod.ini",       "Your inventory quantities per mod per star tier.", key_width=320)
        kv("<GameRoot>\\dxgi.dll",                   "SFE script extender DLL -- installed by Nexus Mod Manager.", key_width=320)

        # ── Tips & Tricks ─────────────────────────────────────────────────────
        section("✨", "Tips & Tricks")
        tip("Use ⟳ Sync Collection on the WTS tab after every play session to auto-populate your sell list with current quantities and cache prices — one click.")
        tip("Set Mode to 'all' when you have multiple copies of a cheap mod and want to sell the whole lot for one bulk price.")
        tip("The WTT field on both WTS and WTB lets you propose a trade-for-trade deal directly on the PNG.")
        tip("Type partial mod names in the dropdown — 'anti' instantly filters to Anti-armor and anything else containing 'anti'. You do not need the full name.")
        tip("Export WTS and WTB lists to JSON at the end of each session. Restoring from JSON is instant if you reinstall or move the app.")
        tip("Pack multiple .json and .txt files into one ServerData.7z. The app processes every file in the archive in one pass — great for combining data from different sources.")
        tip("If the Price Guide shows obviously wrong values for a specific mod, look for the '~' prefix and low 'n' value — these signal low confidence from sparse trade data.")
        tip("The inventOmaticStashConfig.json in your Data folder is automatically copied to your game directory every time you install the mod or launch the app — your settings are always applied.")

        ctk.CTkFrame(S, height=40, fg_color="transparent").pack()



    def _browse(self, target):
        if target == "archive":
            path = filedialog.askopenfilename(
                filetypes=[("7-Zip archive", "*.7z"), ("All files", "*.*")],
                title="Select ServerData.7z"
            )
            if path:
                self.json_entry.delete(0, "end")
                self.json_entry.insert(0, winpath(path))
        elif target == "game_root":
            path = filedialog.askdirectory()
            if path:
                self.game_root_entry.delete(0, "end")
                self.game_root_entry.insert(0, winpath(path))
        elif target == "ini":
            path = filedialog.askopenfilename(filetypes=[("INI files", "*.ini"), ("All", "*.*")])
            if path:
                self.ini_entry.delete(0, "end")
                self.ini_entry.insert(0, winpath(path))
        elif target == "data_dir":
            path = filedialog.askdirectory(title="Select your Data folder")
            if path:
                self.data_dir_entry.delete(0, "end")
                self.data_dir_entry.insert(0, winpath(path))
        elif target == "downloads":
            path = filedialog.askdirectory(title="Select your Downloads folder")
            if path:
                self.downloads_entry.delete(0, "end")
                self.downloads_entry.insert(0, winpath(path))
    
    def _save(self):
        if hasattr(self, 'data_dir_entry'):
            self.settings["data_dir"] = winpath(self.data_dir_entry.get())
        self.settings["archive_path"] = winpath(self.json_entry.get())
        self.settings["game_root"] = winpath(self.game_root_entry.get())
        self.settings["ini_path"] = winpath(self.ini_entry.get())
        if hasattr(self, 'downloads_entry'):
            self.settings["downloads_path"] = winpath(self.downloads_entry.get())
        # Save Nexus API key (stored locally only, never transmitted except to api.nexusmods.com)
        if hasattr(self, 'nexus_api_entry'):
            self.settings["nexus_api_key"] = self.nexus_api_entry.get().strip()
        # Derive game_path (Data folder) from game_root for backward compatibility
        game_root = self.game_root_entry.get()
        if game_root:
            self.settings["game_path"] = winpath(Path(game_root) / "Data")
        # Save trade post profile
        profile = {}
        profile["ign"] = self.prof_ign.get().strip()
        for key, e in self.prof_junk.items():
            profile[key] = e.get().strip() or PROFILE_DEFAULTS[key]
        for key, e in self.prof_craft.items():
            profile[key] = e.get().strip() or PROFILE_DEFAULTS[key]
        for key, e in self.prof_colors.items():
            val = e.get().strip()
            profile[key] = val if val.startswith("#") and len(val) == 7 else PROFILE_DEFAULTS[key]
        for key, e in self.prof_labels.items():
            profile[key] = e.get().strip() or PROFILE_DEFAULTS[key]
        for key, e in self.prof_descs.items():
            profile[key] = e.get().strip() or PROFILE_DEFAULTS[key]
        self.settings["profile"] = profile
        self._save_settings()
        self._check_install_status()  # Update install status after saving
        # Refresh listbox colours and PNG previews so all changes appear immediately
        self._refresh_wts()
        self._refresh_wtb()
        self._refresh_wts_preview()
        self._refresh_wtb_preview()
        self._apply_data_dir()   # re-point DATA_DIR if the user changed it
        messagebox.showinfo("Saved", "Settings saved!")

    def _show_progress(self):
        self.progress_pct.pack(side="top", pady=(0, 2))
        self.progress.pack(side="top")
        self.progress.set(0)
        self.progress_pct.configure(text="0%")
        self._progress_target = 0.0
        self._progress_current = 0.0

    def _hide_progress(self):
        self.progress.pack_forget()
        self.progress_pct.pack_forget()
        self.progress_pct.configure(text="")
        self._progress_target = 0.0
        self._progress_current = 0.0

    def _animate_progress(self):
        """Smooth interpolation tick — called repeatedly until target is reached."""
        if not hasattr(self, '_progress_current'):
            return
        diff = self._progress_target - self._progress_current
        if abs(diff) < 0.001:
            self._progress_current = self._progress_target
            self.progress.set(self._progress_current)
            pct = int(self._progress_current * 100)
            label = getattr(self, '_progress_label', '')
            self.progress_pct.configure(text=f"{pct}%  {label}".strip() if label else f"{pct}%")
            return
        # Ease toward target: move ~20% of remaining gap per frame (16 ms ≈ 60 fps)
        step = max(diff * 0.20, 0.002) if diff > 0 else min(diff * 0.20, -0.002)
        self._progress_current = min(max(self._progress_current + step, 0.0), 1.0)
        self.progress.set(self._progress_current)
        pct = int(self._progress_current * 100)
        label = getattr(self, '_progress_label', '')
        self.progress_pct.configure(text=f"{pct}%  {label}".strip() if label else f"{pct}%")
        self.after(16, self._animate_progress)

    def _set_progress(self, value: float, label: str = ""):
        """Update progress bar target, percentage label, and optionally status text.
        The bar animates smoothly to the target value rather than jumping."""
        self._progress_target = max(getattr(self, '_progress_target', 0.0), float(value))
        self._progress_label = label
        if label:
            self.status.configure(text=label)
        # Start animation loop only if not already running
        if not getattr(self, '_progress_animating', False):
            self._progress_animating = True
            def _anim_loop():
                self._animate_progress()
                diff = abs(self._progress_target - self._progress_current)
                if diff >= 0.001:
                    self.after(16, _anim_loop)
                else:
                    self._progress_animating = False
            self.after(0, _anim_loop)

    def _load_all(self):
        """Load all data - uses LegendaryMods.ini as CANONICAL source with guaranteed 1:1 matching."""
        self.after(0, self._show_progress)
        def task():
            game_path = self.settings.get("game_path", DEFAULT_GAME_PATH)

            if not Path(game_path).exists():
                self.after(0, lambda p=game_path: messagebox.showerror(
                    "Game Path Not Found",
                    f"Game Data folder not found:\n\n{p}\n\n"
                    "Please set the correct Fallout 76 Game Root in Settings."
                ))
                self.after(0, lambda: self.status.configure(text="ERROR: Game path not found - check Settings"))
                self.after(0, self._hide_progress)
                return

            # Step 1 — Load mods
            self.after(0, lambda: self._set_progress(0.05, "Loading mods from LegendaryMods.ini..."))
            self.mods, self.name_lookup, self.mod_total_entries = load_mods_from_ini(game_path)

            if not self.mods:
                self.after(0, lambda: self.status.configure(text="ERROR: No mods loaded from LegendaryMods.ini!"))
                self.after(0, self._hide_progress)
                return

            print(f"Loaded {self.mod_total_entries} mod entries, {len(self.mods)} unique names, {len(self.name_lookup)} lookup entries")
            self.after(0, lambda: self._set_progress(0.1, "Mods loaded"))

            # Step 2 — Prices
            archive_path = Path(self.settings.get("archive_path", str(DATA_DIR / "ServerData.7z")))
            price_cache_path = DATA_DIR / "price_cache.json"

            def progress_cb(value: float, label: str = ""):
                mapped = 0.1 + value * 0.55
                self.after(0, lambda v=mapped, l=label: self._set_progress(v, l))

            if not price_cache_path.exists():
                self.after(0, lambda: self._set_progress(0.1, "Building price cache from trade data..."))
                print("\nPrice cache not found - parsing trade data...")
                raw_prices = run_parser(DATA_DIR, game_path, force_parse=True,
                                        archive_path=archive_path, progress_cb=progress_cb)
            else:
                self.after(0, lambda: self._set_progress(0.15, "Loading prices from cache..."))
                raw_prices = load_prices_and_match_to_mods(DATA_DIR, self.mods)

            self.after(0, lambda: self._set_progress(0.65, "Processing prices..."))
            prices = {}
            for key, val in raw_prices.items():
                name = val.get('name', '')
                star = val.get('star', 0)
                if not name or not star:
                    parts = key.rsplit('_', 1)
                    name = name or parts[0]
                    try:
                        star = star or int(parts[1])
                    except (IndexError, ValueError):
                        star = star or 1
                if name not in self.mods or star not in self.mods[name]:
                    continue
                canonical_key = f"{name}_{star}"
                prices[canonical_key] = PriceData(
                    name=name, star=star,
                    median=val.get('median', 0), low=val.get('low', 0),
                    high=val.get('high', 0), n=val.get('n', 0),
                    estimated=val.get('estimated', False)
                )
            self.prices = prices
            print(f"Loaded {len(self.prices)} prices")
            self.after(0, lambda: self._set_progress(0.75, f"Loaded {len(self.prices)} prices"))

            # Step 3 — Collection
            self.after(0, lambda: self._set_progress(0.85, "Loading collection from game..."))
            self.coll = load_collection_with_canonical(self.mods, self.name_lookup, game_path)
            self.after(0, lambda: self._set_progress(0.95, "Finalising..."))

            self.after(0, self._update_ui)

        threading.Thread(target=task, daemon=True).start()

    def _load_collection_only(self):
        """Load just the collection from game files - faster when prices are already loaded."""
        self.after(0, self._show_progress)
        def task():
            if not self.mods:
                self.after(0, lambda: self.status.configure(text="ERROR: Load mods first — click 'Load All Data' first"))
                self.after(0, self._hide_progress)
                return

            self.after(0, lambda: self.status.configure(text="Loading collection from game..."))
            game_path = self.settings.get("game_path", DEFAULT_GAME_PATH)
            self.coll = load_collection_with_canonical(self.mods, self.name_lookup, game_path)
            self.after(0, lambda: self._set_progress(0.9, "Collection loaded"))

            self.after(0, self._update_ui_collection_only)

        threading.Thread(target=task, daemon=True).start()

    def _parse_discord_only(self):
        """Force re-parse price data from ServerData.7z - bypasses cache."""
        self.after(0, self._show_progress)
        def task():
            if not self.mods:
                self.after(0, lambda: self.status.configure(text="ERROR: Load mods first — click 'Load All Data' first"))
                self.after(0, self._hide_progress)
                return

            game_path    = self.settings.get("game_path", DEFAULT_GAME_PATH)
            archive_path = Path(self.settings.get("archive_path", str(DATA_DIR / "ServerData.7z")))

            def progress_cb(value: float, label: str = ""):
                mapped = value * 0.7
                self.after(0, lambda v=mapped, l=label: self._set_progress(v, l))

            self.after(0, lambda: self._set_progress(0.0, "Parsing trade data files..."))
            raw_prices = run_parser(DATA_DIR, game_path, force_parse=True,
                                    archive_path=archive_path, progress_cb=progress_cb)
            self.after(0, lambda: self._set_progress(0.72, "Processing prices..."))
            valid_mods = build_valid_mods_set(self.mods)
            processed_prices = {}
            for key, val in raw_prices.items():
                name = val.get('name', '')
                star = val.get('star', 0)
                if not name or not star:
                    parts = key.rsplit('_', 1)
                    name = name or parts[0]
                    try:
                        star = star or int(parts[1])
                    except (IndexError, ValueError):
                        star = star or 1
                if (name, star) in valid_mods:
                    canonical_key = f"{name}_{star}"
                    processed_prices[canonical_key] = PriceData(
                        name=name, star=star,
                        median=val.get('median', 0), low=val.get('low', 0),
                        high=val.get('high', 0), n=val.get('n', 0),
                        estimated=val.get('estimated', False)
                    )
            self.prices = processed_prices
            print(f"Valid prices: {len(self.prices)}")
            self.after(0, lambda: self._set_progress(0.9, f"{len(self.prices)} prices ready"))
            self.after(0, self._update_ui_prices_only)

        threading.Thread(target=task, daemon=True).start()

    def _update_ui_collection_only(self):
        """Update UI after loading collection only."""
        self.stat_coll.configure(text=f"{len(self.coll)}")
        self._refresh_collection_value()
        self._refresh_wts()
        self.status.configure(text="Collection loaded!")
        self._set_progress(1.0)
        self.after(1000, self._hide_progress)

    def _update_ui_prices_only(self):
        """Update UI after parsing price data only."""
        self.stat_prices.configure(text=f"{len(self.prices)}")
        self._refresh_prices()
        self.status.configure(text="Price data parsed!")
        self._set_progress(1.0)
        self.after(1000, self._hide_progress)

    def _refresh_collection_value(self):
        """Refresh collection value display."""
        val = 0
        for c in self.coll:
            key = f"{c.name}_{c.star}"
            pd = self.prices.get(key)
            if pd and pd.median > 0:
                val += int(pd.median) * c.qty
        self.stat_val.configure(text=f"{val}L")

    def _clear_caches(self):
        """Clear price and raw cache files."""
        if clear_caches(DATA_DIR):
            messagebox.showinfo("Caches Cleared", "Price caches have been cleared.\nNext load will re-parse your trade data files.")
        else:
            messagebox.showinfo("No Caches Found", "No cache files found to clear.")
    
    def _update_ui(self):
        # Show total entries (each name+star combo is unique), not just unique names
        self.stat_mods.configure(text=f"{getattr(self, 'mod_total_entries', len(self.mods))}")
        self.stat_prices.configure(text=f"{len(self.prices)}")
        self.stat_coll.configure(text=f"{len(self.coll)}")

        val = 0
        for c in self.coll:
            key = f"{c.name}_{c.star}"
            pd = self.prices.get(key)
            if pd and pd.median > 0:
                val += int(pd.median) * c.qty
        self.stat_val.configure(text=f"{val}L")

        self._refresh_prices()
        self._refresh_wts()
        self.status.configure(text="Done!")
        self._set_progress(1.0)
        self.after(1000, self._hide_progress)
    
    def _refresh_prices(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        search = self.search.get().lower()
        for key, pd in sorted(self.prices.items(), key=lambda x: (x[1].star, x[0])):
            if search and search not in pd.name.lower():
                continue
            
            price_str = f"~{int(pd.median)}L" if pd.estimated else f"{int(pd.median)}L"
            n_str = "est" if pd.estimated else pd.n
            
            self.tree.insert("", "end", values=(
                stars_unicode(pd.star),
                pd.name,
                price_str,
                f"{int(pd.low)}-{int(pd.high)}",
                n_str
            ))
    
    def _filter(self, event=None):
        self._refresh_prices()
    
    def _sync(self):
        """Reload collection from game files and rebuild the WTS list."""
        if not self.mods or not hasattr(self, 'name_lookup'):
            messagebox.showwarning("Not Ready", "Please click 'Load All Data' on the Dashboard first.")
            return
        game_path = self.settings.get("game_path", DEFAULT_GAME_PATH)
        self.coll = load_collection_with_canonical(self.mods, self.name_lookup, game_path)

        self.wts = []
        for c in self.coll:
            key = f"{c.name}_{c.star}"
            pd = self.prices.get(key)
            price = int(pd.median) if pd and pd.median > 0 else 0
            self.wts.append(TradeItem(c.star, c.name, c.qty, price, "each", "", c.learned, c.name in UNTRADEABLE_MATERIAL_MODS))
        self._refresh_wts()
    
    def _export_txt(self):
        """Export full price guide as formatted TXT"""
        if not self.prices:
            messagebox.showwarning("Warning", "No price data loaded. Click 'Load All Data' first.")
            return
        
        # Generate header
        lines = []
        lines.append("╔" + "═" * 78 + "╗")
        lines.append("║" + " FALLOUT 76 LEGENDARY ITEM PRICE GUIDE ".center(78) + "║")
        lines.append("╠" + "═" * 78 + "╣")
        lines.append("║" + f" Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')} ".center(78) + "║")
        lines.append("╠" + "═" * 78 + "╣")
        lines.append("║" + " PRICE LEGEND ".center(78, "─") + "║")
        lines.append("║" + "  Median = Middle value - BEST REFERENCE".ljust(78) + "║")
        lines.append("║" + "  Low/High = Typical price range".ljust(78) + "║")
        lines.append("║" + "  ~ = estimated price (low sample data)".ljust(78) + "║")
        lines.append("╚" + "═" * 78 + "╝")
        lines.append("")
        
        # Group by star rating
        for star in [4, 3, 2, 1]:
            star_items = [(k, p) for k, p in self.prices.items() if p.star == star]
            if not star_items:
                continue
            
            star_items.sort(key=lambda x: x[1].name.lower())
            
            lines.append("┌" + "─" * 78 + "┐")
            lines.append("│" + f" ★ {star}-STAR LEGENDARY MODIFICATIONS ".center(78, "─") + "│")
            lines.append("├" + "─" * 78 + "┤")
            
            for key, pd in star_items:
                name = pd.name
                if len(name) > 28:
                    name = name[:26] + ".."
                
                est_marker = "~" if pd.estimated else ""
                price_str = f"{est_marker}{int(pd.median)}L"
                
                line = f"  {name.ljust(28)} │ Median: {price_str:>8} │ Range: {int(pd.low)}-{int(pd.high)}L"
                lines.append("│" + line.ljust(78) + "│")
            
            lines.append("└" + "─" * 78 + "┘")
            lines.append("")
        
        # Footer
        lines.append("─" * 80)
        lines.append("  White=I have this mod — cannot craft tho | Green=Can Craft | Orange=Can Craft (untradeable materials)")
        lines.append("  Happy Trading! 🎮")
        
        # Save to file
        EXPORT_DIR.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=str(EXPORT_DIR),
            initialfile=f"F76_Price_Guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            title="Export Price Guide TXT"
        )
        if not path:
            return
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Exported", f"Price guide saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    EXPORT_DIR.mkdir(exist_ok=True)

    # ── NXM protocol handler entry-point ──────────────────────────────────────
    # When Windows launches us via the nxm:// registry entry, sys.argv[1] is the URL.
    # If another instance is already running, forward it and exit immediately.
    if len(sys.argv) > 1 and sys.argv[1].lower().startswith("nxm://"):
        nxm_url = sys.argv[1]
        if nxm_forward_to_running_instance(nxm_url):
            return   # forwarded — existing instance handles it
        # No running instance; fall through and start app normally with the URL queued
        _pending_nxm = [nxm_url]
    else:
        _pending_nxm = []

    app = App(pending_nxm=_pending_nxm)
    app.mainloop()

if __name__ == "__main__":
    main()