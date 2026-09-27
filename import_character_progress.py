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
        CREATE TABLE IF NOT EXISTS character_progress (
            character_id INTEGER PRIMARY KEY,
            current_level INTEGER NOT NULL,
            target_level INTEGER NOT NULL,
            current_ascension INTEGER NOT NULL,
            target_ascension INTEGER NOT NULL,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    """)

    database.execute("""
        CREATE TABLE IF NOT EXISTS talent_progress (
            character_id INTEGER NOT NULL,
            talent_slot INTEGER NOT NULL CHECK (talent_slot BETWEEN 1 AND 3),
            current_level INTEGER NOT NULL,
            target_level INTEGER NOT NULL,
            PRIMARY KEY (character_id, talent_slot),
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    """)

    characters = database.execute(
        "SELECT id, name FROM characters"
    ).fetchall()

    for character_id, name in characters:
        if name not in workbook:
            raise ValueError(f"No detail sheet for {name}")

        sheet = workbook[name]

        database.execute("""
            INSERT INTO character_progress (
                character_id, current_level, target_level,
                current_ascension, target_ascension
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(character_id) DO UPDATE SET
                current_level = excluded.current_level,
                target_level = excluded.target_level,
                current_ascension = excluded.current_ascension,
                target_ascension = excluded.target_ascension
        """, (
            character_id,
            sheet["B4"].value, sheet["B5"].value,
            sheet["C10"].value, sheet["C11"].value
        ))

        talent_cells = [
            ("F4", "F5"),     # Talent 1
            ("F17", "F18"),   # Talent 2
            ("F30", "F31"),   # Talent 3
        ]

        for slot, (current_cell, target_cell) in enumerate(
            talent_cells, start=1
        ):
            database.execute("""
                INSERT INTO talent_progress (
                    character_id, talent_slot, current_level, target_level
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(character_id, talent_slot) DO UPDATE SET
                    current_level = excluded.current_level,
                    target_level = excluded.target_level
            """, (
                character_id, slot,
                sheet[current_cell].value,
                sheet[target_cell].value
            ))

    database.commit()

    for table in ("character_progress", "talent_progress"):
        count = database.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"{table}: {count}")

finally:
    database.close()
    workbook.close()