'use strict';
// Un seul Dossier Jaune, quatre catégories permanentes, aucune arborescence par lancement.
const GLOB_COLORS={jaune:'Jaune',rose:'Rose',bleu:'Bleu',vert:'Vert'};
let globalIndex=null,globalFolder='jaune',globalQuery='',globalType='all',globalView='list';

async function globalLibraryPage(){
 state.view='dossier';
 globalIndex=await api('/api/dossier-jaune');
 renderGlobalLibrary();
}
async function openGlobalFolder(slug){
 if(!Object.hasOwn(GLOB_COLORS,slug))return;
 globalFolder=slug;
 globalQuery='';
 globalType='all';
 state.dossierFolder=slug;
 state.sidebarDossierOpen=true;
 if(state.view==='dossier'&&globalIndex){renderGlobalLibrary();return}
 await globalLibraryPage();
}
function globalDocumentsVisible(){
 const group=globalIndex.folders.find(f=>f.slug===globalFolder);
 if(!group?.can_read)return [];
 const term=globalQuery.trim().toLocaleLowerCase('fr');
 return group.documents.filter(d=>(globalType==='all'||String(d.doc_type||'').toLowerCase().includes(globalType))&&(!term||[d.title,d.doc_type,d.orli_ref||'',...(d.versions||[]).map(v=>v.original_name)].some(v=>String(v).toLocaleLowerCase('fr').includes(term))));
}
function globalRenderRows(){
 const group=globalIndex.folders.find(f=>f.slug===globalFolder);
 const host=app.querySelector('#global-doc-results'),count=app.querySelector('#global-result-count');
 if(!host)return;
 if(!group.can_read){host.innerHTML='<p class="global-empty">Accès à cette rubrique réservé.</p>';count.textContent='';return}
 const rows=globalDocumentsVisible();
 count.textContent=rows.length+' document'+(rows.length===1?'':'s');
 host.innerHTML=rows.length?`<div class="table-scroll"><table class="global-table">
 <thead><tr><th>Nom</th><th>Type</th><th>Référence / ORLI</th><th>Date d'ajout</th><th>Version</th><th>Actions</th></tr></thead>
 <tbody>${rows.map(d=>`<tr>
 <td><div class="global-file-name"><span class="global-file-icon">${icon('file')}</span><span><strong>${e(d.title)}</strong><small>${e(d.latest?.original_name||'Document')}</small></span></div></td>
 <td><span class="global-type-pill">${e(d.doc_type||'Autre')}</span></td>
 <td>${d.orli_ref?e(d.orli_ref):'<span class="muted">—</span>'}</td>
 <td class="small">${niceDate(d.latest?.created_at||d.created_at)}</td>
 <td>v${d.latest?.number||'—'}</td>
 <td class="global-actions"><button class="link" type="button" data-global-download="${e(d.id)}" data-v="${d.latest?.number||1}" aria-label="Télécharger ${e(d.title)}">${icon('download')}</button>
 ${group.can_write?`<button class="link" type="button" data-global-edit="${e(d.id)}" aria-label="Modifier la référence ORLI">${icon('pencil')}</button>`:''}</td>
 </tr><tr class="global-versions"><td colspan="6"><details><summary>Historique des versions · ${d.versions.length}</summary>
 ${d.versions.map(v=>`<button class="link" type="button" data-global-download="${e(d.id)}" data-v="${v.number}">v${v.number} · ${e(v.original_name)} · ${niceDate(v.created_at)} ${icon('download')}</button>`).join('')}
 </details></td></tr>`).join('')}</tbody></table></div>`:`<div class="global-empty-state"><div class="global-empty-glyph">${icon('folder')}</div><strong>${globalQuery||globalType!=='all'?'Aucun résultat':'Aucun document pour le moment'}</strong><p>${globalQuery||globalType!=='all'?'Modifiez les filtres pour élargir la recherche.':'Les fichiers déposés apparaîtront ici.'}</p>${group.can_write&&!globalQuery&&globalType==='all'?'<button class="primary" id="global-empty-upload" type="button">'+icon('plus')+' Déposer un document</button>':''}</div>`;
 host.querySelector('#global-empty-upload')?.addEventListener('click',globalUploadModal);
 host.querySelectorAll('[data-global-download]').forEach(b=>b.onclick=()=>globalDownload(b.dataset.globalDownload,Number(b.dataset.v)));
 host.querySelectorAll('[data-global-edit]').forEach(b=>b.onclick=()=>globalEditReference(b.dataset.globalEdit));
}
function renderGlobalLibrary(){
 state.dossierFolder=globalFolder;
 const folder=globalIndex.folders.find(f=>f.slug===globalFolder);
 mount(`<div class="global-library global-workspace">
 <nav class="global-breadcrumb" aria-label="Fil d'Ariane"><span>Dossier Jaune</span><span>›</span><strong>${GLOB_COLORS[globalFolder]}</strong></nav>
 <div class="global-workspace-top"><nav class="global-folders" role="tablist" aria-label="Les quatre sous-dossiers">
 ${globalIndex.folders.map(f=>`<button type="button" role="tab" data-global-folder="${f.slug}" aria-selected="${f.slug===globalFolder}" class="global-folder-card ${f.slug} ${f.slug===globalFolder?'selected':''}"><span class="global-card-icon">${icon('folder')}</span><span class="global-card-text"><strong>${GLOB_COLORS[f.slug]}</strong><small>${f.can_read?f.count+' document'+(f.count===1?'':'s'):'Accès restreint'}</small></span></button>`).join('')}</nav>
 ${folder.can_write?`<button type="button" class="primary global-top-upload" id="global-upload">${icon('plus')} Déposer un document</button>`:''}</div>
 <section class="global-workspace-panel">
 <div class="global-panel-heading"><div class="global-panel-title"><span class="global-panel-icon ${globalFolder}">${icon('folder')}</span><div><h1>${GLOB_COLORS[globalFolder]} <span>· ${e(folder.label)}</span></h1><p>Documents partagés dans ce sous-dossier</p></div></div><div class="global-panel-controls"><label class="global-search">${icon('search')}<input type="search" id="global-search-input" aria-label="Rechercher un document" placeholder="Nom, type, référence ORLI..." value="${e(globalQuery)}" ${folder.can_read?'':'disabled'}></label><label class="global-filter-label"><span>Type</span><select id="global-type-filter" aria-label="Filtrer par type"><option value="all">Tous les types</option><option value="pdf">PDF</option><option value="word">Word</option><option value="excel">Excel</option><option value="image">Image</option></select></label></div></div>
 <div class="global-panel-tabbar"><span class="global-panel-tab">${icon('file')} Documents</span><span class="global-panel-count" id="global-result-count"></span></div>
 <div id="global-doc-results"></div>
 </section></div>`,'Dossier Jaune');
 app.querySelector('#global-type-filter')?.addEventListener('change',ev=>{globalType=ev.target.value;globalRenderRows()});
 app.querySelectorAll('[data-global-folder]').forEach(b=>b.onclick=()=>openGlobalFolder(b.dataset.globalFolder).catch(showErr));
 app.querySelector('#global-search-input')?.addEventListener('input',ev=>{globalQuery=ev.target.value;globalRenderRows()});
 app.querySelector('#global-upload')?.addEventListener('click',globalUploadModal);
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
 overlay.querySelector('#g-edit-cancel').onclick=closeModal;
 overlay.querySelector('#g-edit-form').onsubmit=async evt=>{
 evt.preventDefault();
 try{await api('/api/dossier-jaune/documents/'+encodeURIComponent(id)+'/reference',{
   method:'PATCH',body:JSON.stringify({orli_ref:val('g-edit-orli')})});
   closeModal();toast('Référence mise à jour');await globalLibraryPage();
 }catch(err){showErr(err)}
 };
}
