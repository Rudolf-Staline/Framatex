'use strict';
const controlState={tab:'expectations',report:null,folder:''};
const CONTROL_LABELS={consistent:'Cohérent',difference:'Écart à examiner',unavailable:'À compléter',ambiguous:'Sources ambiguës',unit_mismatch:'Unités différentes'};
async function libraryControlsPage(){
 state.view='controls';state.dossierFolder=controlState.folder||'jaune';
 mount('<div class="knowledge-page"><h1 class="page-title">Vérifications</h1><p role="status">Lecture des attentes et des valeurs documentaires…</p></div>','Vérifications');
 controlState.report=await api('/api/dossier-jaune/controls');
 if(state.view!=='controls')return;
 renderLibraryControls();
}
function controlRows(){
 const report=controlState.report,filter=controlState.folder;
 if(controlState.tab==='expectations'){
  const rows=report.expectations.filter(r=>!filter||r.folder===filter);
  return rows.length?'<ul class="control-list">'+rows.map(r=>'<li class="control-row"><div><span class="rex-row-meta">'+GLOB_COLORS[r.folder]+' · '+e(r.orli_ref||'Toute la rubrique')+'</span><h3>'+e(r.title)+'</h3><p>'+e(r.document_type)+'</p>'+(r.documents.length?'<small>'+e(r.documents.map(d=>d.title).join(', '))+'</small>':'')+'</div><div class="control-row-actions"><span class="rex-status rex-status-'+(r.status==='present'?'resolu':'ouvert')+'">'+(r.status==='present'?'Présent':'Manquant dans votre périmètre')+'</span>'+(r.status==='missing'&&can('document.write',r.folder)?'<button type="button" class="secondary tiny" data-control-upload="'+r.folder+'">Déposer la pièce</button>':'')+(r.can_edit?'<button type="button" class="link" data-expectation-off="'+e(r.id)+'">Désactiver cette attente</button>':'')+'</div></li>').join('')+'</ul>':'<div class="knowledge-empty"><strong>Aucune attente documentaire configurée'+(filter?' dans ce sous-dossier':'')+'</strong><p>Définissez un type de pièce et, si nécessaire, une référence ORLI. Aucun manque ne sera déduit sans règle.</p></div>';
 }
 const rows=report.comparisons.filter(r=>!filter||r.folders.includes(filter));
 return (rows.length?'<ul class="control-list">'+rows.map((r,i)=>'<li class="control-row control-comparison"><div><span class="rex-row-meta">'+e(r.orli_ref)+'</span><h3>'+e(r.name)+'</h3><p>'+e(r.reason)+'</p><div class="control-pair">'+r.pair.map(p=>'<div><span>'+e(p.title)+' · v'+p.version+'</span><strong>'+e(p.value??'Valeur à relever')+' '+e(p.unit||'')+'</strong></div>').join('')+'</div><small>Tolérance : '+e(r.tolerance)+'</small></div><div class="control-row-actions"><span class="rex-status rex-status-'+(r.status==='consistent'?'resolu':'ouvert')+'">'+e(CONTROL_LABELS[r.status])+'</span>'+(['difference','unit_mismatch'].includes(r.status)?'<button type="button" class="secondary tiny" data-control-record="'+e(r.rule_id)+'" data-control-ref="'+e(r.orli_ref)+'">Consigner le problème</button>':'')+'</div></li>').join('')+'</ul>':'<div class="knowledge-empty"><strong>Aucun rapprochement disponible</strong><p>Une comparaison exige une règle configurée, une référence ORLI commune et des valeurs relevées sur les versions courantes. Les pièces sans référence ORLI ne sont pas rapprochées automatiquement.</p></div>')+
 '<details class="control-value-register"><summary>Valeurs documentaires et règles actives</summary><p>'+report.rules.length+' règle'+(report.rules.length===1?'':'s')+' active'+(report.rules.length===1?'':'s')+' : '+e(report.rules.map(r=>r.name).join(', ')||'aucune')+'</p><ul class="control-list">'+report.documents.filter(d=>!filter||d.folder===filter).map(d=>'<li class="control-value-row"><div><strong>'+e(d.title)+' · v'+d.version+'</strong><small>'+GLOB_COLORS[d.folder]+' · '+e(d.orli_ref||'ORLI non renseignée')+'</small><p>'+e(d.values.map(v=>(report.fields.find(f=>f.key===v.field_key)?.label||v.field_key)+' : '+v.value+' '+v.unit).join(' · ')||'Aucune valeur relevée sur cette version')+'</p></div>'+(d.can_write?'<button type="button" class="secondary tiny" data-control-value="'+e(d.id)+'">Relever une valeur</button>':'')+'</li>').join('')+'</ul></details>';
}
function renderLibraryControls(){
 const report=controlState.report;
 mount('<div class="knowledge-page"><header class="knowledge-head"><div><span class="knowledge-eyebrow">FIABILITÉ DOCUMENTAIRE</span><h1 class="page-title">Vérifications</h1><p>Repérer les pièces attendues et les écarts entre documents.</p></div><button type="button" class="secondary" id="controls-refresh">'+icon('activity')+' Actualiser</button></header>'+
 '<div class="knowledge-section-head"><div class="knowledge-tabs" role="tablist" aria-label="Contrôles documentaires"><button type="button" role="tab" aria-selected="'+(controlState.tab==='expectations')+'" id="control-tab-expectations" aria-controls="control-results" data-control-tab="expectations" tabindex="'+(controlState.tab==='expectations'?0:-1)+'">Pièces manquantes <span>'+report.counts.missing+'</span></button><button type="button" role="tab" aria-selected="'+(controlState.tab==='consistency')+'" id="control-tab-consistency" aria-controls="control-results" data-control-tab="consistency" tabindex="'+(controlState.tab==='consistency'?0:-1)+'">Cohérence <span>'+report.counts.differences+'</span></button></div><label class="knowledge-filter" for="control-folder">Sous-dossier<select id="control-folder">'+folderOptions(knowledgeFolders(),controlState.folder,true)+'</select></label></div>'+
 '<div class="knowledge-actions">'+(controlState.tab==='expectations'&&report.expectation_folders.length?'<button type="button" class="primary" id="expectation-add">'+icon('plus')+' Définir une pièce attendue</button>':'')+(controlState.tab==='consistency'&&report.can_manage_rules?'<button type="button" class="primary" id="control-rule-add">'+icon('plus')+' Ajouter une règle de cohérence</button>':'')+'</div>'+
 '<section class="control-results" id="control-results" role="tabpanel" aria-labelledby="control-tab-'+controlState.tab+'">'+controlRows()+'</section><p class="knowledge-muted">'+e(report.scope)+' Les écarts signalent une vérification à effectuer.</p></div>','Vérifications');
 app.querySelector('#controls-refresh').onclick=()=>libraryControlsPage().catch(showErr);
 app.querySelector('#control-folder').onchange=event=>{controlState.folder=event.target.value;state.dossierFolder=controlState.folder||'jaune';renderLibraryControls()};
 app.querySelectorAll('[data-control-tab]').forEach(b=>{
  const select=()=>{controlState.tab=b.dataset.controlTab;renderLibraryControls()};
  b.onclick=select;
  b.onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();controlState.tab=event.key==='Home'?'expectations':event.key==='End'?'consistency':controlState.tab==='expectations'?'consistency':'expectations';renderLibraryControls();app.querySelector('[data-control-tab="'+controlState.tab+'"]').focus()}};
 });
 app.querySelector('#expectation-add')?.addEventListener('click',expectationModal);
 app.querySelector('#control-rule-add')?.addEventListener('click',consistencyRuleModal);
 app.querySelectorAll('[data-control-upload]').forEach(b=>b.onclick=async()=>{try{await openGlobalFolder(b.dataset.controlUpload);globalUploadModal()}catch(err){showErr(err)}});
 app.querySelectorAll('[data-expectation-off]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/api/dossier-jaune/expectations/'+encodeURIComponent(b.dataset.expectationOff),{method:'DELETE'});await libraryControlsPage()}catch(err){b.disabled=false;showErr(err)}});
 app.querySelectorAll('[data-control-value]').forEach(b=>b.onclick=()=>datumModal(b.dataset.controlValue));
 app.querySelectorAll('[data-control-record]').forEach(b=>b.onclick=()=>{
  const r=report.comparisons.find(x=>x.rule_id===b.dataset.controlRecord&&x.orli_ref===b.dataset.controlRef);
  if(!r)return;
  openRexEditor(null,{folder:r.folders[0],orli_ref:r.orli_ref,title:r.name,problem:r.reason+' : '+r.pair.map(p=>p.title+' (v'+p.version+') : '+(p.value??'non relevé')+' '+(p.unit||'')).join(' / '),document_id:r.pair[0]?.document_id,tags:['cohérence']}).catch(showErr);
 });
}
function controlFormSubmit(selector,endpoint,makePayload){
 overlay.querySelector(selector).onsubmit=async event=>{
  event.preventDefault();const form=event.currentTarget,button=form.querySelector('[type=submit]');
  button.disabled=true;
  try{await api(endpoint,{method:'POST',body:JSON.stringify(makePayload(form))});closeModal();toast('Enregistrement effectué');await libraryControlsPage()}
  catch(err){form.querySelector('[role=alert]').textContent=err.message}
  finally{button.disabled=false}
 };
 overlay.querySelector('[data-control-cancel]').onclick=closeModal;
 knowledgeDialogFocus();
}
const CONTROL_FORM_END='<div role="alert" class="knowledge-form-error"></div><div class="modal-actions"><button type="button" class="secondary" data-control-cancel>Annuler</button><button type="submit" class="primary">Enregistrer</button></div></form>';
function expectationModal(){
 const report=controlState.report;
 modal('Définir une pièce attendue','<form id="expectation-form" class="knowledge-form"><p>Une référence ORLI cible ses documents. Sans référence, cette attente concerne toute la rubrique.</p><div class="field"><label for="expected-title">Pièce attendue *</label><input id="expected-title" required minlength="3" maxlength="180" placeholder="Bon de livraison fournisseur"></div><div class="two-fields"><div class="field"><label for="expected-folder">Sous-dossier</label><select id="expected-folder">'+folderOptions(report.expectation_folders,controlState.folder||'rose')+'</select></div><div class="field"><label for="expected-orli">Référence ORLI · facultative</label><input id="expected-orli" maxlength="100"></div></div><div class="field"><label for="expected-type">Type documentaire exact *</label><input id="expected-type" required minlength="2" maxlength="100" list="control-document-types" placeholder="Bon de livraison">'+controlDocTypes()+'</div>'+CONTROL_FORM_END);
 controlFormSubmit('#expectation-form','/api/dossier-jaune/expectations',form=>({title:form.querySelector('#expected-title').value.trim(),folder:form.querySelector('#expected-folder').value,orli_ref:form.querySelector('#expected-orli').value.trim()||null,document_type:form.querySelector('#expected-type').value.trim()}));
}
function controlDocTypes(){return '<datalist id="control-document-types">'+[...new Set(controlState.report.documents.map(d=>d.doc_type))].map(t=>'<option value="'+e(t)+'">').join('')+'</datalist>'}
function datumModal(id){
 const d=controlState.report.documents.find(x=>x.id===id);if(!d?.can_write)return;
 const fields=controlState.report.fields.filter(f=>!d.values.some(v=>v.field_key===f.key));
 if(!fields.length){toast('Toutes les valeurs sont déjà relevées sur cette version.');return}
 modal('Relever une valeur','<form id="datum-form" class="knowledge-form"><p>'+e(d.title)+' · version '+d.version+'. La saisie reste liée à cette version.</p><div class="field"><label for="datum-field">Champ</label><select id="datum-field">'+fields.map(f=>'<option value="'+f.key+'">'+e(f.label)+'</option>').join('')+'</select></div><div class="two-fields"><div class="field"><label for="datum-value">Valeur *</label><input id="datum-value" inputmode="decimal" maxlength="50" required></div><div class="field"><label for="datum-unit">Unité *</label><input id="datum-unit" required maxlength="30" value="'+e(fields[0].unit)+'"></div></div>'+CONTROL_FORM_END);
 overlay.querySelector('#datum-field').onchange=event=>{overlay.querySelector('#datum-unit').value=fields.find(f=>f.key===event.target.value).unit};
 controlFormSubmit('#datum-form','/api/dossier-jaune/documents/'+encodeURIComponent(id)+'/data',form=>({field_key:form.querySelector('#datum-field').value,value:form.querySelector('#datum-value').value.trim(),unit:form.querySelector('#datum-unit').value.trim()}));
}
function consistencyRuleModal(){
 const fields=controlState.report.fields;
 modal('Ajouter une règle de cohérence','<form id="consistency-rule-form" class="knowledge-form"><div class="field"><label for="rule-name">Nom du contrôle *</label><input id="rule-name" required minlength="3" maxlength="140" placeholder="Quantité commandée et quantité livrée"></div><div class="field"><label for="rule-field">Valeur à comparer</label><select id="rule-field">'+fields.map(f=>'<option value="'+f.key+'">'+e(f.label)+'</option>').join('')+'</select></div>'+['left','right'].map((side,i)=>'<fieldset><legend>Document '+(i+1)+'</legend><div class="two-fields"><div class="field"><label for="rule-'+side+'-folder">Sous-dossier</label><select id="rule-'+side+'-folder">'+folderOptions(Object.keys(GLOB_COLORS),i?'rose':'jaune')+'</select></div><div class="field"><label for="rule-'+side+'-type">Type documentaire *</label><input id="rule-'+side+'-type" list="control-document-types" required minlength="2" maxlength="100"></div></div></fieldset>').join('')+controlDocTypes()+'<div class="field"><label for="rule-tolerance">Écart absolu toléré · dans l’unité des valeurs</label><input id="rule-tolerance" inputmode="decimal" maxlength="35" value="0" required></div><p class="knowledge-muted">La comparaison porte sur la même référence ORLI, sans conversion d’unité ni sélection arbitraire de source.</p>'+CONTROL_FORM_END,true);
 controlFormSubmit('#consistency-rule-form','/api/admin/quality-rules',form=>{const get=id=>form.querySelector('#rule-'+id).value.trim();return {name:get('name'),field_key:get('field'),left_folder:get('left-folder'),left_doc_type:get('left-type'),right_folder:get('right-folder'),right_doc_type:get('right-type'),tolerance:get('tolerance')}});
}
