'use strict';
let orderFieldCatalog = null;
async function orderFields(){
 if(!orderFieldCatalog)orderFieldCatalog=(await api('/api/launch-fields')).fields;
 return orderFieldCatalog;
}
function orderValue(d,field){return field.storage==='base'?d?.[field.key]:d?.identification?.[field.key]}
function orderFieldHtml(field,d){
 const id='order-'+field.key,value=orderValue(d,field)??'';
 const attributes=' id="'+e(id)+'"'+(field.required?' required minlength="2"':'')+
  (field.max_length?' maxlength="'+field.max_length+'"':'')+
  (field.min!==undefined?' min="'+field.min+'"':'')+(field.max!==undefined?' max="'+field.max+'"':'')+
  (field.step?' step="'+field.step+'"':'');
 const input=field.type==='textarea'?'<textarea'+attributes+' rows="3">'+e(value)+'</textarea>':
  '<input'+attributes+' type="'+e(field.type)+'" value="'+e(value)+'" placeholder="'+e(field.placeholder||'À compléter')+'">';
 return '<div class="field '+(['name','notes'].includes(field.key)?'order-field-wide':'')+'"><label for="'+e(id)+'">'+e(field.label)+(field.required?' *':'')+'</label>'+input+'</div>';
}
function orderPayload(fields){
 const payload={identification:{}};
 for(const field of fields){
  const raw=val('order-'+field.key);
  const value=raw===''?null:field.type==='number'?Number(raw):raw;
  (field.storage==='base'?payload:payload.identification)[field.key]=value;
 }
 return payload;
}
async function orderEditor(d=null){
 try{
 const fields=await orderFields(),editing=!!d;
 const companySelect=await clientSelect('order-client-id',d?.client_id||null);
 modal(editing?'Modifier la fiche commande':'Créer un dossier de commande',
  '<p class="modal-desc">Une commande, un dossier. Les informations peuvent être complétées au fur et à mesure.</p>'+
  '<form id="order-form"><div class="order-field-grid">'+fields.map(f=>orderFieldHtml(f,d)).join('')+
  companySelect+(editing?'<div class="field order-field-wide"><label for="order-status">Statut du dossier</label><select id="order-status">'+['À compléter','En cours','En validation','Clôturé'].map(s=>'<option'+(s===d.status?' selected':'')+'>'+e(s)+'</option>').join('')+'</select></div>':'')+
  '</div><p id="order-error" class="error" role="alert" hidden></p><div class="modal-actions"><button type="button" class="secondary" id="order-cancel">Annuler</button><button type="submit" class="primary">'+icon(editing?'check':'plus')+(editing?' Enregistrer':' Créer le dossier')+'</button></div></form>',true);
 bindClientChoice('order');
 overlay.querySelector('#order-cancel').onclick=closeModal;
 overlay.querySelector('#order-form').onsubmit=async event=>{
  event.preventDefault();const button=event.target.querySelector('[type="submit"]');button.disabled=true;
  const error=overlay.querySelector('#order-error');error.hidden=true;
  const payload=orderPayload(fields);payload.client_id=val('order-client-id')||null;if(editing)payload.status=val('order-status');
  try{
   const saved=await api('/api/launches'+(editing?'/'+encodeURIComponent(d.id):''),{method:editing?'PATCH':'POST',body:JSON.stringify(payload)});
   if(editing&&state.detail?.id===saved.id)state.detail={...state.detail,...saved};
   try{await openLaunch(saved.id,editing?state.folder:'jaune')}
   finally{closeModal();toast(editing?'Fiche commande mise à jour':'Dossier de commande créé')}
  }catch(err){if(error.isConnected){error.textContent=err.message;error.hidden=false;button.disabled=false}else showErr(err)}
 };
 }catch(err){showErr(err)}
}
async function orderInformation(){
 try{
 const d=state.detail;if(!d)return;
 const fields=await orderFields();
 modal('Fiche commande','<dl class="launch-information-list">'+fields.map(f=>{
  const raw=orderValue(d,f),value=raw===null||raw===undefined||raw===''?'Non renseigné':f.type==='date'?niceDate(raw):String(raw);
  return '<div><dt>'+e(f.label)+'</dt><dd>'+e(value)+'</dd></div>';
 }).join('')+'</dl>');
 }catch(err){showErr(err)}
}
function orderTable(rows){
 if(!rows.length)return '<div class="empty"><div class="empty-icon">'+icon('folder')+'</div><strong>Aucune commande</strong><p>Créez un dossier et complétez sa fiche progressivement.</p></div>';
 return '<div class="table-scroll"><table><thead><tr><th scope="col">Commande / dossier</th><th scope="col">Client</th><th scope="col">Atelier</th><th scope="col">Statut</th><th scope="col">Livraison prévue</th><th scope="col"><span class="sr-only">Ouvrir</span></th></tr></thead><tbody>'+rows.map(d=>
 '<tr><td><button type="button" class="link order-open" data-order-open="'+e(d.id)+'">'+icon('folder')+'<span><strong>'+e(d.order_ref||d.name)+'</strong>'+(d.order_ref?'<small>'+e(d.name)+'</small>':'')+'</span></button></td><td>'+e(d.client_name||'—')+'</td><td>'+e(d.identification?.workshop||'—')+'</td><td>'+statusTag(d.status)+'</td><td>'+niceDate(d.identification?.delivery_date)+'</td><td><button type="button" class="link" data-order-open="'+e(d.id)+'" aria-label="Ouvrir le dossier '+e(d.name)+'">'+icon('arrow')+'</button></td></tr>'
 ).join('')+'</tbody></table></div>';
}
async function orderListPage(){
 state.view='launches';state.launches=await api('/api/launches');
 if(state.view!=='launches')return;
 mount('<div class="page-heading"><div><h1 class="page-title">Commandes</h1><p class="page-lead">Un dossier par commande, avec ses quatre sous-dossiers.</p></div>'+
 (can('launch.create')?'<button type="button" class="primary" id="create-launch">'+icon('plus')+' Nouveau dossier</button>':'')+'</div>'+
 '<div class="toolbar"><label class="searchbar">'+icon('search')+'<input type="search" id="order-search" aria-label="Rechercher une commande" placeholder="Commande, client, atelier…" value="'+e(state.query)+'"></label><span id="order-count" role="status" aria-live="polite" class="muted small"></span></div><div class="panel" id="orders-table"></div>','Commandes');
 const render=()=>{
  const term=state.query.trim().toLocaleLowerCase('fr');
  const rows=state.launches.filter(d=>[d.name,d.order_ref,d.client_name,d.orli_ref,...Object.values(d.identification||{})].join(' ').toLocaleLowerCase('fr').includes(term));
  const host=app.querySelector('#orders-table');host.innerHTML=orderTable(rows);
  app.querySelector('#order-count').textContent=rows.length+' dossier'+(rows.length===1?'':'s');
  host.querySelectorAll('[data-order-open]').forEach(button=>button.addEventListener('click',()=>openLaunch(button.dataset.orderOpen,'jaune').catch(showErr)));
 };
 app.querySelector('#order-search').addEventListener('input',event=>{state.query=event.target.value;render()});
 app.querySelector('#create-launch')?.addEventListener('click',()=>orderEditor());render();
}
