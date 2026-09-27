Traveller calculation update
============================

Keep your current genshin_v2.db and Genshin_Tracker.xlsm in the same folder.
Extract these four Python files into that folder, replacing shopping_list.py
when Windows asks. Keep character_requirements.py and weapon_requirements.py there too.

Run these commands in PowerShell from your project folder:

  .\.venv\Scripts\python.exe import_traveller_costs.py
  .\.venv\Scripts\python.exe traveller_requirements.py
  .\.venv\Scripts\python.exe shopping_list.py

The importer adds 576 cost entries for Anemo, Geo, Electro, Dendro, Hydro and
Pyro talents. It also adds four Brilliant Diamond materials and Cornerstone
of Stars and Flames with zero owned, if absent. It never resets existing
inventory or progress. You can rerun it after fixing the workbook.

The current Traveller level and talents are already complete, so the
Traveller-only list should have zero requirements. The combined shopping
list should say 101 characters, 210 weapon copies, 1 Traveller, 12 excluded,
and retain the earlier material totals.

Cryo has three progress rows, but no cost rules in the supplied workbook.
Leave Cryo goals at 1 -> 1 until its material data is available. If you set
a Cryo goal above the current level, Traveller is explicitly excluded.

The 12 existing exclusions (3 characters, 9 weapon copies) still depend on
missing workbook material-family lookup entries. They are not included in
the shopping totals.
