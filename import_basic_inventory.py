import sqlite3
from pathlib import Path

from openpyxl import load_workbook

folder = Path(__file__).parent
workbook = load_workbook(
    folder / "Genshin_Tracker.xlsm",
    read_only=True,
    data_only=True
)
sheet = workbook["Overview"]

database = sqlite3.connect(folder / "genshin_v2.db")
database.execute("PRAGMA foreign_keys = ON")

try:
    database.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL
        )
    """)

    database.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            material_id INTEGER PRIMARY KEY,
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            FOREIGN KEY (material_id) REFERENCES materials(id)
        )
    """)

    def save_item(name, category, quantity):
        if not name or not isinstance(quantity, (int, float)):
            raise ValueError(f"Invalid inventory entry: {name}, {quantity}")

        quantity = int(quantity)

        database.execute("""
            INSERT INTO materials (name, category)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET category = excluded.category
        """, (name, category))

        material_id = database.execute(
            "SELECT id FROM materials WHERE name = ?",
            (name,)
        ).fetchone()[0]

        database.execute("""
            INSERT INTO inventory (material_id, quantity)
            VALUES (?, ?)
            ON CONFLICT(material_id)
            DO UPDATE SET quantity = excluded.quantity
        """, (material_id, quantity))

    save_item("Mora", "currency", sheet["C3"].value)

    for row in (8, 9, 10):
        save_item(
            sheet[f"B{row}"].value,
            "character_exp",
            sheet[f"C{row}"].value
        )

    for row in (16, 17, 18):
        save_item(
            sheet[f"B{row}"].value,
            "weapon_exp",
            sheet[f"C{row}"].value
        )

    for row in range(3, 41):
        save_item(
            sheet[f"AN{row}"].value,
            "character_boss_drop",
            sheet[f"AP{row}"].value
        )

    database.commit()

    count = database.execute(
        "SELECT COUNT(*) FROM inventory"
    ).fetchone()[0]
    print(f"inventory entries: {count}")

finally:
    database.close()
    workbook.close()