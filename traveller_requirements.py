"""Calculate Traveller level and element talent goals from genshin_v2.db.

Requires complete per-level costs for all Traveller elements in genshin_v2.db.
"""
import sqlite3
from collections import Counter
from pathlib import Path

from character_requirements import cumulative_costs, level_exp

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def calculate(db):
    db.row_factory = sqlite3.Row
    progress = db.execute('SELECT * FROM traveller_progress WHERE id=1').fetchone()
    if progress is None:
        raise ValueError('Traveller level progress is missing')
    current, target = progress['current_level'], progress['target_level']
    if target < current:
        raise ValueError('Traveller target level is below current level')
    exp = level_exp(db,target)-level_exp(db,current)
    base_mora = (exp+4)//5
    role_costs = cumulative_costs(db,'character_ascension_costs','ascension',
                                  progress['current_ascension'],progress['target_ascension'])
    level_links = {(r['material_role'],r['tier']):r['material_id'] for r in
        db.execute('SELECT * FROM traveller_level_materials')}
    required = Counter()
    for (role,tier),quantity in role_costs.items():
        if role=='boss_drop' or not quantity:
            continue  # Traveller's workbook ascension has no boss drop.
        mid=level_links.get((role,tier))
        if mid is None:
            raise ValueError(f'No Traveller ascension material for {role}, tier {tier}')
        required[mid]+=quantity
    if base_mora:
        required[level_links['mora',0]]+=base_mora
    talents=db.execute('SELECT * FROM traveller_talent_progress ORDER BY element,talent_slot').fetchall()
    if len(talents)!=21:
        raise ValueError(f'Expected 21 Traveller talent rows; found {len(talents)}')
    for t in talents:
        element,slot,start,end=(t[k] for k in ('element','talent_slot','current_level','target_level'))
        if not 1<=start<=end<=10:
            raise ValueError(f'Invalid Traveller {element} talent {slot}: {start} to {end}')
        if start==end:
            continue
        rows=db.execute('''SELECT talent_level,material_id,quantity FROM traveller_talent_costs
            WHERE element=? AND talent_slot=? AND talent_level>? AND talent_level<=?''',
            (element,slot,start,end)).fetchall()
        if not rows:
            raise ValueError(f'No costs for Traveller {element} talent {slot}, {start} to {end}')
        for row in rows:
            required[row['material_id']]+=row['quantity']
    result=[]
    for mid,quantity in required.items():
        if not quantity: continue
        row=db.execute('''SELECT m.name,COALESCE(i.quantity,0) owned FROM materials m
            LEFT JOIN inventory i ON i.material_id=m.id WHERE m.id=?''',(mid,)).fetchone()
        if row is None:raise ValueError(f'Missing Traveller material ID {mid}')
        result.append((row['name'],quantity,row['owned'],max(0,quantity-row['owned'])))
    return progress,talents,exp,base_mora,sorted(result,key=lambda r:r[0].casefold())


def main():
    if not DB_PATH.is_file():raise SystemExit('Place this script beside genshin_v2.db')
    try:
        with sqlite3.connect(DB_PATH) as db:
            progress,talents,exp,mora,items=calculate(db)
    except (sqlite3.Error,ValueError) as error:
        raise SystemExit(f'Cannot calculate Traveller: {error}') from error
    print(f'Traveller level {progress["current_level"]} -> {progress["target_level"]}, '
          f'ascension {progress["current_ascension"]} -> {progress["target_ascension"]}')
    print(f'EXP points: {exp:,}; leveling Mora baseline: {mora:,}')
    print('Talent goals: '+', '.join(f'{t["element"]} {t["talent_slot"]} '
          f'{t["current_level"]}->{t["target_level"]}' for t in talents if t['current_level']!=t['target_level'])
          if any(t['current_level']!=t['target_level'] for t in talents) else 'Talent goals: none')
    print(f'\n{"Material":42} {"Required":>12} {"Owned":>12} {"Missing":>12}')
    print('-'*81)
    for name,required,owned,missing in items:
        print(f'{name[:42]:42} {required:12,} {owned:12,} {missing:12,}')

if __name__=='__main__':main()
