"""Read-only Genshin shopping-list web page for genshin_v2.db.

Run: python -m uvicorn app_v2:app --reload
Requires shopping_list.py and its calculator modules in the same folder.
"""
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from shopping_list import build

DB_PATH = Path(__file__).resolve().parent / 'genshin_v2.db'
app = FastAPI(title='Genshin Tracker')


class InventoryUpdate(BaseModel):
    material_name: str
    quantity: int = Field(ge=0)


class CharacterGoalUpdate(BaseModel):
    target_level: int = Field(ge=1, le=90)
    target_ascension: int = Field(ge=0, le=6)
    talent_targets: list[int]


class WeaponGoalUpdate(BaseModel):
    target_level: int = Field(ge=1, le=90)
    target_ascension: int = Field(ge=0, le=6)


class NewWeaponCopy(BaseModel):
    weapon_id: int
    label: str | None = Field(default=None, max_length=80)


class TravellerGoalUpdate(BaseModel):
    target_level: int = Field(ge=1, le=90)
    target_ascension: int = Field(ge=0, le=6)
    talent_targets: list[int]


class MaterialFamilyUpdate(BaseModel):
    material_role: str
    family: str
    material_names: list[str]


FAMILY_TIERS = {'common_drop': (1, 2, 3), 'elite_drop': (2, 3, 4)}


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
                db.execute('SELECT id,name FROM characters ORDER BY name')]


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


@app.get('/api/weapons')
def list_weapon_catalog():
    with sqlite3.connect(DB_PATH) as db:
        return [{'id': wid, 'name': name, 'rarity': rarity} for wid, name, rarity in
                db.execute('SELECT id,name,rarity FROM weapons ORDER BY name')]


@app.get('/api/weapon-copies')
def list_weapon_copies():
    with sqlite3.connect(DB_PATH) as db:
        return [{'id': cid, 'weapon_id': wid, 'copy_number': number,
                 'name': name, 'label': label} for cid,wid,number,name,label in
                db.execute('''SELECT wc.id,wc.weapon_id,wc.copy_number,w.name,wc.label
                    FROM weapon_copies wc JOIN weapons w ON w.id=wc.weapon_id
                    ORDER BY w.name,wc.copy_number''')]


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


@app.get('/api/traveller/elements')
def traveller_elements():
    with sqlite3.connect(DB_PATH) as db:
        return [r[0] for r in db.execute('''SELECT DISTINCT element FROM traveller_talent_progress
            ORDER BY CASE element WHEN 'Anemo' THEN 1 WHEN 'Geo' THEN 2
            WHEN 'Electro' THEN 3 WHEN 'Dendro' THEN 4 WHEN 'Hydro' THEN 5
            WHEN 'Pyro' THEN 6 WHEN 'Cryo' THEN 7 ELSE 8 END''')]


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
        raise HTTPException(status_code=422,detail='Unsupported family role')
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
            raise HTTPException(status_code=404,detail='Missing family not found')
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


@app.get('/', response_class=HTMLResponse)
def home():
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
  details { margin: 20px 0; } li { margin: 6px 0; overflow-wrap: anywhere; }
  @media (max-width: 600px) { body { margin: 12px auto; } th,td { padding: 7px 4px; font-size: 13px; } }
</style></head><body>
<h1>Genshin Tracker</h1>
<p class="note">Combined material goals, compared once against your inventory.</p>
<section class="summary"><h2>Character Goal</h2>
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
</section>
<section class="summary"><h2>Weapon Goal</h2>
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
<h3>Add another copy</h3>
<label>Weapon <select id="weapon-catalog"></select></label>
<label>Label (optional) <input id="copy-label" type="text" maxlength="80" placeholder="e.g. second copy"></label>
<button id="add-weapon-copy">Add copy</button> <span id="add-copy-message" role="status"></span>
</section>
<section class="summary"><h2>Traveller Goal</h2>
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
<p class="note">Traveller level and ascension are shared across elements. Cryo talent costs are not available yet.</p>
</section>
<section class="summary"><h2>Missing Material Families</h2>
<p class="note">Enter the exact material names, from lowest to highest tier. Saving links the family to every listed character and weapon.</p>
<div id="missing-families"></div>
<p id="family-message" role="status"></p>
</section>
<section class="summary" id="summary">Loading shopping list…</section>
<p id="save-message" role="status"></p>
<table><thead><tr><th>Material</th><th>Required</th><th>Owned</th><th>Still needed</th><th>Update value</th><th>Action</th></tr></thead>
<tbody id="materials"></tbody></table>
<details id="excluded-section"><summary id="excluded-title">Excluded goals</summary>
<ul id="excluded"></ul></details>
<p class="note">EXP is shown as points. Using EXP items may overshoot and increase the Mora cost.</p>
<script>
  const number = new Intl.NumberFormat();
  async function loadCharacters() {
    const response = await fetch('/api/characters');
    if (!response.ok) throw new Error('Could not load characters.');
    const characters = await response.json();
    const select = document.getElementById('character-select');
    select.replaceChildren();
    for (const character of characters) {
      const option = document.createElement('option');
      option.value = character.id; option.textContent = character.name;
      select.append(option);
    }
    select.addEventListener('change', loadCharacterGoal);
    if (characters.length) await loadCharacterGoal();
  }
  async function loadCharacterGoal() {
    const id = document.getElementById('character-select').value;
    const response = await fetch('/api/characters/' + id);
    if (!response.ok) throw new Error('Could not load character goal.');
    const goal = await response.json();
    document.getElementById('character-current-level').textContent = goal.current_level;
    document.getElementById('character-current-ascension').textContent = goal.current_ascension;
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
  async function loadWeaponCopies(selectedId) {
    const response = await fetch('/api/weapon-copies');
    if (!response.ok) throw new Error('Could not load weapon copies.');
    const copies = await response.json();
    const select = document.getElementById('weapon-copy-select');
    select.replaceChildren();
    for (const copy of copies) {
      const option = document.createElement('option');
      option.value = copy.id;
      option.textContent = copy.copy_number === 1 ? copy.name :
        `${copy.name} — ${copy.label || 'Copy ' + copy.copy_number}`;
      select.append(option);
    }
    if (selectedId) select.value = String(selectedId);
    if (copies.length) await loadWeaponGoal();
  }
  async function loadWeaponGoal() {
    const id = document.getElementById('weapon-copy-select').value;
    const response = await fetch('/api/weapon-copies/' + id);
    if (!response.ok) throw new Error('Could not load weapon copy.');
    const goal = await response.json();
    document.getElementById('selected-weapon').textContent = `${goal.name} (${goal.rarity}-star)`;
    document.getElementById('weapon-current-level').textContent = goal.current_level;
    document.getElementById('weapon-current-ascension').textContent = goal.current_ascension;
    const level = document.getElementById('weapon-level');
    level.value = goal.target_level; level.min = goal.current_level;
    level.max = goal.rarity <= 2 ? 70 : 90;
    const asc = document.getElementById('weapon-ascension');
    asc.value = goal.target_ascension; asc.min = goal.current_ascension;
    asc.max = goal.rarity <= 2 ? 4 : 6;
    document.getElementById('weapon-message').textContent = '';
  }
  async function loadWeaponCatalog() {
    const response = await fetch('/api/weapons');
    if (!response.ok) throw new Error('Could not load weapon catalog.');
    const weapons = await response.json();
    const select = document.getElementById('weapon-catalog');
    select.replaceChildren();
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
    const weapon_id = Number(document.getElementById('weapon-catalog').value);
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
  document.getElementById('add-weapon-copy').addEventListener('click', addWeaponCopy);
  async function loadTravellerElements() {
    const response = await fetch('/api/traveller/elements');
    if (!response.ok) throw new Error('Could not load Traveller elements.');
    const elements = await response.json();
    const select = document.getElementById('traveller-element');
    select.replaceChildren();
    for (const element of elements) {
      const option = document.createElement('option');
      option.value = element; option.textContent = element; select.append(option);
    }
    if (elements.length) await loadTravellerGoal();
  }
  async function loadTravellerGoal() {
    const element = document.getElementById('traveller-element').value;
    const response = await fetch('/api/traveller/' + encodeURIComponent(element));
    if (!response.ok) throw new Error('Could not load Traveller goal.');
    const goal = await response.json();
    document.getElementById('traveller-current-level').textContent = goal.current_level;
    document.getElementById('traveller-current-ascension').textContent = goal.current_ascension;
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
  async function loadMissingFamilies() {
    const response = await fetch('/api/missing-families');
    if (!response.ok) throw new Error('Could not load missing material families.');
    const groups = await response.json();
    const container = document.getElementById('missing-families');
    container.replaceChildren();
    if (!groups.length) { container.textContent = 'All material families are linked.'; return; }
    for (const group of groups) {
      const panel = document.createElement('div'); panel.className = 'goal-group';
      const title = document.createElement('h3');
      title.textContent = `${group.family} (${group.material_role.replaceAll('_',' ')})`;
      panel.append(title);
      const affected = document.createElement('p');
      affected.className = 'note'; affected.textContent = 'Affects: ' + group.affected.join(', ');
      panel.append(affected);
      const inputs = [];
      for (const tier of group.tiers) {
        const label = document.createElement('label');
        label.textContent = `Tier ${tier} material: `;
        const input = document.createElement('input');
        input.type = 'text'; input.placeholder = 'Exact material name';
        input.setAttribute('aria-label', `${group.family} tier ${tier} material`);
        label.append(input); panel.append(label); inputs.push(input);
      }
      const button = document.createElement('button');
      button.textContent = 'Save family';
      button.addEventListener('click', async () => {
        const message = document.getElementById('family-message');
        const material_names = inputs.map(input => input.value.trim());
        if (material_names.some(name => !name) || new Set(material_names).size !== material_names.length) {
          message.textContent = 'Enter three distinct material names for ' + group.family + '.'; return;
        }
        button.disabled = true;
        try {
          const response = await fetch('/api/material-family', {
            method:'PUT', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({material_role:group.material_role,family:group.family,material_names})
          });
          if (!response.ok) throw new Error('Could not save family (HTTP '+response.status+').');
          message.textContent = group.family + ' saved.';
          await loadMissingFamilies(); await load();
        } catch (error) { message.textContent = error.message; button.disabled = false; }
      });
      panel.append(button); container.append(panel);
    }
  }
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
      summary.textContent = `${i.characters || 0} characters, ${i['weapon copies'] || 0} weapon copies, ` +
        `${i.Traveller || 0} Traveller included. ${data.excluded.length} goals excluded. ` +
        `EXP: ${number.format(data.character_exp)} character, ${number.format(data.weapon_exp)} weapon points.`;
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
  loadCharacters().catch(error => { document.getElementById('goal-message').textContent = error.message; });
  loadWeaponCopies().catch(error => { document.getElementById('weapon-message').textContent = error.message; });
  loadWeaponCatalog().catch(error => { document.getElementById('add-copy-message').textContent = error.message; });
  loadTravellerElements().catch(error => { document.getElementById('traveller-message').textContent = error.message; });
  loadMissingFamilies().catch(error => { document.getElementById('family-message').textContent = error.message; });
</script></body></html>'''
