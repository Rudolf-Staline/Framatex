'use strict';
/* 0.11 — lecture seule des exports ORLI ; rapprochement sur confirmation humaine. */
function orliRecordRows(records){
 return `<div class="table-scroll"><table><thead><tr><th>Ligne</th><th>Lancement ORLI</th><th>Commande</th><th>Client</th><th>État</th></tr></thead><tbody>${records.map(r=>`<tr><td>${e(r.row_number)}</td><td><strong>${e(r.orli_ref||'—')}</strong><div class="row-sub">${e(r.designation||'')}</div></td><td>${e(r.order_ref||'—')}</td><td>${e(r.client_name||'—')}</td><td>${r.errors.length?`<span class="tag orange">À vérifier</span><small class="orli-errors">${e(r.errors.join(' · '))}</small>`:r.linked_launch_id?'<span class="tag green">Rapproché</span>':'<span class="tag">Non rapproché</span>'}</td></tr>`).join('')}</tbody></table></div>`;
}
async function orliAdmin(){
 if(!state.me?.admin){toast('Accès réservé à l’administration');return;}
 const batches=await api('/api/orli/imports');state.view='orli';state.orliBatches=batches;
 mount(`<div class="page-heading"><div><div class="page-kicker">IMPORT DE DONNÉES · LECTURE SEULE</div><h1 class="page-title">Imports ORLI<span style="color:#3e926e">.</span></h1><p class="page-lead">Conserver des instantanés d’exports, puis rapprocher manuellement les références avec les dossiers jaunes.</p></div></div><div class="panel orli-import"><h2>Importer un export</h2><p class="orli-help">Le format réel des exports doit être confirmé auprès de Framatex. Associez les noms des colonnes de votre fichier aux champs ci-dessous. Aucune connexion ni écriture dans ORLI.</p><form id="orli-form"><div class="field"><label for="orli-file">Fichier CSV UTF-8 ou XLSX (3 Mo maximum)</label><input id="orli-file" type="file" accept=".csv,.xlsx" required></div><div class="field"><label for="orli-map">Correspondance des colonnes (JSON)</label><textarea id="orli-map" rows="7" required spellcheck="false">${e(JSON.stringify({orli_ref:'Numero lancement',order_ref:'Numero commande',client_name:'Client',designation:'Designation',quantity:'Quantite',status:'Statut'},null,2))}</textarea><small>Le champ orli_ref est obligatoire. Supprimez les champs absents dans votre fichier. Les noms doivent correspondre exactement aux en-têtes.</small></div><button class="primary" type="submit">Importer sans modifier les lancements</button></form></div><div class="section-heading"><h2>Imports conservés</h2><small>Historique de lecture · aucun écrasement</small></div><div class="panel">${batches.length?`<div class="table-scroll"><table><thead><tr><th>Fichier</th><th>Date</th><th>Lignes valides</th><th>Action</th></tr></thead><tbody>${batches.map(b=>`<tr><td><strong>${e(b.file_name)}</strong><div class="row-sub">SHA-256 : ${e(b.file_sha256.slice(0,16))}…</div></td><td>${niceDate(b.imported_at)}</td><td>${e(b.valid_rows)} / ${e(b.total_rows)}</td><td><button class="secondary tiny" data-orli-batch="${e(b.id)}">Voir les lignes</button></td></tr>`).join('')}</tbody></table></div>`:'Aucun export importé pour le moment.'}</div><div id="orli-batch-detail" aria-live="polite"></div>`,'Imports ORLI');
 app.querySelector('#orli-form').addEventListener('submit',async evt=>{
   evt.preventDefault();const file=app.querySelector('#orli-file').files[0];if(!file)return;
   const fd=new FormData();fd.append('file',file);fd.append('mapping',app.querySelector('#orli-map').value);
   try{const imported=await api('/api/orli/imports',{method:'POST',body:fd});toast(`${imported.valid_rows}/${imported.total_rows} lignes valides importées`);await orliAdmin();await orliInspectBatch(imported.id)}catch(err){showErr(err)}
 });
 app.querySelectorAll('[data-orli-batch]').forEach(b=>b.addEventListener('click',()=>orliInspectBatch(b.dataset.orliBatch)));
}
async function orliInspectBatch(batchId){
 try{const data=await api('/api/orli/imports/'+encodeURIComponent(batchId));const slot=app.querySelector('#orli-batch-detail');if(!slot)return;
 slot.innerHTML=`<section class="orli-batch"><div class="section-heading"><h2>Fichier : ${e(data.file_name)}</h2><small>${e(data.total_rows)} ligne(s) · ${e(data.valid_rows)} valides</small></div><div class="panel">${orliRecordRows(data.rows)}</div></section>`;
 slot.scrollIntoView({behavior:'smooth',block:'nearest'});
 }catch(err){showErr(err)}
}
function renderOrliReconciliation(){
 const r=state.orliReconciliation;if(!r)return '';
 const mayLink=can('launch.update')&&!r.linked&&state.detail.status!=='Clôturé';
 return `<section class="orli-reconciliation"><div class="section-heading"><div><h2>Rapprochement ORLI</h2><small>Un dossier jaune = un lancement de fabrication</small></div>${state.me.admin?'<button class="secondary tiny" id="orli-admin-link">Gérer les imports</button>':''}</div>
 <div class="panel"><p class="orli-help">Les rapprochements proposés reposent uniquement sur la référence ORLI et/ou la référence de commande. Ils restent à confirmer ; les données source ne sont jamais synchronisées automatiquement.</p>
 ${r.linked?`<div class="orli-linked"><span class="tag green">Lien vérifié</span><strong>Référence ${e(r.linked.source_ref)}</strong><p>${e(r.linked.decision_note)}</p><small>Confirmé le ${niceDate(r.linked.confirmed_at)}</small></div>`:
 r.candidates.length?`<div class="table-scroll"><table><thead><tr><th>Référence</th><th>Commande</th><th>Client</th><th>Correspondance</th><th></th></tr></thead><tbody>${r.candidates.map(x=>`<tr><td><strong>${e(x.orli_ref)}</strong><div class="row-sub">${e(x.designation||'')}</div></td><td>${e(x.order_ref||'—')}</td><td>${e(x.client_name||'—')}</td><td><span class="tag">${e(x.matches.join(' + '))}</span>${x.conflicts.length?`<span class="tag orange">Écart : ${e(x.conflicts.join(', '))}</span>`:''}</td><td>${mayLink&&!x.already_linked?`<button class="secondary tiny" data-orli-link="${e(x.id)}">Examiner</button>`:x.already_linked?'<small>Déjà associé</small>':'<small>Consultation</small>'}</td></tr>`).join('')}</tbody></table></div>${r.truncated?'<p>Affichage limité à 100 suggestions.</p>':''}`:'<div class="orli-empty">Aucune correspondance exacte repérée. Importez un export ORLI ou renseignez la référence de commande du lancement. Aucune association ne sera déduite automatiquement.</div>'}</div></section>`;
}
function bindOrliReconciliation(){
 app.querySelector('#orli-admin-link')?.addEventListener('click',orliAdmin);
 app.querySelectorAll('[data-orli-link]').forEach(btn=>btn.addEventListener('click',()=>orliConfirmDialog(btn.dataset.orliLink)));
}
function orliConfirmDialog(id){
 const row=(state.orliReconciliation?.candidates||[]).find(r=>r.id===id);if(!row)return;
 const conflicts=row.conflicts||[];
 modal('Confirmer le rapprochement ORLI',`<p class="modal-desc">Vous associez manuellement <strong>${e(row.orli_ref)}</strong> au lancement <strong>${e(state.detail.name)}</strong>. Le lien ne crée ni ne modifie de fiche dans ORLI.</p>
 <div class="panel"><p>Commande ORLI : ${e(row.order_ref||'Non renseignée')}</p><p>Client ORLI : ${e(row.client_name||'Non renseigné')}</p>${conflicts.length?`<p class="orli-errors">Divergences : ${e(conflicts.join(', '))}. Leur acceptation nécessite une justification explicite.</p>`:''}</div>
 <form id="orli-link-form"><div class="field"><label for="orli-reason">Justification de l'association</label><textarea id="orli-reason" minlength="12" maxlength="1500" rows="3" required placeholder="Ex. Référence et commande confirmées auprès de la personne responsable"></textarea></div>${conflicts.length?'<label class="orli-checkbox"><input id="orli-override" type="checkbox"> J’ai vérifié les différences et accepte de les documenter.</label>':''}<label class="orli-checkbox"><input id="orli-confirm" type="checkbox" required> Je confirme avoir comparé les références et sélectionné le bon lancement.</label><div class="modal-actions"><button type="button" id="orli-cancel" class="secondary">Annuler</button><button type="submit" class="primary">Associer au dossier</button></div></form>`,true);
 overlay.querySelector('#orli-cancel').onclick=closeModal;
 overlay.querySelector('#orli-link-form').onsubmit=async evt=>{
  evt.preventDefault();try{await api('/api/launches/'+encodeURIComponent(state.detail.id)+'/orli-reconciliation/link',{method:'POST',body:JSON.stringify({record_id:row.id,confirmation:overlay.querySelector('#orli-confirm').checked,reason:overlay.querySelector('#orli-reason').value,override_conflicts:!!overlay.querySelector('#orli-override')?.checked})});closeModal();toast('Rapprochement enregistré · ORLI inchangé');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}
 };
}
