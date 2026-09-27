import sqlite3

connection = sqlite3.connect("genshin_tracker.db")
connection.execute("PRAGMA foreign_keys = ON")

connection.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
""")

connection.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        material_id INTEGER PRIMARY KEY,
        quantity INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )
""")

connection.execute(
    "INSERT OR IGNORE INTO materials (name) VALUES (?)",
    ("Everflame Seed",)
)

connection.execute("""
    INSERT OR IGNORE INTO inventory (material_id, quantity)
    SELECT id, 8 FROM materials WHERE name = ?
""", ("Everflame Seed",))

connection.commit()

for name, quantity in connection.execute("""
    SELECT materials.name, inventory.quantity
    FROM inventory
    JOIN materials ON inventory.material_id = materials.id
"""):
    print(f"{name}: {quantity} owned")

connection.close()