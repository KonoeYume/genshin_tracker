Per-weapon copy numbers
=======================

1. Stop the web server with Ctrl+C in PowerShell.
2. Put add_weapon_copy_numbers.py and the new app_v2.py beside your
   genshin_v2.db. Keep your existing calculator scripts there.
3. Make a backup, then run the migration from the project folder:

   Copy-Item .\genshin_v2.db .\genshin_v2_backup.db
   .\.venv\Scripts\python.exe add_weapon_copy_numbers.py

   Expected for your currently attached database: 219 weapon copies;
   copy numbers assigned: 219. If you already added more copies locally,
   the numbers will be higher. Rerunning the migration assigns zero new
   numbers and preserves existing ones.

4. Restart the web server:

   .\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload

Each weapon has its own Copy 1, Copy 2, and so on. The first copy is shown
only by weapon name. Additional copies display their optional label, or
Copy 2 / Copy 3 when the label is blank. The old global ID is retained as
an internal database key so existing goals remain linked correctly.

The migration creates a unique rule for (weapon_id, copy_number). Future
scripts that INSERT into weapon_copies must provide a copy_number; existing
rows can still be updated without changing their number. Do not rerun an
older workbook weapon-copy import script that inserts without copy_number
unless you update it to assign a number first.
