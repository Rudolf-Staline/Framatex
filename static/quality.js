'use strict';
// Incrément 0.4 — deux contrôles complémentaires, sans décision automatique.
function qualityStatus(s){return ({consistent:'Cohérent',difference:'Écart à examiner',unavailable:'À renseigner',ambiguous:'Source ambiguë',unit_mismatch:'Unités à vérifier'})[s]||s}
function qualityTag(s){return `<span class="tag ${s==='consistent'?'green':s==='difference'||s==='unit_mismatch'?'orange':'blue'}">${e(qualityStatus(s))}</span>`}
function renderQuality(){
 const results=state.qualityReport?.rows||[],inspections=state.excelInspections||[];
 const differences=results.filter(r=>r.status==='difference'&&!r.decision).length;
 const flags=inspections.reduce((n,x)=>n+(x.inspection?.findings||[]).filter(f=>f.type!=='inspection_limit').length,0);
 const docs=(state.detail?.folders||[]).filter(f=>f.can_read&&f.can_write).flatMap(f=>f.documents).filter(d=>d.latest);
 let rulesMarkup='';
 for(const r of results){
  const pairs=(r.pair||[]).map(p=>'<div><span>'+e(p.document_title)+' · v'+e(p.version)+'</span><strong>'+(p.value!==null&&p.value!==undefined?e(p.value)+' '+e(p.unit):'Valeur absente')+'</strong></div>').join('');
  rulesMarkup+='<article class="quality-item"><div class="quality-row"><strong>'+e(r.name)+'</strong>'+qualityTag(r.status)+'</div>'+
   '<div class="workflow-meta">'+e(r.left_doc_type)+' · '+e(r.right_doc_type)+' · tolérance '+e(r.tolerance)+'</div>'+
   (pairs?'<div class="quality-pair">'+pairs+'</div>':'')+
   (r.reason?'<p class="workflow-help">'+e(r.reason)+'</p>':'')+
   (r.decision?'<div class="workflow-note">'+e(r.decision.status==='justified'?'Écart justifié':'Correction demandée')+' : '+e(r.decision.note)+'</div>':'')+
   (r.status==='difference'&&r.can_review?'<button class="secondary tiny" data-quality-decision="'+e(r.rule_id)+'">Consigner la vérification</button>':'')+
  '</article>';
 }
 let excelMarkup='';
 for(const x of inspections){
  const ins=x.inspection,findings=ins?.findings||[];
  const status=ins?.status==='limited'?'Analyse limitée':ins?.status==='first_version'?'Référence initiale':ins?'Inspecté':'Non inspecté';
  excelMarkup+='<article class="quality-item"><div class="quality-row"><strong>'+e(x.document_title)+' · v'+e(x.version)+'</strong>'+
   '<span class="tag '+(findings.length?'orange':'green')+'">'+status+'</span></div>'+
   (ins?'<div class="workflow-meta">'+e(ins.formula_count)+' formule(s) · '+e(ins.scanned_cells)+' cellules analysées</div>'+
    (findings.length?'<ul class="quality-findings">'+findings.slice(0,12).map(v=>'<li><strong>'+e([v.sheet,v.cell].filter(Boolean).join(' ! '))+'</strong> '+e(v.message)+'</li>').join('')+'</ul>':
     '<p class="workflow-help">Aucune anomalie détectée par les contrôles disponibles.</p>')+
    (findings.length>12?'<p class="workflow-meta">'+(findings.length-12)+' autres signalements disponibles via l’API</p>':''):
    '<p class="workflow-help">Inspection non disponible pour cette version.</p>')+
  '</article>';
 }
 const counts=results.length+differences+flags>0?'<div class="quality-signal-strip">'+
  '<span>'+results.length+' règle(s)</span>'+
  '<span class="'+(differences?'has-warning':'')+'">'+differences+' écart(s) à traiter</span>'+
  '<span class="'+(flags?'has-warning':'')+'">'+flags+' signalement(s) Excel</span>'+
  '</div>':'';
 return `<section class="quality-root quality-simple" aria-label="Fiabilité documentaire">
  <div class="quality-simple-intro"><h3>Fiabilité documentaire</h3><p>Deux contrôles indépendants, avec décision humaine.</p></div>
  ${counts}
  <div class="quality-simple-list">
   <section class="quality-simple-row">
    <div class="quality-simple-row-head">
     <div><h4>Cohérence entre documents</h4><p>Comparer les informations entre deux versions.</p></div>
     <div class="quality-simple-actions">
      ${state.me?.admin?'<button type="button" class="secondary tiny" id="quality-new-rule">Configurer</button>':''}
      ${docs.length?'<button type="button" class="secondary tiny" id="quality-add-data">Relever une valeur</button>':''}
     </div>
    </div>
    ${rulesMarkup||'<p class="quality-simple-empty">Aucune comparaison configurée pour ce lancement.</p>'}
   </section>
   <section class="quality-simple-row">
    <div class="quality-simple-row-head"><div><h4>Système immunitaire Excel</h4><p>Contrôles des fichiers .xlsx déposés.</p></div><span class="quality-simple-count">${inspections.length} fichier(s)</span></div>
    ${excelMarkup||'<p class="quality-simple-empty">Aucun classeur Excel analysé.</p>'}
   </section>
  </div>
  ${differences||flags?'<p class="quality-simple-note">Les alertes sont des points à vérifier, pas des erreurs établies.</p>':''}
 </section>`;
}
function bindQuality(){
 app.querySelector('#quality-add-data')?.addEventListener('click',qualityRecordData);
 app.querySelector('#quality-new-rule')?.addEventListener('click',qualityNewRule);
 app.querySelectorAll('[data-quality-decision]').forEach(el=>el.addEventListener('click',()=>qualityDecision(el.dataset.qualityDecision)));
}
function qualityRecordData(){
 const docs=(state.detail?.folders||[]).filter(f=>f.can_read&&f.can_write).flatMap(f=>f.documents).filter(d=>d.latest);
 const fields=state.workflowFields||[];
 modal('Relever une valeur documentaire',`<p class="modal-desc">Une valeur est conservée sur la version courante du document. Elle ne peut pas être écrasée : une révision nécessite une nouvelle version documentaire.</p><form id="quality-data-form"><div class="field"><label>Document · version</label><select id="qd-version">${docs.map(d=>`<option value="${e(d.latest.id)}">${e(d.title)} · ${e(d.doc_type)} · v${d.latest.number}</option>`).join('')}</select></div><div class="field"><label>Champ à comparer</label><select id="qd-field">${fields.map(f=>`<option value="${e(f.key)}">${e(f.label)}</option>`).join('')}</select></div><div class="two-fields"><div class="field"><label>Valeur</label><input id="qd-value" required inputmode="decimal" placeholder="Ex. 1450"></div><div class="field"><label>Unité</label><input id="qd-unit" required maxlength="30" placeholder="pièce"></div></div><div class="modal-actions"><button type="button" class="secondary" id="qd-cancel">Annuler</button><button type="submit" class="primary">Enregistrer la valeur</button></div></form>`,true);
 overlay.querySelector('#qd-cancel').onclick=closeModal;
 const field=overlay.querySelector('#qd-field');const unit=overlay.querySelector('#qd-unit');
 const unitFromField=()=>{unit.value=fields.find(f=>f.key===field.value)?.suggested_unit||''};field.onchange=unitFromField;unitFromField();
 overlay.querySelector('#quality-data-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/document-versions/'+val('qd-version')+'/data',{method:'POST',body:JSON.stringify({field_key:val('qd-field'),value:val('qd-value'),unit:val('qd-unit')})});closeModal();toast('Valeur documentaire enregistrée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}};
}
function qualityNewRule(){
 const fields=state.workflowFields||[];
 modal('Configurer une comparaison inter-documents',`<p class="modal-desc">Choisissez deux types documentaires distincts et la valeur à comparer. Les documents doivent appartenir au même lancement.</p><form id="quality-rule-form"><div class="field"><label>Nom de la règle</label><input id="qr-name" required minlength="3" maxlength="140" placeholder="Ex. Quantité : lancement provisoire / définitif"></div><div class="field"><label>Champ métier</label><select id="qr-field">${fields.map(f=>`<option value="${e(f.key)}">${e(f.label)}</option>`).join('')}</select></div><div class="two-fields"><div class="field"><label>Document A : type exact</label><input id="qr-left-type" required maxlength="100" placeholder="Lancement provisoire"></div><div class="field"><label>Document B : type exact</label><input id="qr-right-type" required maxlength="100" placeholder="Lancement définitif"></div></div><div class="two-fields"><div class="field"><label>Rubrique A</label><select id="qr-left-folder">${['jaune','rose','bleu','vert'].map(x=>`<option value="${x}">${x}</option>`).join('')}</select></div><div class="field"><label>Rubrique B</label><select id="qr-right-folder">${['jaune','rose','bleu','vert'].map(x=>`<option value="${x}">${x}</option>`).join('')}</select></div></div><div class="field"><label>Tolérance absolue</label><input id="qr-tolerance" inputmode="decimal" required value="0"></div><div class="modal-actions"><button type="button" class="secondary" id="qr-cancel">Annuler</button><button class="primary" type="submit">Créer la règle</button></div></form>`,true);
 overlay.querySelector('#qr-cancel').onclick=closeModal;
 overlay.querySelector('#quality-rule-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/admin/quality-rules',{method:'POST',body:JSON.stringify({name:val('qr-name'),field_key:val('qr-field'),left_doc_type:val('qr-left-type'),right_doc_type:val('qr-right-type'),left_folder:val('qr-left-folder'),right_folder:val('qr-right-folder'),tolerance:val('qr-tolerance')})});closeModal();toast('Comparaison créée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}};
}
function qualityDecision(id){const r=(state.qualityReport?.rows||[]).find(x=>x.rule_id===id);if(!r)return;
 modal('Qualifier un écart',`<p class="modal-desc">La décision sera attachée aux deux versions et aux valeurs actuellement comparées. Un nouveau dépôt réouvrira la vérification.</p><form id="qdec-form"><div class="field"><label>Décision</label><select id="qdec-type"><option value="justified">Écart justifié</option><option value="to_correct">Correction nécessaire</option></select></div><div class="field"><label>Explication détaillée</label><textarea id="qdec-note" required minlength="12" maxlength="1800" rows="4"></textarea></div><div class="modal-actions"><button type="button" class="secondary" id="qdec-cancel">Annuler</button><button type="submit" class="primary">Enregistrer</button></div></form>`);
 overlay.querySelector('#qdec-cancel').onclick=closeModal;
 overlay.querySelector('#qdec-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/launches/'+state.detail.id+'/quality/'+id+'/decisions',{method:'POST',body:JSON.stringify({signature:r.signature,decision:val('qdec-type'),note:val('qdec-note')})});closeModal();toast('Vérification enregistrée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}};
}
