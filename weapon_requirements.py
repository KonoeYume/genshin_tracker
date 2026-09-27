"""Show the remaining materials for one weapon copy in genshin_v2.db.

Run: python weapon_requirements.py "Weapon Name"
If several copies exist, add --copy ID. Run without a name for the first copy.
"""
import argparse
import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'


def cumulative_costs(db, rarity, start, end):
    if end < start:
        raise ValueError('Target ascension is below current ascension')
    rows = db.execute('''SELECT ascension, material_role, tier, cumulative_quantity
        FROM weapon_ascension_costs WHERE rarity = ? AND ascension IN (?, ?)''',
        (rarity, start, end)).fetchall()
    by_step = {(r['ascension'], r['material_role'], r['tier']): r['cumulative_quantity'] for r in rows}
    start_costs = {(role, tier): qty for (step, role, tier), qty in by_step.items() if step == start}
    end_costs = {(role, tier): qty for (step, role, tier), qty in by_step.items() if step == end}
    if not rows or (start != end and (not start_costs or not end_costs)):
        raise ValueError(f'Weapon ascension costs missing for rarity {rarity}, {start} to {end}')
    costs = Counter()
    for role_tier in start_costs.keys() | end_costs.keys():
        difference = end_costs.get(role_tier, 0) - start_costs.get(role_tier, 0)
        if difference < 0:
            raise ValueError(f'Weapon ascension cost decreases for {role_tier}')
        if difference:
            costs[role_tier] = difference
    return costs


def level_exp(db, rarity, level):
    row = db.execute('''SELECT cumulative_exp FROM level_exp
        WHERE entity_kind = 'weapon' AND rarity = ? AND level = ?''', (rarity, level)).fetchone()
    if row is None:
        raise ValueError(f'No EXP entry for rarity {rarity} weapon level {level}')
    return row['cumulative_exp']


def calculate(db, name=None, copy_id=None):
    db.row_factory = sqlite3.Row
    rows = db.execute('''SELECT wc.*, w.name, w.rarity FROM weapon_copies wc
        JOIN weapons w ON w.id = wc.weapon_id
        WHERE (? IS NULL OR w.name = ?) AND (? IS NULL OR wc.id = ?)
        ORDER BY wc.id''', (name, name, copy_id, copy_id)).fetchall()
    if not rows:
        raise ValueError('No matching weapon copy; check the name or copy ID')
    if name is None and copy_id is None:
        rows = rows[:1]
    if len(rows) > 1:
        copies = ', '.join(f'{r["id"]} ({r["label"] or r["source_sheet"] or "copy"})' for r in rows)
        raise ValueError(f'Multiple copies of {name}: {copies}. Add --copy ID')
    weapon = rows[0]
    wid, rarity = weapon['weapon_id'], weapon['rarity']
    issues = db.execute('''SELECT material_role, missing_family FROM material_mapping_issues
        WHERE entity_kind = 'weapon' AND entity_id = ? ORDER BY material_role''', (wid,)).fetchall()
    if issues:
        details = '; '.join(f'{r["material_role"]}: {r["missing_family"]}' for r in issues)
        raise ValueError(f'{weapon["name"]} has incomplete material links: {details}. '
                         'Complete the missing family in the web app.')
    current, target = weapon['current_level'], weapon['target_level']
    if target < current:
        raise ValueError('Target weapon level is below current level')
    exp = level_exp(db, rarity, target) - level_exp(db, rarity, current)
    if exp < 0:
        raise ValueError('Weapon EXP total decreased')
    base_mora = (exp + 9) // 10
    costs = cumulative_costs(db, rarity, weapon['current_ascension'], weapon['target_ascension'])
    costs[('mora', 0)] += base_mora
    links = {(r['material_role'], r['tier']): r['material_id'] for r in
             db.execute('''SELECT material_role, tier, material_id FROM weapon_materials
                 WHERE weapon_id = ?''', (wid,))}
    required_by_id = Counter()
    for role_tier, quantity in costs.items():
        if quantity <= 0:
            continue
        material_id = links.get(role_tier)
        if material_id is None:
            raise ValueError(f'No material link for {weapon["name"]} {role_tier}; '
                             'check the material mappings in the database')
        required_by_id[material_id] += quantity
    materials = []
    for material_id, required in required_by_id.items():
        row = db.execute('''SELECT m.name, COALESCE(i.quantity, 0) AS owned
            FROM materials m LEFT JOIN inventory i ON i.material_id = m.id
            WHERE m.id = ?''', (material_id,)).fetchone()
        if row is None:
            raise ValueError(f'Material ID {material_id} is missing')
        materials.append((row['name'], required, row['owned'], max(0, required - row['owned'])))
    return weapon, exp, base_mora, sorted(materials, key=lambda r: r[0].casefold())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weapon', nargs='?', help='exact weapon name')
    parser.add_argument('--copy', type=int, help='ID of one particular owned copy')
    args = parser.parse_args()
    if not DB_PATH.is_file():
        parser.exit(1, f'Place this script beside {DB_PATH.name}\n')
    try:
        with sqlite3.connect(DB_PATH) as db:
            w, exp, base_mora, materials = calculate(db, args.weapon, args.copy)
    except (sqlite3.Error, ValueError) as error:
        parser.exit(1, f'Cannot calculate: {error}\n')
    print(f'{w["name"]} (copy ID {w["id"]}, {w["rarity"]}-star): '
          f'level {w["current_level"]} -> {w["target_level"]}, '
          f'ascension {w["current_ascension"]} -> {w["target_ascension"]}')
    print(f'Weapon EXP points: {exp:,} (leveling Mora baseline: {base_mora:,})')
    print(f'\n{"Material":42} {"Required":>12} {"Owned":>12} {"Missing":>12}')
    print('-' * 81)
    for name, required, owned, missing in materials:
        print(f'{name[:42]:42} {required:12,} {owned:12,} {missing:12,}')
    print('\nEXP points are separate from the material list; EXP item use can overshoot.')


if __name__ == '__main__':
    main()
