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
  '<form id="order-form"><div class="order-field-grid">'+fields.filter(f=>editing||['name','order_ref'].includes(f.key)).map(f=>orderFieldHtml(f,d)).join('')+
  (editing?companySelect:'')+(editing?'<div class="field order-field-wide"><label for="order-status">Statut du dossier</label><select id="order-status">'+['À compléter','En cours','En validation','Clôturé'].map(s=>'<option'+(s===d.status?' selected':'')+'>'+e(s)+'</option>').join('')+'</select></div>':'')+
  '</div>'+(!editing?'<details class="optional-fields"><summary>Ajouter les informations de la commande <span class="muted">· facultatif</span></summary><div class="order-field-grid">'+companySelect+fields.filter(f=>!['name','order_ref'].includes(f.key)).map(f=>orderFieldHtml(f,d)).join('')+'</div></details><div class="form-note">'+icon('folder')+' Les quatre sous-dossiers sont créés automatiquement.</div>':'')+'<p id="order-error" class="error" role="alert" hidden></p><div class="modal-actions"><button type="button" class="secondary" id="order-cancel">Annuler</button><button type="submit" class="primary">'+icon(editing?'check':'plus')+(editing?' Enregistrer':' Créer le dossier')+'</button></div></form>',true);
 bindClientChoice('order');
 overlay.querySelector('#order-cancel').onclick=closeModal;
 overlay.querySelector('#order-form').addEventListener('invalid',event=>{const section=event.target.closest('details');if(section)section.open=true},true);
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
function normalizeOrderText(text){return String(text||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('fr')}
function orderDocumentHint(d){
 const c=d.document_check;if(!c)return '';
 if(!c.configured)return '<small class="order-document-hint">Pièces attendues à définir</small>';
 const text=c.missing?c.missing+' pièce(s) manquante(s)':c.pending_validation?c.pending_validation+' pièce(s) à valider':'Aucune pièce exigible manquante';
 return '<small class="order-document-hint '+(c.missing?'has-missing':'')+'">'+e(text)+(c.partial_visibility?' · bilan partiel':'')+'</small>';
}
function orderTable(rows){
 if(!rows.length)return '<div class="empty"><div class="empty-icon">'+icon('search')+'</div><strong>Aucun dossier à afficher</strong><p>Essayez une autre recherche ou créez votre premier dossier de commande.</p></div>';
 return '<div class="table-scroll"><table><thead><tr><th scope="col">Commande / dossier</th><th scope="col">Client</th><th scope="col">Atelier</th><th scope="col">Statut</th><th scope="col"><span class="sr-only">Ouvrir</span></th></tr></thead><tbody>'+rows.map(d=>
 '<tr><td><button type="button" class="link order-open" data-order-open="'+e(d.id)+'"><span class="order-folder-mark">'+icon('folder')+'</span><span><strong>'+e(d.name)+'</strong><small>'+e(d.order_ref||'Référence à renseigner')+'</small>'+orderDocumentHint(d)+'</span></button></td><td><span class="client-cell">'+(d.client_name?'<span class="client-initial" aria-hidden="true">'+e(d.client_name.slice(0,2).toUpperCase())+'</span>':'')+e(d.client_name||'—')+'</span></td><td>'+e(d.identification?.workshop||'—')+'</td><td>'+statusTag(d.status)+'</td><td><button type="button" class="link" data-order-open="'+e(d.id)+'" aria-label="Ouvrir le dossier '+e(d.name)+'">'+icon('arrow')+'</button></td></tr>'
 ).join('')+'</tbody></table></div>';
}
function orderCards(rows){
 if(!rows.length)return orderTable(rows);
 return '<div class="order-card-grid">'+rows.map(d=>'<article class="order-card"><div class="order-card-top"><span class="order-folder-mark">'+icon('folder')+'</span>'+statusTag(d.status)+'</div><button class="link order-open" data-order-open="'+e(d.id)+'"><span><strong>'+e(d.name)+'</strong><small>'+e(d.order_ref||'Référence à renseigner')+'</small>'+orderDocumentHint(d)+'</span></button><p>'+e(d.client_name||'Client à renseigner')+'</p><small>Livraison · '+niceDate(d.identification?.delivery_date)+'</small></article>').join('')+'</div>';
}
async function orderListPage(){
 state.view='launches';state.launches=await api('/api/launches');
 if(state.view!=='launches')return;
 let selected='',page=1;const pageSize=10;let layout=state.orderLayout||'list';
 const baseRows=()=>state.launches.filter(d=>!state.clientFilter||d.client_id===state.clientFilter.id);
 const statuses=[['','Tous les dossiers'],['En cours','En cours'],['À compléter','À compléter'],['En validation','En validation'],['Clôturé','Clôturés']];
 mount('<div class="page-heading"><div><h1 class="page-title">Dossiers Jaunes<span class="heading-count">'+baseRows().length+'</span></h1><p class="page-lead">Vos dossiers de fabrication, au même endroit.</p></div>'+
 (can('launch.create')?'<button type="button" class="primary" id="create-launch">'+icon('plus')+' Nouveau dossier</button>':'')+'</div>'+
 '<section class="order-workspace" aria-label="Liste des dossiers jaunes"><nav class="order-status-tabs" aria-label="Filtrer par statut">'+statuses.map(([value,label])=>'<button type="button" data-order-status="'+e(value)+'" aria-pressed="'+(!value)+'">'+label+'<small>'+baseRows().filter(d=>!value||d.status===value).length+'</small></button>').join('')+'</nav>'+
 '<div class="order-toolbar"><label class="searchbar">'+icon('search')+'<input type="search" id="order-search" aria-label="Rechercher une commande" placeholder="Rechercher une commande, un client…" value="'+e(state.query)+'"></label><select id="order-sort" aria-label="Trier les dossiers"><option value="recent">Dernière mise à jour</option><option value="delivery">Livraison prévue</option><option value="name">Nom du dossier</option></select><div class="view-switch" aria-label="Affichage"><button type="button" data-layout="list" aria-label="Vue liste" aria-pressed="'+(layout==='list')+'">'+icon('book')+'</button><button type="button" data-layout="grid" aria-label="Vue grille" aria-pressed="'+(layout==='grid')+'">'+icon('grid')+'</button></div></div>'+
 (state.clientFilter?'<div class="filter-chip"><span class="tag">Client : '+e(state.clientFilter.name)+'</span><button type="button" class="link" id="clear-client-filter">'+icon('x')+' Afficher tous les dossiers jaunes</button></div>':'')+
 '<div id="orders-table"></div><footer class="table-footer"><span id="order-count" role="status" aria-live="polite"></span><div class="pagination"><button class="secondary tiny" id="orders-prev" aria-label="Page précédente">'+icon('back')+'</button><span id="order-page"></span><button class="secondary tiny" id="orders-next" aria-label="Page suivante">'+icon('arrow')+'</button></div></footer></section>','Dossiers Jaunes');
 const render=()=>{
  const term=normalizeOrderText(state.query.trim());
  const rows=baseRows().filter(d=>(!selected||d.status===selected)&&normalizeOrderText([d.name,d.order_ref,d.client_name,d.orli_ref,...Object.values(d.identification||{})].join(' ')).includes(term));
  const sort=app.querySelector('#order-sort').value;
  rows.sort((a,b)=>sort==='name'?a.name.localeCompare(b.name,'fr'):sort==='delivery'?(a.identification?.delivery_date||'9999').localeCompare(b.identification?.delivery_date||'9999'):(b.updated_at||b.created_at||'').localeCompare(a.updated_at||a.created_at||''));
  const pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages);
  const host=app.querySelector('#orders-table');host.innerHTML=(layout==='grid'?orderCards:orderTable)(rows.slice((page-1)*pageSize,page*pageSize));
  app.querySelector('#order-count').textContent=rows.length?((page-1)*pageSize+1)+'–'+Math.min(page*pageSize,rows.length)+' sur '+rows.length+' dossier'+(rows.length===1?'':'s'):'Aucun résultat';
  app.querySelector('#order-page').textContent=page+' / '+pages;
  app.querySelector('#orders-prev').disabled=page===1;app.querySelector('#orders-next').disabled=page===pages;
  host.querySelectorAll('[data-order-open]').forEach(button=>button.addEventListener('click',()=>openLaunch(button.dataset.orderOpen,'jaune').catch(showErr)));
 };
 app.querySelector('#order-search').addEventListener('input',event=>{state.query=event.target.value;page=1;render()});
 app.querySelector('#order-sort').addEventListener('change',()=>{page=1;render()});
 app.querySelectorAll('[data-order-status]').forEach(button=>button.onclick=()=>{selected=button.dataset.orderStatus;page=1;app.querySelectorAll('[data-order-status]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render()});
 app.querySelectorAll('[data-layout]').forEach(button=>button.onclick=()=>{layout=state.orderLayout=button.dataset.layout;app.querySelectorAll('[data-layout]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render()});
 app.querySelector('#orders-prev').onclick=()=>{page--;render()};app.querySelector('#orders-next').onclick=()=>{page++;render()};
 app.querySelector('#clear-client-filter')?.addEventListener('click',()=>{state.clientFilter=null;state.query='';orderListPage().catch(showErr)});
 app.querySelector('#create-launch')?.addEventListener('click',()=>orderEditor());render();
}
async function openCommandSearch(){
 if(!state.me||state.me.client_account||!can('launch.read'))return;
 modal('Retrouver un dossier','<label class="searchbar">'+icon('search')+'<input id="command-search" type="search" aria-label="Rechercher un dossier" placeholder="Nom, référence, client, atelier…" autocomplete="off"></label><div class="command-results" id="command-results" role="region" aria-label="Résultats"><p class="muted small" role="status">Chargement des dossiers…</p></div>');
 const host=overlay.querySelector('#command-results'),input=overlay.querySelector('#command-search');
 try{
 const rows=await api('/api/launches');if(!host.isConnected)return;
 const draw=()=>{const term=normalizeOrderText(input.value);const matches=rows.filter(d=>normalizeOrderText([d.name,d.order_ref,d.client_name,...Object.values(d.identification||{})].join(' ')).includes(term)).slice(0,12);host.innerHTML=matches.length?matches.map(d=>'<button type="button" data-command="'+e(d.id)+'">'+icon('folder')+'<span><strong>'+e(d.name)+'</strong><small>'+e([d.order_ref,d.client_name].filter(Boolean).join(' · ')||'Dossier de commande')+'</small></span>'+icon('arrow')+'</button>').join(''):'<p class="muted small" role="status">Aucun dossier trouvé.</p>';host.querySelectorAll('[data-command]').forEach(button=>button.onclick=()=>{closeModal();openLaunch(button.dataset.command,'jaune').catch(showErr)})};
 input.addEventListener('input',draw);input.addEventListener('keydown',event=>{if(event.key==='ArrowDown'){event.preventDefault();host.querySelector('button')?.focus()}if(event.key==='Enter'){event.preventDefault();host.querySelector('button')?.click()}});draw();
 }catch(err){if(host.isConnected)host.textContent=err.message}
}
document.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'&&state.me&&!state.me.client_account){event.preventDefault();if(!overlay.querySelector('[role="dialog"]'))openCommandSearch().catch(showErr)}});
