"""Standalone inventory and catalog progress screens."""

from sticky_table_headers import STICKY_TABLE_SCRIPT

STYLE = '''<style>
body{font:15px system-ui,sans-serif;color:#263244;background:#f8fafc;max-width:1250px;margin:25px auto;padding:0 16px}
nav a{margin-right:18px}section{background:white;border:1px solid #d6dfe8;border-radius:8px;padding:16px;margin:20px 0}
.shopping-family{margin:18px 0 22px}.shopping-family h3{margin:0 0 8px;font-size:1.05rem}
.shopping-table td:nth-child(n+2),.shopping-table th:nth-child(n+2){text-align:center}
.shopping-table .needed{background:#FFC7CE;color:#9C0006;font-weight:600}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:750px}th,td{border-bottom:1px solid #e2e8ef;padding:8px;text-align:left;white-space:nowrap}
th{background:#eaf0f6;position:sticky;top:0}.inventory-table th:not(:first-child),.inventory-table td.num,.inventory-table td.control{text-align:center}
.inventory-table tr.family-start td{border-top:2px solid #92a8bc}
.inventory-table tr.single-item-start td{border-top:1px solid #92a8bc}
.inventory-table tr.region-start td{border-top:3px solid #395b78}
.inventory-table td.deficit{background:#FFC7CE;color:#9C0006;font-weight:600}
.inventory-table tfoot th{position:static}.inventory-table tfoot td{font-weight:600}
input[type=number]{width:95px;padding:5px}
button{padding:6px 9px;cursor:pointer}.note{color:#526071}.missing{color:#9a3412;font-weight:600}
.table-tools{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:12px 0}a{color:#135b8d}
.progress-table thead input{width:100%;min-width:80px;box-sizing:border-box;padding:5px}
.progress-table thead button{border:0;background:transparent;font-weight:700;text-align:left;white-space:nowrap}
body.progress-page{max-width:1800px}.progress-table{width:max-content;min-width:100%}
.progress-table th,.progress-table td{padding:10px 14px}
.progress-table td:last-child{white-space:nowrap}
.progress-table td.progress-meter{background:linear-gradient(90deg,#C6E8CF var(--progress),#F1F5F9 var(--progress));
  color:#193525;font-weight:600}
.progress-table td.progress-meter.complete{background:#B7E1CD;color:#14532D}
.progress-legend{display:flex;gap:12px;align-items:center;margin:8px 0;color:#526071}
.progress-legend-swatch{display:inline-block;width:90px;height:14px;vertical-align:middle;
  background:linear-gradient(90deg,#C6E8CF 60%,#F1F5F9 60%);border:1px solid #d6dfe8}
.column-options{display:flex;flex-wrap:wrap;gap:8px 18px;margin:10px 0}.column-options label{white-space:nowrap}
.column-actions{display:flex;gap:8px;margin:10px 0}
.site-header{position:sticky;top:0;z-index:30;background:#f8fafc;padding:10px 0 12px;
  box-shadow:0 4px 8px -8px #263244}
.site-header h1{margin:12px 0 0}.site-title{font-size:20px;font-weight:700;margin-bottom:10px}
.inventory-header-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.bulk-goals{margin-top:8px}.bulk-goals h2{margin:0 0 6px}
.bulk-goal-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px}
.bulk-goal-options details{border:1px solid #d6dfe8;border-radius:6px;padding:10px;align-self:start}
.bulk-goal-options summary{cursor:pointer;font-weight:600}
.bulk-goal-options label{display:block;margin:8px 0}
.bulk-goal-options input{display:block;box-sizing:border-box;margin-top:3px}
</style>'''


def overview_page():
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inventory Overview · Genshin Tracker</title>''' + STYLE + '''</head><body>
<header class="site-header inventory-header">
<div class="site-title">Genshin Tracker</div>
<nav><a href="/">Inventory Overview</a><a href="/shopping">Shopping List</a><a href="/characters">Characters</a><a href="/weapons">Weapons</a><a href="/traveller">Traveller</a><a href="/catalog">Add data</a></nav>
<h1>Inventory Overview</h1>
<div class="inventory-header-actions"><span class="note">Inventory saves when you leave an update box.</span><span id="save-status" role="status"></span></div>
</header>
<section class="bulk-goals"><h2>Goals</h2>
<p class="note">Bulk targets apply to every entry in that group. Recorded progress is kept when it is already above the chosen target. One- and two-star weapons stop at level 70 and ascension 4.</p>
<div class="bulk-goal-options">
<details><summary>Reset All Goals</summary>
<p>Set every character, weapon, and Traveller target to its current progress.</p>
<button type="button" data-bulk-scope="reset">Reset All Goals</button></details>
<details><summary>Set Character Targets</summary>
<label>Target Level <input type="number" min="1" max="90" step="1" data-bulk-field="level"></label>
<label>Target Ascension <input type="number" min="0" max="6" step="1" data-bulk-field="ascension"></label>
<label>All Talent Target Levels <input type="number" min="1" max="10" step="1" data-bulk-field="talent"></label>
<button type="button" data-bulk-scope="characters">Set Character Targets</button></details>
<details><summary>Set Weapon Targets</summary>
<p class="note">Applies to every weapon copy.</p>
<label>Target Level <input type="number" min="1" max="90" step="1" data-bulk-field="level"></label>
<label>Target Ascension <input type="number" min="0" max="6" step="1" data-bulk-field="ascension"></label>
<button type="button" data-bulk-scope="weapons">Set Weapon Targets</button></details>
<details><summary>Set Traveller Targets</summary>
<p class="note">Shared level and ascension; the talent target applies to all three talents for every element.</p>
<label>Target Level <input type="number" min="1" max="90" step="1" data-bulk-field="level"></label>
<label>Target Ascension <input type="number" min="0" max="6" step="1" data-bulk-field="ascension"></label>
<label>All Talent Target Levels <input type="number" min="1" max="10" step="1" data-bulk-field="talent"></label>
<button type="button" data-bulk-scope="traveller">Set Traveller Targets</button></details>
</div><p id="bulk-goal-status" role="status"></p></section>
<div id="warnings"></div><div id="sections">Loading…</div>
<script>
const fmt = new Intl.NumberFormat();
const n = x => fmt.format(x);
function cell(row, value, className='') {const td=row.insertCell();td.textContent=value;td.className=className;return td;}
for(const button of document.querySelectorAll('[data-bulk-scope]'))button.addEventListener('click',async()=>{
  const scope=button.dataset.bulkScope;
  const status=document.getElementById('bulk-goal-status');
  const panel=button.closest('details');
  const payload={scope};
  if(scope!=='reset'){
    for(const [field,key] of [['level','target_level'],['ascension','target_ascension'],
                               ['talent','talent_target']]){
      const input=panel.querySelector('[data-bulk-field="'+field+'"]');
      if(!input)continue;
      const value=Number(input.value);
      if(!input.value.trim()||!Number.isInteger(value)||!input.checkValidity()){
        status.textContent='Enter valid whole-number targets for '+scope+'.';input.focus();return;
      }
      payload[key]=value;
    }
  }
  button.disabled=true;status.textContent='Saving goals…';
  try{
    const response=await fetch('/api/goals/bulk',{method:'PUT',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok){const error=await response.json();throw new Error(error.detail||'Could not update goals.');}
    const result=await response.json();
    await load();
    status.textContent=scope==='reset'?'All goals reset to current progress.':
      result.updated+' '+scope+' updated.';
  }catch(error){status.textContent=error.message;}finally{button.disabled=false;}
});
let inventorySaveQueue=Promise.resolve();
let refreshingInventory=false;
function queueInventorySave(input){
  if(refreshingInventory)return;
  const raw=input.value.trim();
  if(!raw)return;
  const quantity=Number(raw);
  const materialId=input.dataset.materialId, name=input.dataset.materialName;
  const message=document.getElementById('save-status');
  if(!Number.isSafeInteger(quantity)||quantity<0){
    message.textContent='Enter a whole number of zero or more for '+name+'.';
    input.setAttribute('aria-invalid','true');return;
  }
  input.removeAttribute('aria-invalid');
  inventorySaveQueue=inventorySaveQueue.then(async()=>{
    message.textContent='Saving '+name+'…';
    try{
      const response=await fetch('/api/inventory/batch',{method:'PUT',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({updates:[{material_id:Number(materialId),quantity}]})});
      if(!response.ok)throw new Error('Could not save '+name+' (HTTP '+response.status+').');
      const current=document.querySelector('#sections input[data-material-id="'+materialId+'"]');
      if(current && current.value.trim()===raw)current.value='';
      message.textContent=name+' saved.';
      try{await load();}catch(error){message.textContent=name+' saved, but totals could not refresh. Refresh the page.';}
    }catch(error){message.textContent=error.message+' Leave the box again to retry.';}
  });
}
async function load() {
  const response=await fetch('/api/overview');
  if(!response.ok) throw new Error('Could not load inventory overview.');
  const data=await response.json();
  const warnings=document.getElementById('warnings');warnings.replaceChildren();
  const p=document.createElement('p');p.className='note';
  p.textContent=data.max_note;warnings.append(p);
  for(const [title,entries] of [['Goals excluded from required totals',data.goal_excluded],['Entries excluded from max totals',data.max_excluded]]) {
    if(!entries.length) continue;
    const details=document.createElement('details');details.open=true;
    const summary=document.createElement('summary');summary.textContent=title+' ('+entries.length+')';details.append(summary);
    const ul=document.createElement('ul');for(const entry of entries){const li=document.createElement('li');li.textContent=entry;ul.append(li);}
    details.append(ul);warnings.append(details);
  }
  const root=document.getElementById('sections');
  const pending=new Map([...root.querySelectorAll('input[data-material-id]')]
    .map(input=>[input.dataset.materialId,input.value]));
  const focused=root.contains(document.activeElement)?document.activeElement.dataset.materialId:null;
  const scrollX=window.scrollX,scrollY=window.scrollY;
  refreshingInventory=true;
  root.replaceChildren();
  for(const section of data.sections) {
    const panel=document.createElement('section');const heading=document.createElement('h2');heading.textContent=section.title;panel.append(heading);
    const isExp=section.category==='character_exp'||section.category==='weapon_exp';
    const exp=isExp ? data.experience[section.category==='character_exp'?'character':'weapon'] : null;
    if(['talent_book','weapon_ascension','common_drop','elite_drop','ascension_gem','weekly_boss_drop'].includes(section.category)){
      const info=document.createElement('p');info.className='note';
      info.textContent=section.category==='weekly_boss_drop' ?
        'Convert columns show 1:1 conversion actions on the source item row. Inventory is not changed automatically.' :
        'Convert columns show 3:1 conversion actions on the source item row; each action makes one higher tier item. Inventory is not changed automatically.';
      panel.append(info);
    }
    const wrap=document.createElement('div');wrap.className='scroll';const table=document.createElement('table');table.className='inventory-table';
    const head=table.createTHead().insertRow();
    const titles=isExp ? ['Item','Items Owned','Update Value'] :
      ['Material','Required','Owned','Still Needed','Convert (Goal)','Max Required','To Max','Convert (Max)','Update Value'];
    for(const title of titles) {
      const th=document.createElement('th');th.textContent=title;head.append(th);
    }
    const body=table.createTBody();
    const familySizes=new Map();
    for(const item of section.materials)
      familySizes.set(item.family,(familySizes.get(item.family)||0)+1);
    let lastFamily=null,lastRegion=null;
    for(const material of section.materials) {
      const row=body.insertRow();
      if(!isExp && section.category!=='currency' && lastFamily!==null && material.family!==lastFamily)
        row.classList.add(familySizes.get(material.family)===1?
          'single-item-start':'family-start');
      if(!isExp && lastRegion!==null && material.region && material.region!==lastRegion)
        row.classList.add('region-start');
      lastFamily=material.family;lastRegion=material.region||null;
      const materialCell=cell(row,'');
      const materialLink=document.createElement('a');materialLink.href='/catalog?material='+encodeURIComponent(material.id);
      materialLink.textContent=material.name;materialCell.append(materialLink);
      if(isExp){cell(row,n(material.owned),'num');} else {
        cell(row,n(material.required),'num');cell(row,n(material.owned),'num');
        const needed=cell(row,n(material.still_needed),'num');if(material.still_needed)needed.classList.add('deficit');
        const goalConversion=cell(row,n(material.convert_for_goal),'num');
        if(material.convert_for_goal)goalConversion.classList.add('deficit');
        cell(row,n(material.max_required),'num');
        cell(row,n(material.max_still_needed),'num');
        cell(row,n(material.convert_for_max),'num');
      }
      const input=document.createElement('input');input.type='number';input.min='0';input.step='1';
      input.dataset.materialId=material.id;input.dataset.materialName=material.name;
      input.setAttribute('aria-label','Update '+material.name);
      input.value=pending.get(String(material.id))||'';
      input.addEventListener('blur',()=>queueInventorySave(input));
      cell(row,'','control').append(input);
    }
    if(isExp){
      const foot=table.createTFoot();
      for(const [label,value] of [
        ['EXP Required',exp.required],['EXP Held',exp.owned],
        ['EXP Remaining',Math.max(0,exp.required-exp.owned)],
        ['Max EXP Required',exp.max_required],
        ['EXP To Max',Math.max(0,exp.max_required-exp.owned)]
      ]){
        const row=foot.insertRow(), heading=document.createElement('th');
        heading.scope='row';heading.textContent=label;row.append(heading);
        const valueCell=cell(row,n(value),'num');
        if(label==='EXP Remaining' && value>0)valueCell.classList.add('deficit');
        cell(row,'');
      }
    }
    wrap.append(table);panel.append(wrap);root.append(panel);
  }
  if(focused){
    const replacement=root.querySelector('input[data-material-id="'+focused+'"]');
    if(replacement)replacement.focus({preventScroll:true});
  }
  window.scrollTo(scrollX,scrollY);
  refreshingInventory=false;
}
load().catch(error=>{document.getElementById('sections').textContent=error.message;});
</script></body></html>'''.replace('</body>', STICKY_TABLE_SCRIPT+'</body>')


def shopping_page():
    # Share the inventory table, including conversion and inventory editing.
    page=overview_page()
    page=page.replace('Inventory Overview · Genshin Tracker</title>',
                      'Shopping List · Genshin Tracker</title>')
    page=page.replace('<h1>Inventory Overview</h1>', '<h1>Shopping List</h1>')
    start=page.index('<section class="bulk-goals">')
    end=page.index('<div id="warnings">',start)
    page=page[:start]+page[end:]
    page=page.replace("fetch('/api/overview')", "fetch('/api/shopping')")
    page=page.replace('Could not load inventory overview.', 'Could not load shopping list.')
    page=page.replace('for(const section of data.sections) {',
        "if(!data.sections.length)root.textContent='No materials are currently needed for your goals.';\n  for(const section of data.sections) {")
    page=page.replace('<div id="warnings"></div>',
        '<p class="note">Only families with a shortage or needed conversion appear here. All inventory columns and automatic saving work as on Inventory Overview.</p><div id="warnings"></div>')
    return page


def progress_page(kind='characters'):
    if kind not in ('characters','weapons','traveller'):
        raise ValueError('Unknown progress list')
    title = {'characters':'Character Progress','weapons':'Weapon Progress',
             'traveller':'Traveller Progress'}[kind]
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · Genshin Tracker</title>''' + STYLE + '''</head><body class="progress-page">
<header class="site-header">
<div class="site-title">Genshin Tracker</div>
<nav><a href="/">Inventory Overview</a><a href="/shopping">Shopping List</a><a href="/characters">Characters</a><a href="/weapons">Weapons</a><a href="/traveller">Traveller</a><a href="/catalog">Add data</a></nav>
<h1>__TITLE__</h1>
</header>
<p class="note">Click a heading to sort, or use the filter beneath it. Column choices and filters persist on this device; sorting resets when the page reloads.</p>
<p class="progress-legend"><span class="progress-legend-swatch" aria-hidden="true"></span>Green fill shows recorded progress toward the cap; talents count as complete at level 9.</p>
<section><p id="shared-progress"></p><button type="button" id="clear-filters">Clear filters</button>
<details><summary>Show or Hide Columns</summary>
<div class="column-actions"><button type="button" id="show-all-columns">Show All</button><button type="button" id="hide-all-columns">Hide All</button></div>
<div id="column-options" class="column-options"></div></details>
<div class="scroll"><table class="progress-table"><thead id="progress-head"></thead><tbody id="progress-body"></tbody></table></div></section>
<p id="status" role="status"></p><script>
const kind='__KIND__';
const range=(current,target)=>current+' → '+target;
const definitions={
  characters:[['id','ID',true],['name','Character'],['element','Element'],
    ['gem_family','Gem'],['boss_material','World Boss Material'],
    ['common_drop_family','Common Enemy Drop'],['local_specialty','Local Speciality'],
    ['talent_book_family','Talent Material'],['weekly_boss_material','Weekly Boss Material'],
    ['level','Level',true],['ascension','Ascension',true],
    ['talent1','Talent 1',true],['talent2','Talent 2',true],['talent3','Talent 3',true]],
  weapons:[['weapon_id','Weapon ID',true],['name','Weapon'],['weapon_type','Type'],
    ['rarity','Rarity',true],['ascension_family','Ascension Material'],
    ['common_drop_family','Common Enemy Drop'],['elite_drop_family','Elite Enemy Drop'],
    ['copy_number','Copy ID',true],
    ['level','Level',true],['ascension','Ascension',true]],
  traveller:[['element','Element'],['common_drop_family','Common Enemy Drop'],
    ['talent_slot','Talent',true],['talent_material_type','Talent Material'],
    ['weekly_boss_type','Weekly Boss Material'],['current_level','Current Level',true],
    ['target_level','Target Level',true]]
};
const columns=definitions[kind];
const allColumns=columns.map(column=>column[0]).concat('actions');
const columnStorageKey='genshin-tracker:progress-columns:'+kind;
const filterStorageKey='genshin-tracker:progress-filters:'+kind;
function savedFilters(){
  try {
    const stored=JSON.parse(localStorage.getItem(filterStorageKey));
    if(stored && typeof stored==='object' && !Array.isArray(stored))
      return Object.fromEntries(columns.map(([key])=>[key,stored[key]])
        .filter(([,value])=>typeof value==='string' && value));
  } catch(error) { /* Browser storage may be unavailable; keep defaults. */ }
  return {};
}
const filters=savedFilters();
function rememberFilters(){
  try {localStorage.setItem(filterStorageKey,JSON.stringify(filters));}
  catch(error) { /* Filters still work for this visit. */ }
}
function savedColumns(){
  try {
    const stored=JSON.parse(localStorage.getItem(columnStorageKey));
    if(Array.isArray(stored))return stored.filter(key=>allColumns.includes(key));
  } catch(error) { /* Browser storage may be unavailable; keep defaults. */ }
  return allColumns;
}
const visibleColumns=new Set(savedColumns());
function rememberColumns(){
  try {localStorage.setItem(columnStorageKey,JSON.stringify([...visibleColumns]));}
  catch(error) { /* The checkboxes still work for this visit. */ }
}
let rows=[],sortKey=kind==='weapons'?'weapon_id':kind==='traveller'?'order_id':'id',sortDirection=1;
const collator=new Intl.Collator(undefined,{numeric:true,sensitivity:'base'});
function syncColumnOptions(){
  for(const input of document.querySelectorAll('#column-options input[data-column]'))
    input.checked=visibleColumns.has(input.dataset.column);
}
function setAllColumns(show){
  visibleColumns.clear();
  if(show)for(const key of allColumns)visibleColumns.add(key);
  else {for(const key of Object.keys(filters))delete filters[key];rememberFilters();}
  rememberColumns();syncColumnOptions();buildHead();render();
}
function buildColumnOptions(){
  const options=document.getElementById('column-options');
  for(const [key,label] of [...columns,['actions','Actions']]){
    const wrapper=document.createElement('label'),input=document.createElement('input');
    input.type='checkbox';input.dataset.column=key;input.checked=visibleColumns.has(key);
    input.setAttribute('aria-label','Show '+label);
    input.addEventListener('change',()=>{
      if(input.checked)visibleColumns.add(key);
      else {visibleColumns.delete(key);delete filters[key];
        if(sortKey===key){sortKey=kind==='weapons'?'weapon_id':kind==='traveller'?'order_id':'id';sortDirection=1;}}
      rememberFilters();
      rememberColumns();buildHead();render();
    });
    wrapper.append(input,' '+label);options.append(wrapper);
  }
}
function makeRows(data){
  if(kind==='characters')return data.characters.map(c=>({...c,
    level:range(c.current_level,c.target_level),ascension:range(c.current_ascension,c.target_ascension),
    ...Object.fromEntries(c.talents.map(t=>['talent'+t.talent_slot,range(t.current_level,t.target_level)]))}));
  if(kind==='weapons')return data.weapons.map(w=>({...w,copy_id:w.id,
    name:w.name+(w.copy_number>1?' #'+w.copy_number+(w.label?' · '+w.label:''):''),
    level:range(w.current_level,w.target_level),ascension:range(w.current_ascension,w.target_ascension)}));
  return data.traveller.talents.map(t=>({...t,order_id:t.id}));
}
function numericValue(row,key){
  return Number.parseInt(String(row[key]??''),10)||0;
}
function progressFraction(item,key){
  let current,maximum;
  if(kind==='characters'){
    if(key==='level'){current=item.current_level;maximum=90;}
    else if(key==='ascension'){current=item.current_ascension;maximum=6;}
    else if(/^talent[123]$/.test(key)){
      current=item.talents.find(t=>t.talent_slot===Number(key.slice(-1)))?.current_level;
      maximum=9;
    }
  }else if(kind==='weapons'){
    if(key==='level'){current=item.current_level;maximum=item.rarity<=2?70:90;}
    else if(key==='ascension'){current=item.current_ascension;maximum=item.rarity<=2?4:6;}
  }else if(key==='current_level'){
    current=item.current_level;maximum=9;
  }
  if(current===undefined)return null;
  const start=key==='ascension'?0:1;
  return Math.max(0,Math.min(1,(current-start)/(maximum-start)));
}
function buildHead(){
  const head=document.getElementById('progress-head');head.replaceChildren();
  const headings=head.insertRow(),inputs=head.insertRow();
  for(const [key,label,numeric] of columns){
    if(!visibleColumns.has(key))continue;
    const th=document.createElement('th'),button=document.createElement('button');
    button.type='button';button.textContent=label+(sortKey===key?(sortDirection===1?' ▲':' ▼'):'');
    button.addEventListener('click',()=>{sortDirection=sortKey===key?-sortDirection:1;sortKey=key;buildHead();render();});
    th.setAttribute('aria-sort',sortKey===key?(sortDirection===1?'ascending':'descending'):'none');
    th.append(button);headings.append(th);
    const filterCell=document.createElement('th'),input=document.createElement('input');
    input.type='search';input.value=filters[key]||'';input.placeholder='Filter';
    input.setAttribute('aria-label','Filter '+label);
    input.addEventListener('input',()=>{
      if(input.value)filters[key]=input.value;else delete filters[key];
      rememberFilters();render();
    });
    filterCell.append(input);inputs.append(filterCell);
  }
  if(visibleColumns.has('actions')){
    const actionHead=document.createElement('th');actionHead.textContent='Actions';headings.append(actionHead);
    inputs.append(document.createElement('th'));
  }
}
function render(){
  const body=document.getElementById('progress-body');body.replaceChildren();
  if(!visibleColumns.size){
    document.getElementById('status').textContent='All columns are hidden. Select a checkbox or choose Show All.';
    return;
  }
  const visible=rows.filter(row=>columns.every(([key,,numeric])=>{
    const filter=(filters[key]||'').trim().toLocaleLowerCase();
    if(!filter)return true;
    return String(row[key]??'').toLocaleLowerCase().includes(filter);
  })).sort((a,b)=>{
    const numeric=sortKey==='order_id'||columns.find(column=>column[0]===sortKey)[2];
    const compared=numeric?numericValue(a,sortKey)-numericValue(b,sortKey):
      collator.compare(String(a[sortKey]??''),String(b[sortKey]??''));
    return compared*sortDirection || (a.order_id??a.weapon_id??a.id)-(b.order_id??b.weapon_id??b.id);
  });
  for(const item of visible){
    const row=body.insertRow();
    for(const [key] of columns){
      if(!visibleColumns.has(key))continue;
      const cell=row.insertCell(),value=item[key]??'—';
      if((key==='name' && kind!=='traveller') || (key==='element' && kind==='traveller')){
        const link=document.createElement('a');link.href=
          kind==='characters'?'/goals/character?character='+encodeURIComponent(item.id):
          kind==='weapons'?'/goals/weapon?weapon='+encodeURIComponent(item.copy_id):
          '/goals/traveller?traveller='+encodeURIComponent(item.element);
        link.textContent=value;cell.append(link);
      } else cell.textContent=value;
      const fraction=progressFraction(item,key);
      if(fraction!==null){
        cell.classList.add('progress-meter');
        cell.style.setProperty('--progress',Math.round(fraction*100)+'%');
        if(fraction===1)cell.classList.add('complete');
      }
    }
    if(!visibleColumns.has('actions'))continue;
    const actions=row.insertCell();
    const edit=document.createElement('a');edit.href='/catalog?'+
      (kind==='characters'?'character='+encodeURIComponent(item.id):
       kind==='weapons'?'weapon='+encodeURIComponent(item.weapon_id):
       'traveller='+encodeURIComponent(item.element)+'&slot='+encodeURIComponent(item.talent_slot));
    edit.textContent='Edit data';actions.append(edit);
    if(kind==='weapons' && item.copy_number>1){
      const copyEdit=document.createElement('a');
      copyEdit.href='/catalog?copy='+encodeURIComponent(item.copy_id);
      copyEdit.textContent='Edit label';actions.append(' · ',copyEdit);
    }
  }
  document.getElementById('status').textContent=visible.length+' entries shown.';
}
async function load(){
  const response=await fetch('/api/progress');if(!response.ok)throw new Error('Could not load progress lists.');
  const data=await response.json();rows=makeRows(data);buildHead();render();
  if(kind==='traveller'){
    const p=data.traveller.progress;
    document.getElementById('shared-progress').textContent='Shared level '+range(p.current_level,p.target_level)+
      ' · Ascension '+range(p.current_ascension,p.target_ascension);
  }
}
document.getElementById('clear-filters').addEventListener('click',()=>{
  for(const key of Object.keys(filters))delete filters[key];
  rememberFilters();
  sortKey=kind==='weapons'?'weapon_id':kind==='traveller'?'order_id':'id';sortDirection=1;
  buildHead();render();
});
document.getElementById('show-all-columns').addEventListener('click',()=>setAllColumns(true));
document.getElementById('hide-all-columns').addEventListener('click',()=>setAllColumns(false));
buildColumnOptions();
load().catch(error=>{document.getElementById('status').textContent=error.message;});
</script></body></html>'''
    return page.replace('__KIND__', kind).replace('__TITLE__', title).replace('</body>', STICKY_TABLE_SCRIPT+'</body>')
