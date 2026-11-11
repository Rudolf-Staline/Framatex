'use strict';
// Apply labels and focus handling to the existing dynamic screens without a redesign.
let returnFocus=null;
function paginateTables(){
 document.querySelectorAll('table').forEach(table=>{
  if(table.dataset.paginationManaged)return;
  const rows=[...table.tBodies].flatMap(body=>[...body.rows]);if(rows.length<=25)return;
  table.dataset.paginationManaged='1';let page=0;
  const nav=document.createElement('nav');nav.className='table-pagination';nav.setAttribute('aria-label','Pagination du tableau');
  const previous=document.createElement('button'),next=document.createElement('button'),status=document.createElement('span');
  previous.type=next.type='button';previous.textContent='Page précédente';next.textContent='Page suivante';status.setAttribute('role','status');
  const render=()=>{rows.forEach((row,i)=>row.hidden=i<page*25||i>=(page+1)*25);previous.disabled=page===0;next.disabled=(page+1)*25>=rows.length;status.textContent=`Page ${page+1} / ${Math.ceil(rows.length/25)} · ${rows.length} lignes`;};
  previous.onclick=()=>{page--;render()};next.onclick=()=>{page++;render()};nav.append(previous,status,next);table.after(nav);render();
 });
}
function repairAccessibility(){
 paginateTables();
 document.querySelectorAll('label').forEach(label=>{
  if(label.htmlFor||label.querySelector('input,select,textarea'))return;
  const next=label.nextElementSibling;
  if(next?.matches('input,select,textarea')){
   if(!next.id)next.id='field-'+Math.random().toString(36).slice(2);
   label.htmlFor=next.id;
  }
 });
 document.querySelectorAll('.table-scroll,.panel:has(table)').forEach(region=>{
  if(!region.hasAttribute('tabindex')){
   region.tabIndex=0;region.setAttribute('role','region');region.setAttribute('aria-label','Tableau défilant au clavier');
  }
 });
 const dialog=document.querySelector('[role=dialog]');
 if(dialog&&!dialog.dataset.focusManaged){
  dialog.dataset.focusManaged='1';returnFocus=document.activeElement;
  dialog.addEventListener('keydown',event=>{
   if(event.key!=='Tab')return;
   const nodes=[...dialog.querySelectorAll('button,input,select,textarea,a[href],[tabindex="0"]')].filter(n=>!n.disabled&&n.getClientRects().length);
   if(!nodes.length)return;
   if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes[nodes.length-1].focus()}
   else if(!event.shiftKey&&document.activeElement===nodes[nodes.length-1]){event.preventDefault();nodes[0].focus()}
  });
  (dialog.querySelector('input,select,textarea')||dialog.querySelector('button'))?.focus();
 }else if(!dialog&&returnFocus){const target=returnFocus;returnFocus=null;if(target.isConnected)target.focus()}
}
new MutationObserver(repairAccessibility).observe(document.body,{childList:true,subtree:true});
repairAccessibility();
