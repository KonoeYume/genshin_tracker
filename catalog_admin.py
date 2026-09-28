"""Add catalog entries and their material links directly to SQLite.

Existing family links are reused. Unknown families become mapping issues so
shopping totals cannot silently omit their requirements.
"""
import sqlite3

FAMILY_TIERS = {
    'common_drop': (1, 2, 3),
    'elite_drop': (2, 3, 4),
    'talent_book': (2, 3, 4),
    'weapon_ascension': (2, 3, 4, 5),
    'weekly_boss_drop': (0,),
}
GEM_SUFFIXES = {2: 'Sliver', 3: 'Fragment', 4: 'Chunk', 5: 'Gemstone'}


def material(db, name, category):
    if category in ('currency','talent_special'):
        existing=db.execute('SELECT id FROM materials WHERE category=? ORDER BY id LIMIT 1',
                            (category,)).fetchone()
        if existing is not None:
            db.execute('''INSERT INTO inventory(material_id,quantity) VALUES (?,0)
                ON CONFLICT(material_id) DO NOTHING''',(existing[0],))
            return existing[0]
    db.execute('''INSERT INTO materials(name,category) VALUES (?,?)
        ON CONFLICT(name) DO NOTHING''', (name, category))
    mid = db.execute('SELECT id FROM materials WHERE name=?', (name,)).fetchone()[0]
    db.execute('''INSERT INTO inventory(material_id,quantity) VALUES (?,0)
        ON CONFLICT(material_id) DO NOTHING''', (mid,))
    return mid


def gem_material(db, family, tier, suffix, excluded_character=None):
    existing=db.execute('''SELECT cm.material_id FROM characters c
        JOIN character_materials cm ON cm.character_id=c.id
        WHERE c.gem_family=? AND cm.material_role='gem' AND cm.tier=?
        AND (? IS NULL OR c.id!=?) ORDER BY c.id LIMIT 1''',
        (family,tier,excluded_character,excluded_character)).fetchone()
    return existing[0] if existing else material(db,f'{family} {suffix}','ascension_gem')


def attach_id(db, kind, entity_id, role, tier, material_id):
    table, id_col = (('character_materials','character_id') if kind == 'character'
                     else ('weapon_materials','weapon_id'))
    db.execute(f'''INSERT INTO {table}({id_col},material_role,tier,material_id)
        VALUES (?,?,?,?)''',(entity_id,role,tier,material_id))


def family_links(db, role, family):
    """Find a complete tier set in saved families or any existing catalog item."""
    expected = set(FAMILY_TIERS[role])
    try:
        saved = dict(db.execute('''SELECT tier,material_id FROM material_family_tiers
            WHERE material_role=? AND family=?''', (role, family)))
    except sqlite3.OperationalError as error:
        if 'no such table' not in str(error):
            raise
        saved = {}
    if set(saved) == expected:
        return saved
    sources = {
        'common_drop': (
            ('characters', 'character_materials', 'character_id', 'common_drop_family'),
            ('weapons', 'weapon_materials', 'weapon_id', 'common_drop_family')),
        'elite_drop': (('weapons', 'weapon_materials', 'weapon_id', 'elite_drop_family'),),
        'talent_book': (('characters', 'character_materials', 'character_id', 'talent_book_family'),),
        'weapon_ascension': (('weapons', 'weapon_materials', 'weapon_id', 'ascension_family'),),
        'weekly_boss_drop': (('characters', 'character_materials', 'character_id',
                              'weekly_boss_material'),),
    }[role]
    for catalog, links, id_col, family_col in sources:
        for (entity_id,) in db.execute(f'SELECT id FROM {catalog} WHERE {family_col}=? ORDER BY id',
                                       (family,)).fetchall():
            found = dict(db.execute(f'''SELECT tier,material_id FROM {links}
                WHERE {id_col}=? AND material_role=?''', (entity_id, role)))
            if set(found) == expected:
                return found
    return None


def attach_family(db, kind, entity_id, role, family):
    links = family_links(db, role, family)
    if links is None:
        db.execute('''INSERT INTO material_mapping_issues
            (entity_kind,entity_id,material_role,missing_family) VALUES (?,?,?,?)''',
            (kind, entity_id, role, family))
        return False
    table, id_col = (('character_materials', 'character_id') if kind == 'character'
                     else ('weapon_materials', 'weapon_id'))
    db.executemany(f'''INSERT INTO {table}({id_col},material_role,tier,material_id)
        VALUES (?,?,?,?)''', [(entity_id, role, tier, mid) for tier, mid in links.items()])
    return True


def attach_named(db, kind, entity_id, role, tier, name, category):
    table, id_col = (('character_materials', 'character_id') if kind == 'character'
                     else ('weapon_materials', 'weapon_id'))
    mid = material(db, name, category)
    db.execute(f'''INSERT INTO {table}({id_col},material_role,tier,material_id)
        VALUES (?,?,?,?)''', (entity_id, role, tier, mid))


def create_character(db, data):
    """Call inside a database transaction; returns (id, missing roles)."""
    columns = ('name','element','boss_material','common_drop_family',
               'local_specialty','talent_book_family','weekly_boss_type')
    values = [data[key].strip() for key in columns]
    if any(not value for value in values):
        raise ValueError('Every character catalog field is required')
    gem_row = db.execute('SELECT gem_family FROM element_gems WHERE element=?',
                         (data['element'].strip(),)).fetchone()
    if gem_row is None:
        raise ValueError(f'Unknown element: {data["element"].strip()}')
    gem_family = gem_row[0]
    cursor = db.execute('''INSERT INTO characters
        (name,element,gem_family,boss_material,common_drop_family,local_specialty,
         talent_book_family,weekly_boss_material) VALUES (?,?,?,?,?,?,?,?)''',
        (values[0],values[1],gem_family,*values[2:]))
    cid = cursor.lastrowid
    db.execute('INSERT INTO character_progress VALUES (?,1,1,0,0)', (cid,))
    db.executemany('INSERT INTO talent_progress VALUES (?,?,1,1)',
                   [(cid, slot) for slot in (1,2,3)])
    for tier, suffix in GEM_SUFFIXES.items():
        attach_id(db,'character',cid,'gem',tier,gem_material(db,gem_family,tier,suffix,cid))
    for role, field, category in (
        ('boss_drop','boss_material','character_boss_drop'),
        ('local_specialty','local_specialty','local_specialty')):
        attach_named(db, 'character', cid, role, 0, data[field].strip(), category)
    attach_named(db, 'character', cid, 'crown', 0, 'Crown of Insight', 'talent_special')
    attach_named(db, 'character', cid, 'mora', 0, 'Mora', 'currency')
    missing = [role for role, field in (
        ('common_drop','common_drop_family'),('talent_book','talent_book_family'),
        ('weekly_boss_drop','weekly_boss_type'))
        if not attach_family(db, 'character', cid, role, data[field].strip())]
    return cid, missing


def create_weapon(db, data):
    """Call inside a database transaction; returns (id, copy_id, missing roles)."""
    columns = ('name','weapon_type','ascension_family','common_drop_family','elite_drop_family')
    values = [data[key].strip() for key in columns]
    if any(not value for value in values):
        raise ValueError('Every weapon catalog field is required')
    rarity = data['rarity']
    if type(rarity) is not int or rarity not in range(1,6):
        raise ValueError('Weapon rarity must be 1 through 5')
    cursor = db.execute('''INSERT INTO weapons
        (name,weapon_type,rarity,ascension_family,common_drop_family,elite_drop_family)
        VALUES (?,?,?,?,?,?)''', (values[0], values[1], rarity, *values[2:]))
    wid = cursor.lastrowid
    copy = db.execute('''INSERT INTO weapon_copies
        (weapon_id,copy_number,source_sheet,label,current_level,target_level,
         current_ascension,target_ascension) VALUES (?,1,NULL,NULL,1,1,0,0)''',
        (wid,))
    attach_named(db, 'weapon', wid, 'mora', 0, 'Mora', 'currency')
    missing = [role for role, field in (
        ('weapon_ascension','ascension_family'),('common_drop','common_drop_family'),
        ('elite_drop','elite_drop_family'))
        if not attach_family(db, 'weapon', wid, role, data[field].strip())]
    return wid, copy.lastrowid, missing
