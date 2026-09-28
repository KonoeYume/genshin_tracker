"""Add Cryo Traveller's rotating Snezhnaya talent books to an existing database.

The other Cryo talent costs are still unknown; this does not enable Cryo goals.
Usage: python add_cryo_traveller_books.py path/to/genshin_v2.db
"""
import sqlite3
import sys
from pathlib import Path


def add_books(db):
    families = {}
    for family, tier, material_id in db.execute('''
        SELECT family,tier,material_id FROM material_family_tiers
        WHERE material_role='talent_book' AND family IN
        ('Snezhnaya 1','Snezhnaya 2','Snezhnaya 3')'''):
        families[(family, tier)] = material_id
    if len(families) != 9:
        raise ValueError('Expected three Snezhnaya families, each with tiers 2, 3 and 4')
    template = db.execute('''
        SELECT t.talent_level,CASE WHEN m.name LIKE 'Teachings of %' THEN 2
        WHEN m.name LIKE 'Guide to %' THEN 3 ELSE 4 END,t.quantity
        FROM traveller_talent_costs t
        JOIN materials m ON m.id=t.material_id
        WHERE t.element='Anemo' AND t.talent_slot=1 AND
        (m.name LIKE 'Teachings of %' OR m.name LIKE 'Guide to %'
         OR m.name LIKE 'Philosophies of %')
        ORDER BY t.talent_level''').fetchall()
    if len(template) != 9 or [row[0] for row in template] != list(range(2,11)):
        raise ValueError('Expected Anemo book costs for levels 2 through 10')
    for slot in (1,2,3):
        if db.execute('''SELECT 1 FROM traveller_talent_progress
            WHERE element='Cryo' AND talent_slot=?''',(slot,)).fetchone() is None:
            raise ValueError(f'Cryo talent slot {slot} is absent')
        for level,tier,quantity in template:
            family=f'Snezhnaya {(level-2)%3+1}'
            material_id=families[(family,tier)]
            existing=db.execute('''SELECT t.material_id FROM traveller_talent_costs t
                JOIN material_family_tiers f ON f.material_id=t.material_id
                WHERE t.element='Cryo' AND t.talent_slot=? AND t.talent_level=?
                AND f.material_role='talent_book' ''',(slot,level)).fetchall()
            if existing and existing != [(material_id,)]:
                raise ValueError(f'Conflicting Cryo book cost at talent {slot}, level {level}')
            if not existing:
                db.execute('''INSERT INTO traveller_talent_costs
                    (element,talent_slot,talent_level,material_id,quantity)
                    VALUES ('Cryo',?,?,?,?)''',(slot,level,material_id,quantity))
    return db.execute("SELECT COUNT(*) FROM traveller_talent_costs WHERE element='Cryo'").fetchone()[0]


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python add_cryo_traveller_books.py path/to/genshin_v2.db')
    with sqlite3.connect(Path(sys.argv[1])) as db:
        print('Cryo book rows:',add_books(db))
