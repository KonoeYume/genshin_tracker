"""Edit catalog records while keeping material IDs and requirement links intact."""
from catalog_admin import FAMILY_TIERS, GEM_SUFFIXES, family_links, gem_material, material
from traveller_catalog_data import TRAVELLER_DETAILS

MATERIAL_CATEGORIES = ('currency','character_exp','weapon_exp','talent_book',
    'weapon_ascension','common_drop','elite_drop','character_boss_drop',
    'weekly_boss_drop','local_specialty','ascension_gem','talent_special')


def create_material_type(db, role, family, names):
    if role in ('character_boss_drop','local_specialty'):
        family=clean(family,'Material name')
        if len(names)!=1 or clean(names[0],'Material name')!=family:
            raise ValueError('For this bucket, the material name must match the type name')
        existing=db.execute('SELECT 1 FROM materials WHERE name=?',(family,)).fetchone()
        if existing:
            raise ValueError('This material already exists')
        mid=material(db,family,role)
        return {'material_role':role,'family':family,'materials':[family],
                'updated_records':0,'material_id':mid}
    if role not in FAMILY_TIERS:
        raise ValueError('Choose a supported material bucket')
    family=clean(family,'Type name')
    names=[clean(name,'Material name') for name in names]
    tiers=FAMILY_TIERS[role]
    if len(names)!=len(tiers) or len(set(names))!=len(names):
        raise ValueError(f'Enter {len(tiers)} distinct material names')
    if family_links(db,role,family) is not None:
        raise ValueError('This type already exists')
    for name in names:
        existing=db.execute('SELECT category FROM materials WHERE name=?',(name,)).fetchone()
        if existing and existing[0]!=role:
            raise ValueError(f'{name} belongs to the {existing[0]} bucket')
    db.execute('''CREATE TABLE IF NOT EXISTS material_family_tiers (
        material_role TEXT NOT NULL, family TEXT NOT NULL, tier INTEGER NOT NULL,
        material_id INTEGER NOT NULL REFERENCES materials(id),
        PRIMARY KEY(material_role,family,tier))''')
    links=[]
    for tier,name in zip(tiers,names):
        mid=material(db,name,role)
        db.execute('''INSERT INTO material_family_tiers(material_role,family,tier,material_id)
            VALUES (?,?,?,?) ON CONFLICT(material_role,family,tier)
            DO UPDATE SET material_id=excluded.material_id''',(role,family,tier,mid))
        links.append((tier,mid))
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='material_type_order'").fetchone():
        if db.execute('SELECT 1 FROM material_type_order WHERE material_role=? AND type_name=?',
                      (role,family)).fetchone() is None:
            position=db.execute('''SELECT COALESCE(MAX(sort_order),0)+1 FROM material_type_order
                WHERE material_role=?''',(role,)).fetchone()[0]
            db.execute('''INSERT INTO material_type_order(material_role,type_name,sort_order)
                VALUES (?,?,?)''',(role,family,position))
    issues=db.execute('''SELECT entity_kind,entity_id FROM material_mapping_issues
        WHERE material_role=? AND missing_family=?''',(role,family)).fetchall()
    for kind,entity_id in issues:
        if kind not in ('character','weapon'):
            raise ValueError('Unknown catalog entry in missing material types')
        table,col=(('character_materials','character_id') if kind=='character'
                   else ('weapon_materials','weapon_id'))
        db.executemany(f'''INSERT INTO {table}({col},material_role,tier,material_id)
            VALUES (?,?,?,?) ON CONFLICT({col},material_role,tier)
            DO UPDATE SET material_id=excluded.material_id''',
            [(entity_id,role,tier,mid) for tier,mid in links])
    db.execute('''DELETE FROM material_mapping_issues WHERE material_role=?
        AND missing_family=?''',(role,family))
    return {'material_role':role,'family':family,'materials':names,'updated_records':len(issues)}


def traveller_details(db, element, slot):
    if db.execute('''SELECT 1 FROM traveller_talent_progress
        WHERE element=? AND talent_slot=?''',(element,slot)).fetchone() is None:
        raise LookupError('Traveller talent not found')
    db.execute('''CREATE TABLE IF NOT EXISTS traveller_catalog_details (
        element TEXT NOT NULL, talent_slot INTEGER NOT NULL,
        common_drop_family TEXT NOT NULL, talent_material_type TEXT NOT NULL,
        weekly_boss_type TEXT NOT NULL,
        PRIMARY KEY(element,talent_slot))''')
    row=db.execute('''SELECT common_drop_family,talent_material_type,weekly_boss_type
        FROM traveller_catalog_details WHERE element=? AND talent_slot=?''',
        (element,slot)).fetchone()
    if row is None:
        values=TRAVELLER_DETAILS.get(element,())
        row=values[slot-1] if 1<=slot<=len(values) else ('','','')
    return dict(element=element,talent_slot=slot,common_drop_family=row[0],
                talent_material_type=row[1],weekly_boss_type=row[2])


def edit_traveller(db, element, slot, data):
    traveller_details(db,element,slot)
    values=[data[key].strip() for key in (
        'common_drop_family','talent_material_type','weekly_boss_type')]
    db.execute('''INSERT INTO traveller_catalog_details
        (element,talent_slot,common_drop_family,talent_material_type,weekly_boss_type)
        VALUES (?,?,?,?,?) ON CONFLICT(element,talent_slot) DO UPDATE SET
        common_drop_family=excluded.common_drop_family,
        talent_material_type=excluded.talent_material_type,
        weekly_boss_type=excluded.weekly_boss_type''',(element,slot,*values))
    return traveller_details(db,element,slot)


def clean(value, field):
    result = value.strip()
    if not result:
        raise ValueError(f'{field} cannot be blank')
    return result


def named_link(db, kind, entity_id, role, tier, name, category):
    table, column = (('character_materials','character_id') if kind=='character'
                     else ('weapon_materials','weapon_id'))
    mid = material(db,name,category)
    db.execute(f'''INSERT INTO {table}({column},material_role,tier,material_id)
        VALUES (?,?,?,?) ON CONFLICT({column},material_role,tier)
        DO UPDATE SET material_id=excluded.material_id''',(entity_id,role,tier,mid))
    db.execute('''DELETE FROM material_mapping_issues WHERE entity_kind=? AND entity_id=?
        AND material_role=?''',(kind,entity_id,role))


def relink_family(db, kind, entity_id, role, family):
    table, column = (('character_materials','character_id') if kind=='character'
                     else ('weapon_materials','weapon_id'))
    db.execute(f'DELETE FROM {table} WHERE {column}=? AND material_role=?',(entity_id,role))
    db.execute('''DELETE FROM material_mapping_issues WHERE entity_kind=? AND entity_id=?
        AND material_role=?''',(kind,entity_id,role))
    links = family_links(db,role,family)
    if links is None:
        db.execute('''INSERT INTO material_mapping_issues
            (entity_kind,entity_id,material_role,missing_family) VALUES (?,?,?,?)''',
            (kind,entity_id,role,family))
        return False
    if set(links) != set(FAMILY_TIERS[role]):
        raise ValueError(f'Incomplete {role} type {family}')
    db.executemany(f'''INSERT INTO {table}({column},material_role,tier,material_id)
        VALUES (?,?,?,?)''',[(entity_id,role,tier,mid) for tier,mid in links.items()])
    return True


def edit_character(db, cid, data):
    old=db.execute('''SELECT common_drop_family,talent_book_family,weekly_boss_material
        FROM characters WHERE id=?''',(cid,)).fetchone()
    if old is None:
        raise LookupError('Character not found')
    fields={key:clean(data[key],key) for key in (
        'name','element','boss_material','common_drop_family','local_specialty',
        'talent_book_family','weekly_boss_type')}
    gem=db.execute('SELECT gem_family FROM element_gems WHERE element=?',
                   (fields['element'],)).fetchone()
    if gem is None:
        raise ValueError('Unknown character element')
    db.execute('''UPDATE characters SET name=?,element=?,gem_family=?,boss_material=?,
        common_drop_family=?,local_specialty=?,talent_book_family=?,weekly_boss_material=?
        WHERE id=?''',(fields['name'],fields['element'],gem[0],fields['boss_material'],
                     fields['common_drop_family'],fields['local_specialty'],
                     fields['talent_book_family'],fields['weekly_boss_type'],cid))
    for tier,suffix in GEM_SUFFIXES.items():
        mid=gem_material(db,gem[0],tier,suffix,cid)
        db.execute('''INSERT INTO character_materials
            (character_id,material_role,tier,material_id) VALUES (?,'gem',?,?)
            ON CONFLICT(character_id,material_role,tier)
            DO UPDATE SET material_id=excluded.material_id''',(cid,tier,mid))
    for role,key,category in (('boss_drop','boss_material','character_boss_drop'),
                              ('local_specialty','local_specialty','local_specialty')):
        named_link(db,'character',cid,role,0,fields[key],category)
    missing=[]
    for role,key,previous in (('common_drop','common_drop_family',old[0]),
                              ('talent_book','talent_book_family',old[1]),
                              ('weekly_boss_drop','weekly_boss_type',old[2])):
        issue=db.execute('''SELECT 1 FROM material_mapping_issues WHERE entity_kind='character'
            AND entity_id=? AND material_role=?''',(cid,role)).fetchone()
        if previous!=fields[key] or issue:
            if not relink_family(db,'character',cid,role,fields[key]):
                missing.append(role)
    return missing


def edit_weapon(db, wid, data):
    old=db.execute('''SELECT ascension_family,common_drop_family,elite_drop_family
        FROM weapons WHERE id=?''',(wid,)).fetchone()
    if old is None:
        raise LookupError('Weapon not found')
    fields={key:clean(data[key],key) for key in (
        'name','weapon_type','ascension_family','common_drop_family','elite_drop_family')}
    if fields['weapon_type'] not in ('Sword','Claymore','Polearm','Catalyst','Bow'):
        raise ValueError('Unknown weapon type')
    rarity=data['rarity']
    if type(rarity) is not int or rarity not in range(1,6):
        raise ValueError('Rarity must be 1 through 5')
    if rarity<=2 and db.execute('''SELECT 1 FROM weapon_copies WHERE weapon_id=? AND
        (current_level>70 OR target_level>70 OR current_ascension>4 OR target_ascension>4)
        LIMIT 1''',(wid,)).fetchone():
        raise ValueError('A weapon copy exceeds the level 70 / ascension 4 cap for this rarity')
    db.execute('''UPDATE weapons SET name=?,weapon_type=?,rarity=?,ascension_family=?,
        common_drop_family=?,elite_drop_family=? WHERE id=?''',
        (fields['name'],fields['weapon_type'],rarity,fields['ascension_family'],
         fields['common_drop_family'],fields['elite_drop_family'],wid))
    missing=[]
    for role,key,previous in (('weapon_ascension','ascension_family',old[0]),
                              ('common_drop','common_drop_family',old[1]),
                              ('elite_drop','elite_drop_family',old[2])):
        issue=db.execute('''SELECT 1 FROM material_mapping_issues WHERE entity_kind='weapon'
            AND entity_id=? AND material_role=?''',(wid,role)).fetchone()
        if previous!=fields[key] or issue:
            if not relink_family(db,'weapon',wid,role,fields[key]):
                missing.append(role)
    return missing


def edit_material(db, mid, name, category):
    name=clean(name,'Material name')
    if category not in MATERIAL_CATEGORIES:
        raise ValueError('Unknown material category')
    old=db.execute('SELECT name,category FROM materials WHERE id=?',(mid,)).fetchone()
    if old is None:
        raise LookupError('Material not found')
    db.execute('''CREATE TABLE IF NOT EXISTS material_display_names (
        material_id INTEGER PRIMARY KEY REFERENCES materials(id),
        original_name TEXT NOT NULL)''')
    if old[0]!=name:
        # Keep workbook family position after a rename; IDs remain unchanged.
        db.execute('''INSERT OR IGNORE INTO material_display_names(material_id,original_name)
            VALUES (?,?)''',(mid,old[0]))
    if old[1]!=category:
        db.execute("DELETE FROM material_display_names WHERE material_id=?",(mid,))
    db.execute('UPDATE materials SET name=?,category=? WHERE id=?',(name,category,mid))
    if old[0]!=name:
        for role,column in (('boss_drop','boss_material'),
                            ('local_specialty','local_specialty')):
            db.execute(f'''UPDATE characters SET {column}=? WHERE id IN (
                SELECT character_id FROM character_materials
                WHERE material_role=? AND material_id=?)''',(name,role,mid))
    return name
