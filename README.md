# Genshin Tracker

A local web app for tracking Genshin Impact character, weapon, and Traveller goals against your inventory. It runs on your computer with Python and stores changes in the included SQLite database. You do not need the old Excel workbook or any import scripts to use it.

## Start the app

Install **Python 3.10 or newer**. On Windows, open PowerShell in the project folder (the folder containing `app_v2.py` and `genshin_v2.db`), then run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn
.\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload
```

Open <http://127.0.0.1:8000/> in your browser. Keep the PowerShell window open while using the app. Press **Ctrl+C** there to stop it. On later visits, run only the last command from the project folder; the environment and packages are already installed.

If `py` is unavailable but `python` works, substitute `python` for `py -3` in the first command. On macOS or Linux, use `python3 -m venv .venv`, install packages with `.venv/bin/python -m pip install fastapi uvicorn`, and start with `.venv/bin/python -m uvicorn app_v2:app --reload`.

The included `genshin_v2.db` already contains the catalog, inventory, goals, cost rules, and material links. **Do not run a database creation or workbook import script.** The app can create small supporting lookup tables itself when you use certain editors.

## Keep your data safe

The app saves directly to `genshin_v2.db`. Before a large edit or an update from GitHub, stop the app and copy that file to a safe location. If you replace the database with a fresh copy from the repository, you replace your saved inventory and progress too. To restore a backup, stop the app, put your backed-up `genshin_v2.db` in the project folder, then restart it.

Python's `__pycache__/` files and the local `.venv/` environment are generated; they are not your saved game data.

## Pages and everyday use

| Page | What it does |
| --- | --- |
| **Inventory Overview** (`/`) | Lists materials by category and family. Enter the **new total owned** in **Update Value**, then save. It shows requirements for saved goals and for maxing the catalog. |
| **Goals** (`/goals`) | Set target levels, ascensions, and talents for characters, weapon copies, and Traveller elements. **Record Current Progress** after leveling up. The page also lists goals excluded because their costs are incomplete. |
| **Characters**, **Weapons**, **Traveller** | View progress in separate tables. Click headings to sort, enter text below headings to filter, and use **Show or Hide Columns** to choose visible columns. These view choices reset on reload. The far-right **Actions** column opens the relevant editor. |
| **Add data** (`/catalog`) | Add characters, weapons, and material types; edit existing data; complete missing material types. |

A weapon may have any number of copies. Goals and current progress belong to each copy, while its name, rarity, type, and material families belong to the weapon. The Goals summary counts **unique weapons**, rather than copies. The max calculation includes the first copy of each weapon; saved goals include the copies you have set up.

Saving current progress raises a target if the new current value passes it. It does **not** subtract spent materials from inventory. Update the owned total separately to match what you actually have.

### Reading the overview

**Required**, **Owned**, and **Still Needed** compare all included goals with your inventory. **Max Required** and **To Max** compare the inventory with a ceiling where every character reaches level 90, ascension 6, and three level 10 talents; first copies of weapons reach their supported maximum (level 70 / ascension 4 for 1★ and 2★ weapons, level 90 / ascension 6 otherwise). Traveller's shared level and ascension are included, along with defined talent costs for its elements.

For three or four tier families, the conversion columns show lower tier materials that would be consumed at a 3:1 rate. Weekly boss materials can be exchanged within a boss family at 1:1. These columns are estimates for each scenario, **not** automatic inventory changes. Highlighted cells indicate a shortage or needed conversion for saved goals.

Character and weapon EXP items are entered as item counts. Each EXP section totals the points held across its item denominations and compares them with required EXP. Using items can overshoot the exact target and cost more Mora than the displayed baseline.

**Cryo Traveller talent costs are not yet defined.** Leave Cryo talent goals at their current levels; otherwise Traveller is excluded from the affected totals. The overview marks its max totals as incomplete for the same reason. Other missing material links appear as exclusions until completed.

## Add and correct catalog data

On **Add data → Add New**, use **New Character** or **New Weapon** to create an entry at level 1 and ascension 0 (with talents at level 1 for characters). New weapons start with Copy 1. The element determines a character's gem type. Choose existing material types when available.

Use **New Material** to choose a category such as Talent Material, Weapon Ascension Material, Common Enemy Drop, Elite Enemy Drop, Weekly Boss Drop, World Boss Drop, or Local Speciality. Enter a type name and the material names for its tiers, from lowest to highest. New materials start with zero owned. A completed type becomes available when adding characters or weapons and links entries that were waiting for that type.

If an entry reports a missing type, open **Missing Material Types**, enter the exact tier material names, and save. Until its links are complete, the app excludes that entry's costs instead of silently understating the total.

Under **Edit Existing Data**, you can correct character fields, weapon fields, a weapon copy label, Traveller progress-list labels, and material types. The material editor groups tiered items by type, including ascension gems, and lets you edit each tier's name. Material renames retain database IDs, inventory, and cost links. Category changes for materials already used in costs are blocked to protect those links. Traveller label edits change the progress list only; they do not rewrite the separately stored talent cost rules.

## Project files

`app_v2.py` starts the web app. The other `.py` files in the project folder supply its calculators, catalog editing, ordering, and page rendering. `genshin_v2.db` is the live SQLite database. Keep these files together in the same folder.

The app runs locally at `127.0.0.1:8000`; it does not need a hosted server to use the included database.
