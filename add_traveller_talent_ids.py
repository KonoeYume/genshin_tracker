"""Add explicit Traveller talent IDs, with Cryo occupying the last slots.

Run once against an existing genshin_v2.db. Safe to rerun; keeps all progress.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def migrate(db):
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('BEGIN IMMEDIATE')
    try:
        columns = {row[1] for row in db.execute('PRAGMA table_info(traveller_talent_progress)')}
        if not columns:
            raise ValueError('Traveller talent progress table is missing')
        order = '''ORDER BY CASE WHEN element='Cryo' THEN 1 ELSE 0 END,
            CASE element WHEN 'Anemo' THEN 1 WHEN 'Geo' THEN 2 WHEN 'Electro' THEN 3
            WHEN 'Dendro' THEN 4 WHEN 'Hydro' THEN 5 WHEN 'Pyro' THEN 6 ELSE 7 END,
            element,talent_slot'''
        rows = db.execute('''SELECT element,talent_slot,current_level,target_level
            FROM traveller_talent_progress ''' + order).fetchall()
        if 'id' in columns:
            current = db.execute('''SELECT element,talent_slot FROM traveller_talent_progress
                ORDER BY id''').fetchall()
            if current == [(row[0],row[1]) for row in rows]:
                db.commit()
                return len(rows)
        db.execute('''CREATE TABLE traveller_talent_progress_reordered (
            id INTEGER PRIMARY KEY,
            element TEXT NOT NULL,
            talent_slot INTEGER NOT NULL CHECK(talent_slot BETWEEN 1 AND 3),
            current_level INTEGER NOT NULL,
            target_level INTEGER NOT NULL,
            UNIQUE(element,talent_slot))''')
        db.executemany('''INSERT INTO traveller_talent_progress_reordered
            (id,element,talent_slot,current_level,target_level) VALUES (?,?,?,?,?)''',
            [(index,*row) for index,row in enumerate(rows,1)])
        db.execute('DROP TABLE traveller_talent_progress')
        db.execute('ALTER TABLE traveller_talent_progress_reordered RENAME TO traveller_talent_progress')
        db.commit()
        return len(rows)
    except Exception:
        db.rollback()
        raise


if __name__ == '__main__':
    if not DB_PATH.is_file():
        raise SystemExit('Place this script beside genshin_v2.db')
    with sqlite3.connect(DB_PATH) as connection:
        count = migrate(connection)
    print(f'Traveller talent progress: {count} rows; Cryo has the last three IDs.')
