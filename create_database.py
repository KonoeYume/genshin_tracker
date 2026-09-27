import sqlite3

# Creates genshin_tracker.db if it does not already exist.
connection = sqlite3.connect("genshin_tracker.db")

# SQL describes the table and its columns.
connection.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        current_level INTEGER NOT NULL DEFAULT 1,
        target_level INTEGER NOT NULL DEFAULT 1
    )
""")

# Add one example character if she is not already there.
connection.execute("""
    INSERT OR IGNORE INTO characters
        (name, current_level, target_level)
    VALUES (?, ?, ?)
""", ("Amber", 80, 90))

connection.commit()

for row in connection.execute("SELECT * FROM characters"):
    print(row)

connection.close()