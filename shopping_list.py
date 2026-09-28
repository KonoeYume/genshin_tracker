"""Combine character and weapon goals into one inventory-aware shopping list.

Run beside genshin_v2.db, character_requirements.py, weapon_requirements.py:
    python shopping_list.py
Incomplete records are named and excluded. Traveller goals are not yet included.
"""
import sqlite3
from collections import Counter
from pathlib import Path

from character_requirements import calculate as character_requirements
from weapon_requirements import calculate as weapon_requirements
from traveller_requirements import calculate as traveller_requirements

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def build(db):
    totals = Counter()
    owned_by_name = {}
    included = Counter()
    included_weapons = set()
    excluded = []
    character_exp = weapon_exp = 0
    # Individual calculators return required amounts; discard their individual
    # "missing" values and subtract inventory only after combining all goals.
    for cid, name in db.execute('SELECT id, name FROM characters ORDER BY name').fetchall():
        try:
            _, _, exp, _, materials = character_requirements(db, name)
        except (ValueError, sqlite3.Error) as error:
            excluded.append(f'Character {name}: {error}')
            continue
        included['characters'] += 1
        character_exp += exp
        for material, required, owned, _ in materials:
            totals[material] += required
            owned_by_name[material] = owned

    for copy_id, weapon_id, name in db.execute('''SELECT wc.id,w.id,w.name FROM weapon_copies wc
        JOIN weapons w ON w.id = wc.weapon_id ORDER BY wc.id''').fetchall():
        try:
            _, exp, _, materials = weapon_requirements(db, name, copy_id)
        except (ValueError, sqlite3.Error) as error:
            excluded.append(f'Weapon copy {copy_id} ({name}): {error}')
            continue
        included['weapon copies'] += 1
        included_weapons.add(weapon_id)
        weapon_exp += exp
        for material, required, owned, _ in materials:
            totals[material] += required
            owned_by_name[material] = owned
    try:
        _, _, exp, _, materials = traveller_requirements(db)
    except (ValueError, sqlite3.Error) as error:
        excluded.append(f'Traveller: {error}')
    else:
        included['Traveller'] = 1
        character_exp += exp
        for material, required, owned, _ in materials:
            totals[material] += required
            owned_by_name[material] = owned
    included['weapons'] = len(included_weapons)
    return totals, owned_by_name, included, excluded, character_exp, weapon_exp


def main():
    if not DB_PATH.is_file():
        raise SystemExit('Place this script beside genshin_v2.db')
    with sqlite3.connect(DB_PATH) as db:
        try:
            totals, owned, included, excluded, char_exp, weapon_exp = build(db)
        except sqlite3.Error as error:
            raise SystemExit(f'Cannot read database: {error}') from error
    print(f'Included: {included["characters"]} characters, {included["weapon copies"]} weapon copies, '
          f'{included["Traveller"]} Traveller')
    print(f'Excluded: {len(excluded)} records')
    print(f'EXP points: characters {char_exp:,}; weapons {weapon_exp:,}')
    print('EXP points are separate; using EXP items can overshoot and increase Mora.\n')
    print(f'{"Material":42} {"Required":>12} {"Owned":>12} {"Missing":>12}')
    print('-' * 81)
    for name in sorted(totals, key=str.casefold):
        required = totals[name]
        have = owned[name]
        print(f'{name[:42]:42} {required:12,} {have:12,} {max(0, required-have):12,}')
    if excluded:
        print('\nEXCLUDED GOALS (their costs are absent from the totals):')
        for reason in excluded:
            print(' - ' + reason)


if __name__ == '__main__':
    main()
