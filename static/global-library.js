'use strict';
// Bibliothèque safran : quatre rubriques permanentes, documents et contrôles sourcés.
const GLOB_COLORS={jaune:'Jaune',rose:'Rose',bleu:'Bleu',vert:'Vert'};
const GLOB_DESCRIPTIONS={jaune:'Technique',rose:'Réception',bleu:'Douane',vert:'Facturation'};
let globalIndex=null,globalFolder='jaune',globalQuery='',globalType='all',globalView='list';
let globalControlReport=null,globalControlStatus='loading',globalSelectedId=null,globalSort='recent',globalLoad=0;

async function globalLibraryPage(){
 const load=++globalLoad;
 state.view='dossier';
 const index=await api('/api/dossier-jaune');
 if(load!==globalLoad||state.view!=='dossier')return;
 globalIndex=index;globalControlReport=null;globalControlStatus='loading';
 renderGlobalLibrary();
 try{
  const report=await api('/api/dossier-jaune/controls');
  if(load!==globalLoad||state.view!=='dossier')return;
  globalControlReport=report;globalControlStatus='ready';renderGlobalContext();
 }catch(error){
  if(load!==globalLoad||state.view!=='dossier'||!state.me)return;
  globalControlStatus='error';renderGlobalContext();
 }
}
async function openGlobalFolder(slug){
 if(!Object.hasOwn(GLOB_COLORS,slug))return;
 globalFolder=slug;globalQuery='';globalType='all';globalSelectedId=null;
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
 return '<span class="saffron-file-icon global-format-'+format+'">'+icon(({pdf:'file-pdf',word:'file-doc',excel:'file-xls',image:'file-image'})[format]||'file')+'</span>';
}
function globalDocumentsVisible(){
 const group=globalIndex?.folders.find(f=>f.slug===globalFolder);
 if(!group?.can_read)return [];
 const term=globalQuery.trim().toLocaleLowerCase('fr');
 const rows=group.documents.filter(d=>(globalType==='all'||globalDocumentFormat(d)===globalType)&&(!term||[d.title,d.doc_type,d.orli_ref||'',...(d.versions||[]).map(v=>v.original_name)].some(v=>String(v).toLocaleLowerCase('fr').includes(term))));
 const date=d=>new Date(d.latest?.created_at||d.created_at).getTime()||0;
 if(globalSort==='name'||globalSort==='name-desc')rows.sort((a,b)=>a.title.localeCompare(b.title,'fr')*(globalSort==='name'?1:-1));
 else rows.sort((a,b)=>(date(b)-date(a))*(globalSort==='oldest'?-1:1));
 return rows;
}
function globalRenderRows(){
 const group=globalIndex.folders.find(f=>f.slug===globalFolder);
 const host=app.querySelector('#global-doc-results'),count=app.querySelector('#global-result-count');
 if(!host)return;
 if(!group.can_read){
  host.innerHTML='<div class="saffron-empty"><strong>Accès à cette rubrique réservé.</strong><p>Votre rôle ne permet pas de consulter ces documents.</p></div>';
  if(count)count.textContent='';renderGlobalContext();return;
 }
 const rows=globalDocumentsVisible();
 if(!rows.some(d=>d.id===globalSelectedId))globalSelectedId=rows[0]?.id||null;
 if(count)count.textContent=rows.length+' document'+(rows.length===1?'':'s');
 const nameOrder=globalSort==='name'?'ascending':globalSort==='name-desc'?'descending':'none';
 const dateOrder=globalSort==='recent'?'descending':globalSort==='oldest'?'ascending':'none';
 host.innerHTML=rows.length?'<div class="saffron-table-scroll"><table class="saffron-table"><caption class="sr-only">Documents accessibles du sous-dossier '+GLOB_COLORS[globalFolder]+'</caption>'+
 '<thead><tr><th scope="col" aria-sort="'+nameOrder+'"><button type="button" data-global-sort="name">Nom '+icon('sort')+'</button></th><th scope="col" class="saffron-type-col">Type</th><th scope="col" class="saffron-orli-col">Référence ORLI</th><th scope="col">Version</th><th scope="col" class="saffron-date-col" aria-sort="'+dateOrder+'"><button type="button" data-global-sort="date">Modifié '+icon('sort')+'</button></th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead>'+
 '<tbody>'+rows.map(d=>'<tr class="'+(d.id===globalSelectedId?'is-selected':'')+'">'+
 '<td><button class="saffron-document-name" type="button" data-global-select="'+e(d.id)+'" aria-pressed="'+(d.id===globalSelectedId)+'" title="Afficher les contrôles de '+e(d.title)+'">'+globalFileIcon(d)+'<span><strong>'+e(d.title)+'</strong><small class="saffron-mobile-meta">'+e(d.doc_type||'Autre')+(d.orli_ref?' · '+e(d.orli_ref):'')+'</small></span></button></td>'+
 '<td class="saffron-type-col">'+e(d.doc_type||'Autre')+'</td><td class="saffron-orli-col">'+(d.orli_ref?e(d.orli_ref):'<span class="saffron-muted">Non renseignée</span>')+'</td>'+
 '<td><span class="global-version-pill">v'+(d.latest?.number||'—')+'</span></td><td class="saffron-date-col">'+niceDate(d.latest?.created_at||d.created_at)+'</td>'+
 '<td class="saffron-row-actions"><button type="button" class="saffron-more" data-global-actions="'+e(d.id)+'" aria-label="Actions pour '+e(d.title)+'">'+icon('more')+'</button></td></tr>').join('')+'</tbody></table></div>':
 '<div class="saffron-empty"><span class="saffron-empty-icon">'+icon('file')+'</span><strong>'+(globalQuery||globalType!=='all'?'Aucun résultat':'Aucun document pour le moment')+'</strong><p>'+(globalQuery||globalType!=='all'?'Modifiez les filtres pour élargir la recherche.':'Les fichiers déposés apparaîtront ici.')+'</p>'+(group.can_write&&!globalQuery&&globalType==='all'?'<button type="button" class="primary" id="global-empty-upload">'+icon('plus')+' Déposer un document</button>':'')+'</div>';
 host.querySelector('#global-empty-upload')?.addEventListener('click',globalUploadModal);
 host.querySelectorAll('[data-global-select]').forEach(button=>button.addEventListener('click',()=>{
  globalSelectedId=button.dataset.globalSelect;
  host.querySelectorAll('[data-global-select]').forEach(item=>{
   const selected=item.dataset.globalSelect===globalSelectedId;
   item.setAttribute('aria-pressed',String(selected));item.closest('tr').classList.toggle('is-selected',selected);
  });
  renderGlobalContext();
 }));
 host.querySelectorAll('[data-global-actions]').forEach(button=>button.addEventListener('click',()=>globalDocumentActions(button.dataset.globalActions)));
 host.querySelectorAll('[data-global-sort]').forEach(button=>button.addEventListener('click',()=>{
  globalSort=button.dataset.globalSort==='name'?(globalSort==='name'?'name-desc':'name'):(globalSort==='recent'?'oldest':'recent');
  globalRenderRows();app.querySelector('[data-global-sort="'+button.dataset.globalSort+'"]')?.focus();
 }));
 renderGlobalContext();
}
function globalRef(value){return String(value||'').trim().replace(/\s+/g,' ').toLocaleLowerCase('fr')}
function globalNumber(value){
 const [integer,decimal]=String(value).split('.');
 return integer.replace(/\B(?=(\d{3})+(?!\d))/g,'\u202f')+(decimal?','+decimal:'');
}
function globalContextIssues(){
 if(globalControlStatus!=='ready'||!globalControlReport)return [];
 const group=globalIndex.folders.find(f=>f.slug===globalFolder);
 if(!group?.can_read)return [];
 const selected=group.documents.find(d=>d.id===globalSelectedId);
 const refs=new Set((selected?.orli_ref?[selected.orli_ref]:globalDocumentsVisible().map(d=>d.orli_ref)).filter(Boolean).map(globalRef));
 const issues=[];
 for(const row of globalControlReport.comparisons||[]){
  if(row.status==='consistent')continue;
  if(!refs.has(globalRef(row.orli_ref)))continue;
  if(!(row.folders||[]).includes(globalFolder)&&!refs.has(globalRef(row.orli_ref)))continue;
  const pair=row.pair||[],numeric=pair.length===2&&pair.every(p=>p.value!==null&&p.value!==undefined);
  const description=numeric?pair.map(p=>globalNumber(p.value)).join(' / ')+(pair[0].unit===pair[1].unit?' '+pair[0].unit:' · unités différentes'):row.reason;
  issues.push({title:row.status==='difference'?'Écart à examiner':row.status==='unit_mismatch'?'Unités différentes':row.status==='ambiguous'?'Sources à préciser':'Valeur ou pièce à compléter',description,detail:row.name,tab:'consistency',folder:(row.folders||[]).includes(globalFolder)?globalFolder:(row.folders||[])[0],rank:row.status==='difference'||row.status==='unit_mismatch'?0:2});
 }
 for(const row of globalControlReport.expectations||[]){
  if(row.status!=='missing')continue;
  if(row.orli_ref&&!refs.has(globalRef(row.orli_ref)))continue;
  if(row.folder!==globalFolder&&(!row.orli_ref||!refs.has(globalRef(row.orli_ref))))continue;
  issues.push({title:row.title+' manquant',description:row.orli_ref||GLOB_COLORS[row.folder],detail:row.document_type,tab:'expectations',folder:row.folder,rank:1});
 }
 return issues.sort((a,b)=>a.rank-b.rank);
}
function renderGlobalContext(){
 const host=app.querySelector('#global-context-issues');if(!host)return;
 const group=globalIndex?.folders.find(f=>f.slug===globalFolder);
 const issues=globalContextIssues(),visible=issues.slice(0,2);
 if(!group?.can_read){host.innerHTML='<p class="saffron-context-note">Les contrôles respectent les droits d’accès à cette rubrique.</p>';return}
 if(globalControlStatus==='loading')host.innerHTML='<p class="saffron-context-note" role="status">Lecture des vérifications…</p>';
 else if(globalControlStatus==='error')host.innerHTML='<p class="saffron-context-note" role="status">Les vérifications sont momentanément indisponibles.</p>';
 else if(!issues.length)host.innerHTML='<p class="saffron-context-note">'+((globalControlReport?.rules?.length||globalControlReport?.expectations?.length)?'Aucun point à examiner pour les documents affichés.':'Aucune règle de vérification configurée pour ces documents.')+'</p>';
 else host.innerHTML=visible.map((issue,i)=>'<button class="saffron-context-issue" type="button" data-global-issue="'+i+'" title="'+e(issue.detail)+'"><span class="saffron-warning">'+icon('warning')+'</span><span><strong>'+e(issue.title)+'</strong><small>'+e(issue.description)+'</small></span></button>').join('')+(issues.length>2?'<p class="saffron-context-note">'+(issues.length-2)+' autre'+(issues.length>3?'s':'')+' point'+(issues.length>3?'s':'')+' à examiner</p>':'');
 host.querySelectorAll('[data-global-issue]').forEach(button=>button.addEventListener('click',()=>{
  const issue=visible[+button.dataset.globalIssue];
  controlState.tab=issue.tab;controlState.folder=issue.folder||'';navigate('controls');
 }));
}
function globalDocumentActions(id){
 const doc=globalIndex.folders.flatMap(f=>f.documents).find(d=>d.id===id);if(!doc)return;
 const writable=can('document.write',doc.folder);
 modal('Actions du document','<div class="saffron-document-actions"><p class="saffron-action-title">'+e(doc.title)+'</p><button type="button" class="secondary" id="global-action-download">'+icon('download')+' Télécharger la version actuelle</button>'+
 (writable?'<button type="button" class="secondary" id="global-action-reference">'+icon('pencil')+' Modifier la référence ORLI</button>':'')+
 '<section class="saffron-version-list" aria-labelledby="global-version-heading"><h3 id="global-version-heading">Historique des versions</h3>'+doc.versions.slice().reverse().map(v=>'<button class="link" type="button" data-global-version="'+v.number+'"><span>v'+v.number+' · '+e(v.original_name)+'<small>'+niceDate(v.created_at)+'</small></span>'+icon('download')+'</button>').join('')+'</section></div>');
 overlay.querySelector('#global-action-download').onclick=()=>globalDownload(doc.id,doc.latest?.number||1);
 overlay.querySelector('#global-action-reference')?.addEventListener('click',()=>globalEditReference(doc.id));
 overlay.querySelectorAll('[data-global-version]').forEach(button=>button.addEventListener('click',()=>globalDownload(doc.id,Number(button.dataset.globalVersion))));
 if(typeof knowledgeDialogFocus==='function')knowledgeDialogFocus();
}
function renderGlobalLibrary(){
 state.dossierFolder=globalFolder;
 const folder=globalIndex.folders.find(f=>f.slug===globalFolder);
 const writableMemory=can('document.read',globalFolder)&&can('rex.read',globalFolder)&&can('rex.write',globalFolder);
 mount('<div class="global-library saffron-workspace">'+
 '<section class="saffron-library-main"><nav class="global-breadcrumb" aria-label="Fil d’Ariane"><span>Espace documentaire</span><span aria-hidden="true">/</span><strong>'+GLOB_COLORS[globalFolder]+'</strong></nav>'+
 '<header class="saffron-page-head"><h1>'+e(folder.label||GLOB_DESCRIPTIONS[globalFolder])+'</h1><p>Documents du sous-dossier '+GLOB_COLORS[globalFolder].toLocaleLowerCase('fr')+'.</p></header>'+
 '<nav class="saffron-folders" role="tablist" aria-label="Les quatre sous-dossiers">'+globalIndex.folders.map(f=>'<button type="button" role="tab" id="folder-tab-'+f.slug+'" data-global-folder="'+f.slug+'" aria-selected="'+(f.slug===globalFolder)+'" aria-controls="global-document-panel" aria-label="Sous-dossier '+GLOB_COLORS[f.slug]+' · '+e(f.label||GLOB_DESCRIPTIONS[f.slug])+'" tabindex="'+(f.slug===globalFolder?'0':'-1')+'" class="saffron-folder-tab '+f.slug+' '+(f.slug===globalFolder?'selected':'')+'"><span class="dossier-child-dot '+f.slug+'" aria-hidden="true"></span>'+GLOB_COLORS[f.slug]+(!f.can_read?'<span class="sr-only"> · Accès restreint</span>':'')+'</button>').join('')+'</nav>'+
 '<section id="global-document-panel" class="saffron-document-panel" role="tabpanel" aria-labelledby="folder-tab-'+globalFolder+'"><div class="saffron-document-toolbar"><label class="saffron-document-search">'+icon('search')+'<input type="search" id="global-search-input" aria-label="Rechercher dans ce sous-dossier" placeholder="Rechercher dans ce dossier…" value="'+e(globalQuery)+'" '+(folder.can_read?'':'disabled')+'></label>'+
 '<label class="saffron-type-filter"><span class="sr-only">Type de document</span><select id="global-type-filter" aria-label="Filtrer par type"><option value="all">Tous les types</option><option value="pdf">PDF</option><option value="word">Word</option><option value="excel">Excel</option><option value="image">Image</option><option value="other">Autres</option></select></label></div><span class="sr-only" id="global-result-count" role="status" aria-live="polite"></span><div id="global-doc-results"></div></section></section>'+
 '<aside class="saffron-context" aria-label="Vérifications contextuelles">'+(folder.can_write?'<button type="button" class="primary saffron-upload" id="global-upload">Déposer un document</button>':'')+
 '<section class="saffron-context-section"><h2>À vérifier</h2><div id="global-context-issues" aria-live="polite"></div><button type="button" class="saffron-context-link" id="global-open-controls">Voir les vérifications '+icon('forward')+'</button></section>'+
 (writableMemory?'<div class="saffron-context-footer"><button type="button" class="saffron-context-link" id="global-record-issue">'+icon('chat')+' Consigner un problème '+icon('forward')+'</button></div>':'')+'</aside></div>','Dossier Jaune');
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
 app.querySelector('#global-open-controls')?.addEventListener('click',()=>{controlState.folder=globalFolder;navigate('controls')});
 app.querySelector('#global-record-issue')?.addEventListener('click',()=>{
  const doc=folder.documents.find(d=>d.id===globalSelectedId);
  openRexEditor(null,{folder:globalFolder,orli_ref:doc?.orli_ref||'',document_id:doc?.id||null}).catch(showErr);
 });
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
