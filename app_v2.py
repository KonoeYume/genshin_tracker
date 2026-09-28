"""SQLite-backed Genshin goal, inventory, and catalog web app.

Run: python -m uvicorn app_v2:app --reload
Requires shopping_list.py and its calculator modules in the same folder.
"""
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from shopping_list import build
from catalog_admin import FAMILY_TIERS, create_character, create_weapon
from overview_data import overview, progress_lists
from dashboard_pages import overview_page, progress_page
from catalog_edit import (MATERIAL_CATEGORIES, edit_character, edit_weapon,
                          edit_material, traveller_details, edit_traveller,
                          create_material_type)
from material_type_edit import material_types, update_material_type

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'
app = FastAPI(title='Genshin Tracker')


class InventoryUpdate(BaseModel):
    material_name: str
    quantity: int = Field(ge=0)


class CharacterGoalUpdate(BaseModel):
    target_level: int = Field(ge=1, le=90)
    target_ascension: int = Field(ge=0, le=6)
    talent_targets: list[int]


class CharacterProgressUpdate(BaseModel):
    current_level: int = Field(ge=1, le=90)
    current_ascension: int = Field(ge=0, le=6)
    talent_levels: list[int]


class WeaponGoalUpdate(BaseModel):
    target_level: int = Field(ge=1, le=90)
    target_ascension: int = Field(ge=0, le=6)


class WeaponProgressUpdate(BaseModel):
    current_level: int = Field(ge=1, le=90)
    current_ascension: int = Field(ge=0, le=6)


class NewWeaponCopy(BaseModel):
    weapon_id: int
    label: str | None = Field(default=None, max_length=80)


class WeaponCopyLabelUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=80)


class TravellerGoalUpdate(BaseModel):
    target_level: int = Field(ge=1, le=90)
    target_ascension: int = Field(ge=0, le=6)
    talent_targets: list[int]


class TravellerProgressUpdate(BaseModel):
    current_level: int = Field(ge=1, le=90)
    current_ascension: int = Field(ge=0, le=6)
    talent_levels: list[int]


class MaterialFamilyUpdate(BaseModel):
    material_role: str
    family: str
    material_names: list[str]


@app.post('/api/material-types', status_code=201)
def add_material_type(update: MaterialFamilyUpdate):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            return create_material_type(db,update.material_role,update.family,update.material_names)
    except (ValueError,sqlite3.IntegrityError) as error:
        raise HTTPException(status_code=422,detail=str(error)) from error


class NewCharacter(BaseModel):
    name: str
    element: str
    boss_material: str
    common_drop_family: str
    local_specialty: str
    talent_book_family: str
    weekly_boss_type: str


class NewWeapon(BaseModel):
    name: str
    weapon_type: str
    rarity: int = Field(ge=1, le=5)
    ascension_family: str
    common_drop_family: str
    elite_drop_family: str


class MaterialCatalogUpdate(BaseModel):
    name: str
    category: str


class MaterialTypeUpdate(BaseModel):
    key: str
    name: str
    category: str
    materials: list[dict]


@app.get('/api/catalog/material-types')
def catalog_material_types():
    with sqlite3.connect(DB_PATH) as db:
        return material_types(db)


@app.put('/api/catalog/material-types')
def save_catalog_material_type(update: MaterialTypeUpdate):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            return update_material_type(db,update.key,update.name,update.category,update.materials)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409,detail='Name or type already exists') from error
    except (ValueError,KeyError,TypeError) as error:
        raise HTTPException(status_code=422,detail=str(error)) from error


class TravellerCatalogUpdate(BaseModel):
    common_drop_family: str
    talent_material_type: str
    weekly_boss_type: str


@app.get('/api/catalog/traveller/{element}/{slot}')
def catalog_traveller(element: str, slot: int):
    try:
        with sqlite3.connect(DB_PATH) as db:
            return traveller_details(db,element,slot)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error


@app.put('/api/catalog/traveller/{element}/{slot}')
def update_catalog_traveller(element: str, slot: int, update: TravellerCatalogUpdate):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('BEGIN IMMEDIATE')
            return edit_traveller(db,element,slot,update.model_dump())
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error


@app.get('/api/catalog/characters/{character_id}')
def catalog_character(character_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory=sqlite3.Row
        row=db.execute('''SELECT id,name,element,gem_family,boss_material,
            common_drop_family,local_specialty,talent_book_family,
            weekly_boss_material AS weekly_boss_type FROM characters WHERE id=?''',
            (character_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Character not found')
        return dict(row)


@app.put('/api/catalog/characters/{character_id}')
def update_catalog_character(character_id: int, update: NewCharacter):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            missing=edit_character(db,character_id,update.model_dump())
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409,detail='Character name already exists') from error
    except ValueError as error:
        raise HTTPException(status_code=422,detail=str(error)) from error
    return {'id':character_id,'missing_families':missing}


@app.get('/api/catalog/weapons/{weapon_id}')
def catalog_weapon(weapon_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory=sqlite3.Row
        row=db.execute('''SELECT id,name,weapon_type,rarity,ascension_family,
            common_drop_family,elite_drop_family FROM weapons WHERE id=?''',
            (weapon_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Weapon not found')
        return dict(row)


@app.put('/api/catalog/weapons/{weapon_id}')
def update_catalog_weapon(weapon_id: int, update: NewWeapon):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            missing=edit_weapon(db,weapon_id,update.model_dump())
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409,detail='Weapon name already exists') from error
    except ValueError as error:
        raise HTTPException(status_code=422,detail=str(error)) from error
    return {'id':weapon_id,'missing_families':missing}


@app.get('/api/catalog/materials')
def catalog_materials():
    with sqlite3.connect(DB_PATH) as db:
        return {'categories':MATERIAL_CATEGORIES,
                'materials':[{'id':mid,'name':name,'category':category} for mid,name,category
                in db.execute('SELECT id,name,category FROM materials ORDER BY id')]}


@app.put('/api/catalog/materials/{material_id}')
def update_catalog_material(material_id: int, update: MaterialCatalogUpdate):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            name=edit_material(db,material_id,update.name,update.category)
    except LookupError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409,detail='Material name already exists') from error
    except ValueError as error:
        raise HTTPException(status_code=422,detail=str(error)) from error
    return {'id':material_id,'name':name,'category':update.category}


@app.get('/api/catalog/options')
def catalog_options():
    fields = {
        'common_families': ('characters','common_drop_family'),
        'talent_families': ('characters','talent_book_family'),
        'ascension_families': ('weapons','ascension_family'),
        'elite_families': ('weapons','elite_drop_family'),
    }
    with sqlite3.connect(DB_PATH) as db:
        result = {key:[r[0] for r in db.execute(
            f'SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}')]
            for key,(table,column) in fields.items()}
        result['element_gems'] = dict(db.execute(
            'SELECT element,gem_family FROM element_gems ORDER BY element'))
        result['weapon_types'] = ['Sword','Claymore','Polearm','Catalyst','Bow']
        saved={role:set() for role in FAMILY_TIERS}
        for role,family in db.execute('SELECT DISTINCT material_role,family FROM material_family_tiers'):
            if role in saved:
                saved[role].add(family)
        common = (set(result['common_families']) |
            {r[0] for r in db.execute('''SELECT DISTINCT common_drop_family FROM weapons
                WHERE common_drop_family IS NOT NULL''')} | saved['common_drop'])
        weekly = {r[0] for r in db.execute('''SELECT DISTINCT weekly_boss_material
            FROM characters WHERE weekly_boss_material IS NOT NULL''')}
        weekly.update(saved['weekly_boss_drop'])
        order = {(role,name):position for role,name,position in db.execute(
            'SELECT material_role,type_name,sort_order FROM material_type_order')}
        def workbook_order(role, values):
            return sorted(values,key=lambda name:(order.get((role,name),100000),name))
        result['common_families'] = workbook_order('common_drop', common)
        result['elite_families'] = workbook_order('elite_drop', set(result['elite_families'])|saved['elite_drop'])
        result['talent_families'] = workbook_order('talent_book', set(result['talent_families'])|saved['talent_book'])
        result['ascension_families'] = workbook_order('weapon_ascension', set(result['ascension_families'])|saved['weapon_ascension'])
        result['weekly_boss_types'] = workbook_order('weekly_boss_drop', weekly)
        return result


@app.post('/api/catalog/characters', status_code=201)
def add_character(new: NewCharacter):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            cid, missing = create_character(db, new.model_dump())
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail='Character name already exists') from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {'id':cid,'name':new.name.strip(),'missing_families':missing}


@app.post('/api/catalog/weapons', status_code=201)
def add_weapon(new: NewWeapon):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            wid, copy_id, missing = create_weapon(db, new.model_dump())
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail='Weapon name already exists') from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {'id':wid,'copy_id':copy_id,'name':new.name.strip(),
            'missing_families':missing}


def shopping_data(db_path=DB_PATH):
    if not db_path.is_file():
        raise FileNotFoundError(f'{db_path.name} was not found beside app_v2.py')
    with sqlite3.connect(db_path) as db:
        totals, owned, included, excluded, character_exp, weapon_exp = build(db)
    items = [dict(material=name, required=totals[name], owned=owned[name],
                  still_needed=max(0, totals[name]-owned[name]))
             for name in sorted(totals, key=str.casefold)]
    return dict(included=dict(included), excluded=excluded,
                character_exp=character_exp, weapon_exp=weapon_exp, materials=items)


@app.get('/api/shopping-list')
def shopping_list_api():
    try:
        return shopping_data()
    except (sqlite3.Error, FileNotFoundError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get('/api/overview')
def overview_api():
    try:
        with sqlite3.connect(DB_PATH) as db:
            return overview(db)
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get('/api/progress')
def progress_api():
    try:
        with sqlite3.connect(DB_PATH) as db:
            return progress_lists(db)
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get('/overview', response_class=HTMLResponse)
def overview_screen():
    return overview_page()


@app.get('/', response_class=HTMLResponse)
def home():
    return overview_page()


@app.get('/progress', response_class=HTMLResponse)
def progress_screen():
    return progress_page('characters')


@app.get('/characters', response_class=HTMLResponse)
def character_progress_screen():
    return progress_page('characters')


@app.get('/weapons', response_class=HTMLResponse)
def weapon_progress_screen():
    return progress_page('weapons')


@app.get('/traveller', response_class=HTMLResponse)
def traveller_progress_screen():
    return progress_page('traveller')


@app.put('/api/inventory')
def update_inventory(update: InventoryUpdate):
    try:
        with sqlite3.connect(DB_PATH) as db:
            row = db.execute('SELECT id FROM materials WHERE name=?',
                             (update.material_name,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail='Material not found')
            db.execute('''INSERT INTO inventory(material_id,quantity) VALUES (?,?)
                ON CONFLICT(material_id) DO UPDATE SET quantity=excluded.quantity''',
                (row[0],update.quantity))
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {'material_name':update.material_name,'quantity':update.quantity}


@app.get('/api/characters')
def list_characters():
    with sqlite3.connect(DB_PATH) as db:
        return [{'id': cid, 'name': name} for cid, name in
                db.execute('SELECT id,name FROM characters ORDER BY id')]


@app.get('/api/characters/{character_id}')
def character_goal(character_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute('''SELECT c.id,c.name,p.current_level,p.target_level,
            p.current_ascension,p.target_ascension FROM characters c
            JOIN character_progress p ON p.character_id=c.id WHERE c.id=?''',
            (character_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='Character not found')
        result = dict(row)
        result['talents'] = [dict(t) for t in db.execute('''SELECT talent_slot,current_level,target_level
            FROM talent_progress WHERE character_id=? ORDER BY talent_slot''',(character_id,))]
        return result


@app.put('/api/characters/{character_id}/goal')
def save_character_goal(character_id: int, update: CharacterGoalUpdate):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute('''SELECT current_level,current_ascension FROM character_progress
            WHERE character_id=?''',(character_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Character not found')
        current_level,current_ascension=row
        max_level=(20,40,50,60,70,80,90)[update.target_ascension]
        if (update.target_level < current_level or
            update.target_ascension < current_ascension or
            update.target_level > max_level):
            raise HTTPException(status_code=422,detail='Target level or ascension is outside the valid range')
        talents=db.execute('''SELECT talent_slot,current_level FROM talent_progress
            WHERE character_id=? ORDER BY talent_slot''',(character_id,)).fetchall()
        if len(talents)!=3 or [r[0] for r in talents]!=[1,2,3] or len(update.talent_targets)!=3:
            raise HTTPException(status_code=422,detail='Three talent targets are required')
        if any(not isinstance(target,int) or isinstance(target,bool) or
               target < current or target>10 for (_,current),target in zip(talents,update.talent_targets)):
            raise HTTPException(status_code=422,detail='Talent targets must be whole numbers from current level to 10')
        db.execute('''UPDATE character_progress SET target_level=?,target_ascension=?
            WHERE character_id=?''',(update.target_level,update.target_ascension,character_id))
        db.executemany('''UPDATE talent_progress SET target_level=?
            WHERE character_id=? AND talent_slot=?''',
            [(target,character_id,slot) for (slot,_),target in zip(talents,update.talent_targets)])
    return character_goal(character_id)


@app.put('/api/characters/{character_id}/progress')
def save_character_progress(character_id: int, update: CharacterProgressUpdate):
    with sqlite3.connect(DB_PATH) as db:
        row=db.execute('''SELECT current_level,current_ascension,target_level,target_ascension
            FROM character_progress WHERE character_id=?''',(character_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Character not found')
        old_level,old_asc,target_level,target_asc=row
        if (update.current_level<old_level or update.current_ascension<old_asc or
            update.current_level>(20,40,50,60,70,80,90)[update.current_ascension]):
            raise HTTPException(status_code=422,detail='Current level or ascension is outside the valid range')
        talents=db.execute('''SELECT talent_slot,current_level,target_level FROM talent_progress
            WHERE character_id=? ORDER BY talent_slot''',(character_id,)).fetchall()
        if (len(talents)!=3 or [t[0] for t in talents]!=[1,2,3] or
            len(update.talent_levels)!=3 or
            any(type(level) is not int or level<old or level>10
                for (_,old,_),level in zip(talents,update.talent_levels))):
            raise HTTPException(status_code=422,detail='Enter three valid current talent levels')
        db.execute('''UPDATE character_progress SET current_level=?,current_ascension=?,
            target_level=?,target_ascension=? WHERE character_id=?''',
            (update.current_level,update.current_ascension,max(target_level,update.current_level),
             max(target_asc,update.current_ascension),character_id))
        db.executemany('''UPDATE talent_progress SET current_level=?,target_level=?
            WHERE character_id=? AND talent_slot=?''',
            [(level,max(level,target),character_id,slot)
             for (slot,_,target),level in zip(talents,update.talent_levels)])
    return character_goal(character_id)


@app.get('/api/weapons')
def list_weapon_catalog():
    with sqlite3.connect(DB_PATH) as db:
        return [{'id': wid, 'name': name, 'rarity': rarity} for wid, name, rarity in
                db.execute('SELECT id,name,rarity FROM weapons ORDER BY id')]


@app.get('/api/weapon-copies')
def list_weapon_copies():
    with sqlite3.connect(DB_PATH) as db:
        return [{'id': cid, 'weapon_id': wid, 'copy_number': number,
                 'name': name, 'label': label} for cid,wid,number,name,label in
                db.execute('''SELECT wc.id,wc.weapon_id,wc.copy_number,w.name,wc.label
                    FROM weapon_copies wc JOIN weapons w ON w.id=wc.weapon_id
                    ORDER BY w.id,wc.copy_number''')]


@app.get('/api/weapon-copies/{copy_id}')
def weapon_copy_goal(copy_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory=sqlite3.Row
        row=db.execute('''SELECT wc.id,wc.weapon_id,wc.copy_number,wc.label,w.name,w.rarity,
            wc.current_level,wc.target_level,wc.current_ascension,wc.target_ascension
            FROM weapon_copies wc JOIN weapons w ON w.id=wc.weapon_id WHERE wc.id=?''',
            (copy_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Weapon copy not found')
        return dict(row)


@app.post('/api/weapon-copies',status_code=201)
def add_weapon_copy(new: NewWeaponCopy):
    label=new.label.strip() if new.label else None
    with sqlite3.connect(DB_PATH) as db:
        db.execute('BEGIN IMMEDIATE')
        exists=db.execute('SELECT id FROM weapons WHERE id=?',(new.weapon_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404,detail='Weapon not found')
        copy_number=db.execute('''SELECT COALESCE(MAX(copy_number),0)+1
            FROM weapon_copies WHERE weapon_id=?''',(new.weapon_id,)).fetchone()[0]
        cursor=db.execute('''INSERT INTO weapon_copies
            (weapon_id,copy_number,source_sheet,label,current_level,target_level,current_ascension,target_ascension)
            VALUES (?,?,NULL,?,1,1,0,0)''',(new.weapon_id,copy_number,label or None))
        copy_id=cursor.lastrowid
    return weapon_copy_goal(copy_id)


@app.put('/api/weapon-copies/{copy_id}/label')
def update_weapon_copy_label(copy_id: int, update: WeaponCopyLabelUpdate):
    label=update.label.strip() if update.label else None
    with sqlite3.connect(DB_PATH) as db:
        result=db.execute('UPDATE weapon_copies SET label=? WHERE id=?',(label or None,copy_id))
        if result.rowcount==0:
            raise HTTPException(status_code=404,detail='Weapon copy not found')
    return weapon_copy_goal(copy_id)


@app.put('/api/weapon-copies/{copy_id}/goal')
def save_weapon_goal(copy_id: int, update: WeaponGoalUpdate):
    with sqlite3.connect(DB_PATH) as db:
        row=db.execute('''SELECT wc.current_level,wc.current_ascension,w.rarity
            FROM weapon_copies wc JOIN weapons w ON w.id=wc.weapon_id WHERE wc.id=?''',
            (copy_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Weapon copy not found')
        current_level,current_ascension,rarity=row
        maximum_ascension=4 if rarity in (1,2) else 6
        level_caps=(20,40,50,60,70,80,90)
        if (update.target_level<current_level or update.target_ascension<current_ascension or
            update.target_ascension>maximum_ascension or
            update.target_level>level_caps[update.target_ascension]):
            raise HTTPException(status_code=422,detail='Target level or ascension is outside the valid range')
        db.execute('''UPDATE weapon_copies SET target_level=?,target_ascension=? WHERE id=?''',
                   (update.target_level,update.target_ascension,copy_id))
    return weapon_copy_goal(copy_id)


@app.put('/api/weapon-copies/{copy_id}/progress')
def save_weapon_progress(copy_id: int, update: WeaponProgressUpdate):
    with sqlite3.connect(DB_PATH) as db:
        row=db.execute('''SELECT wc.current_level,wc.current_ascension,wc.target_level,
            wc.target_ascension,w.rarity FROM weapon_copies wc
            JOIN weapons w ON w.id=wc.weapon_id WHERE wc.id=?''',(copy_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,detail='Weapon copy not found')
        old_level,old_asc,target_level,target_asc,rarity=row
        max_asc=4 if rarity<=2 else 6
        if (update.current_level<old_level or update.current_ascension<old_asc or
            update.current_ascension>max_asc or
            update.current_level>(20,40,50,60,70,80,90)[update.current_ascension]):
            raise HTTPException(status_code=422,detail='Current weapon level or ascension is outside the valid range')
        db.execute('''UPDATE weapon_copies SET current_level=?,current_ascension=?,
            target_level=?,target_ascension=? WHERE id=?''',
            (update.current_level,update.current_ascension,max(target_level,update.current_level),
             max(target_asc,update.current_ascension),copy_id))
    return weapon_copy_goal(copy_id)


@app.get('/api/traveller/elements')
def traveller_elements():
    with sqlite3.connect(DB_PATH) as db:
        return [r[0] for r in db.execute('''SELECT element FROM traveller_talent_progress
            GROUP BY element ORDER BY MIN(id)''')]


@app.get('/api/traveller/{element}')
def traveller_goal(element: str):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory=sqlite3.Row
        row=db.execute('SELECT * FROM traveller_progress WHERE id=1').fetchone()
        talents=[dict(t) for t in db.execute('''SELECT talent_slot,current_level,target_level
            FROM traveller_talent_progress WHERE element=? ORDER BY talent_slot''',(element,))]
        if row is None or len(talents)!=3:
            raise HTTPException(status_code=404,detail='Traveller element not found')
        return dict(row) | {'element':element,'talents':talents}


@app.put('/api/traveller/{element}/goal')
def save_traveller_goal(element: str, update: TravellerGoalUpdate):
    with sqlite3.connect(DB_PATH) as db:
        row=db.execute('''SELECT current_level,current_ascension FROM traveller_progress
            WHERE id=1''').fetchone()
        talents=db.execute('''SELECT talent_slot,current_level FROM traveller_talent_progress
            WHERE element=? ORDER BY talent_slot''',(element,)).fetchall()
        if row is None or len(talents)!=3 or [r[0] for r in talents]!=[1,2,3]:
            raise HTTPException(status_code=404,detail='Traveller element not found')
        current_level,current_ascension=row
        if (update.target_level<current_level or update.target_ascension<current_ascension or
            update.target_level>(20,40,50,60,70,80,90)[update.target_ascension]):
            raise HTTPException(status_code=422,detail='Target level or ascension is outside the valid range')
        if len(update.talent_targets)!=3 or any(
            not isinstance(target,int) or isinstance(target,bool) or
            target<current or target>10
            for (_,current),target in zip(talents,update.talent_targets)):
            raise HTTPException(status_code=422,detail='Three valid talent targets are required')
        if element=='Cryo' and any(target>current for (_,current),target in zip(talents,update.talent_targets)):
            raise HTTPException(status_code=422,detail='Cryo material costs are not available yet')
        db.execute('UPDATE traveller_progress SET target_level=?,target_ascension=? WHERE id=1',
                   (update.target_level,update.target_ascension))
        db.executemany('''UPDATE traveller_talent_progress SET target_level=?
            WHERE element=? AND talent_slot=?''',
            [(target,element,slot) for (slot,_),target in zip(talents,update.talent_targets)])
    return traveller_goal(element)


@app.put('/api/traveller/{element}/progress')
def save_traveller_progress(element: str, update: TravellerProgressUpdate):
    with sqlite3.connect(DB_PATH) as db:
        row=db.execute('''SELECT current_level,current_ascension,target_level,target_ascension
            FROM traveller_progress WHERE id=1''').fetchone()
        talents=db.execute('''SELECT talent_slot,current_level,target_level
            FROM traveller_talent_progress WHERE element=? ORDER BY talent_slot''',(element,)).fetchall()
        if row is None or len(talents)!=3 or [t[0] for t in talents]!=[1,2,3]:
            raise HTTPException(status_code=404,detail='Traveller element not found')
        old_level,old_asc,target_level,target_asc=row
        if (update.current_level<old_level or update.current_ascension<old_asc or
            update.current_level>(20,40,50,60,70,80,90)[update.current_ascension]):
            raise HTTPException(status_code=422,detail='Current Traveller level or ascension is outside the valid range')
        if (len(update.talent_levels)!=3 or
            any(type(level) is not int or level<old or level>10
                for (_,old,_),level in zip(talents,update.talent_levels))):
            raise HTTPException(status_code=422,detail='Enter three valid current talent levels')
        if element=='Cryo' and any(level>old for (_,old,_),level in zip(talents,update.talent_levels)):
            raise HTTPException(status_code=422,detail='Cryo material costs are not available yet')
        db.execute('''UPDATE traveller_progress SET current_level=?,current_ascension=?,
            target_level=?,target_ascension=? WHERE id=1''',
            (update.current_level,update.current_ascension,max(target_level,update.current_level),
             max(target_asc,update.current_ascension)))
        db.executemany('''UPDATE traveller_talent_progress SET current_level=?,target_level=?
            WHERE element=? AND talent_slot=?''',
            [(level,max(level,target),element,slot)
             for (slot,_,target),level in zip(talents,update.talent_levels)])
    return traveller_goal(element)


@app.get('/api/missing-families')
def missing_families():
    with sqlite3.connect(DB_PATH) as db:
        rows=db.execute('''SELECT i.material_role,i.missing_family,i.entity_kind,i.entity_id,
            CASE WHEN i.entity_kind='character' THEN c.name ELSE w.name END
            FROM material_mapping_issues i
            LEFT JOIN characters c ON i.entity_kind='character' AND c.id=i.entity_id
            LEFT JOIN weapons w ON i.entity_kind='weapon' AND w.id=i.entity_id
            ORDER BY i.material_role,i.missing_family,i.entity_kind,i.entity_id''').fetchall()
    groups={}
    for role,family,kind,entity_id,name in rows:
        key=(role,family)
        if key not in groups:
            groups[key]={'material_role':role,'family':family,
                         'tiers':list(FAMILY_TIERS.get(role,())), 'affected':[]}
        groups[key]['affected'].append(f'{kind}: {name or entity_id}')
    return list(groups.values())


@app.put('/api/material-family')
def save_material_family(update: MaterialFamilyUpdate):
    tiers=FAMILY_TIERS.get(update.material_role)
    if tiers is None:
        raise HTTPException(status_code=422,detail='Unsupported material type')
    names=[name.strip() for name in update.material_names]
    if (not update.family.strip() or len(names)!=len(tiers) or
        any(not name for name in names) or len(set(names))!=len(names)):
        raise HTTPException(status_code=422,detail='Enter one distinct material name for each tier')
    with sqlite3.connect(DB_PATH) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        issues=db.execute('''SELECT entity_kind,entity_id FROM material_mapping_issues
            WHERE material_role=? AND missing_family=?''',
            (update.material_role,update.family)).fetchall()
        if not issues:
            raise HTTPException(status_code=404,detail='Missing material type not found')
        db.execute('''CREATE TABLE IF NOT EXISTS material_family_tiers (
            material_role TEXT NOT NULL, family TEXT NOT NULL, tier INTEGER NOT NULL,
            material_id INTEGER NOT NULL REFERENCES materials(id),
            PRIMARY KEY(material_role,family,tier))''')
        for tier,name in zip(tiers,names):
            db.execute('''INSERT INTO materials(name,category) VALUES (?,?)
                ON CONFLICT(name) DO NOTHING''',(name,update.material_role))
            material_id=db.execute('SELECT id FROM materials WHERE name=?',(name,)).fetchone()[0]
            db.execute('''INSERT INTO inventory(material_id,quantity) VALUES (?,0)
                ON CONFLICT(material_id) DO NOTHING''',(material_id,))
            db.execute('''INSERT INTO material_family_tiers(material_role,family,tier,material_id)
                VALUES (?,?,?,?) ON CONFLICT(material_role,family,tier)
                DO UPDATE SET material_id=excluded.material_id''',
                (update.material_role,update.family,tier,material_id))
            for kind,entity_id in issues:
                table,id_column=(('character_materials','character_id') if kind=='character'
                                 else ('weapon_materials','weapon_id'))
                if kind not in ('character','weapon'):
                    raise HTTPException(status_code=422,detail='Unknown entity kind')
                db.execute(f'''INSERT INTO {table}({id_column},material_role,tier,material_id)
                    VALUES (?,?,?,?) ON CONFLICT({id_column},material_role,tier)
                    DO UPDATE SET material_id=excluded.material_id''',
                    (entity_id,update.material_role,tier,material_id))
        db.execute('''DELETE FROM material_mapping_issues
            WHERE material_role=? AND missing_family=?''',(update.material_role,update.family))
    return {'updated_records':len(issues),'material_role':update.material_role,
            'family':update.family,'materials':names}


@app.get('/goals', response_class=HTMLResponse)
def goals_screen():
    return main_page('goals')


@app.get('/catalog', response_class=HTMLResponse)
def catalog_screen():
    return main_page('catalog')


def main_page(view):
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Genshin Tracker</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 32px auto; padding: 0 16px;
         color: #232a36; background: #f8fafc; }
  h1 { margin-bottom: 8px; } .summary { background: white; padding: 16px; border: 1px solid #ddd;
         border-radius: 8px; margin: 16px 0; } .note { color: #526071; }
  table { width: 100%; border-collapse: collapse; background: white; }
  th, td { border-bottom: 1px solid #ddd; padding: 10px; text-align: left; }
  th:nth-child(n+2), td:nth-child(n+2) { text-align: right; }
  th { background: #e9eff5; } .missing { font-weight: 700; color: #9a3412; }
  input[type=number] { width: 85px; padding: 6px; } button { padding: 6px 10px; cursor: pointer; }
  label { display: inline-block; margin: 8px 12px 8px 0; } select { padding: 6px; }
  .goal-row { margin: 8px 0; } .goal-row label { margin: 0; }
  .goal-group { margin: 18px 0; }
  .catalog-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 4px 16px; }
  .catalog-fields label { display: block; }
  .catalog-fields input, .catalog-fields select, .catalog-fields .read-only-field {
    display: block; box-sizing: border-box; width: 100%; height: 34px;
    padding: 6px; font: 13.333px Arial, sans-serif;
  }
  .catalog-fields [hidden] { display: none; }
  .catalog-value { margin: 8px 12px 8px 0; }
  .catalog-fields .read-only-field { display: flex; align-items: center;
    border: 1px solid #ccc; border-radius: 2px; background: #f8fafc; }
  details { margin: 20px 0; } li { margin: 6px 0; overflow-wrap: anywhere; }
  body.goals-view .catalog-only, body.catalog-view .goals-only { display: none; }
  details.summary > summary { font-size: 1.35em; font-weight: bold; cursor: pointer; }
  @media (max-width: 600px) { body { margin: 12px auto; } th,td { padding: 7px 4px; font-size: 13px; } }
</style></head><body class="''' + view + '''-view">
<h1>Genshin Tracker</h1>
<nav><a href="/">Inventory Overview</a> · <a href="/goals">Goals</a> · <a href="/characters">Characters</a> · <a href="/weapons">Weapons</a> · <a href="/traveller">Traveller</a> · <a href="/catalog">Add data</a></nav>
<p class="note goals-only">Set targets and record current progress. View all materials on Inventory Overview.</p>
<details class="summary goals-only" open><summary>Character Goal</summary>
<label>Character <select id="character-select"></select></label>
<div class="goal-group">
  <p class="goal-row">Current Level: <span id="character-current-level"></span></p>
  <div class="goal-row"><label>Target Level: <input id="character-level" type="number" min="1" max="90" step="1"></label></div>
</div>
<div class="goal-group">
  <p class="goal-row">Current Ascension: <span id="character-current-ascension"></span></p>
  <div class="goal-row"><label>Target Ascension: <input id="character-ascension" type="number" min="0" max="6" step="1"></label></div>
</div>
<div id="talent-inputs"></div>
<button id="save-character">Save Character Goal</button> <span id="goal-message" role="status"></span>
<details><summary>Record Current Progress</summary>
<label>Current Level <input id="record-character-level" type="number" min="1" max="90" step="1"></label>
<label>Current Ascension <input id="record-character-ascension" type="number" min="0" max="6" step="1"></label>
<div id="record-character-talents"></div>
<button id="record-character" type="button">Save Current Progress</button>
<span id="record-character-message" role="status"></span>
</details>
</details>
<details class="summary goals-only"><summary>Weapon Goal</summary>
<label>Weapon <select id="weapon-copy-select"></select></label>
<p id="selected-weapon"></p>
<div class="goal-group">
  <p class="goal-row">Current Level: <span id="weapon-current-level"></span></p>
  <div class="goal-row"><label>Target Level: <input id="weapon-level" type="number" min="1" max="90" step="1"></label></div>
</div>
<div class="goal-group">
  <p class="goal-row">Current Ascension: <span id="weapon-current-ascension"></span></p>
  <div class="goal-row"><label>Target Ascension: <input id="weapon-ascension" type="number" min="0" max="6" step="1"></label></div>
</div>
<button id="save-weapon">Save Weapon Goal</button> <span id="weapon-message" role="status"></span>
<details><summary>Record Current Progress</summary>
<label>Current Level <input id="record-weapon-level" type="number" min="1" max="90" step="1"></label>
<label>Current Ascension <input id="record-weapon-ascension" type="number" min="0" max="6" step="1"></label>
<button id="record-weapon" type="button">Save Current Progress</button>
<span id="record-weapon-message" role="status"></span>
</details>
<h3>Add Another Copy</h3>
<label>Weapon <select id="weapon-catalog"></select></label>
<label>Label (Optional) <input id="copy-label" type="text" maxlength="80" placeholder="e.g. second copy"></label>
<button id="add-weapon-copy">Add Copy</button> <span id="add-copy-message" role="status"></span>
</details>
<details class="summary goals-only"><summary>Traveller Goal</summary>
<label>Element <select id="traveller-element"></select></label>
<div class="goal-group">
  <p class="goal-row">Current Level: <span id="traveller-current-level"></span></p>
  <div class="goal-row"><label>Target Level: <input id="traveller-level" type="number" min="1" max="90" step="1"></label></div>
</div>
<div class="goal-group">
  <p class="goal-row">Current Ascension: <span id="traveller-current-ascension"></span></p>
  <div class="goal-row"><label>Target Ascension: <input id="traveller-ascension" type="number" min="0" max="6" step="1"></label></div>
</div>
<div id="traveller-talents"></div>
<button id="save-traveller">Save Traveller Goal</button> <span id="traveller-message" role="status"></span>
<details><summary>Record Current Progress</summary>
<label>Current Level <input id="record-traveller-level" type="number" min="1" max="90" step="1"></label>
<label>Current Ascension <input id="record-traveller-ascension" type="number" min="0" max="6" step="1"></label>
<div id="record-traveller-talents"></div>
<button id="record-traveller" type="button">Save Current Progress</button>
<span id="record-traveller-message" role="status"></span>
</details>
<p class="note">Traveller level and ascension are shared across elements. Cryo talent costs are not available yet.</p>
</details>
<section class="summary catalog-only"><h2>Add New</h2>
<p class="note">New entries start at level 1, ascension 0, and talent level 1. Existing material types are reused. If a type is new, complete it in Missing Material Types after saving.</p>
<details><summary>New Character</summary>
<div class="catalog-fields">
  <label>Name <input id="new-character-name" type="text"></label>
  <label>Element <select id="new-character-element"></select></label>
  <div class="catalog-value">Gem Type <span id="new-character-gem" class="read-only-field"></span></div>
  <label>World Boss Material <input id="new-character-boss" type="text"></label>
  <label>Common Enemy Drop Type <select id="new-character-common" data-new-id="new-character-common-custom"></select>
    <input id="new-character-common-custom" type="text" placeholder="New Common Enemy Drop Type" hidden></label>
  <label>Local Speciality <input id="new-character-local" type="text"></label>
  <label>Talent Book Type <select id="new-character-talent" data-new-id="new-character-talent-custom"></select>
    <input id="new-character-talent-custom" type="text" placeholder="New Talent Book Type" hidden></label>
  <label>Weekly Boss Type <select id="new-character-weekly" data-new-id="new-character-weekly-custom"></select>
    <input id="new-character-weekly-custom" type="text" placeholder="New Weekly Boss Type" hidden></label>
</div>
<button id="create-character" type="button">Add Character</button> <span id="create-character-message" role="status"></span>
</details>
<details><summary>New Weapon</summary>
<div class="catalog-fields">
  <label>Name <input id="new-weapon-name" type="text"></label>
  <label>Weapon Type <select id="new-weapon-type"></select></label>
  <label>Rarity <input id="new-weapon-rarity" type="number" min="1" max="5" step="1"></label>
  <label>Ascension Material Type <select id="new-weapon-ascension" data-new-id="new-weapon-ascension-custom"></select>
    <input id="new-weapon-ascension-custom" type="text" placeholder="New Ascension Material Type" hidden></label>
  <label>Common Enemy Drop Type <select id="new-weapon-common" data-new-id="new-weapon-common-custom"></select>
    <input id="new-weapon-common-custom" type="text" placeholder="New Common Enemy Drop Type" hidden></label>
  <label>Elite Enemy Drop Type <select id="new-weapon-elite" data-new-id="new-weapon-elite-custom"></select>
    <input id="new-weapon-elite-custom" type="text" placeholder="New Elite Enemy Drop Type" hidden></label>
</div>
<button id="create-weapon" type="button">Add Weapon</button> <span id="create-weapon-message" role="status"></span>
</details>
<details><summary>New Material</summary>
<p class="note">Choose the bucket, enter a type name, then name each material from lowest to highest tier. The new type will be available for characters and weapons.</p>
<label>Material Type <select id="new-type-bucket">
  <option value="">Select a Type</option>
  <option value="talent_book">Talent Material</option>
  <option value="weapon_ascension">Weapon Ascension Material</option>
  <option value="common_drop">Common Enemy Drop</option>
  <option value="elite_drop">Elite Enemy Drop</option>
  <option value="weekly_boss_drop">Weekly Boss Drop</option>
  <option value="character_boss_drop">World Boss Drop</option>
  <option value="local_specialty">Local Speciality</option>
</select></label>
<label>Type Name <input id="new-type-name" type="text"></label>
<div id="new-type-tiers"></div>
<button id="create-material-type" type="button">Add Material Type</button>
<span id="new-type-message" role="status"></span>
</details>
</section>
<section class="summary catalog-only"><h2>Edit Existing Data</h2>
<p class="note">Select an entry, correct its fields, then save. Editing a material name keeps its inventory and cost links. New material types appear under Missing Material Types.</p>
<details><summary>Edit Character</summary>
<label>Character <select id="edit-character-select"></select></label>
<div class="catalog-fields">
  <label>Name <input id="edit-character-name" type="text"></label>
  <label>Element <select id="edit-character-element"></select></label>
  <div class="catalog-value">Gem Type <span id="edit-character-gem" class="read-only-field"></span></div>
  <label>World Boss Material <input id="edit-character-boss" type="text"></label>
  <label>Common Enemy Drop Type <input id="edit-character-common" type="text"></label>
  <label>Local Speciality <input id="edit-character-local" type="text"></label>
  <label>Talent Book Type <input id="edit-character-talent" type="text"></label>
  <label>Weekly Boss Type <input id="edit-character-weekly" type="text"></label>
</div>
<button id="update-character" type="button">Save Character Data</button> <span id="edit-character-message" role="status"></span>
</details>
<details><summary>Edit Weapon</summary>
<label>Weapon <select id="edit-weapon-select"></select></label>
<div class="catalog-fields">
  <label>Name <input id="edit-weapon-name" type="text"></label>
  <label>Type <select id="edit-weapon-type"></select></label>
  <label>Rarity <input id="edit-weapon-rarity" type="number" min="1" max="5" step="1"></label>
  <label>Ascension Material Type <input id="edit-weapon-ascension" type="text"></label>
  <label>Common Enemy Drop Type <input id="edit-weapon-common" type="text"></label>
  <label>Elite Enemy Drop Type <input id="edit-weapon-elite" type="text"></label>
</div>
<button id="update-weapon" type="button">Save Weapon Data</button> <span id="edit-weapon-message" role="status"></span>
</details>
<details><summary>Edit Weapon Copy Label</summary>
<label>Weapon Copy <select id="edit-copy-select"></select></label>
<label>Label (Optional) <input id="edit-copy-label" type="text" maxlength="80"></label>
<button id="update-copy" type="button">Save Copy Label</button> <span id="edit-copy-message" role="status"></span>
</details>
<details id="edit-traveller-section"><summary>Edit Traveller</summary>
<p class="note">These are progress-list labels. Talent costs are stored separately and are not changed here.</p>
<label>Element <select id="edit-traveller-element"></select></label>
<label>Talent <select id="edit-traveller-slot"><option value="1">1</option><option value="2">2</option><option value="3">3</option></select></label>
<div class="catalog-fields">
  <label>Common Enemy Drop Type <input id="edit-traveller-common" type="text"></label>
  <label>Talent Material Type <input id="edit-traveller-talent" type="text"></label>
  <label>Weekly Boss Type <input id="edit-traveller-weekly" type="text"></label>
</div>
<button id="update-traveller" type="button">Save Traveller Data</button> <span id="edit-traveller-message" role="status"></span>
</details>
<details><summary>Edit Material</summary>
<label>Find Material Type <input id="edit-material-search" type="search" placeholder="Filter by type name"></label>
<label>Material Type <select id="edit-material-select"></select></label>
<div class="catalog-fields">
  <label>Type Name <input id="edit-material-name" type="text"></label>
  <label>Category <select id="edit-material-category"></select></label>
</div>
<div id="edit-material-tiers"></div>
<button id="update-material" type="button">Save Material Data</button> <span id="edit-material-message" role="status"></span>
</details>
</section>
<section class="summary catalog-only"><h2>Missing Material Types</h2>
<p class="note">Enter exact material names from lowest to highest tier. Saving links the type to every listed character and weapon.</p>
<div id="missing-families"></div>
<p id="family-message" role="status"></p>
</section>
<section class="summary goals-only" id="summary">Loading goal summary…</section>
<p id="save-message" role="status" class="goals-only"></p>
<table class="goals-only" hidden><thead><tr><th>Material</th><th>Required</th><th>Owned</th><th>Still Needed</th><th>Update Value</th><th>Action</th></tr></thead>
<tbody id="materials"></tbody></table>
<details class="goals-only" id="excluded-section"><summary id="excluded-title">Excluded goals</summary>
<ul id="excluded"></ul></details>
<p class="note goals-only">EXP is shown as points. Using EXP items may overshoot and increase the Mora cost.</p>
<script>
  const number = new Intl.NumberFormat();
  async function loadCharacters(selectedId) {
    const response = await fetch('/api/characters');
    if (!response.ok) throw new Error('Could not load characters.');
    const characters = await response.json();
    const select = document.getElementById('character-select');
    select.replaceChildren();
    select.add(new Option('Select a character', ''));
    for (const character of characters) {
      const option = document.createElement('option');
      option.value = character.id; option.textContent = character.name;
      select.append(option);
    }
    select.value = selectedId ? String(selectedId) : '';
    select.onchange = loadCharacterGoal;
    if (select.value) await loadCharacterGoal();
  }
  function fillCurrentTalents(containerId, className, talents, cryo=false) {
    const container = document.getElementById(containerId);
    container.replaceChildren();
    for (const talent of talents) {
      const label = document.createElement('label');
      label.textContent = `Talent ${talent.talent_slot} Current Level `;
      const input = document.createElement('input');
      input.type = 'number'; input.step = '1'; input.min = talent.current_level;
      input.max = cryo ? talent.current_level : 10;
      input.value = talent.current_level; input.className = className;
      label.append(input); container.append(label);
    }
  }
  async function loadCharacterGoal() {
    const id = document.getElementById('character-select').value;
    if (!id) {
      for (const key of ['character-current-level','character-current-ascension'])
        document.getElementById(key).textContent = '';
      for (const key of ['character-level','character-ascension','record-character-level','record-character-ascension'])
        document.getElementById(key).value = '';
      for (const key of ['talent-inputs','record-character-talents'])
        document.getElementById(key).replaceChildren();
      return;
    }
    const response = await fetch('/api/characters/' + id);
    if (!response.ok) throw new Error('Could not load character goal.');
    const goal = await response.json();
    document.getElementById('character-current-level').textContent = goal.current_level;
    document.getElementById('character-current-ascension').textContent = goal.current_ascension;
    const currentLevel = document.getElementById('record-character-level');
    currentLevel.min = goal.current_level; currentLevel.value = goal.current_level;
    const currentAsc = document.getElementById('record-character-ascension');
    currentAsc.min = goal.current_ascension; currentAsc.value = goal.current_ascension;
    fillCurrentTalents('record-character-talents','record-character-talent',goal.talents);
    const level = document.getElementById('character-level');
    level.min = goal.current_level; level.value = goal.target_level;
    const asc = document.getElementById('character-ascension');
    asc.min = goal.current_ascension; asc.value = goal.target_ascension;
    const container = document.getElementById('talent-inputs');
    container.replaceChildren();
    for (const talent of goal.talents) {
      const group = document.createElement('div');
      group.className = 'goal-group';
      const current = document.createElement('p');
      current.className = 'goal-row';
      current.textContent = `Talent ${talent.talent_slot} Current Level: ${talent.current_level}`;
      group.append(current);
      const targetRow = document.createElement('div');
      targetRow.className = 'goal-row';
      const label = document.createElement('label');
      label.textContent = `Talent ${talent.talent_slot} Target Level: `;
      const input = document.createElement('input');
      input.type = 'number'; input.min = talent.current_level;
      input.max = '10'; input.step = '1'; input.value = talent.target_level;
      input.className = 'talent-target'; label.append(input);
      targetRow.append(label); group.append(targetRow); container.append(group);
    }
    document.getElementById('goal-message').textContent = '';
    document.getElementById('record-character-message').textContent = '';
  }
  async function saveCharacterGoal() {
    const message = document.getElementById('goal-message');
    const levelInput = document.getElementById('character-level');
    const ascInput = document.getElementById('character-ascension');
    const talentInputs = [...document.querySelectorAll('.talent-target')];
    const inputs = [levelInput, ascInput, ...talentInputs];
    if (inputs.length !== 5 || inputs.some(input => !input.value.trim() ||
        !Number.isSafeInteger(Number(input.value)) || Number(input.value)<Number(input.min) ||
        Number(input.value)>Number(input.max))) {
      message.textContent = 'Enter valid whole-number targets.'; return;
    }
    const target_level = Number(levelInput.value);
    const target_ascension = Number(ascInput.value);
    if (target_level > [20,40,50,60,70,80,90][target_ascension]) {
      message.textContent = 'Increase target ascension to support that level.'; return;
    }
    const id = document.getElementById('character-select').value;
    const response = await fetch('/api/characters/' + id + '/goal', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target_level,target_ascension,
        talent_targets:talentInputs.map(input=>Number(input.value))})
    });
    if (!response.ok) { message.textContent = 'Could not save goal (HTTP ' + response.status + ').'; return; }
    message.textContent = 'Goal saved.';
    await load();
  }
  document.getElementById('save-character').addEventListener('click', saveCharacterGoal);
  async function recordCharacterProgress() {
    const message = document.getElementById('record-character-message');
    const level = document.getElementById('record-character-level');
    const asc = document.getElementById('record-character-ascension');
    const talents = [...document.querySelectorAll('.record-character-talent')];
    if (!validCurrentFields([level,asc,...talents],5,message)) return;
    const response = await fetch('/api/characters/' + document.getElementById('character-select').value + '/progress', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({current_level:Number(level.value),current_ascension:Number(asc.value),
        talent_levels:talents.map(input=>Number(input.value))})
    });
    if (!response.ok) { message.textContent = 'Could not save current progress (HTTP '+response.status+').'; return; }
    await loadCharacterGoal(); await load();
    message.textContent = 'Current progress saved.';
  }
  document.getElementById('record-character').addEventListener('click', recordCharacterProgress);
  async function loadWeaponCopies(selectedId) {
    const response = await fetch('/api/weapon-copies');
    if (!response.ok) throw new Error('Could not load weapon copies.');
    const copies = await response.json();
    const select = document.getElementById('weapon-copy-select');
    select.replaceChildren();
    select.add(new Option('Select a weapon', ''));
    for (const copy of copies) {
      const option = document.createElement('option');
      option.value = copy.id;
      option.textContent = copy.copy_number === 1 ? copy.name :
        `${copy.name} — ${copy.label || 'Copy ' + copy.copy_number}`;
      select.append(option);
    }
    select.value = selectedId ? String(selectedId) : '';
    if (select.value) await loadWeaponGoal();
  }
  async function loadWeaponGoal() {
    const id = document.getElementById('weapon-copy-select').value;
    if (!id) {
      for (const key of ['selected-weapon','weapon-current-level','weapon-current-ascension'])
        document.getElementById(key).textContent = '';
      for (const key of ['weapon-level','weapon-ascension','record-weapon-level','record-weapon-ascension'])
        document.getElementById(key).value = '';
      return;
    }
    const response = await fetch('/api/weapon-copies/' + id);
    if (!response.ok) throw new Error('Could not load weapon copy.');
    const goal = await response.json();
    document.getElementById('selected-weapon').textContent = `${goal.name} (${goal.rarity}-star)`;
    document.getElementById('weapon-current-level').textContent = goal.current_level;
    document.getElementById('weapon-current-ascension').textContent = goal.current_ascension;
    const currentLevel = document.getElementById('record-weapon-level');
    currentLevel.min = goal.current_level; currentLevel.max = goal.rarity <= 2 ? 70 : 90;
    currentLevel.value = goal.current_level;
    const currentAsc = document.getElementById('record-weapon-ascension');
    currentAsc.min = goal.current_ascension; currentAsc.max = goal.rarity <= 2 ? 4 : 6;
    currentAsc.value = goal.current_ascension;
    const level = document.getElementById('weapon-level');
    level.value = goal.target_level; level.min = goal.current_level;
    level.max = goal.rarity <= 2 ? 70 : 90;
    const asc = document.getElementById('weapon-ascension');
    asc.value = goal.target_ascension; asc.min = goal.current_ascension;
    asc.max = goal.rarity <= 2 ? 4 : 6;
    document.getElementById('weapon-message').textContent = '';
    document.getElementById('record-weapon-message').textContent = '';
  }
  async function loadWeaponCatalog() {
    const response = await fetch('/api/weapons');
    if (!response.ok) throw new Error('Could not load weapon catalog.');
    const weapons = await response.json();
    const select = document.getElementById('weapon-catalog');
    select.replaceChildren();
    select.add(new Option('Select a weapon', ''));
    for (const weapon of weapons) {
      const option = document.createElement('option');
      option.value = weapon.id; option.textContent = `${weapon.name} (${weapon.rarity}-star)`;
      select.append(option);
    }
  }
  async function saveWeaponGoal() {
    const message = document.getElementById('weapon-message');
    const level = document.getElementById('weapon-level');
    const asc = document.getElementById('weapon-ascension');
    if ([level,asc].some(input => !input.value.trim() || !Number.isSafeInteger(Number(input.value)) ||
        Number(input.value)<Number(input.min) || Number(input.value)>Number(input.max))) {
      message.textContent = 'Enter valid whole-number targets.'; return;
    }
    if (Number(level.value)>[20,40,50,60,70,80,90][Number(asc.value)]) {
      message.textContent = 'Increase target ascension to support that level.'; return;
    }
    const id = document.getElementById('weapon-copy-select').value;
    const response = await fetch('/api/weapon-copies/' + id + '/goal', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target_level:Number(level.value),target_ascension:Number(asc.value)})
    });
    if (!response.ok) { message.textContent = 'Could not save weapon goal (HTTP '+response.status+').'; return; }
    message.textContent = 'Weapon goal saved.';
    await load();
  }
  async function addWeaponCopy() {
    const message = document.getElementById('add-copy-message');
    const chosen = document.getElementById('weapon-catalog').value;
    if (!chosen) { message.textContent = 'Select a weapon first.'; return; }
    const weapon_id = Number(chosen);
    const label = document.getElementById('copy-label').value.trim();
    const response = await fetch('/api/weapon-copies', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({weapon_id,label:label || null})
    });
    if (!response.ok) { message.textContent = 'Could not add copy (HTTP '+response.status+').'; return; }
    const copy = await response.json();
    await loadWeaponCopies(copy.id);
    document.getElementById('copy-label').value = '';
    message.textContent = 'Weapon added. Set its goals above.';
    await load();
  }
  document.getElementById('weapon-copy-select').addEventListener('change', loadWeaponGoal);
  document.getElementById('save-weapon').addEventListener('click', saveWeaponGoal);
  async function recordWeaponProgress() {
    const message = document.getElementById('record-weapon-message');
    const level = document.getElementById('record-weapon-level');
    const asc = document.getElementById('record-weapon-ascension');
    if (!validCurrentFields([level,asc],2,message)) return;
    const response = await fetch('/api/weapon-copies/' + document.getElementById('weapon-copy-select').value + '/progress', {
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({current_level:Number(level.value),current_ascension:Number(asc.value)})
    });
    if (!response.ok) { message.textContent = 'Could not save current progress (HTTP '+response.status+').'; return; }
    await loadWeaponGoal(); await load();
    message.textContent = 'Current progress saved.';
  }
  document.getElementById('record-weapon').addEventListener('click', recordWeaponProgress);
  document.getElementById('add-weapon-copy').addEventListener('click', addWeaponCopy);
  async function loadTravellerElements() {
    const response = await fetch('/api/traveller/elements');
    if (!response.ok) throw new Error('Could not load Traveller elements.');
    const elements = await response.json();
    const select = document.getElementById('traveller-element');
    select.replaceChildren();
    select.add(new Option('Select an element', ''));
    for (const element of elements) {
      const option = document.createElement('option');
      option.value = element; option.textContent = element; select.append(option);
    }
    select.value = '';
  }
  async function loadTravellerGoal() {
    const element = document.getElementById('traveller-element').value;
    if (!element) {
      for (const key of ['traveller-current-level','traveller-current-ascension'])
        document.getElementById(key).textContent = '';
      for (const key of ['traveller-level','traveller-ascension','record-traveller-level','record-traveller-ascension'])
        document.getElementById(key).value = '';
      for (const key of ['traveller-talents','record-traveller-talents'])
        document.getElementById(key).replaceChildren();
      return;
    }
    const response = await fetch('/api/traveller/' + encodeURIComponent(element));
    if (!response.ok) throw new Error('Could not load Traveller goal.');
    const goal = await response.json();
    document.getElementById('traveller-current-level').textContent = goal.current_level;
    document.getElementById('traveller-current-ascension').textContent = goal.current_ascension;
    const currentLevel = document.getElementById('record-traveller-level');
    currentLevel.min = goal.current_level; currentLevel.value = goal.current_level;
    const currentAsc = document.getElementById('record-traveller-ascension');
    currentAsc.min = goal.current_ascension; currentAsc.value = goal.current_ascension;
    fillCurrentTalents('record-traveller-talents','record-traveller-talent',goal.talents,
      element === 'Cryo');
    const level = document.getElementById('traveller-level');
    level.min = goal.current_level; level.value = goal.target_level;
    const asc = document.getElementById('traveller-ascension');
    asc.min = goal.current_ascension; asc.value = goal.target_ascension;
    const container = document.getElementById('traveller-talents');
    container.replaceChildren();
    for (const talent of goal.talents) {
      const group = document.createElement('div'); group.className = 'goal-group';
      const current = document.createElement('p'); current.className = 'goal-row';
      current.textContent = `Talent ${talent.talent_slot} Current Level: ${talent.current_level}`;
      const targetRow = document.createElement('div'); targetRow.className = 'goal-row';
      const label = document.createElement('label');
      label.textContent = `Talent ${talent.talent_slot} Target Level: `;
      const input = document.createElement('input');
      input.type = 'number'; input.min = talent.current_level;
      input.max = element === 'Cryo' ? talent.current_level : 10;
      input.step = '1'; input.value = talent.target_level;
      input.className = 'traveller-talent-target'; label.append(input);
      targetRow.append(label); group.append(current, targetRow); container.append(group);
    }
    document.getElementById('traveller-message').textContent = '';
    document.getElementById('record-traveller-message').textContent = '';
  }
  async function saveTravellerGoal() {
    const message = document.getElementById('traveller-message');
    const level = document.getElementById('traveller-level');
    const asc = document.getElementById('traveller-ascension');
    const talents = [...document.querySelectorAll('.traveller-talent-target')];
    const inputs = [level,asc,...talents];
    if (inputs.length!==5 || inputs.some(input => !input.value.trim() ||
        !Number.isSafeInteger(Number(input.value)) || Number(input.value)<Number(input.min) ||
        Number(input.value)>Number(input.max))) {
      message.textContent = 'Enter valid whole-number targets.'; return;
    }
    if (Number(level.value)>[20,40,50,60,70,80,90][Number(asc.value)]) {
      message.textContent = 'Increase target ascension to support that level.'; return;
    }
    const element = document.getElementById('traveller-element').value;
    const response = await fetch('/api/traveller/' + encodeURIComponent(element) + '/goal', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target_level:Number(level.value),target_ascension:Number(asc.value),
        talent_targets:talents.map(input=>Number(input.value))})
    });
    if (!response.ok) { message.textContent = 'Could not save Traveller goal (HTTP '+response.status+').'; return; }
    message.textContent = 'Traveller goal saved.';
    await load();
  }
  document.getElementById('traveller-element').addEventListener('change', loadTravellerGoal);
  document.getElementById('save-traveller').addEventListener('click', saveTravellerGoal);
  async function recordTravellerProgress() {
    const message = document.getElementById('record-traveller-message');
    const level = document.getElementById('record-traveller-level');
    const asc = document.getElementById('record-traveller-ascension');
    const talents = [...document.querySelectorAll('.record-traveller-talent')];
    if (!validCurrentFields([level,asc,...talents],5,message)) return;
    const element = document.getElementById('traveller-element').value;
    const response = await fetch('/api/traveller/' + encodeURIComponent(element) + '/progress', {
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({current_level:Number(level.value),current_ascension:Number(asc.value),
        talent_levels:talents.map(input=>Number(input.value))})
    });
    if (!response.ok) { message.textContent = 'Could not save current progress (HTTP '+response.status+').'; return; }
    await loadTravellerGoal(); await load();
    message.textContent = 'Current progress saved.';
  }
  document.getElementById('record-traveller').addEventListener('click', recordTravellerProgress);
  function validCurrentFields(inputs, expected, message) {
    if (inputs.length!==expected || inputs.some(input => !input.value.trim() ||
        !Number.isSafeInteger(Number(input.value)) || Number(input.value)<Number(input.min) ||
        Number(input.value)>Number(input.max))) {
      message.textContent = 'Enter valid current levels and ascension.'; return false;
    }
    const level = Number(inputs[0].value), asc = Number(inputs[1].value);
    if (level>[20,40,50,60,70,80,90][asc]) {
      message.textContent = 'Increase current ascension to support that level.'; return false;
    }
    return true;
  }
  async function loadMissingFamilies() {
    const response = await fetch('/api/missing-families');
    if (!response.ok) throw new Error('Could not load missing material types.');
    const groups = await response.json();
    const container = document.getElementById('missing-families');
    container.replaceChildren();
    if (!groups.length) { container.textContent = 'All material types are linked.'; return; }
    for (const group of groups) {
      const panel = document.createElement('div'); panel.className = 'goal-group';
      const title = document.createElement('h3');
      const roleName = group.material_role.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
      title.textContent = `${group.family} (${roleName})`;
      panel.append(title);
      const affected = document.createElement('p');
      affected.className = 'note'; affected.textContent = 'Affects: ' + group.affected.join(', ');
      panel.append(affected);
      const inputs = [];
      for (const tier of group.tiers) {
        const label = document.createElement('label');
        label.textContent = `Tier ${tier} Material: `;
        const input = document.createElement('input');
        input.type = 'text'; input.placeholder = 'Exact material name';
        input.setAttribute('aria-label', `${group.family} tier ${tier} material`);
        label.append(input); panel.append(label); inputs.push(input);
      }
      const button = document.createElement('button');
      button.textContent = 'Save Type';
      button.addEventListener('click', async () => {
        const message = document.getElementById('family-message');
        const material_names = inputs.map(input => input.value.trim());
        if (material_names.some(name => !name) || new Set(material_names).size !== material_names.length) {
          message.textContent = `Enter ${group.tiers.length} distinct material names for ${group.family}.`; return;
        }
        button.disabled = true;
        try {
          const response = await fetch('/api/material-family', {
            method:'PUT', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({material_role:group.material_role,family:group.family,material_names})
          });
          if (!response.ok) throw new Error('Could not save type (HTTP '+response.status+').');
          message.textContent = group.family + ' saved.';
          await loadMissingFamilies(); await load();
        } catch (error) { message.textContent = error.message; button.disabled = false; }
      });
      panel.append(button); container.append(panel);
    }
  }
  const newTypeTiers={talent_book:[2,3,4],weapon_ascension:[2,3,4,5],
    common_drop:[1,2,3],elite_drop:[2,3,4],weekly_boss_drop:[0],
    character_boss_drop:[0],local_specialty:[0]};
  function showNewTypeTiers(){
    const bucket=document.getElementById('new-type-bucket').value;
    const container=document.getElementById('new-type-tiers');container.replaceChildren();
    for(const tier of newTypeTiers[bucket]||[]){
      if(bucket==='character_boss_drop'||bucket==='local_specialty')continue;
      const label=document.createElement('label');
      label.textContent=bucket==='weekly_boss_drop'?'Material Name: ':'Tier '+tier+' Material: ';
      const input=document.createElement('input');input.type='text';input.className='new-type-material';
      label.append(input);container.append(label);
    }
  }
  document.getElementById('new-type-bucket').addEventListener('change',showNewTypeTiers);
  document.getElementById('create-material-type').addEventListener('click',async()=>{
    const material_role=document.getElementById('new-type-bucket').value;
    const family=document.getElementById('new-type-name').value.trim();
    const material_names=['character_boss_drop','local_specialty'].includes(material_role)?
      [family]:[...document.querySelectorAll('.new-type-material')].map(input=>input.value.trim());
    const message=document.getElementById('new-type-message');
    if(!material_role||!family||material_names.length!==newTypeTiers[material_role]?.length||
       material_names.some(name=>!name)||new Set(material_names).size!==material_names.length){
      message.textContent='Select a bucket and enter a type and distinct material names.';return;
    }
    const button=document.getElementById('create-material-type');button.disabled=true;
    try{
      const response=await fetch('/api/material-types',{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({material_role,family,material_names})});
      if(!response.ok){const error=await response.json();throw new Error(
        typeof error.detail==='string'?error.detail:'Could not add material type.');}
      const saved=await response.json();
      message.textContent=family+' added.'+(saved.updated_records?
        ' Linked '+saved.updated_records+' existing entries.':'');
      document.getElementById('new-type-name').value='';showNewTypeTiers();
      await loadCatalogOptions();await loadMissingFamilies();await load();
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
  });
  async function loadCatalogOptions() {
    const response = await fetch('/api/catalog/options');
    if (!response.ok) throw new Error('Could not load catalog suggestions.');
    const options = await response.json();
    const elementSelect = document.getElementById('new-character-element');
    const previousElement = elementSelect.value;
    elementSelect.replaceChildren();
    const emptyElement = document.createElement('option');
    emptyElement.value = ''; emptyElement.textContent = '';
    elementSelect.append(emptyElement);
    for (const element of Object.keys(options.element_gems)) {
      const option = document.createElement('option');
      option.value = element; option.textContent = element; elementSelect.append(option);
    }
    if (previousElement && options.element_gems[previousElement]) elementSelect.value = previousElement;
    const showGem = () => {
      document.getElementById('new-character-gem').textContent =
        options.element_gems[elementSelect.value] || '';
    };
    elementSelect.onchange = showGem;
    showGem();
    const weaponTypeSelect = document.getElementById('new-weapon-type');
    const previousType = weaponTypeSelect.value;
    weaponTypeSelect.replaceChildren();
    const emptyWeaponType = document.createElement('option');
    emptyWeaponType.value = ''; emptyWeaponType.textContent = '';
    weaponTypeSelect.append(emptyWeaponType);
    for (const type of options.weapon_types) {
      const option = document.createElement('option');
      option.value = type; option.textContent = type; weaponTypeSelect.append(option);
    }
    if (options.weapon_types.includes(previousType)) weaponTypeSelect.value = previousType;
    function fillTypeSelect(id, values) {
      const select = document.getElementById(id);
      const previous = select.value;
      select.replaceChildren();
      const blank = document.createElement('option');
      blank.value = ''; blank.textContent = '';
      select.append(blank);
      for (const value of values) {
        const option = document.createElement('option');
        option.value = value; option.textContent = value; select.append(option);
      }
      const newOption = document.createElement('option');
      newOption.value = '__new__'; newOption.textContent = 'New Type…';
      select.append(newOption);
      if (values.includes(previous)) select.value = previous;
      const custom = document.getElementById(select.dataset.newId);
      const toggle = () => { custom.hidden = select.value !== '__new__'; };
      select.onchange = toggle; toggle();
    }
    fillTypeSelect('new-character-common', options.common_families);
    fillTypeSelect('new-weapon-common', options.common_families);
    fillTypeSelect('new-weapon-elite', options.elite_families);
    fillTypeSelect('new-character-weekly', options.weekly_boss_types);
    fillTypeSelect('new-character-talent', options.talent_families);
    fillTypeSelect('new-weapon-ascension', options.ascension_families);
  }
  async function submitCatalog(kind, fields, messageId) {
    const message = document.getElementById(messageId);
    const data = {};
    for (const [key,id] of Object.entries(fields)) {
      const control = document.getElementById(id);
      const value = (control.value === '__new__' && control.dataset.newId ?
        document.getElementById(control.dataset.newId).value : control.value).trim();
      if (!value) { message.textContent = 'Fill in every field.'; return; }
      data[key] = key === 'rarity' ? Number(value) : value;
    }
    if (kind === 'weapons' && (!Number.isInteger(data.rarity) || data.rarity<1 || data.rarity>5)) {
      message.textContent = 'Rarity must be a whole number from 1 to 5.'; return;
    }
    const button = document.getElementById(kind === 'characters' ? 'create-character' : 'create-weapon');
    button.disabled = true;
    try {
      const response = await fetch('/api/catalog/' + kind, {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(typeof error.detail === 'string' ? error.detail :
          'Could not add entry (HTTP '+response.status+').');
      }
      const result = await response.json();
      message.textContent = result.name + ' added.' + (result.missing_families.length ?
        ' Complete its entries in Missing Material Types before its costs appear.' : '');
      for (const id of Object.values(fields)) {
        const control = document.getElementById(id);
        control.value = '';
        if (control.dataset.newId) document.getElementById(control.dataset.newId).value = '';
      }
      if (kind === 'characters') await loadCharacters(result.id);
      else { await loadWeaponCatalog(); await loadWeaponCopies(result.copy_id); }
      await loadCatalogOptions(); await loadMissingFamilies(); await load();
    } catch (error) { message.textContent = error.message; }
    finally { button.disabled = false; }
  }
  document.getElementById('create-character').addEventListener('click', () =>
    submitCatalog('characters', {
      name:'new-character-name', element:'new-character-element',
      boss_material:'new-character-boss',
      common_drop_family:'new-character-common', local_specialty:'new-character-local',
      talent_book_family:'new-character-talent',weekly_boss_type:'new-character-weekly'
    }, 'create-character-message'));
  document.getElementById('create-weapon').addEventListener('click', () =>
    submitCatalog('weapons', {
      name:'new-weapon-name',weapon_type:'new-weapon-type',rarity:'new-weapon-rarity',
      ascension_family:'new-weapon-ascension',common_drop_family:'new-weapon-common',
      elite_drop_family:'new-weapon-elite'
    }, 'create-weapon-message'));
  let editMaterials=[];
  let editCopies=[];
  async function loadEditTraveller(){
    const element=document.getElementById('edit-traveller-element').value;
    const slot=document.getElementById('edit-traveller-slot').value;
    if(!element)return;
    const response=await fetch('/api/catalog/traveller/'+encodeURIComponent(element)+'/'+slot);
    if(!response.ok)throw new Error('Could not load Traveller data.');
    const data=await response.json();
    for(const [key,value] of Object.entries({common:data.common_drop_family,
      talent:data.talent_material_type,weekly:data.weekly_boss_type}))
      document.getElementById('edit-traveller-'+key).value=value||'';
  }
  async function setupEditTraveller(element,slot){
    const response=await fetch('/api/traveller/elements');
    if(!response.ok)throw new Error('Could not load Traveller elements.');
    const select=document.getElementById('edit-traveller-element');select.replaceChildren();
    for(const value of await response.json())select.add(new Option(value,value));
    if(element && [...select.options].some(option=>option.value===element))select.value=element;
    if(['1','2','3'].includes(slot))document.getElementById('edit-traveller-slot').value=slot;
    await loadEditTraveller();
    if(element)document.getElementById('edit-traveller-section').open=true;
  }
  for(const id of ['edit-traveller-element','edit-traveller-slot'])
    document.getElementById(id).addEventListener('change',()=>loadEditTraveller().catch(error=>
      document.getElementById('edit-traveller-message').textContent=error.message));
  document.getElementById('update-traveller').addEventListener('click',async()=>{
    const element=document.getElementById('edit-traveller-element').value;
    const slot=document.getElementById('edit-traveller-slot').value;
    const message=document.getElementById('edit-traveller-message');
    const data={common_drop_family:document.getElementById('edit-traveller-common').value.trim(),
      talent_material_type:document.getElementById('edit-traveller-talent').value.trim(),
      weekly_boss_type:document.getElementById('edit-traveller-weekly').value.trim()};
    if(!element){message.textContent='Select an element first.';return;}
    const button=document.getElementById('update-traveller');button.disabled=true;
    try{
      const response=await fetch('/api/catalog/traveller/'+encodeURIComponent(element)+'/'+slot,{
        method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
      if(!response.ok)throw new Error('Could not save Traveller data (HTTP '+response.status+').');
      message.textContent='Traveller data saved.';
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
  });
  function selectEntries(id, entries, chosen, label) {
    const select=document.getElementById(id);select.replaceChildren();
    select.add(new Option('Select '+label,''));
    for(const entry of entries)select.add(new Option(entry.name,entry.id));
    select.value=chosen ? String(chosen) : '';
  }
  function materialCategoryLabel(value){
    if(value==='character_boss_drop')return 'World Boss Drop';
    if(value==='talent_special')return 'Crown of Insight';
    if(value==='common_drop')return 'Common Enemy Drop';
    if(value==='elite_drop')return 'Elite Enemy Drop';
    return value.split('_').map(word=>word[0].toUpperCase()+word.slice(1)).join(' ');
  }
  async function loadEditCatalog(characterId,weaponId,materialId,copyId) {
    const [charactersResponse,weaponsResponse,materialsResponse,optionsResponse,copiesResponse,typesResponse]=await Promise.all([
      fetch('/api/characters'),fetch('/api/weapons'),fetch('/api/catalog/materials'),
      fetch('/api/catalog/options'),fetch('/api/weapon-copies'),fetch('/api/catalog/material-types')]);
    if([charactersResponse,weaponsResponse,materialsResponse,optionsResponse,copiesResponse,typesResponse].some(r=>!r.ok))
      throw new Error('Could not load catalog entries.');
    const [characters,weapons,materialData,options,copies,types]=await Promise.all([
      charactersResponse.json(),weaponsResponse.json(),materialsResponse.json(),
      optionsResponse.json(),copiesResponse.json(),typesResponse.json()]);
    selectEntries('edit-character-select',characters,characterId,'a character');
    selectEntries('edit-weapon-select',weapons,weaponId,'a weapon');
    editCopies=copies;
    selectEntries('edit-copy-select',copies.map(copy=>({id:copy.id,
      name:copy.name+' #'+copy.copy_number+(copy.label?' · '+copy.label:'')})),
      copyId,'a weapon copy');
    editMaterials=types;
    const category=document.getElementById('edit-material-category');category.replaceChildren();
    for(const value of materialData.categories){
      category.add(new Option(materialCategoryLabel(value),value));
    }
    for(const [id,values] of [['edit-character-element',Object.keys(options.element_gems)],
                                ['edit-weapon-type',options.weapon_types]]){
      const select=document.getElementById(id);select.replaceChildren();
      select.add(new Option('',''));
      for(const value of values)select.add(new Option(value,value));
    }
    document.getElementById('edit-character-element').onchange=()=>{
      const element=document.getElementById('edit-character-element').value;
      document.getElementById('edit-character-gem').textContent=options.element_gems[element]||'';
    };
    const chosenType=materialId ? types.find(type=>type.materials.some(item=>String(item.id)===String(materialId)))?.key : null;
    filterEditMaterials(chosenType);
    if(characterId)await loadEditCharacter();
    if(weaponId)await loadEditWeapon();
    if(copyId)showEditCopy();
    for(const [kind,id] of [['character',characterId],['weapon',weaponId],
                             ['material',chosenType],['copy',copyId]])
      if(id)document.getElementById('edit-'+kind+'-select').closest('details').open=true;
  }
  function showEditCopy(){
    const id=Number(document.getElementById('edit-copy-select').value);
    const copy=editCopies.find(entry=>entry.id===id);
    document.getElementById('edit-copy-label').value=copy?.label||'';
  }
  function filterEditMaterials(chosen) {
    const filter=document.getElementById('edit-material-search').value.trim().toLocaleLowerCase();
    const select=document.getElementById('edit-material-select');
    const previous=chosen||select.value;
    select.replaceChildren();select.add(new Option('Select a material type',''));
    for(const material of editMaterials.filter(m=>m.name.toLocaleLowerCase().includes(filter)))
      select.add(new Option(material.name+' ('+materialCategoryLabel(material.category)+')',material.key));
    select.value=previous ? String(previous) : '';
    showEditMaterial();
  }
  function showEditMaterial() {
    const id=document.getElementById('edit-material-select').value;
    const item=editMaterials.find(material=>material.key===id);
    document.getElementById('edit-material-name').value=item?.name||'';
    document.getElementById('edit-material-category').value=item?.category||'';
    const container=document.getElementById('edit-material-tiers');container.replaceChildren();
    for(const part of item?.materials||[]){
      const label=document.createElement('label');
      label.textContent=(item.materials.length===1?'Material':'Tier '+part.tier+' Material')+': ';
      const input=document.createElement('input');input.type='text';input.value=part.name;
      input.dataset.id=part.id;input.className='edit-material-tier';label.append(input);container.append(label);
    }
    if(item?.key.startsWith('material|')){
      const typeInput=document.getElementById('edit-material-name');
      const materialInput=container.querySelector('input');
      typeInput.oninput=()=>{materialInput.value=typeInput.value;};
      materialInput.oninput=()=>{typeInput.value=materialInput.value;};
    }else document.getElementById('edit-material-name').oninput=null;
  }
  async function loadEditCharacter() {
    const id=document.getElementById('edit-character-select').value;
    if(!id){
      for(const key of ['name','element','boss','common','local','talent','weekly'])
        document.getElementById('edit-character-'+key).value='';
      document.getElementById('edit-character-gem').textContent='';return;
    }
    const response=await fetch('/api/catalog/characters/'+id);
    if(!response.ok)throw new Error('Could not load character data.');
    const c=await response.json();
    for(const [key,value] of Object.entries({name:c.name,element:c.element,
      boss:c.boss_material,common:c.common_drop_family,local:c.local_specialty,
      talent:c.talent_book_family,weekly:c.weekly_boss_type}))
      document.getElementById('edit-character-'+key).value=value||'';
    document.getElementById('edit-character-gem').textContent=c.gem_family;
  }
  async function loadEditWeapon() {
    const id=document.getElementById('edit-weapon-select').value;
    if(!id){
      for(const key of ['name','type','rarity','ascension','common','elite'])
        document.getElementById('edit-weapon-'+key).value='';
      return;
    }
    const response=await fetch('/api/catalog/weapons/'+id);
    if(!response.ok)throw new Error('Could not load weapon data.');
    const w=await response.json();
    for(const [key,value] of Object.entries({name:w.name,type:w.weapon_type,rarity:w.rarity,
      ascension:w.ascension_family,common:w.common_drop_family,elite:w.elite_drop_family}))
      document.getElementById('edit-weapon-'+key).value=value??'';
  }
  async function saveEdit(kind) {
    const id=document.getElementById('edit-'+kind+'-select').value;
    const message=document.getElementById('edit-'+kind+'-message');
    if(!id){message.textContent='Select an entry first.';return;}
    const fields=kind==='character' ? {
      name:'name',element:'element',boss_material:'boss',common_drop_family:'common',
      local_specialty:'local',talent_book_family:'talent',weekly_boss_type:'weekly'} :
      {name:'name',weapon_type:'type',rarity:'rarity',
        ascension_family:'ascension',common_drop_family:'common',elite_drop_family:'elite'};
    const data={};
    for(const [key,suffix] of Object.entries(fields)){
      const value=document.getElementById('edit-'+kind+'-'+suffix).value.trim();
      if(!value){message.textContent='Fill in every field.';return;}
      data[key]=key==='rarity'?Number(value):value;
    }
    const button=document.getElementById('update-'+kind);button.disabled=true;
    try{
      const collection=kind==='weapon'?'weapons':'characters';
      const response=await fetch('/api/catalog/'+collection+'/'+id,{
        method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
      if(!response.ok){const error=await response.json();throw new Error(
        typeof error.detail==='string'?error.detail:'Could not save data (HTTP '+response.status+').');}
      const saved=await response.json();
      message.textContent='Saved.'+(saved.missing_families?.length?
        ' Complete missing types: '+saved.missing_families.join(', '):'');
      await loadEditCatalog(kind==='character'?id:null,kind==='weapon'?id:null);
      await loadCatalogOptions();await loadMissingFamilies();await load();
      if(kind==='character')await loadCharacters();
      if(kind==='weapon'){await loadWeaponCatalog();await loadWeaponCopies();}
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
  }
  async function saveMaterialType(){
    const key=document.getElementById('edit-material-select').value;
    const message=document.getElementById('edit-material-message');
    if(!key){message.textContent='Select a material type first.';return;}
    const name=document.getElementById('edit-material-name').value.trim();
    const category=document.getElementById('edit-material-category').value;
    const materials=[...document.querySelectorAll('.edit-material-tier')].map(input=>({
      id:Number(input.dataset.id),name:input.value.trim()}));
    if(!name||materials.some(item=>!item.name)){message.textContent='Fill in the type and material names.';return;}
    const button=document.getElementById('update-material');button.disabled=true;
    try{
      const response=await fetch('/api/catalog/material-types',{method:'PUT',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({key,name,category,materials})});
      if(!response.ok){const error=await response.json();throw new Error(
        typeof error.detail==='string'?error.detail:'Could not save material type.');}
      const result=await response.json();
      document.getElementById('edit-material-search').value='';
      await loadEditCatalog();filterEditMaterials(result.key);
      await loadCatalogOptions();await loadMissingFamilies();await load();
      message.textContent='Material type saved.';
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
  }
  document.getElementById('edit-character-select').addEventListener('change',()=>
    loadEditCharacter().catch(error=>document.getElementById('edit-character-message').textContent=error.message));
  document.getElementById('edit-weapon-select').addEventListener('change',()=>
    loadEditWeapon().catch(error=>document.getElementById('edit-weapon-message').textContent=error.message));
  document.getElementById('edit-material-select').addEventListener('change',showEditMaterial);
  document.getElementById('edit-copy-select').addEventListener('change',showEditCopy);
  document.getElementById('edit-material-search').addEventListener('input',()=>filterEditMaterials());
  for(const kind of ['character','weapon'])
    document.getElementById('update-'+kind).addEventListener('click',()=>saveEdit(kind));
  document.getElementById('update-material').addEventListener('click',saveMaterialType);
  document.getElementById('update-copy').addEventListener('click',async()=>{
    const id=document.getElementById('edit-copy-select').value;
    const message=document.getElementById('edit-copy-message');
    if(!id){message.textContent='Select a weapon copy first.';return;}
    const label=document.getElementById('edit-copy-label').value.trim();
    const button=document.getElementById('update-copy');button.disabled=true;
    try{
      const response=await fetch('/api/weapon-copies/'+id+'/label',{
        method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:label||null})});
      if(!response.ok)throw new Error('Could not save copy label (HTTP '+response.status+').');
      await loadEditCatalog(null,null,null,id);await loadWeaponCopies();
      message.textContent='Copy label saved.';
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
  });
  async function saveInventory(material, input, button) {
    const message = document.getElementById('save-message');
    const raw = input.value.trim();
    const quantity = Number(raw);
    if (!raw || !Number.isSafeInteger(quantity) || quantity < 0) {
      message.textContent = 'Enter a whole number of zero or more.';
      return;
    }
    button.disabled = true;
    try {
      const response = await fetch('/api/inventory', {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({material_name: material, quantity})
      });
      if (!response.ok) throw new Error('Could not save inventory (HTTP ' + response.status + ').');
      message.textContent = material + ' saved.';
      await load();
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false;
    }
  }
  async function load() {
    const summary = document.getElementById('summary');
    try {
      const response = await fetch('/api/shopping-list');
      if (!response.ok) throw new Error('Could not load the shopping list (HTTP ' + response.status + ').');
      const data = await response.json();
      const i = data.included;
      summary.textContent = `${i.characters || 0} characters, ${i.weapons || 0} weapons, ` +
        `${i.Traveller || 0} Traveller included. ${data.excluded.length} goals excluded.`;
      const body = document.getElementById('materials');
      body.replaceChildren();
      for (const item of data.materials) {
        const row = body.insertRow();
        row.insertCell().textContent = item.material;
        row.insertCell().textContent = number.format(item.required);
        row.insertCell().textContent = number.format(item.owned);
        const needed = row.insertCell();
        needed.textContent = number.format(item.still_needed);
        if (item.still_needed) needed.className = 'missing';
        const updateCell = row.insertCell();
        const input = document.createElement('input');
        input.type = 'number'; input.min = '0'; input.step = '1';
        input.placeholder = 'New total';
        input.setAttribute('aria-label', 'New owned total for ' + item.material);
        updateCell.append(input);
        const button = document.createElement('button');
        button.textContent = 'Save';
        button.addEventListener('click', () => saveInventory(item.material, input, button));
        row.insertCell().append(button);
      }
      document.getElementById('excluded-title').textContent = `Excluded goals (${data.excluded.length})`;
      const list = document.getElementById('excluded');
      list.replaceChildren();
      for (const reason of data.excluded) {
        const li = document.createElement('li'); li.textContent = reason; list.append(li);
      }
    } catch (error) { summary.textContent = error.message; }
  }
  load();
  const selected = new URLSearchParams(location.search);
  loadCharacters(selected.get('character')).catch(error => { document.getElementById('goal-message').textContent = error.message; });
  loadWeaponCopies(selected.get('weapon')).catch(error => { document.getElementById('weapon-message').textContent = error.message; });
  loadWeaponCatalog().catch(error => { document.getElementById('add-copy-message').textContent = error.message; });
  loadTravellerElements().catch(error => { document.getElementById('traveller-message').textContent = error.message; });
  loadMissingFamilies().catch(error => { document.getElementById('family-message').textContent = error.message; });
  setupEditTraveller(selected.get('traveller'),selected.get('slot')).catch(error=>{
    document.getElementById('edit-traveller-message').textContent=error.message;});
  loadCatalogOptions().then(()=>loadEditCatalog(selected.get('character'),selected.get('weapon'),
    selected.get('material'),selected.get('copy'))).catch(error => {
      document.getElementById('create-character-message').textContent = error.message;
    });
</script></body></html>'''
