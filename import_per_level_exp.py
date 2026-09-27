"""Import the per-level EXP tables into genshin_v2.db.

Keep this file and per_level_exp.csv beside your existing database.
"""
import csv
import sqlite3
from pathlib import Path

folder = Path(__file__).resolve().parent
database_path = folder / "genshin_v2.db"
csv_path = folder / "per_level_exp.csv"

if not database_path.is_file():
    raise SystemExit("genshin_v2.db was not found beside this script. No new database was created.")

records = []
with csv_path.open(newline="", encoding="utf-8") as stream:
    for row in csv.DictReader(stream):
        records.append((
            row["entity_kind"], int(row["rarity"]), int(row["level"]),
            None if not row["exp_to_next"] else int(row["exp_to_next"]),
            int(row["cumulative_exp"]),
        ))

expected = {("character", 0): 90, **{("weapon", rarity): 70 if rarity < 3 else 90 for rarity in range(1, 6)}}
groups = {}
for kind, rarity, level, next_exp, total_exp in records:
    groups.setdefault((kind, rarity), {})[level] = (next_exp, total_exp)
if set(groups) != set(expected) or len(records) != 500:
    raise ValueError("Missing or extra rarity group or level row in CSV")
for group, rows in groups.items():
    if set(rows) != set(range(1, expected[group] + 1)) or rows[1][1] != 0:
        raise ValueError(f"Level range is incomplete: {group}")
    for level in range(1, expected[group]):
        if rows[level][0] is None or rows[level][1] + rows[level][0] != rows[level + 1][1]:
            raise ValueError(f"EXP totals do not reconcile: {group} level {level}")
    if rows[expected[group]][0] is not None:
        raise ValueError(f"Final level must have no next-level EXP: {group}")

database = sqlite3.connect(database_path)
try:
    database.execute("""
        CREATE TABLE IF NOT EXISTS level_exp (
            entity_kind TEXT NOT NULL CHECK (entity_kind IN ('character', 'weapon')),
            rarity INTEGER NOT NULL,
            level INTEGER NOT NULL,
            exp_to_next INTEGER,
            cumulative_exp INTEGER NOT NULL,
            PRIMARY KEY (entity_kind, rarity, level)
        )
    """)
    database.executemany("""
        INSERT INTO level_exp (entity_kind, rarity, level, exp_to_next, cumulative_exp)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(entity_kind, rarity, level) DO UPDATE SET
            exp_to_next = excluded.exp_to_next,
            cumulative_exp = excluded.cumulative_exp
    """, records)
    database.commit()
    for (kind, rarity), count in sorted(expected.items()):
        actual = database.execute(
            "SELECT COUNT(*) FROM level_exp WHERE entity_kind = ? AND rarity = ?",
            (kind, rarity),
        ).fetchone()[0]
        if actual != count:
            raise ValueError(f"Expected {count} rows for {kind} rarity {rarity}; found {actual}")
        label = kind if kind == "character" else f"{rarity}-star weapon"
        print(f"{label}: {actual} levels")
    print("Total: 500 levels imported")
finally:
    database.close()
