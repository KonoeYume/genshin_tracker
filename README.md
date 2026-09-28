# Genshin Tracker

Run the local web app from this folder:

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn
.\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload
```

Open <http://127.0.0.1:8000/> for Inventory Overview. `genshin_v2.db` holds the catalog, inventory,
goals, cost rules, and material links. Back up this file before making large
sets of changes. The browser saves directly to it.

After installing this version, stop the app and assign explicit IDs to Traveller
talent rows, with Cryo last. This preserves all current and target values and
can be rerun safely:

```powershell
.\.venv\Scripts\python.exe add_traveller_talent_ids.py
```

## Inventory Overview and Progress Lists

Use **Inventory Overview** in the navigation, or open
<http://127.0.0.1:8000/overview>. It shows all catalog materials, including
materials with no inventory, grouped and ordered by the workbook's families.
Mora has the same columns as other materials. Enter a new total in
**Update Value** and save. Character EXP item values are 1,000 / 5,000 /
20,000 points; weapon ores are 400 / 2,000 / 10,000 points. The summary
compares your combined held EXP points with the EXP required by your current
goals. The three item quantities come first, followed by five total EXP rows:
required, held, remaining, max required, and to max.
Numeric columns are centered. A heavier line starts each new material family;
talent books and weapon ascension materials have a slightly stronger line between
regions. Boss drops and local specialties each count as their own family.
Within a three or four tier material family, three lower tier items can be
converted to one of the next tier. Weekly boss drops can be exchanged 1:1
within their boss family. **Still Needed** and **To Max** take these possible
conversions into account. **Convert (Goal)** and **Convert (Max)** show how many
of that row's owned items would be spent as conversion inputs in each separate
scenario. These are plans, not automatic changes to inventory; owned values
stay as entered. Pink cells mark remaining shortages or required conversions
for saved goals only. Max columns are unhighlighted.
The lines between individual boss drops and local specialties are 1px; other
family dividers are 2px, and region dividers are 3px.

**Max Required** shows what it would take from current progress to level 90,
ascension 6, and three level 10 talents for every character. It includes the
first copy of every weapon; 1★ and 2★ weapons use their actual level 70 / ascension 4
maximum because the game cost tables end there. Extra copies are not counted in
this ceiling, although they remain in your normal goal totals. Traveller's
shared level is raised to 90 / ascension 6 and every element with defined
talent costs is raised to level 10. Cryo Traveller talent costs are absent, so
the displayed max total is incomplete until those rules are supplied.
Any material mapping gaps are listed as exclusions.
The **To Max** number subtracts owned inventory from Max Required. Crafting
conversions and EXP item overshoot are not included in these quantities.

Use separate **Characters**, **Weapons**, and **Traveller** pages to see each
progress list in database ID order. The weapon page uses `weapons.id` followed
by copy number. Traveller talent rows now have explicit IDs, with Cryo last.
Search characters or weapons and click a name to edit its
goals or current progress. The **Goals** page at `/goals` contains collapsible
editors and the excluded-goals list. Select a character, weapon, or Traveller
element before editing; each selector starts blank. Use **Add data** to add entries and complete missing
material types.

Each progress page has temporary sorting by clicking a column heading and a
filter field beneath every heading. **Clear filters** restores ID order. Character
IDs come from `characters.id`. The weapon page follows the **Weapon Data Table**
column order, displays `weapons.id` and the per-weapon `copy_number` as **Copy ID**,
and still links each row to its actual database copy. The character page follows
**Character Data Table** column order, including gem, world boss material, mob drop,
and local speciality. Traveller shows one row per talent in **Traveller Data
Table** column order. Cryo's material fields remain blank because the workbook
has no Cryo rows; it has no visible ID column.
Progress tables expand on wide screens and scroll horizontally on smaller ones
so every catalog and progress column can be read.
Use **Show or Hide Columns** on each progress page to choose visible columns;
column choices reset when the page reloads.
The far-right **Actions** column opens the editors for characters, weapons,
weapon copy labels, and Traveller talent rows.

## Correct Existing Data

Under **Add data → Add New → New Material**, choose the material type, enter a type
name, and fill in the material names in tier order. The form supports talent
books, weapon ascension materials, common and elite enemy drops, weekly boss
drops, world boss drops, and local specialities. New types can be selected
when adding characters or weapons. Existing missing type entries with that
name are linked automatically. Materials start with zero inventory.

Open **Add data → Edit Existing Data**, then select a character, weapon, weapon
copy label, or material type. The progress lists offer **Edit data** links, and material names on
the overview open the material editor. You can correct names, character or
weapon catalog fields, a material type name, its category, and each tier's
material name. Material renames keep their
database ID, inventory quantity, requirement links, and workbook display
position. Changing a character or weapon's material type refreshes its links;
an unknown type appears under **Missing Material Types** until completed.
The material type picker follows the overview's category and family order;
ascension gems appear in four tier groups, including Brilliant Diamond.
Changing the bucket of a material already used in costs is blocked to prevent
its requirements from moving into an unrelated category.
Changing a weapon to rarity 1 or 2 is rejected if any copy already exceeds
that rarity's level or ascension cap.
Traveller editing saves the common drop, talent material, and weekly boss
labels for each element and talent slot. These labels appear in the Traveller
progress list; changing them does not alter separately stored talent costs.

The Goals summary counts distinct weapons, so adding another copy does not
increase the weapon count. It omits EXP point totals; those remain on Inventory
Overview.

For an existing database, run the lookup migrations before using the catalog
forms. Rerunning them is safe:

```powershell
.\.venv\Scripts\python.exe add_element_gem_lookup.py
.\.venv\Scripts\python.exe add_catalog_type_lookups.py
```

## Add New Game Content

Open **Add New** on the page. A new character needs its name, element,
world boss material, common drop type, local specialty, talent book
type, and weekly boss **type** (for example, `Dvalin 3`). A new weapon needs its name, weapon type,
rarity, ascension material type, common drop type, and elite drop type.
The app creates level 1 progress and, for a weapon, Copy 1. Set their goals
using the normal goal controls afterward.

## Record Progress

In a character, weapon, or Traveller goal, open **Record Current Progress**
after leveling up. Enter the current level and ascension, plus current talent
levels for characters and Traveller, then save. Current values cannot move
backward. If a current value passes its target, the target moves up to match.
The shopping list then recalculates. Updating progress does not automatically
subtract materials from inventory; use the inventory update field to record
the quantities you actually own.

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
