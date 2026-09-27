"""Add stable, per-weapon copy numbers to genshin_v2.db.

Run once before using the updated web app. Safe to rerun. Existing IDs,
progress, labels, inventory and source-sheet links are preserved.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def migrate(db):
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('BEGIN IMMEDIATE')
    try:
        columns = {row[1] for row in db.execute('PRAGMA table_info(weapon_copies)')}
        if not columns:
            raise ValueError('weapon_copies table is missing')
        if 'copy_number' not in columns:
            db.execute('ALTER TABLE weapon_copies ADD COLUMN copy_number INTEGER')
        rows = db.execute('''SELECT id,weapon_id,copy_number FROM weapon_copies
            ORDER BY weapon_id,id''').fetchall()
        occupied = {}
        for _id, weapon_id, number in rows:
            if number is None:
                continue
            if not isinstance(number,int) or number<1:
                raise ValueError(f'Invalid copy number for row {_id}: {number}')
            numbers = occupied.setdefault(weapon_id,set())
            if number in numbers:
                raise ValueError(f'Duplicate copy number {number} for weapon {weapon_id}')
            numbers.add(number)
        next_number = {wid:max(numbers)+1 for wid,numbers in occupied.items()}
        added = 0
        for copy_id, weapon_id, number in rows:
            if number is not None:
                continue
            number = next_number.get(weapon_id,1)
            db.execute('UPDATE weapon_copies SET copy_number=? WHERE id=?',(number,copy_id))
            next_number[weapon_id] = number+1
            added += 1
        db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS weapon_copies_number_unique
            ON weapon_copies(weapon_id,copy_number)''')
        db.execute('''CREATE TRIGGER IF NOT EXISTS weapon_copy_number_insert
            BEFORE INSERT ON weapon_copies
            WHEN NEW.copy_number IS NULL OR NEW.copy_number < 1
            BEGIN SELECT RAISE(ABORT,'copy_number must be positive'); END''')
        db.execute('''CREATE TRIGGER IF NOT EXISTS weapon_copy_number_update
            BEFORE UPDATE OF copy_number ON weapon_copies
            WHEN NEW.copy_number IS NULL OR NEW.copy_number < 1
            BEGIN SELECT RAISE(ABORT,'copy_number must be positive'); END''')
        db.commit()
        return added, len(rows)
    except Exception:
        db.rollback()
        raise


def main():
    if not DB_PATH.is_file():
        raise SystemExit('Place this script beside genshin_v2.db')
    with sqlite3.connect(DB_PATH) as db:
        added,total=migrate(db)
        print(f'Weapon copies: {total}; copy numbers assigned: {added}')
        print('Each weapon starts at Copy 1. The original database IDs are unchanged.')

if __name__=='__main__':main()
