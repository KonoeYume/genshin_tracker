import sqlite3
from pathlib import Path

from openpyxl import load_workbook

folder = Path(__file__).parent
workbook = load_workbook(
    folder / "Genshin_Tracker.xlsm",
    read_only=True,
    data_only=True
)
sheet = workbook["Character Misc Tables"]

database = sqlite3.connect(folder / "genshin_v2.db")

try:
    database.execute("""
        CREATE TABLE IF NOT EXISTS character_ascension_costs (
            ascension INTEGER NOT NULL,
            material_role TEXT NOT NULL,
            tier INTEGER NOT NULL DEFAULT 0,
            cumulative_quantity INTEGER NOT NULL,
            PRIMARY KEY (ascension, material_role, tier)
        )
    """)

    columns = [
        ("H", "gem", 2),
        ("I", "gem", 3),
        ("J", "gem", 4),
        ("K", "gem", 5),
        ("L", "boss_drop", 0),
        ("M", "common_drop", 1),
        ("N", "common_drop", 2),
        ("O", "common_drop", 3),
        ("P", "local_specialty", 0),
        ("Q", "mora", 0),
    ]

    for row_number in range(15, 22):
        ascension = sheet[f"G{row_number}"].value

        for column, role, tier in columns:
            quantity = sheet[f"{column}{row_number}"].value

            database.execute("""
                INSERT INTO character_ascension_costs (
                    ascension, material_role, tier, cumulative_quantity
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(ascension, material_role, tier)
                DO UPDATE SET
                    cumulative_quantity = excluded.cumulative_quantity
            """, (ascension, role, tier, quantity))

    database.commit()

    count = database.execute(
        "SELECT COUNT(*) FROM character_ascension_costs"
    ).fetchone()[0]
    print(f"character ascension rules: {count}")

finally:
    database.close()
    workbook.close()