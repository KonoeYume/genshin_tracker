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

try:
    database.execute("""
        CREATE TABLE IF NOT EXISTS traveller_progress (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_level INTEGER NOT NULL,
            target_level INTEGER NOT NULL,
            current_ascension INTEGER NOT NULL,
            target_ascension INTEGER NOT NULL
        )
    """)

    database.execute("""
        CREATE TABLE IF NOT EXISTS traveller_talent_progress (
            element TEXT NOT NULL,
            talent_slot INTEGER NOT NULL CHECK (talent_slot BETWEEN 1 AND 3),
            current_level INTEGER NOT NULL,
            target_level INTEGER NOT NULL,
            PRIMARY KEY (element, talent_slot)
        )
    """)

    level_sheet = workbook["Traveller Level"]

    database.execute("""
        INSERT INTO traveller_progress (
            id, current_level, target_level,
            current_ascension, target_ascension
        ) VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            current_level = excluded.current_level,
            target_level = excluded.target_level,
            current_ascension = excluded.current_ascension,
            target_ascension = excluded.target_ascension
    """, (
        level_sheet["B4"].value,
        level_sheet["B5"].value,
        level_sheet["C10"].value,
        level_sheet["C11"].value
    ))

    elements = ["Anemo", "Geo", "Electro", "Dendro", "Hydro", "Pyro"]

    # Cryo has no sheet in this workbook yet.
    # Create its three talent slots without overwriting later edits.
    for slot in (1, 2, 3):
        database.execute("""
            INSERT OR IGNORE INTO traveller_talent_progress (
                element, talent_slot, current_level, target_level
            ) VALUES ('Cryo', ?, 1, 1)
        """, (slot,))

    for element in elements:
        sheet = workbook[f"Traveller {element}"]

        talent_cells = [
            ("B4", "B5"),
            ("E4", "E5"),
            ("H4", "H5"),
        ]

        for slot, (current_cell, target_cell) in enumerate(
            talent_cells, start=1
        ):
            database.execute("""
                INSERT INTO traveller_talent_progress (
                    element, talent_slot, current_level, target_level
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(element, talent_slot) DO UPDATE SET
                    current_level = excluded.current_level,
                    target_level = excluded.target_level
            """, (
                element, slot,
                sheet[current_cell].value,
                sheet[target_cell].value
            ))

    database.commit()

    level_count = database.execute(
        "SELECT COUNT(*) FROM traveller_progress"
    ).fetchone()[0]
    talent_count = database.execute(
        "SELECT COUNT(*) FROM traveller_talent_progress"
    ).fetchone()[0]

    print(f"traveller_progress: {level_count}")
    print(f"traveller_talent_progress: {talent_count}")

finally:
    database.close()
    workbook.close()