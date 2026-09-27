Editable inventory dashboard
============================

Replace app_v2.py in your project folder with the copy in this ZIP.
Keep genshin_v2.db and the three calculator modules and shopping_list.py
beside it. Restart the server if needed:

  .\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload

Open http://127.0.0.1:8000/ . Each material row has an Owned input and
Save button. Enter a nonnegative whole number and save. The value is stored
in genshin_v2.db, then all Still needed values recalculate.

This updates the inventory amount as an absolute count, not an increment.
For example, entering 12 replaces the previous owned amount with 12.
