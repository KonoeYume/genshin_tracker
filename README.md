# Genshin Tracker

Run the local web app from this folder:

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn
.\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload
```

Open <http://127.0.0.1:8000/>. `genshin_v2.db` holds the catalog, inventory,
goals, cost rules, and material links. Back up this file before making large
sets of changes. The browser saves directly to it.

For an existing database, run the lookup migrations before using the catalog
forms. Rerunning them is safe:

```powershell
.\.venv\Scripts\python.exe add_element_gem_lookup.py
.\.venv\Scripts\python.exe add_catalog_type_lookups.py
```

## Add New Game Content

Open **Add to Catalog** on the page. A new character needs its name, element,
boss material, common drop type, local specialty, talent book
type, and weekly boss **type** (for example, `Dvalin 3`). A new weapon needs its name, weapon type,
rarity, ascension material type, common drop type, and elite drop type.
The app creates level 1 progress and, for a weapon, Copy 1. Set their goals
using the normal goal controls afterward.

The gem type is determined from the selected element using the
`element_gems` table. This lookup was migrated from the workbook's
**Enemy Drops Table**; the web app does not read the workbook.

The Common Drop and Elite Drop dropdowns follow **Enemy Drops Table** order.
Talent Book and Weekly Boss Type follow **Character Talent Mats** order;
Ascension Material Type follows **Weapon Ascension Mats** order. Weekly boss
types map to one material name. The one-time lookups now live in SQLite;
the running app does not read the workbook. Every catalog field starts blank.
These type dropdowns offer **New Type…** for game content without a saved mapping.

Existing material types are linked automatically. A type not yet in the
database appears under **Missing Material Types**. Enter its exact material
names in tier order: common drops and talent books have tiers 1–3 and 2–4
respectively; elite drops use tiers 2–4; weapon ascension materials use 2–5;
weekly boss types have one material at tier 0.
Until those names are saved, the shopping list excludes the affected entry
and says why. Newly created individual materials start with zero owned.

The `.xlsm` workbook and `import_*.py` / `link_materials.py` files were used
for the initial migration. The running app does not read the workbook.
Do not rerun `link_materials.py` after editing mappings in SQLite: it deletes
the current links and rebuilds them from the old workbook.
