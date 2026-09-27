"""Show one character's remaining materials from genshin_v2.db.

Run: python character_requirements.py Ineffa
The EXP and Mora figures use exact level-table EXP; consuming EXP items may
overshoot that amount and cost extra Mora.
"""
import argparse
import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def cumulative_costs(db, table, key, start, end):
    """Return material (role, tier) increases between two cumulative rows."""
    if end < start:
        raise ValueError(f'{table}: target {end} is below current {start}')
    rows = db.execute(
        f'SELECT {key}, material_role, tier, cumulative_quantity FROM {table} '
        f'WHERE {key} IN (?, ?)', (start, end)
    ).fetchall()
    by_step = {(row[key], row['material_role'], row['tier']): row['cumulative_quantity']
               for row in rows}
    end_costs = {(role, tier): qty for (step, role, tier), qty in by_step.items()
                 if step == end}
    start_costs = {(role, tier): qty for (step, role, tier), qty in by_step.items()
                   if step == start}
    if not rows or (start != end and (not start_costs or not end_costs)):
        raise ValueError(f'{table} is missing cumulative rows for {start} or {end}')
    result = Counter()
    for role_tier in start_costs.keys() | end_costs.keys():
        difference = end_costs.get(role_tier, 0) - start_costs.get(role_tier, 0)
        if difference < 0:
            raise ValueError(f'{table} decreases for {role_tier}: {start} to {end}')
        if difference:
            result[role_tier] = difference
    return result


def level_exp(db, level):
    row = db.execute(
        "SELECT cumulative_exp FROM level_exp "
        "WHERE entity_kind = 'character' AND rarity = 0 AND level = ?", (level,)
    ).fetchone()
    if row is None:
        raise ValueError(f'No character EXP entry for level {level}')
    return row['cumulative_exp']


def calculate(db, name):
    db.row_factory = sqlite3.Row
    character = db.execute('''SELECT c.id, c.name, p.current_level, p.target_level,
        p.current_ascension, p.target_ascension
        FROM characters c JOIN character_progress p ON p.character_id = c.id
        WHERE c.name = ?''', (name,)).fetchone()
    if character is None:
        raise ValueError(f'Character {name!r} not found (or progress not imported)')
    cid = character['id']
    issues = db.execute('''SELECT material_role, missing_family
        FROM material_mapping_issues WHERE entity_kind = 'character' AND entity_id = ?
        ORDER BY material_role''', (cid,)).fetchall()
    if issues:
        details = '; '.join(f'{r["material_role"]}: {r["missing_family"]}' for r in issues)
        raise ValueError(f'{name} has incomplete material links: {details}. '
                         'Complete the missing family in the web app.')

    current, target = character['current_level'], character['target_level']
    if target < current:
        raise ValueError('Target character level is below current level')
    exp = level_exp(db, target) - level_exp(db, current)
    if exp < 0:
        raise ValueError('Level EXP total decreased')
    base_mora = (exp + 4) // 5
    costs = cumulative_costs(db, 'character_ascension_costs', 'ascension',
                             character['current_ascension'], character['target_ascension'])
    talents = db.execute('''SELECT talent_slot, current_level, target_level
        FROM talent_progress WHERE character_id = ? ORDER BY talent_slot''', (cid,)).fetchall()
    if len(talents) != 3 or [t['talent_slot'] for t in talents] != [1, 2, 3]:
        raise ValueError(f'{name} needs exactly three imported talent progress rows')
    for talent in talents:
        costs.update(cumulative_costs(db, 'talent_costs', 'talent_level',
                                      talent['current_level'], talent['target_level']))
    costs[('mora', 0)] += base_mora

    material_ids = {(r['material_role'], r['tier']): r['material_id'] for r in
        db.execute('''SELECT material_role, tier, material_id FROM character_materials
            WHERE character_id = ?''', (cid,))}
    quantities = Counter()
    for role_tier, quantity in costs.items():
        if quantity <= 0:
            continue
        material_id = material_ids.get(role_tier)
        if material_id is None:
            raise ValueError(f'{name} has no material link for {role_tier}; '
                             'check the material mappings in the database')
        quantities[material_id] += quantity

    result = []
    for material_id, required in quantities.items():
        row = db.execute('''SELECT m.name, COALESCE(i.quantity, 0) AS owned
            FROM materials m LEFT JOIN inventory i ON i.material_id = m.id
            WHERE m.id = ?''', (material_id,)).fetchone()
        if row is None:
            raise ValueError(f'Material ID {material_id} is missing')
        result.append((row['name'], required, row['owned'], max(0, required - row['owned'])))
    return character, talents, exp, base_mora, sorted(result, key=lambda r: r[0].casefold())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('character', nargs='?', default='Ineffa', help='exact character name (default: Ineffa)')
    args = parser.parse_args()
    if not DB_PATH.is_file():
        parser.exit(1, f'Place this script beside {DB_PATH.name}\n')
    try:
        with sqlite3.connect(DB_PATH) as db:
            c, talents, exp, base_mora, materials = calculate(db, args.character)
    except (sqlite3.Error, ValueError) as error:
        parser.exit(1, f'Cannot calculate: {error}\n')
    print(f'{c["name"]}: level {c["current_level"]} -> {c["target_level"]}, '
          f'ascension {c["current_ascension"]} -> {c["target_ascension"]}')
    print('Talents: ' + ', '.join(f'{t["talent_slot"]}: {t["current_level"]} -> {t["target_level"]}'
                                for t in talents))
    print(f'Character EXP points: {exp:,} (leveling Mora baseline: {base_mora:,})')
    print(f'\n{"Material":42} {"Required":>12} {"Owned":>12} {"Missing":>12}')
    print('-' * 81)
    for name, required, owned, missing in materials:
        print(f'{name[:42]:42} {required:12,} {owned:12,} {missing:12,}')
    print('\nEXP points are separate from the material list; EXP item use can overshoot.')


if __name__ == '__main__':
    main()
