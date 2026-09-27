"""Store the workbook's element-to-gem lookup in SQLite (safe to rerun)."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'
ELEMENT_GEMS = {
    'Anemo': 'Vayuda Turquoise',
    'Cryo': 'Shivada Jade',
    'Dendro': 'Nagadus Emerald',
    'Electro': 'Vajrada Amethyst',
    'Geo': 'Prithiva Topaz',
    'Hydro': 'Varunada Lazurite',
    'Pyro': 'Agnidus Agate',
}


def migrate(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        mismatches = [(element, gem) for element, gem in
            db.execute('SELECT DISTINCT element,gem_family FROM characters')
            if element in ELEMENT_GEMS and gem != ELEMENT_GEMS[element]]
        if mismatches:
            raise ValueError(f'Existing characters disagree with the element-gem lookup: {mismatches}')
        db.execute('''CREATE TABLE IF NOT EXISTS element_gems (
            element TEXT PRIMARY KEY, gem_family TEXT NOT NULL)''')
        for element, gem in ELEMENT_GEMS.items():
            existing=db.execute('SELECT gem_family FROM element_gems WHERE element=?',(element,)).fetchone()
            if existing and existing[0]!=gem:
                raise ValueError(f'Existing element_gems entry differs for {element}')
            db.execute('INSERT OR IGNORE INTO element_gems(element,gem_family) VALUES (?,?)',
                       (element,gem))
        db.commit()
        return db.execute('SELECT COUNT(*) FROM element_gems').fetchone()[0]
    except Exception:
        db.rollback()
        raise


def main():
    if not DB_PATH.is_file():
        raise SystemExit('Place this script beside genshin_v2.db')
    with sqlite3.connect(DB_PATH) as db:
        print(f'Element-gem lookup: {migrate(db)} rows')

if __name__ == '__main__':
    main()
