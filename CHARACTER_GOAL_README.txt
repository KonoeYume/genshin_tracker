Character goals in the browser
==============================

Replace app_v2.py in your project folder with this version. Keep your
current genshin_v2.db, shopping_list.py, character_requirements.py,
weapon_requirements.py, and traveller_requirements.py beside it.

If uvicorn is running with --reload, refresh http://127.0.0.1:8000/ .
Otherwise restart it:

  .\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload

Select a character, choose target level and ascension and the three talent
targets, then click Save character goal. The current values shown above
are imported progress and are not changed by this form. The shopping list
recalculates after a successful save.

A target cannot be below the current value. Character level caps by target
ascension are 20, 40, 50, 60, 70, 80, 90 for ascensions 0 through 6.
Characters with incomplete material links stay listed in Excluded goals
until their workbook lookup families are completed and reimported.

Inventory layout remains: Required, Owned, Still needed, Update value, Save.
