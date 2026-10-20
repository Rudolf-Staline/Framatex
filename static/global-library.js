'use strict';
// Bibliothèque safran : quatre rubriques permanentes, documents et contrôles sourcés.
const GLOB_COLORS={jaune:'Jaune',rose:'Rose',bleu:'Bleu',vert:'Vert'};
const GLOB_DESCRIPTIONS={jaune:'Technique',rose:'Réception',bleu:'Douane',vert:'Facturation'};
let globalIndex=null,globalFolder='jaune',globalQuery='',globalType='all',globalView='list';
let globalSort='recent',globalLoad=0;
const globalChosenIds=new Set();

async function globalLibraryPage(){
 const load=++globalLoad;
 state.view='dossier';
 const index=await api('/api/dossier-jaune');
 if(load!==globalLoad||state.view!=='dossier')return;
 globalIndex=index;
 const available=new Set(globalIndex.folders.find(f=>f.slug===globalFolder)?.documents.map(d=>d.id)||[]);
 for(const id of globalChosenIds)if(!available.has(id))globalChosenIds.delete(id);
 renderGlobalLibrary();
}

async function openGlobalFolder(slug){
 if(!Object.hasOwn(GLOB_COLORS,slug))return;
 globalFolder=slug;globalQuery='';globalType='all';globalChosenIds.clear();
 state.dossierFolder=slug;state.sidebarDossierOpen=true;
 if(state.view==='dossier'&&globalIndex){renderGlobalLibrary();return}
 await globalLibraryPage();
}
function globalDocumentFormat(doc){
 const name=String(doc.latest?.original_name||'').toLowerCase(),ext=name.split('.').pop();
 const type=String(doc.doc_type||'').toLowerCase();
 if(ext==='pdf'||type.includes('pdf'))return 'pdf';
 if(['doc','docx','odt'].includes(ext)||/word|texte|courrier/.test(type))return 'word';
 if(['xls','xlsx','csv','ods'].includes(ext)||/excel|tableur/.test(type))return 'excel';
 if(['jpg','jpeg','png','webp','gif'].includes(ext)||/image|photo/.test(type))return 'image';
 return 'other';
}
function globalFileIcon(doc){
 const format=globalDocumentFormat(doc);
 return '<span class="saffron-file-icon global-format-'+format+'"><img src="/assets/icons/file-types/'+(({pdf:'pdf-simple',word:'docx',excel:'xlsx',image:'image'})[format]||'empty')+'.svg" alt="" aria-hidden="true"></span>';
}
function globalFileSize(doc){
 const size=doc.latest?.size;
 if(size===undefined||size===null)return '—';
 return sizeText(size);
}
function globalUploader(doc){
 const name=doc.latest?.uploaded_by?.trim();
 if(!name)return '<span class="saffron-muted">Non renseigné</span>';
 const initials=name.split(/\s+/).map(word=>word[0]).slice(0,2).join('').toLocaleUpperCase('fr');
 return '<span class="saffron-uploader"><span class="saffron-uploader-avatar" aria-hidden="true">'+e(initials)+'</span><span class="saffron-uploader-info"><strong title="'+e(name)+'">'+e(name)+'</strong><small>Version '+(doc.latest?.number||'—')+'</small></span></span>';
}
function globalDocumentsVisible(){
 const group=globalIndex?.folders.find(f=>f.slug===globalFolder);
 if(!group?.can_read)return [];
 const term=globalQuery.trim().toLocaleLowerCase('fr');
 const rows=group.documents.filter(d=>(globalType==='all'||globalDocumentFormat(d)===globalType)&&(!term||[d.title,d.doc_type,d.orli_ref||'',...(d.versions||[]).map(v=>v.original_name)].some(v=>String(v).toLocaleLowerCase('fr').includes(term))));
 const date=d=>new Date(d.latest?.created_at||d.created_at).getTime()||0;
 if(globalSort==='name'||globalSort==='name-desc')rows.sort((a,b)=>String(a.latest?.original_name||a.title).localeCompare(String(b.latest?.original_name||b.title),'fr')*(globalSort==='name'?1:-1));
 else rows.sort((a,b)=>(date(b)-date(a))*(globalSort==='oldest'?-1:1));
 return rows;
}
function globalRenderRows(){
 const group=globalIndex.folders.find(f=>f.slug===globalFolder);
 const host=app.querySelector('#global-doc-results'),count=app.querySelector('#global-result-count');
 if(!host)return;
 if(!group.can_read){
  host.innerHTML='<div class="saffron-empty"><strong>Accès à cette rubrique réservé.</strong><p>Votre rôle ne permet pas de consulter ces documents.</p></div>';
  if(count)count.textContent='';globalUpdateSelection();return;
 }
 const rows=globalDocumentsVisible();
 if(count)count.textContent=rows.length+' document'+(rows.length===1?'':'s');
 const nameOrder=globalSort==='name'?'ascending':globalSort==='name-desc'?'descending':'none';
 const dateOrder=globalSort==='recent'?'descending':globalSort==='oldest'?'ascending':'none';
 host.innerHTML=rows.length?'<div class="saffron-table-scroll"><table class="saffron-table"><caption class="sr-only">Documents accessibles du sous-dossier '+GLOB_COLORS[globalFolder]+'</caption>'+
 '<colgroup><col class="register-check-col"><col class="register-name-col"><col class="register-size-col"><col class="register-added-col"><col class="register-updated-col"><col class="register-uploader-col"></colgroup>'+
 '<thead><tr><th scope="col" class="saffron-check-col"><label class="register-checkbox"><input type="checkbox" id="global-select-all" aria-label="Sélectionner tous les fichiers affichés"></label></th><th scope="col" aria-sort="'+nameOrder+'"><button type="button" data-global-sort="name">Nom du fichier '+icon('sort')+'</button></th><th scope="col" class="saffron-size-col">Taille</th><th scope="col" class="saffron-added-col">Ajouté le</th><th scope="col" class="saffron-updated-col" aria-sort="'+dateOrder+'"><button type="button" data-global-sort="date">Mis à jour '+icon('sort')+'</button></th><th scope="col" class="saffron-uploader-col">Déposé par</th></tr></thead>'+
 '<tbody>'+rows.map(d=>'<tr class="'+(globalChosenIds.has(d.id)?'is-selected':'')+'">'+
 '<td class="saffron-check-col"><label class="register-checkbox"><input type="checkbox" data-global-check="'+e(d.id)+'" aria-label="Sélectionner '+e(d.latest?.original_name||d.title)+'"'+(globalChosenIds.has(d.id)?' checked':'')+'></label></td>'+
 '<td><button class="saffron-document-name" type="button" data-global-actions="'+e(d.id)+'" title="Ouvrir '+e(d.latest?.original_name||d.title)+'">'+globalFileIcon(d)+'<span><strong>'+e(d.latest?.original_name||d.title)+'</strong><small class="saffron-file-meta">'+globalFileSize(d)+'</small></span></button></td>'+
 '<td class="saffron-size-col">'+globalFileSize(d)+'</td><td class="saffron-added-col">'+niceDate(d.created_at)+'</td><td class="saffron-updated-col">'+niceDate(d.latest?.created_at||d.created_at)+'</td><td class="saffron-uploader-col">'+globalUploader(d)+'</td></tr>').join('')+'</tbody></table></div>':
 '<div class="saffron-empty"><span class="saffron-empty-icon">'+icon('file')+'</span><strong>'+(globalQuery||globalType!=='all'?'Aucun résultat':'Aucun document pour le moment')+'</strong><p>'+(globalQuery||globalType!=='all'?'Modifiez les filtres pour élargir la recherche.':'Les fichiers déposés apparaîtront ici.')+'</p>'+(group.can_write&&!globalQuery&&globalType==='all'?'<button type="button" class="primary" id="global-empty-upload">'+icon('plus')+' Déposer un document</button>':'')+'</div>';
 host.querySelector('#global-empty-upload')?.addEventListener('click',globalUploadModal);
 host.querySelector('#global-select-all')?.addEventListener('change',event=>{
  rows.forEach(d=>event.target.checked?globalChosenIds.add(d.id):globalChosenIds.delete(d.id));globalUpdateSelection();
 });
 host.querySelectorAll('[data-global-check]').forEach(input=>input.addEventListener('change',()=>{
  if(input.checked)globalChosenIds.add(input.dataset.globalCheck);else globalChosenIds.delete(input.dataset.globalCheck);
  globalUpdateSelection();
 }));
 host.querySelectorAll('[data-global-actions]').forEach(button=>button.addEventListener('click',()=>globalDocumentActions(button.dataset.globalActions)));
 host.querySelectorAll('[data-global-sort]').forEach(button=>button.addEventListener('click',()=>{
  globalSort=button.dataset.globalSort==='name'?(globalSort==='name'?'name-desc':'name'):(globalSort==='recent'?'oldest':'recent');
  globalRenderRows();app.querySelector('[data-global-sort="'+button.dataset.globalSort+'"]')?.focus();
 }));
 globalUpdateSelection();
}
function globalSelectedDocuments(){
 const folder=globalIndex?.folders.find(f=>f.slug===globalFolder);
 return folder?.can_read?folder.documents.filter(d=>globalChosenIds.has(d.id)):[];
}
function globalUpdateSelection(){
 const selected=globalSelectedDocuments(),bar=app.querySelector('#global-selection-actions');
 if(bar)bar.hidden=!selected.length;
 const count=app.querySelector('#global-selected-count');if(count)count.textContent=selected.length+' fichier'+(selected.length===1?' sélectionné':'s sélectionnés');
 const host=app.querySelector('#global-doc-results');if(!host)return;
 host.querySelectorAll('[data-global-check]').forEach(input=>{
  input.checked=globalChosenIds.has(input.dataset.globalCheck);
  input.closest('tr')?.classList.toggle('is-selected',input.checked);
 });
 const all=host.querySelector('#global-select-all'),visible=globalDocumentsVisible();
 if(all){const n=visible.filter(d=>globalChosenIds.has(d.id)).length;all.checked=visible.length>0&&n===visible.length;all.indeterminate=n>0&&n<visible.length}
}
async function globalDownloadSelection(){
 const docs=globalSelectedDocuments(),button=app.querySelector('#global-download-selection');
 if(button)button.disabled=true;
 try{for(const doc of docs)await globalDownload(doc.id,doc.latest?.number||1)}finally{if(button)button.disabled=false}
}
function globalRecordIssue(id){
 const doc=globalIndex.folders.flatMap(f=>f.documents).find(d=>d.id===id);
 if(!doc||!can('document.read',doc.folder)||!can('rex.read',doc.folder)||!can('rex.write',doc.folder))return;
 return openRexEditor(null,{folder:doc.folder,orli_ref:doc.orli_ref||'',document_id:doc.id});
}
function globalDocumentActions(id){
 const doc=globalIndex.folders.flatMap(f=>f.documents).find(d=>d.id===id);if(!doc)return;
 const writable=can('document.write',doc.folder);
 const writableMemory=can('document.read',doc.folder)&&can('rex.read',doc.folder)&&can('rex.write',doc.folder);
 modal('Actions du document','<div class="saffron-document-actions"><p class="saffron-action-title">'+e(doc.title)+'</p><p class="register-document-meta">'+e(doc.orli_ref||'ORLI : Non renseignée')+' · v'+(doc.latest?.number||'—')+'</p><button type="button" class="secondary" id="global-action-download">'+icon('download')+' Télécharger la version actuelle</button>'+
 (writable?'<button type="button" class="secondary" id="global-action-reference">'+icon('pencil')+' Modifier la référence ORLI</button>':'')+
 (writableMemory?'<button type="button" class="secondary" id="global-action-rex">'+icon('chat')+' Consigner un problème</button>':'')+
 '<section class="saffron-version-list" aria-labelledby="global-version-heading"><h3 id="global-version-heading">'+icon('clock')+' Historique des versions</h3>'+doc.versions.slice().reverse().map(v=>'<button class="link" type="button" data-global-version="'+v.number+'"><span>v'+v.number+' · '+e(v.original_name)+'<small>'+niceDate(v.created_at)+'</small></span>'+icon('download')+'</button>').join('')+'</section></div>');
 overlay.querySelector('#global-action-download').onclick=()=>globalDownload(doc.id,doc.latest?.number||1);
 overlay.querySelector('#global-action-rex')?.addEventListener('click',()=>globalRecordIssue(doc.id)?.catch(showErr));
 overlay.querySelector('#global-action-reference')?.addEventListener('click',()=>globalEditReference(doc.id));
 overlay.querySelectorAll('[data-global-version]').forEach(button=>button.addEventListener('click',()=>globalDownload(doc.id,Number(button.dataset.globalVersion))));
 if(typeof knowledgeDialogFocus==='function')knowledgeDialogFocus();
}
function renderGlobalLibrary(){
 state.dossierFolder=globalFolder;
 const folder=globalIndex.folders.find(f=>f.slug===globalFolder);
 mount('<div class="global-library saffron-workspace document-register">'+
 '<section class="saffron-library-main"><div class="register-folder-bar">'+
 '<nav class="saffron-folders" role="tablist" aria-label="Les quatre sous-dossiers">'+globalIndex.folders.map(f=>'<button type="button" role="tab" id="folder-tab-'+f.slug+'" data-global-folder="'+f.slug+'" aria-selected="'+(f.slug===globalFolder)+'" aria-controls="global-document-panel" aria-label="Sous-dossier '+GLOB_COLORS[f.slug]+' · '+e(f.label||GLOB_DESCRIPTIONS[f.slug])+'" tabindex="'+(f.slug===globalFolder?'0':'-1')+'" class="saffron-folder-tab '+f.slug+' '+(f.slug===globalFolder?'selected':'')+'"><span class="register-folder-icon '+f.slug+'">'+icon('folder')+'</span>'+GLOB_COLORS[f.slug]+(!f.can_read?'<span class="sr-only"> · Accès restreint</span>':'')+'</button>').join('')+'</nav>'+(folder.can_write?'<button type="button" class="primary register-upload" id="global-upload">'+icon('upload')+' Déposer un document</button>':'')+'</div>'+
 '<section id="global-document-panel" class="saffron-document-panel" role="tabpanel" aria-labelledby="folder-tab-'+globalFolder+'"><div class="saffron-document-toolbar"><label class="saffron-document-search">'+icon('search')+'<input type="search" id="global-search-input" aria-label="Rechercher dans ce sous-dossier" placeholder="Rechercher dans ce dossier…" value="'+e(globalQuery)+'" '+(folder.can_read?'':'disabled')+'></label>'+
 '<label class="saffron-type-filter"><span class="sr-only">Type de document</span><select id="global-type-filter" aria-label="Filtrer par type"><option value="all">Tous les types</option><option value="pdf">PDF</option><option value="word">Word</option><option value="excel">Excel</option><option value="image">Image</option><option value="other">Autres</option></select></label></div><span class="sr-only" id="global-result-count" role="status" aria-live="polite"></span><div id="global-doc-results"></div><div id="global-selection-actions" class="register-selection-bar" hidden><span id="global-selected-count" role="status" aria-live="polite"></span><button type="button" class="secondary" id="global-download-selection">'+icon('download')+' Télécharger la sélection</button><button type="button" class="link" id="global-clear-selection">Désélectionner</button></div></section></section></div>','Dossier Jaune');
 const typeSelect=app.querySelector('#global-type-filter');if(typeSelect)typeSelect.value=globalType;
 app.querySelector('#global-type-filter')?.addEventListener('change',event=>{globalType=event.target.value;globalRenderRows()});
 app.querySelectorAll('[data-global-folder]').forEach(button=>button.onclick=()=>openGlobalFolder(button.dataset.globalFolder).catch(showErr));
 app.querySelector('.saffron-folders')?.addEventListener('keydown',event=>{
  if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
  const tabs=[...app.querySelectorAll('[data-global-folder]')],current=tabs.indexOf(document.activeElement);if(current<0)return;
  event.preventDefault();
  const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(current+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
  openGlobalFolder(tabs[next].dataset.globalFolder).then(()=>app.querySelector('[data-global-folder="'+tabs[next].dataset.globalFolder+'"]')?.focus()).catch(showErr);
 });
 app.querySelector('#global-search-input')?.addEventListener('input',event=>{globalQuery=event.target.value;globalRenderRows()});
 app.querySelector('#global-upload')?.addEventListener('click',globalUploadModal);
 app.querySelector('#global-download-selection')?.addEventListener('click',globalDownloadSelection);
 app.querySelector('#global-clear-selection')?.addEventListener('click',()=>{globalChosenIds.clear();globalUpdateSelection()});
 globalRenderRows();
}

async function globalDownload(id,v){
 try{
 const response=await api('/api/documents/'+encodeURIComponent(id)+'/versions/'+v+'/download');
 const d=globalIndex.folders.flatMap(f=>f.documents).find(x=>x.id===id);
 const name=d?.versions?.find(x=>x.number===v)?.original_name||'document';
 const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');
 a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(err){showErr(err)}
}
function globalUploadModal(){
 const group=globalIndex.folders.find(f=>f.slug===globalFolder);
 if(!group.can_write)return;
 modal('Déposer dans '+GLOB_COLORS[globalFolder],`<form id="global-upload-form">
  <div class="field"><label for="g-title">Nom du document *</label><input id="g-title" required maxlength="220"></div>
  <div class="field"><label for="g-type">Type</label><input id="g-type" maxlength="100" value="Autre"></div>
  <div class="field"><label for="g-orli">Référence lancement / ORLI (facultative)</label><input id="g-orli" maxlength="100"></div>
  <div class="field"><label for="g-file">Fichier *</label><input id="g-file" type="file" required accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.txt,.eml"></div>
  <div class="modal-actions"><button type="button" class="secondary" id="g-cancel">Annuler</button><button type="submit" class="primary">Déposer</button></div></form>`);
 if(typeof knowledgeDialogFocus==='function')knowledgeDialogFocus();
 overlay.querySelector('#g-cancel').onclick=closeModal;
 overlay.querySelector('#global-upload-form').onsubmit=async evt=>{
   evt.preventDefault();const file=overlay.querySelector('#g-file').files[0];if(!file)return;
   const button=evt.target.querySelector('[type=submit]');button.disabled=true;
   const body=new FormData();body.set('folder',globalFolder);body.set('title',val('g-title'));
   body.set('doc_type',val('g-type')||'Autre');body.set('orli_ref',val('g-orli'));body.set('file',file);
   try{await api('/api/dossier-jaune/documents',{method:'POST',body});
     closeModal();toast('Document enregistré');await globalLibraryPage();
   }catch(err){showErr(err);button.disabled=false}
 };
}
function globalEditReference(id){
 const d=globalIndex.folders.flatMap(f=>f.documents).find(x=>x.id===id);
 if(!d||!can('document.write',d.folder))return;
 modal('Référence de lancement',`<form id="g-edit-form"><p class="modal-desc">${e(d.title)} · Cette modification ne déplace pas le document.</p>
 <div class="field"><label for="g-edit-orli">Référence ORLI (facultative)</label><input id="g-edit-orli" maxlength="100" value="${e(d.orli_ref||'')}"></div>
 <div class="modal-actions"><button type="button" class="secondary" id="g-edit-cancel">Annuler</button><button type="submit" class="primary">Enregistrer</button></div></form>`);
 if(typeof knowledgeDialogFocus==='function')knowledgeDialogFocus();
 overlay.querySelector('#g-edit-cancel').onclick=closeModal;
 overlay.querySelector('#g-edit-form').onsubmit=async evt=>{
 evt.preventDefault();
 try{await api('/api/dossier-jaune/documents/'+encodeURIComponent(id)+'/reference',{
   method:'PATCH',body:JSON.stringify({orli_ref:val('g-edit-orli')})});
   closeModal();toast('Référence mise à jour');await globalLibraryPage();
 }catch(err){showErr(err)}
 };
}
