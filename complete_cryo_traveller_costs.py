"""Complete Cryo Traveller talent costs in an existing genshin_v2.db.

Usage: python complete_cryo_traveller_costs.py path/to/genshin_v2.db
Back up your database first. Existing conflicting Cryo costs cause an error.
"""
import sqlite3
import sys


def complete(db):
    family = dict(db.execute('''SELECT tier,material_id FROM material_family_tiers
        WHERE material_role='common_drop' AND family='Aberrant Chimeric Monster' '''))
    if set(family)!={1,2,3}:
        raise ValueError('Aberrant Chimeric Monster needs all three material tiers')
    boss=db.execute('''SELECT material_id FROM material_family_tiers
        WHERE material_role='weekly_boss_drop' AND family='Game before the Gate 3'
        AND tier=0''').fetchone()
    crown=db.execute("SELECT id FROM materials WHERE name='Crown of Insight'").fetchone()
    mora=db.execute("SELECT id FROM materials WHERE name='Mora'").fetchone()
    if not boss or not crown or not mora:raise ValueError('Missing weekly boss material, crown or Mora')
    # Reuse the exact per-level quantities from an existing complete Traveller element.
    template=db.execute('''SELECT t.talent_level,m.category,t.quantity
        FROM traveller_talent_costs t JOIN materials m ON m.id=t.material_id
        WHERE t.element='Anemo' AND t.talent_slot=1
        AND m.category IN ('common_drop','weekly_boss_drop','talent_special','currency')
        ORDER BY t.talent_level,m.category''').fetchall()
    if len(template)!=23:raise ValueError(f'Expected 23 non-book costs per talent, found {len(template)}')
    for slot in (1,2,3):
        if not db.execute("SELECT 1 FROM traveller_talent_progress WHERE element='Cryo' AND talent_slot=?",(slot,)).fetchone():
            raise ValueError(f'Cryo talent slot {slot} is absent')
        for level,category,quantity in template:
            material_id={'common_drop':family[1 if level==2 else 2 if level<7 else 3],
                         'weekly_boss_drop':boss[0],'talent_special':crown[0],
                         'currency':mora[0]}[category]
            existing=db.execute('''SELECT t.material_id,t.quantity FROM traveller_talent_costs t
                JOIN materials m ON m.id=t.material_id WHERE t.element='Cryo'
                AND t.talent_slot=? AND t.talent_level=? AND m.category=?''',
                (slot,level,category)).fetchall()
            if existing and existing!=[(material_id,quantity)]:
                raise ValueError(f'Conflicting Cryo {category} at talent {slot}, level {level}')
            if not existing:
                db.execute('''INSERT INTO traveller_talent_costs
                    (element,talent_slot,talent_level,material_id,quantity)
                    VALUES ('Cryo',?,?,?,?)''',(slot,level,material_id,quantity))
    for slot in (1,2,3):
        rows=db.execute("SELECT talent_level,COUNT(*) FROM traveller_talent_costs WHERE element='Cryo' AND talent_slot=? GROUP BY talent_level ORDER BY talent_level",(slot,)).fetchall()
        if rows!=[(level,3 if level<7 else 5 if level==10 else 4) for level in range(2,11)]:
            raise ValueError(f'Cryo talent {slot} has incomplete costs: {rows}')
    return db.execute("SELECT COUNT(*) FROM traveller_talent_costs WHERE element='Cryo'").fetchone()[0]

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python complete_cryo_traveller_costs.py path/to/genshin_v2.db')
    with sqlite3.connect(sys.argv[1]) as db:print('Cryo cost rows:',complete(db))
