"""Inventory overview and remaining costs to max the owned catalog."""
import sqlite3
from collections import Counter

from character_requirements import calculate as character_requirements
from weapon_requirements import calculate as weapon_requirements
from traveller_requirements import calculate as traveller_requirements
from shopping_list import build
from overview_order_data import MATERIAL_ORDER
from catalog_lookup_data import TALENT_BOOK_ORDER, WEAPON_ASCENSION_ORDER, WEEKLY_BOSS_TYPES
from conversion_plan import plan as conversion_plan
from traveller_catalog_data import TRAVELLER_DETAILS

CATEGORIES = [
    ('currency', 'Mora'), ('character_exp', 'Character EXP Items'),
    ('weapon_exp', 'Weapon EXP Items'), ('talent_book', 'Talent Materials'),
    ('weapon_ascension', 'Weapon Ascension Materials'),
    ('common_drop', 'Common Enemy Drops'), ('elite_drop', 'Elite Enemy Drops'),
    ('character_boss_drop', 'World Boss Drops'),
    ('weekly_boss_drop', 'Weekly Boss Drops'),
    ('local_specialty', 'Local Specialties'), ('ascension_gem', 'Ascension Gems'),
    ('talent_special', 'Crown of Insight'),
]
EXP_VALUES = {
    "Wanderer's Advice": 1000, "Adventurer's Experience": 5000,
    "Hero's Wit": 20000, 'Enhancement Ore': 400,
    'Fine Enhancement Ore': 2000, 'Mystic Enhancement Ore': 10000,
}


def max_remaining(db):
    """Calculate from current progress to max in a private in-memory snapshot.

    The real database, its targets, and additional weapon copies are untouched.
    """
    temp = sqlite3.connect(':memory:')
    try:
        db.backup(temp)
        temp.row_factory = sqlite3.Row
        temp.execute('UPDATE character_progress SET target_level=90,target_ascension=6')
        temp.execute('UPDATE talent_progress SET target_level=10')
        temp.execute('''UPDATE weapon_copies SET target_level=(CASE WHEN
            (SELECT rarity FROM weapons WHERE id=weapon_id)<=2 THEN 70 ELSE 90 END),
            target_ascension=(CASE WHEN
            (SELECT rarity FROM weapons WHERE id=weapon_id)<=2 THEN 4 ELSE 6 END)''')
        temp.execute('UPDATE traveller_progress SET target_level=90,target_ascension=6')
        temp.execute("UPDATE traveller_talent_progress SET target_level=10")
        totals = Counter()
        excluded = []
        character_exp = weapon_exp = 0
        count = Counter()
        for cid, name in temp.execute('SELECT id,name FROM characters ORDER BY id').fetchall():
            try:
                _, _, exp, _, items = character_requirements(temp, name)
            except (ValueError, sqlite3.Error) as error:
                excluded.append(f'Character {name}: {error}')
                continue
            count['characters'] += 1
            character_exp += exp
            for material, required, _, _ in items:
                totals[material] += required
        copies = temp.execute('''SELECT wc.id,w.name FROM weapon_copies wc
            JOIN weapons w ON w.id=wc.weapon_id WHERE wc.copy_number=1
            ORDER BY wc.id''').fetchall()
        for copy_id, name in copies:
            try:
                _, exp, _, items = weapon_requirements(temp, name, copy_id)
            except (ValueError, sqlite3.Error) as error:
                excluded.append(f'Weapon {name}: {error}')
                continue
            count['first weapon copies'] += 1
            weapon_exp += exp
            for material, required, _, _ in items:
                totals[material] += required
        try:
            _, _, exp, _, items = traveller_requirements(temp)
        except (ValueError, sqlite3.Error) as error:
            excluded.append(f'Traveller: {error}')
        else:
            count['Traveller'] = 1
            character_exp += exp
            for material, required, _, _ in items:
                totals[material] += required
        return totals, character_exp, weapon_exp, dict(count), excluded
    finally:
        temp.close()


def overview(db):
    goals, _, included, goal_excluded, character_exp, weapon_exp = build(db)
    maximum, max_character_exp, max_weapon_exp, max_included, max_excluded = max_remaining(db)
    db.row_factory = sqlite3.Row
    sections = {category: {'category':category,'title':title,'materials':[]}
                for category,title in CATEGORIES}
    sections['other'] = {'category':'other','title':'Other Materials','materials':[]}
    try:
        display_names=dict(db.execute('SELECT material_id,original_name FROM material_display_names'))
    except sqlite3.OperationalError as error:
        if 'no such table' not in str(error):
            raise
        display_names={}
    new_families = {}
    for category, table, links, entity_id, field, role in (
        ('common_drop','characters','character_materials','character_id','common_drop_family','common_drop'),
        ('common_drop','weapons','weapon_materials','weapon_id','common_drop_family','common_drop'),
        ('elite_drop','weapons','weapon_materials','weapon_id','elite_drop_family','elite_drop'),
        ('talent_book','characters','character_materials','character_id','talent_book_family','talent_book'),
        ('weapon_ascension','weapons','weapon_materials','weapon_id','ascension_family','weapon_ascension'),
        ('weekly_boss_drop','characters','character_materials','character_id','weekly_boss_material','weekly_boss_drop'),
    ):
        for name, family, tier in db.execute(f'''SELECT m.name,e.{field},l.tier FROM {table} e
            JOIN {links} l ON l.{entity_id}=e.id AND l.material_role=?
            JOIN materials m ON m.id=l.material_id''',(role,)):
            key = (category,name)
            value = ((family or '').casefold(),tier)
            new_families[key] = min(new_families.get(key,value),value)
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='material_family_tiers'").fetchone():
        for category,name,family,tier in db.execute('''SELECT f.material_role,m.name,f.family,f.tier
            FROM material_family_tiers f JOIN materials m ON m.id=f.material_id'''):
            new_families[(category,name)]=(family.casefold(),tier)
    owned_exp = {'character':0,'weapon':0}
    for row in db.execute('''SELECT m.id,m.name,m.category,COALESCE(i.quantity,0) owned
        FROM materials m LEFT JOIN inventory i ON i.material_id=m.id ORDER BY m.name'''):
        mid, name, category, owned = row
        goal, ceiling = goals[name], maximum[name]
        material = {'id':mid,'name':name,'owned':owned,'required':goal,
                    'still_needed':max(0,goal-owned),'max_required':ceiling,
                    'max_still_needed':max(0,ceiling-owned),
                    'sort_name':display_names.get(mid,name)}
        if name in EXP_VALUES:
            material['exp_each'] = EXP_VALUES[name]
            material['exp_held'] = owned * EXP_VALUES[name]
            kind = 'character' if category == 'character_exp' else 'weapon'
            owned_exp[kind] += owned * EXP_VALUES[name]
        sections.get(category,sections['other'])['materials'].append(material)
    for section in sections.values():
        category = section['category']
        if category in ('character_exp','weapon_exp'):
            section['materials'].sort(key=lambda item: (item.get('exp_each',float('inf')),item['name']))
            continue
        priority = {name:index for index,name in enumerate(MATERIAL_ORDER.get(category,()))}
        section['materials'].sort(key=lambda item: (
            0 if item['sort_name'] in priority else 1,
            priority.get(item['sort_name'],0),
            new_families.get((category,item['name']),(item['name'].casefold(),0)),
            item['name'].casefold()))
        for item in section['materials']:
            position = priority.get(item['sort_name'])
            if position is not None and category in ('common_drop','elite_drop','talent_book',
                                                      'weapon_ascension','ascension_gem','weekly_boss_drop'):
                family_size = 4 if category in ('weapon_ascension','ascension_gem') else (1 if category=='weekly_boss_drop' else 3)
                if category == 'weekly_boss_drop':
                    type_name = WEEKLY_BOSS_TYPES[position][0]
                    family = type_name.rsplit(' ',1)[0] if type_name.rsplit(' ',1)[-1].isdigit() else type_name
                else:
                    family = str(position // family_size)
                if category in ('talent_book','weapon_ascension'):
                    types = TALENT_BOOK_ORDER if category=='talent_book' else WEAPON_ASCENSION_ORDER
                    type_name = types[position // family_size]
                    family = type_name
                    item['region'] = type_name.rsplit(' ',1)[0]
            else:
                family = new_families.get((category,item['name']),(item['name'].casefold(),0))[0]
                if category in ('talent_book','weapon_ascension'):
                    item['region'] = family.rsplit(' ',1)[0] if family.rsplit(' ',1)[-1].isdigit() else family
            item['family'] = family
        materials = section['materials']
        start = 0
        while start < len(materials):
            end = start + 1
            while end < len(materials) and materials[end]['family'] == materials[start]['family']:
                end += 1
            group = materials[start:end]
            can_convert = (category == 'weekly_boss_drop' and len(group) > 1 or
                           category in ('common_drop','elite_drop','talent_book',
                                        'weapon_ascension','ascension_gem') and len(group) in (3,4))
            for required_field,needed_field,converted_field in (
                ('required','still_needed','convert_for_goal'),
                ('max_required','max_still_needed','convert_for_max')):
                if can_convert:
                    missing, converted = conversion_plan(
                        [item['owned'] for item in group],
                        [item[required_field] for item in group],
                        interchangeable=category=='weekly_boss_drop')
                else:
                    missing = [max(0,item[required_field]-item['owned']) for item in group]
                    converted = [0]*len(group)
                for item,shortage,outputs in zip(group,missing,converted):
                    item[needed_field] = shortage
                    item[converted_field] = outputs
            start = end
    return {'sections':[section for section in sections.values() if section['materials']],
            'experience':{
                'character':{'required':character_exp,'owned':owned_exp['character'],
                             'max_required':max_character_exp},
                'weapon':{'required':weapon_exp,'owned':owned_exp['weapon'],
                          'max_required':max_weapon_exp}},
            'goal_included':dict(included),'goal_excluded':goal_excluded,
            'max_included':max_included,'max_excluded':max_excluded,
            'max_complete':not max_excluded,
        'max_note':''}


def progress_lists(db):
    db.row_factory=sqlite3.Row
    characters=[]
    for row in db.execute('''SELECT c.id,c.name,c.element,c.gem_family,c.boss_material,
        c.common_drop_family,c.local_specialty,c.talent_book_family,
        c.weekly_boss_material,p.current_level,p.target_level,
        p.current_ascension,p.target_ascension FROM characters c
        JOIN character_progress p ON p.character_id=c.id ORDER BY c.id''').fetchall():
        item=dict(row)
        item['talents']=[dict(t) for t in db.execute('''SELECT talent_slot,current_level,target_level
            FROM talent_progress WHERE character_id=? ORDER BY talent_slot''',(row['id'],))]
        characters.append(item)
    weapons=[dict(row) for row in db.execute('''SELECT wc.id,w.id AS weapon_id,w.name,w.weapon_type,w.rarity,
        w.ascension_family,w.common_drop_family,w.elite_drop_family,wc.copy_number,wc.label,
        wc.current_level,wc.target_level,wc.current_ascension,wc.target_ascension
        FROM weapon_copies wc JOIN weapons w ON w.id=wc.weapon_id
        ORDER BY w.id,wc.copy_number''')]
    traveller_talents=[]
    has_traveller_details=bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='traveller_catalog_details'").fetchone())
    for row in db.execute('''SELECT id,element,talent_slot,current_level,target_level
        FROM traveller_talent_progress ORDER BY id'''):
        item=dict(row)
        details=TRAVELLER_DETAILS.get(row['element'],())
        common,talent_mat,weekly=(details[row['talent_slot']-1]
            if 1<=row['talent_slot']<=len(details) else (None,None,None))
        if has_traveller_details:
            saved=db.execute('''SELECT common_drop_family,talent_material_type,weekly_boss_type
                FROM traveller_catalog_details WHERE element=? AND talent_slot=?''',
                (row['element'],row['talent_slot'])).fetchone()
            if saved is not None:
                common,talent_mat,weekly=saved
        item.update(common_drop_family=common,talent_material_type=talent_mat,
                    weekly_boss_type=weekly)
        traveller_talents.append(item)
    traveller={'progress':dict(db.execute('SELECT * FROM traveller_progress WHERE id=1').fetchone()),
               'talents':traveller_talents}
    return {'characters':characters,'weapons':weapons,'traveller':traveller}
