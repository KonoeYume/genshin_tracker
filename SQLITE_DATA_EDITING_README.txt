Material family editing in the web app
======================================

Replace these three files in your project folder:
  app_v2.py
  character_requirements.py
  weapon_requirements.py

Keep your current genshin_v2.db and other calculator scripts. Refresh the
page if uvicorn runs with --reload; otherwise restart it.

A new Missing Material Families section groups unresolved lookup families.
For each group, enter the exact three material names in tier order and
click Save family. This creates any absent materials with zero owned,
links every affected character and weapon, and removes those mapping issues.
The shopping list refreshes and includes newly complete goals.

Check the names before saving: the app treats the text as the material's
unique name. You can correct a mistaken link later in DB Browser, but this
first interface does not yet offer an edit form for completed families.

The workbook is no longer needed to resolve these gaps, and the web app
does not read it. Existing workbook import scripts were one-time migration
tools. Do not rerun link_materials.py: it clears and rebuilds mappings from
the old workbook. Future catalog forms will add new characters, weapons and
other materials directly to SQLite.
