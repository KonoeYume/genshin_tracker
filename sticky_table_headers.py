"""Shared sticky column headers for horizontally scrollable tables."""

STICKY_TABLE_SCRIPT = r'''<style>
.floating-table-header{position:fixed;z-index:24;overflow:hidden;pointer-events:auto;
  background:#eaf0f6;box-shadow:0 3px 6px -5px #263244}
.floating-table-header table{margin:0!important;min-width:0!important}
.floating-table-header th{position:static!important}
</style>
<script>
(()=>{
  const overlay=document.createElement('div');overlay.className='floating-table-header';
  overlay.hidden=true;document.body.append(overlay);
  let active=null,copy=null,originalCells=[],clonedCells=[];
  const header=document.querySelector('.site-header');
  function rebuild(table){
    overlay.replaceChildren();active=table;copy=null;
    if(!table)return;
    const source=table.tHead;if(!source)return;
    copy=table.cloneNode(false);copy.removeAttribute('id');
    copy.append(source.cloneNode(true));overlay.append(copy);
    originalCells=[...source.querySelectorAll('th')];
    clonedCells=[...copy.tHead.querySelectorAll('th')];
    // Progress filters and sort buttons work in the floating header too.
    copy.addEventListener('input',event=>{
      const input=event.target;
      if(!input.matches('input'))return;
      const original=originalCells[clonedCells.indexOf(input.closest('th'))]?.querySelector('input');
      if(original){original.value=input.value;original.dispatchEvent(new Event('input',{bubbles:true}));}
    });
    copy.addEventListener('click',event=>{
      const button=event.target.closest('button');
      if(!button)return;
      const original=originalCells[clonedCells.indexOf(button.closest('th'))]?.querySelector('button');
      if(original)original.click();
    });
  }
  function update(){
    const top=header?header.getBoundingClientRect().bottom:0;
    let selected=null,container=null;
    for(const table of document.querySelectorAll('table')){
      if(!table.tHead || overlay.contains(table))continue;
      const rect=table.getBoundingClientRect();
      if(rect.top < top && rect.bottom > top){
        selected=table;container=table.closest('.scroll')||table;break;
      }
    }
    if(selected!==active)rebuild(selected);
    if(!selected||!copy){overlay.hidden=true;return;}
    const tableRect=selected.getBoundingClientRect();
    const viewportRect=container.getBoundingClientRect();
    const headHeight=selected.tHead.getBoundingClientRect().height;
    const width=container===selected?tableRect.width:viewportRect.width;
    overlay.hidden=false;
    overlay.style.left=viewportRect.left+'px';overlay.style.width=width+'px';
    overlay.style.top=Math.min(top,tableRect.bottom-headHeight)+'px';
    copy.style.width=tableRect.width+'px';
    copy.style.transform='translateX('+(tableRect.left-viewportRect.left)+'px)';
    for(let i=0;i<originalCells.length;i++){
      const width=originalCells[i].getBoundingClientRect().width;
      clonedCells[i].style.boxSizing='border-box';
      clonedCells[i].style.width=width+'px';
      clonedCells[i].style.minWidth=width+'px';
      clonedCells[i].style.maxWidth=width+'px';
    }
  }
  let queued=false;
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;update();});}
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',schedule);
  document.addEventListener('scroll',schedule,{passive:true,capture:true});
  const observer=new MutationObserver(()=>{if(active)rebuild(active);schedule();});
  const progressHead=document.getElementById('progress-head');
  if(progressHead)observer.observe(progressHead,{childList:true,subtree:true});
  const sections=document.getElementById('sections');
  if(sections)observer.observe(sections,{childList:true});
  schedule();
})();
</script>'''
