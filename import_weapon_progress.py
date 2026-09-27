import sqlite3
from pathlib import Path

from openpyxl import load_workbook

folder = Path(__file__).parent
workbook = load_workbook(
    folder / "Genshin_Tracker.xlsm",
    read_only=True,
    data_only=True
)

database = sqlite3.connect(folder / "genshin_v2.db")
database.execute("PRAGMA foreign_keys = ON")

try:
    database.execute("""
        CREATE TABLE IF NOT EXISTS weapon_copies (
            id INTEGER PRIMARY KEY,
            weapon_id INTEGER NOT NULL,
            source_sheet TEXT UNIQUE,
            label TEXT,
            current_level INTEGER NOT NULL,
            target_level INTEGER NOT NULL,
            current_ascension INTEGER NOT NULL,
            target_ascension INTEGER NOT NULL,
            FOREIGN KEY (weapon_id) REFERENCES weapons(id)
        )
    """)

    weapons = database.execute(
        "SELECT id, name FROM weapons"
    ).fetchall()

    for weapon_id, name in weapons:
        if name not in workbook:
            raise ValueError(f"No detail sheet for {name}")

        sheet = workbook[name]

        database.execute("""
            INSERT INTO weapon_copies (
                weapon_id, source_sheet,
                current_level, target_level,
                current_ascension, target_ascension
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_sheet) DO UPDATE SET
                weapon_id = excluded.weapon_id,
                current_level = excluded.current_level,
                target_level = excluded.target_level,
                current_ascension = excluded.current_ascension,
                target_ascension = excluded.target_ascension
        """, (
            weapon_id, name,
            sheet["B4"].value, sheet["B5"].value,
            sheet["C10"].value, sheet["C11"].value
        ))

    database.commit()

    count = database.execute(
        "SELECT COUNT(*) FROM weapon_copies"
    ).fetchone()[0]
    print(f"weapon_copies: {count}")

finally:
    database.close()
    workbook.close()