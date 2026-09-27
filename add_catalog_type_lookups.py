"""One-time SQLite migration for workbook type order and weekly boss mapping.

Safe to rerun. Does not change character progress or owned quantities.
"""
import sqlite3
from pathlib import Path

from catalog_lookup_data import (COMMON_DROP_ORDER, ELITE_DROP_ORDER,
                                 TALENT_BOOK_ORDER, WEAPON_ASCENSION_ORDER,
                                 WEEKLY_BOSS_TYPES)

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def migrate(db):
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS material_type_order (
            material_role TEXT NOT NULL, type_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            PRIMARY KEY(material_role,type_name))''')
        db.execute('''CREATE TABLE IF NOT EXISTS material_family_tiers (
            material_role TEXT NOT NULL, family TEXT NOT NULL, tier INTEGER NOT NULL,
            material_id INTEGER NOT NULL REFERENCES materials(id),
            PRIMARY KEY(material_role,family,tier))''')
        for role, names in (('common_drop',COMMON_DROP_ORDER),
                            ('elite_drop',ELITE_DROP_ORDER),
                            ('talent_book',TALENT_BOOK_ORDER),
                            ('weapon_ascension',WEAPON_ASCENSION_ORDER),
                            ('weekly_boss_drop',[item[0] for item in WEEKLY_BOSS_TYPES])):
            db.executemany('''INSERT OR IGNORE INTO material_type_order
                (material_role,type_name,sort_order) VALUES (?,?,?)''',
                [(role,name,index) for index,name in enumerate(names,1)])
        for type_name, material_name in WEEKLY_BOSS_TYPES:
            db.execute('''INSERT INTO materials(name,category) VALUES (?,?)
                ON CONFLICT(name) DO NOTHING''',(material_name,'weekly_boss_drop'))
            mid=db.execute('SELECT id FROM materials WHERE name=?',(material_name,)).fetchone()[0]
            db.execute('''INSERT INTO inventory(material_id,quantity) VALUES (?,0)
                ON CONFLICT(material_id) DO NOTHING''',(mid,))
            existing=db.execute('''SELECT material_id FROM material_family_tiers
                WHERE material_role='weekly_boss_drop' AND family=? AND tier=0''',
                (type_name,)).fetchone()
            if existing and existing[0]!=mid:
                raise ValueError(f'Weekly boss type {type_name} conflicts with its saved mapping')
            db.execute('''INSERT OR IGNORE INTO material_family_tiers
                (material_role,family,tier,material_id) VALUES ('weekly_boss_drop',?,0,?)''',
                (type_name,mid))
        # Preserve links for any newer type already added through the app.
        for type_name,mid in db.execute('''SELECT DISTINCT c.weekly_boss_material,cm.material_id
            FROM characters c JOIN character_materials cm ON cm.character_id=c.id
            WHERE cm.material_role='weekly_boss_drop' AND cm.tier=0''').fetchall():
            existing=db.execute('''SELECT material_id FROM material_family_tiers
                WHERE material_role='weekly_boss_drop' AND family=? AND tier=0''',
                (type_name,)).fetchone()
            if existing and existing[0]!=mid:
                raise ValueError(f'Existing character link conflicts for weekly boss type {type_name}')
            db.execute('''INSERT OR IGNORE INTO material_family_tiers
                (material_role,family,tier,material_id) VALUES ('weekly_boss_drop',?,0,?)''',
                (type_name,mid))
        db.commit()
        return db.execute("SELECT COUNT(*) FROM material_family_tiers WHERE material_role='weekly_boss_drop'").fetchone()[0]
    except Exception:
        db.rollback()
        raise


def main():
    if not DB_PATH.is_file():
        raise SystemExit('Place this script beside genshin_v2.db')
    with sqlite3.connect(DB_PATH) as db:
        count=migrate(db)
        print(f'Weekly boss types linked: {count}')
        print('Common, elite, talent book, and ascension type order stored in SQLite.')

if __name__=='__main__':main()
