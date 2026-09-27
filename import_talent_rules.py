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
        CREATE TABLE IF NOT EXISTS talent_costs (
            talent_level INTEGER NOT NULL,
            material_role TEXT NOT NULL,
            tier INTEGER NOT NULL DEFAULT 0,
            cumulative_quantity INTEGER NOT NULL,
            PRIMARY KEY (talent_level, material_role, tier)
        )
    """)

    columns = [
        ("T", "talent_book", 2),
        ("U", "talent_book", 3),
        ("V", "talent_book", 4),
        ("W", "weekly_boss_drop", 0),
        ("X", "crown", 0),
        ("Y", "common_drop", 1),
        ("Z", "common_drop", 2),
        ("AA", "common_drop", 3),
        ("AB", "mora", 0),
    ]

    for row_number in range(18, 28):
        talent_level = sheet[f"S{row_number}"].value

        for column, role, tier in columns:
            quantity = sheet[f"{column}{row_number}"].value

            database.execute("""
                INSERT INTO talent_costs (
                    talent_level, material_role, tier, cumulative_quantity
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(talent_level, material_role, tier)
                DO UPDATE SET
                    cumulative_quantity = excluded.cumulative_quantity
            """, (talent_level, role, tier, quantity))

    database.commit()

    count = database.execute(
        "SELECT COUNT(*) FROM talent_costs"
    ).fetchone()[0]
    print(f"talent rules: {count}")

finally:
    database.close()
    workbook.close()