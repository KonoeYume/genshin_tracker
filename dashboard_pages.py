"""Standalone inventory and catalog progress screens."""

STYLE = '''<style>
body{font:15px system-ui,sans-serif;color:#263244;background:#f8fafc;max-width:1250px;margin:25px auto;padding:0 16px}
nav a{margin-right:18px}section{background:white;border:1px solid #d6dfe8;border-radius:8px;padding:16px;margin:20px 0}
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
.column-options{display:flex;flex-wrap:wrap;gap:8px 18px;margin:10px 0}.column-options label{white-space:nowrap}
</style>'''


def overview_page():
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inventory Overview · Genshin Tracker</title>''' + STYLE + '''</head><body>
<nav><a href="/">Inventory Overview</a><a href="/goals">Goals</a><a href="/characters">Characters</a><a href="/weapons">Weapons</a><a href="/traveller">Traveller</a><a href="/catalog">Add data</a></nav>
<h1>Inventory Overview</h1>
<div id="warnings"></div><div id="sections">Loading…</div>
<p id="save-status" role="status"></p>
<script>
const fmt = new Intl.NumberFormat();
const n = x => fmt.format(x);
function cell(row, value, className='') {const td=row.insertCell();td.textContent=value;td.className=className;return td;}
async function save(name, input, button) {
  const raw=input.value.trim(), quantity=Number(raw), message=document.getElementById('save-status');
  if (!raw || !Number.isSafeInteger(quantity) || quantity<0) {message.textContent='Enter a whole number of zero or more.';return;}
  button.disabled=true;
  try {
    const response=await fetch('/api/inventory',{method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({material_name:name,quantity})});
    if(!response.ok) throw new Error('Could not save '+name+' (HTTP '+response.status+').');
    await load();message.textContent=name+' saved.';
  } catch(error){message.textContent=error.message;} finally{button.disabled=false;}
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
  const root=document.getElementById('sections');root.replaceChildren();
  for(const section of data.sections) {
    const panel=document.createElement('section');const heading=document.createElement('h2');heading.textContent=section.title;panel.append(heading);
    const isExp=section.category==='character_exp'||section.category==='weapon_exp';
    const exp=isExp ? data.experience[section.category==='character_exp'?'character':'weapon'] : null;
    if(['talent_book','weapon_ascension','common_drop','elite_drop','ascension_gem','weekly_boss_drop'].includes(section.category)){
      const info=document.createElement('p');info.className='note';
      info.textContent=section.category==='weekly_boss_drop' ?
        'Convert columns show source items spent at 1:1 within each boss family. Inventory is not changed automatically.' :
        'Convert columns show lower tier source items spent at 3:1 within each family. Inventory is not changed automatically.';
      panel.append(info);
    }
    const wrap=document.createElement('div');wrap.className='scroll';const table=document.createElement('table');table.className='inventory-table';
    const head=table.createTHead().insertRow();
    const titles=isExp ? ['Item','Items Owned','Update Value',''] :
      ['Material','Required','Owned','Still Needed','Convert (Goal)','Max Required','To Max','Convert (Max)','Update Value',''];
    for(const title of titles) {
      const th=document.createElement('th');th.textContent=title;head.append(th);
    }
    const body=table.createTBody();
    let lastFamily=null,lastRegion=null;
    for(const material of section.materials) {
      const row=body.insertRow();
      if(!isExp && section.category!=='currency' && lastFamily!==null && material.family!==lastFamily)
        row.classList.add(['character_boss_drop','local_specialty'].includes(section.category)?
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
      const input=document.createElement('input');input.type='number';input.min='0';input.step='1';input.setAttribute('aria-label','Update '+material.name);
      cell(row,'','control').append(input);
      const button=document.createElement('button');button.textContent='Save';cell(row,'','control').append(button);
      button.addEventListener('click',()=>save(material.name,input,button));
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
        const spacer=cell(row,'');spacer.colSpan=2;
      }
    }
    wrap.append(table);panel.append(wrap);root.append(panel);
  }
}
load().catch(error=>{document.getElementById('sections').textContent=error.message;});
</script></body></html>'''


def progress_page(kind='characters'):
    if kind not in ('characters','weapons','traveller'):
        raise ValueError('Unknown progress list')
    title = {'characters':'Character Progress','weapons':'Weapon Progress',
             'traveller':'Traveller Progress'}[kind]
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · Genshin Tracker</title>''' + STYLE + '''</head><body class="progress-page">
<nav><a href="/">Inventory Overview</a><a href="/goals">Goals</a><a href="/characters">Characters</a><a href="/weapons">Weapons</a><a href="/traveller">Traveller</a><a href="/catalog">Add data</a></nav>
<h1>__TITLE__</h1><p class="note">Click a heading to sort, or use the filter beneath it. Sorting, filters, and column choices reset when the page reloads.</p>
<section><p id="shared-progress"></p><button type="button" id="clear-filters">Clear filters</button>
<details><summary>Show or Hide Columns</summary><div id="column-options" class="column-options"></div></details>
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
const columns=definitions[kind], filters={};
const visibleColumns=new Set(columns.map(column=>column[0]).concat('actions'));
let rows=[],sortKey=kind==='weapons'?'weapon_id':kind==='traveller'?'order_id':'id',sortDirection=1;
const collator=new Intl.Collator(undefined,{numeric:true,sensitivity:'base'});
function buildColumnOptions(){
  const options=document.getElementById('column-options');
  for(const [key,label] of [...columns,['actions','Actions']]){
    const wrapper=document.createElement('label'),input=document.createElement('input');
    input.type='checkbox';input.checked=true;input.setAttribute('aria-label','Show '+label);
    input.addEventListener('change',()=>{
      if(!input.checked && visibleColumns.size===1){input.checked=true;return;}
      if(input.checked)visibleColumns.add(key);
      else {visibleColumns.delete(key);delete filters[key];
        if(sortKey===key){sortKey=kind==='weapons'?'weapon_id':kind==='traveller'?'order_id':'id';sortDirection=1;}}
      buildHead();render();
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
    input.addEventListener('input',()=>{filters[key]=input.value;render();});
    filterCell.append(input);inputs.append(filterCell);
  }
  if(visibleColumns.has('actions')){
    const actionHead=document.createElement('th');actionHead.textContent='Actions';headings.append(actionHead);
    inputs.append(document.createElement('th'));
  }
}
function render(){
  const body=document.getElementById('progress-body');body.replaceChildren();
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
      if(key==='name' && kind!=='traveller'){
        const link=document.createElement('a');link.href='/goals?'+
          (kind==='characters'?'character='+encodeURIComponent(item.id):'weapon='+encodeURIComponent(item.copy_id));
        link.textContent=value;cell.append(link);
      } else cell.textContent=value;
    }
    if(!visibleColumns.has('actions'))continue;
    const actions=row.insertCell();
    const edit=document.createElement('a');edit.href='/catalog?'+
      (kind==='characters'?'character='+encodeURIComponent(item.id):
       kind==='weapons'?'weapon='+encodeURIComponent(item.weapon_id):
       'traveller='+encodeURIComponent(item.element)+'&slot='+encodeURIComponent(item.talent_slot));
    edit.textContent='Edit data';actions.append(edit);
    if(kind==='weapons'){
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
  sortKey=kind==='weapons'?'weapon_id':kind==='traveller'?'order_id':'id';sortDirection=1;
  buildHead();render();
});
buildColumnOptions();
load().catch(error=>{document.getElementById('status').textContent=error.message;});
</script></body></html>'''
    return page.replace('__KIND__', kind).replace('__TITLE__', title)
