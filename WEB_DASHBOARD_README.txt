Genshin Tracker browser dashboard
=================================

Put app_v2.py in your project folder beside genshin_v2.db, shopping_list.py,
character_requirements.py, weapon_requirements.py, and traveller_requirements.py.

From PowerShell in that folder, run:

  .\.venv\Scripts\python.exe -m uvicorn app_v2:app --reload

Open http://127.0.0.1:8000/ in your browser. If uvicorn is not installed,
run .\.venv\Scripts\python.exe -m pip install fastapi uvicorn first.

The first version is read-only. It calculates the totals from the SQLite
file every time you refresh the page. It displays excluded goals separately.
The JSON data is at http://127.0.0.1:8000/api/shopping-list .

Stop the server by pressing Ctrl+C in PowerShell.
