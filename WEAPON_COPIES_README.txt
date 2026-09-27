Weapon copies and goals in the browser
======================================

Replace app_v2.py in your project folder with this version. Keep your
current SQLite database and calculator scripts beside it. Refresh the page
if your server uses --reload; otherwise restart uvicorn.

Under Weapon copy goal, select an owned copy, change its target level and
ascension, then save. Under Add another copy, choose a weapon and optionally
name the copy. Each added copy starts at level 1 -> 1, ascension 0 -> 0.
Select that copy above to set its goal. You can add as many copies of the
same weapon as you need. Existing copies and inventory are unchanged.

The page keeps character goals and the separate inventory Update value box.
Weapons with unresolved workbook lookup families remain excluded from the
shopping list, even if another copy is added.
