'use strict';
const REX_LABELS={ouvert:'Ouvert',en_cours:'En cours',resolu:'Résolu'};
const rexState={folder:'',query:'',offset:0,report:null,answer:null};
function knowledgeFolders(action){
 return Object.keys(GLOB_COLORS).filter(s=>can('document.read',s)&&(!action||can(action,s)));
}
function folderOptions(slugs,selected,all=false){
 return (all?'<option value="">Tous les sous-dossiers</option>':'')+slugs.map(s=>'<option value="'+s+'"'+(s===selected?' selected':'')+'>'+GLOB_COLORS[s]+' · '+GLOB_DESCRIPTIONS[s]+'</option>').join('');
}
function knowledgeDialogFocus(){
 const dialog=overlay.querySelector('[role=dialog]'),previous=document.activeElement;
 if(!dialog)return;
 const focusables=()=>[...dialog.querySelectorAll('button:not([disabled]),input:not([disabled]),textarea,select')].filter(n=>n.getClientRects().length);
 dialog.addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.preventDefault();closeModal();previous?.isConnected&&previous.focus();return}
  if(event.key!=='Tab')return;
  const items=focusables(),first=items[0],last=items.at(-1);
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
 });
 dialog.querySelector('#close-modal')?.addEventListener('click',()=>previous?.isConnected&&previous.focus());
 (dialog.querySelector('input,textarea,select')||dialog.querySelector('button'))?.focus();
}
function rexStatus(status){return '<span class="rex-status rex-status-'+e(status)+'">'+e(REX_LABELS[status]||status)+'</span>'}
function rexSourceButtons(sources){
 return sources.map((r,i)=>'<button type="button" class="rex-citation" data-rex-source="'+e(r.id)+'"><span>Fiche '+(i+1)+'</span><strong>'+e(r.title)+'</strong><small>'+GLOB_COLORS[r.folder]+(r.orli_ref?' · '+e(r.orli_ref):'')+' · '+e(REX_LABELS[r.status])+'</small>'+icon('arrow')+'</button>').join('');
}
function bindRexSources(root=app){
 root.querySelectorAll('[data-rex-source]').forEach(b=>b.addEventListener('click',()=>{
  if(typeof closeFloatingAssistant==='function')closeFloatingAssistant(false);
  openRexRecord(b.dataset.rexSource).catch(showErr);
 }));
}
async function rexPage(){
 state.view='rex';state.dossierFolder=rexState.folder||'jaune';
 mount('<div class="knowledge-page"><h1 class="page-title">'+icon('book')+' Mémoire métier</h1><p role="status">Chargement des retours d’expérience…</p></div>','Mémoire métier');
 const params=new URLSearchParams({offset:String(rexState.offset),limit:'30'});
 if(rexState.folder)params.set('folder',rexState.folder);
 if(rexState.query)params.set('q',rexState.query);
 rexState.report=await api('/api/experience?'+params);
 if(state.view!=='rex')return;
 renderRexPage();
}
function renderRexPage(){
 const report=rexState.report;
 const rows=report.items.map(r=>'<li class="rex-row"><button type="button" data-rex-source="'+e(r.id)+'" class="rex-row-open"><span class="rex-row-meta">'+GLOB_COLORS[r.folder]+(r.orli_ref?' · '+e(r.orli_ref):'')+'</span><strong>'+e(r.title)+'</strong><span class="rex-row-excerpt">'+e(r.problem)+'</span></button><div class="rex-row-side">'+rexStatus(r.status)+'<small>'+niceDate(r.updated_at)+'</small></div></li>').join('');
 const answer=rexState.answer?'<section class="rex-answer" aria-label="Résultats de la question"><h2>Dans les cas enregistrés</h2><p class="knowledge-prose">'+e(rexState.answer.answer)+'</p>'+rexSourceButtons(rexState.answer.sources)+'<small>'+e(rexState.answer.method)+'</small></section>':'';
 mount('<div class="knowledge-page"><header class="knowledge-head"><div><span class="knowledge-eyebrow">RETOURS D’EXPÉRIENCE</span><h1 class="page-title">'+icon('book')+' Mémoire métier</h1><p>Conserver les problèmes rencontrés et retrouver ce qui a permis de les résoudre.</p></div>'+(report.writable_folders.length?'<button type="button" class="primary" id="rex-create">'+icon('plus')+' Enregistrer un problème</button>':'')+'</header>'+
 '<section class="rex-question-section"><form id="rex-question-form"><label for="rex-question">Quel problème cherchez-vous à résoudre ?</label><div class="rex-question-input"><input id="rex-question" type="search" maxlength="500" minlength="3" required placeholder="Comment avons-nous résolu un écart de quantité ?" value="'+e(rexState.query)+'"><button type="submit" class="primary">'+icon('search')+' Interroger</button></div><span class="knowledge-muted">Recherche dans les fiches accessibles, avec leurs solutions et leurs sources.</span></form><div id="rex-question-answer" role="status" aria-live="polite">'+answer+'</div></section>'+
 '<section class="rex-register"><div class="knowledge-section-head"><h2>'+icon('warning')+' Problèmes enregistrés <span>'+report.total+'</span></h2><label class="knowledge-filter" for="rex-folder">Sous-dossier<select id="rex-folder">'+folderOptions(knowledgeFolders('rex.read'),rexState.folder,true)+'</select></label></div>'+
 (rows?'<ul class="rex-list">'+rows+'</ul>':'<div class="knowledge-empty"><strong>'+(rexState.query?'Aucun cas correspondant':'Aucun problème enregistré')+'</strong><p>'+(rexState.query?'Précisez le document, la référence ORLI ou le symptôme.':'Consignez un premier incident pour pouvoir le retrouver et réutiliser sa solution.')+'</p></div>')+
 '<div class="knowledge-pagination"><span>'+report.total+' fiche'+(report.total===1?'':'s')+'</span><div><button type="button" class="secondary tiny" id="rex-prev"'+(!rexState.offset?' disabled':'')+'>Précédent</button><button type="button" class="secondary tiny" id="rex-next"'+(rexState.offset+report.limit>=report.total?' disabled':'')+'>Suivant</button></div></div></section></div>','Mémoire métier');
 app.querySelector('#rex-create')?.addEventListener('click',()=>openRexEditor().catch(showErr));
 app.querySelector('#rex-folder').addEventListener('change',event=>{rexState.folder=event.target.value;rexState.offset=0;rexState.answer=null;rexPage().catch(showErr)});
 app.querySelector('#rex-prev').onclick=()=>{rexState.offset=Math.max(0,rexState.offset-report.limit);rexPage().catch(showErr)};
 app.querySelector('#rex-next').onclick=()=>{rexState.offset+=report.limit;rexPage().catch(showErr)};
 app.querySelector('#rex-question-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.currentTarget.querySelector('button'),input=app.querySelector('#rex-question');
  button.disabled=true;rexState.query=input.value.trim();rexState.offset=0;
  try{
   const result=await api('/api/experience/ask',{method:'POST',body:JSON.stringify({question:rexState.query,folder:rexState.folder||null})});
   if(state.view!=='rex')return;
   rexState.answer=result;await rexPage();
  }catch(err){showErr(err)}finally{button.disabled=false}
 });
 bindRexSources();
}
async function openRexRecord(id){
 const row=await api('/api/experience/'+encodeURIComponent(id));
 const parts=[['Problème rencontré',row.problem],['Contexte',row.context],['Cause identifiée',row.cause],['Solution appliquée ou envisagée',row.solution],['À retenir',row.lesson]];
 modal(row.title,'<article class="rex-record"><div class="rex-record-meta">'+rexStatus(row.status)+'<span>'+GLOB_COLORS[row.folder]+(row.orli_ref?' · '+e(row.orli_ref):'')+'</span></div>'+
 parts.filter(([,v])=>v).map(([label,value])=>'<section><h3>'+label+'</h3><p class="knowledge-prose">'+e(value)+'</p></section>').join('')+
 (row.source?'<p class="knowledge-source">Document source : <strong>'+e(row.source.title)+'</strong> · version '+row.source.version+'</p>':'')+
 '<p class="knowledge-muted">Mis à jour le '+niceDate(row.updated_at)+' · révision '+row.revision+'</p>'+
 (row.can_edit?'<div class="modal-actions"><button type="button" class="primary" id="rex-edit">'+icon('pencil')+' Compléter la fiche</button></div>':'')+'</article>',true);
 overlay.querySelector('#rex-edit')?.addEventListener('click',()=>openRexEditor(row).catch(showErr));
 knowledgeDialogFocus();
}
async function openRexEditor(record=null,prefill={}){
 const allowed=knowledgeFolders('rex.write').filter(s=>can('rex.read',s));
 if(!allowed.length){toast('Aucun droit de saisie dans la mémoire métier');return}
 const archive=await api('/api/dossier-jaune');
 const row=record||prefill,folder=allowed.includes(row.folder)?row.folder:allowed[0];
 modal(record?'Compléter le retour d’expérience':'Enregistrer un problème',
 '<form id="rex-edit-form" class="knowledge-form"><div id="rex-form-error" role="alert"></div>'+
 '<div class="two-fields"><div class="field"><label for="rex-edit-folder">Sous-dossier</label><select id="rex-edit-folder">'+folderOptions(allowed,folder)+'</select></div><div class="field"><label for="rex-edit-orli">Référence ORLI · facultative</label><input id="rex-edit-orli" maxlength="100" value="'+e(row.orli_ref||'')+'"></div></div>'+
 '<div class="field"><label for="rex-edit-title">Titre du problème *</label><input id="rex-edit-title" minlength="3" maxlength="180" required value="'+e(row.title||'')+'" placeholder="Écart de quantité entre la fiche et la livraison"></div>'+
 '<div class="field"><label for="rex-edit-problem">Que s’est-il passé ? *</label><textarea id="rex-edit-problem" minlength="12" maxlength="8000" required rows="3">'+e(row.problem||'')+'</textarea></div>'+
 '<div class="field"><label for="rex-edit-context">Contexte · facultatif</label><textarea id="rex-edit-context" maxlength="4000" rows="2">'+e(row.context||'')+'</textarea></div>'+
 '<div class="field"><label for="rex-edit-document">Document source · facultatif</label><select id="rex-edit-document"></select><small>La version liée est conservée avec la fiche.</small></div>'+
 '<details class="rex-resolution-fields"'+(record||row.solution?' open':'')+'><summary>Cause, solution et enseignements</summary>'+
 [['cause','Cause identifiée',4000],['solution','Solution appliquée ou envisagée',6000],['lesson','À retenir pour les prochains cas',4000]].map(([key,label,max])=>'<div class="field"><label for="rex-edit-'+key+'">'+label+'</label><textarea id="rex-edit-'+key+'" maxlength="'+max+'" rows="2">'+e(row[key]||'')+'</textarea></div>').join('')+'</details>'+
 '<div class="two-fields"><div class="field"><label for="rex-edit-status">État</label><select id="rex-edit-status">'+Object.entries(REX_LABELS).map(([s,label])=>'<option value="'+s+'"'+((row.status||'ouvert')===s?' selected':'')+'>'+label+'</option>').join('')+'</select></div><div class="field"><label for="rex-edit-tags">Mots-clés · séparés par des virgules</label><input id="rex-edit-tags" maxlength="410" value="'+e((row.tags||[]).join(', '))+'"></div></div>'+
 '<div class="modal-actions"><button type="button" class="secondary" id="rex-cancel">Annuler</button><button type="submit" class="primary">'+icon('check')+' Enregistrer</button></div></form>',true);
 const docs=archive.folders.flatMap(f=>f.can_read?f.documents:[]);
 const documentSelect=overlay.querySelector('#rex-edit-document');
 const fillDocuments=selected=>{
  const selectedFolder=overlay.querySelector('#rex-edit-folder').value;
  documentSelect.innerHTML='<option value="">Sans document source</option>'+docs.filter(d=>d.folder===selectedFolder).map(d=>'<option value="'+e(d.id)+'"'+(selected===d.id?' selected':'')+'>'+e(d.title)+' · v'+d.latest?.number+'</option>').join('');
 };
 fillDocuments(row.source?.document_id||row.document_id);
 overlay.querySelector('#rex-edit-folder').onchange=()=>fillDocuments(null);
 overlay.querySelector('#rex-cancel').onclick=closeModal;
 overlay.querySelector('#rex-edit-form').addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget,button=form.querySelector('[type=submit]');
  const get=id=>form.querySelector('#rex-edit-'+id).value.trim();
  const payload={folder:get('folder'),title:get('title'),problem:get('problem'),context:get('context'),cause:get('cause'),solution:get('solution'),lesson:get('lesson'),status:get('status'),orli_ref:get('orli')||null,document_id:get('document')||null,tags:get('tags').split(',').map(x=>x.trim()).filter(Boolean)};
  const error=form.querySelector('#rex-form-error');error.textContent='';
  if(payload.status==='resolu'&&payload.solution.length<12){error.textContent='Décrivez la solution (12 caractères minimum) avant de déclarer le problème résolu.';form.querySelector('details').open=true;form.querySelector('#rex-edit-solution').focus();return}
  if(payload.tags.length>10||payload.tags.some(t=>t.length>40)){error.textContent='Utilisez au plus 10 mots-clés de 40 caractères maximum.';return}
  if(record)payload.revision=record.revision;
  button.disabled=true;
  try{
   await api('/api/experience'+(record?'/'+encodeURIComponent(record.id):''),{method:record?'PUT':'POST',body:JSON.stringify(payload)});
   closeModal();toast('Retour d’expérience enregistré');rexState.answer=null;rexState.query='';rexState.offset=0;await rexPage();
  }catch(err){error.textContent=err.message}finally{button.disabled=false}
 });
 knowledgeDialogFocus();
}
