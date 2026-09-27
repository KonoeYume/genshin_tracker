import sqlite3
from pathlib import Path

from openpyxl import load_workbook

folder = Path(__file__).parent
workbook = load_workbook(
    folder / "Genshin_Tracker.xlsm",
    read_only=True,
    data_only=True
)
sheet = workbook["Weapon Ascension Tables"]

database = sqlite3.connect(folder / "genshin_v2.db")

try:
    database.execute("""
        CREATE TABLE IF NOT EXISTS weapon_ascension_costs (
            rarity INTEGER NOT NULL,
            ascension INTEGER NOT NULL,
            material_role TEXT NOT NULL,
            tier INTEGER NOT NULL DEFAULT 0,
            cumulative_quantity INTEGER NOT NULL,
            PRIMARY KEY (rarity, ascension, material_role, tier)
        )
    """)

    columns = [
        ("B", "weapon_ascension", 2),
        ("C", "weapon_ascension", 3),
        ("D", "weapon_ascension", 4),
        ("E", "weapon_ascension", 5),
        ("F", "common_drop", 1),
        ("G", "common_drop", 2),
        ("H", "common_drop", 3),
        ("I", "elite_drop", 2),
        ("J", "elite_drop", 3),
        ("K", "elite_drop", 4),
        ("L", "mora", 0),
    ]

    row_ranges = {
        1: range(13, 18),
        2: range(31, 36),
        3: range(51, 58),
        4: range(73, 80),
        5: range(95, 102),
    }

    for rarity, row_numbers in row_ranges.items():
        for row_number in row_numbers:
            ascension = sheet[f"A{row_number}"].value

            for column, role, tier in columns:
                quantity = sheet[f"{column}{row_number}"].value

                database.execute("""
                    INSERT INTO weapon_ascension_costs (
                        rarity, ascension, material_role,
                        tier, cumulative_quantity
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(rarity, ascension, material_role, tier)
                    DO UPDATE SET
                        cumulative_quantity = excluded.cumulative_quantity
                """, (rarity, ascension, role, tier, quantity))

    database.commit()

    count = database.execute(
        "SELECT COUNT(*) FROM weapon_ascension_costs"
    ).fetchone()[0]
    print(f"weapon ascension rules: {count}")

finally:
    database.close()
    workbook.close()