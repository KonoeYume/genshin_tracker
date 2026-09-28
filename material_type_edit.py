"""Grouped material editing; material IDs and inventory remain stable."""
import sqlite3

from catalog_admin import FAMILY_TIERS
from catalog_edit import MATERIAL_CATEGORIES, edit_material
from overview_order_data import MATERIAL_ORDER
from overview_data import CATEGORIES, EXP_VALUES

SOURCES = (
    ('common_drop','characters','character_materials','character_id','common_drop_family'),
    ('common_drop','weapons','weapon_materials','weapon_id','common_drop_family'),
    ('elite_drop','weapons','weapon_materials','weapon_id','elite_drop_family'),
    ('talent_book','characters','character_materials','character_id','talent_book_family'),
    ('weapon_ascension','weapons','weapon_materials','weapon_id','ascension_family'),
    ('weekly_boss_drop','characters','character_materials','character_id','weekly_boss_material'),
    ('ascension_gem','characters','character_materials','character_id','gem_family'),
)
SINGLE = ('character_boss_drop','local_specialty')


def _exists(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None


def material_types(db):
    groups={}
    def add(role,family,tier,mid):
        if not family or mid is None:
            return
        key=role+'|'+family
        group=groups.setdefault(key,{'key':key,'name':family,'category':role,'materials':{}})
        group['materials'][tier]=mid
    if _exists(db,'material_family_tiers'):
        for role,family,tier,mid in db.execute('''SELECT material_role,family,tier,material_id
            FROM material_family_tiers'''):
            add(role,family,tier,mid)
    for role,table,links,id_col,column in SOURCES:
        link_role='gem' if role=='ascension_gem' else role
        for family,tier,mid in db.execute(f'''SELECT e.{column},l.tier,l.material_id
            FROM {table} e JOIN {links} l ON l.{id_col}=e.id
            WHERE l.material_role=? ORDER BY e.id''',(link_role,)):
            add(role,family,tier,mid)
    names=dict(db.execute('SELECT id,name FROM materials'))
    result=[]
    used=set()
    for group in groups.values():
        items=[{'id':mid,'tier':tier,'name':names[mid]} for tier,mid in sorted(group['materials'].items())
               if mid in names]
        if not items:continue
        group['materials']=items
        used.update(item['id'] for item in items)
        result.append(group)
    # Traveller's Brilliant Diamond gems have no character links. Group the
    # remaining complete gem sets by their conventional tier suffixes.
    suffixes={2:' Sliver',3:' Fragment',4:' Chunk',5:' Gemstone'}
    unlinked_gems={}
    for mid,name,category in db.execute("SELECT id,name,category FROM materials WHERE category='ascension_gem'"):
        if mid in used:continue
        for tier,suffix in suffixes.items():
            if name.endswith(suffix):
                family=name[:-len(suffix)]
                unlinked_gems.setdefault(family,{})[tier]=mid
                break
    for family,tiers in unlinked_gems.items():
        if set(tiers)!=set(suffixes):continue
        result.append({'key':'ascension_gem|'+family,'name':family,'category':'ascension_gem',
                       'materials':[{'id':tiers[tier],'tier':tier,'name':names[tiers[tier]]}
                                    for tier in suffixes]})
        used.update(tiers.values())
    for mid,name,category in db.execute('SELECT id,name,category FROM materials ORDER BY id'):
        if mid in used:continue
        result.append({'key':'material|'+str(mid),'name':name,'category':category,
                       'materials':[{'id':mid,'tier':0,'name':name}]})
    try:
        display_names=dict(db.execute('SELECT material_id,original_name FROM material_display_names'))
    except sqlite3.OperationalError as error:
        if 'no such table' not in str(error):raise
        display_names={}
    category_order={category:i for i,(category,_) in enumerate(CATEGORIES)}
    priorities={category:{name:i for i,name in enumerate(MATERIAL_ORDER.get(category,()))}
                for category in MATERIAL_CATEGORIES}
    def sort_key(group):
        category=group['category']
        if category in ('character_exp','weapon_exp'):
            item=min(group['materials'],key=lambda m:(EXP_VALUES.get(m['name'],float('inf')),m['name']))
            inside=(EXP_VALUES.get(item['name'],float('inf')),item['name'].casefold())
        else:
            priority=priorities.get(category,{})
            inside=min((0,priority[display_names.get(m['id'],m['name'])],m['name'].casefold())
                       if display_names.get(m['id'],m['name']) in priority else
                       (1,0,group['name'].casefold(),m['tier'],m['name'].casefold())
                       for m in group['materials'])
        return (category_order.get(category,len(category_order)),inside,group['name'].casefold())
    return sorted(result,key=sort_key)


def update_material_type(db, key, new_name, category, items):
    old=next((group for group in material_types(db) if group['key']==key),None)
    if old is None:raise LookupError('Material type not found')
    new_name=new_name.strip()
    if not new_name:raise ValueError('Type name cannot be blank')
    if category not in MATERIAL_CATEGORIES:raise ValueError('Unknown material category')
    original=old['materials']
    names=[item['name'].strip() for item in items]
    if ([item['id'] for item in items]!=[item['id'] for item in original]
        or not all(names) or len(set(names))!=len(names)):
        raise ValueError('Enter distinct names for all existing tiers in order')
    old_role=old['category']
    family=not key.startswith('material|')
    if family and category!=old_role:
        if old_role not in FAMILY_TIERS or category not in FAMILY_TIERS or len(FAMILY_TIERS[category])!=len(original):
            raise ValueError('This type cannot move to a bucket with different tiers')
    if not family and category in FAMILY_TIERS and category!=old_role:
        raise ValueError('Create a tiered material type in Add New instead')
    if not family and len(original)!=1:raise ValueError('Invalid material type')
    if family and (category!=old_role or new_name!=old['name']):
        if any(g['category']==category and g['name']==new_name for g in material_types(db) if g['key']!=key):
            raise ValueError('A material type with this name already exists in that bucket')
    ids=[item['id'] for item in original]
    if category!=old_role:
        for table in ('character_materials','weapon_materials','traveller_level_materials','traveller_talent_costs'):
            if not _exists(db,table):continue
            marks=','.join('?' for _ in ids)
            if db.execute(f'SELECT 1 FROM {table} WHERE material_id IN ({marks}) LIMIT 1',ids).fetchone():
                raise ValueError('This type is used in material costs. Update its users before changing the category')
    if family:
        if _exists(db,'material_family_tiers'):
            db.execute('DELETE FROM material_family_tiers WHERE material_role=? AND family=?',(old_role,old['name']))
        for role,table,links,id_col,column in SOURCES:
            if role==old_role and category==old_role:
                db.execute(f'UPDATE {table} SET {column}=? WHERE {column}=?',
                           (new_name,old['name']))
        if _exists(db,'material_type_order'):
            row=db.execute('''SELECT sort_order FROM material_type_order
                WHERE material_role=? AND type_name=?''',(old_role,old['name'])).fetchone()
            db.execute('DELETE FROM material_type_order WHERE material_role=? AND type_name=?',
                       (old_role,old['name']))
            if row:
                db.execute('''INSERT INTO material_type_order(material_role,type_name,sort_order)
                    VALUES (?,?,?)''',(category,new_name,row[0]))
        if _exists(db,'material_mapping_issues'):
            db.execute('''UPDATE material_mapping_issues SET missing_family=?
                WHERE material_role=? AND missing_family=?''',(new_name,old_role,old['name']))
        if old_role=='ascension_gem' and category==old_role:
            db.execute('UPDATE element_gems SET gem_family=? WHERE gem_family=?',
                       (new_name,old['name']))
    elif new_name!=names[0]:
        raise ValueError('For a single material, the type name must match its material name')
    for item,name in zip(original,names):
        edit_material(db,item['id'],name,category)
    if family and _exists(db,'material_family_tiers'):
        tiers=FAMILY_TIERS.get(category) or (tuple(item['tier'] for item in original)
                                            if category=='ascension_gem' else None)
        if tiers is None:raise ValueError('Unsupported family category')
        db.executemany('''INSERT INTO material_family_tiers(material_role,family,tier,material_id)
            VALUES (?,?,?,?)''',[(category,new_name,tier,item['id']) for tier,item in zip(tiers,original)])
    return {'key':(category+'|'+new_name if family else key),'name':new_name,'category':category}
