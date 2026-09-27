Traveller goals in the browser
=============================

Replace app_v2.py in your project folder with this version. Keep your
migrated genshin_v2.db, shopping_list.py, traveller_requirements.py,
character_requirements.py and weapon_requirements.py beside it.
Refresh http://127.0.0.1:8000/ if uvicorn is running with --reload.

The Traveller Goal section has one shared character level and ascension,
plus a selector for Anemo, Geo, Electro, Dendro, Hydro, Pyro and Cryo.
Each element has three separate talent targets. Save Traveller Goal
updates the shared level/ascension and the selected element's talents.

Cryo talents remain fixed at their current level because the workbook
contains no Cryo cost rules. Other elements use the 576 Traveller cost
entries imported earlier. Existing character, weapon and inventory
controls remain available.
