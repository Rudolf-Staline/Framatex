/* Completeness interactions, API calls and refresh of the existing views. */
'use strict';
function bindCompleteness(){
 app.querySelector('#edit-completeness')?.addEventListener('click',editCompletenessContext);
 app.querySelectorAll('[data-complete-validate]').forEach(el=>el.addEventListener('click',()=>reviewCompleteness(el.dataset.completeValidate)));
 app.querySelectorAll('[data-complete-exception]').forEach(el=>el.addEventListener('click',()=>editCompletenessException(el.dataset.completeException,false)));
 app.querySelectorAll('[data-complete-clear]').forEach(el=>el.addEventListener('click',()=>editCompletenessException(el.dataset.completeClear,true)));
}
async function editCompletenessContext(){
 try{
  const profiles=await api('/api/completeness/profiles'), c=state.completeness;
  modal('Paramétrer la complétude',`<p class="modal-desc">Les étapes et profils sont provisoires. Définir des règles nécessite une validation avec les équipes Framatex.</p><form id="context-form"><div class="field"><label>Profil documentaire</label><select id="c-profile"><option value="">Aucun profil (suivi désactivé)</option>${profiles.map(p=>`<option value="${e(p.id)}" ${p.id===c.profile_id?'selected':''}>${e(p.name)} · ${p.active_rules} règle(s)</option>`).join('')}</select></div><div class="field"><label>Étape actuelle du lancement</label><select id="c-phase">${c.phases.map(p=>`<option value="${e(p.code)}" ${p.code===c.phase?'selected':''}>${e(p.label)}</option>`).join('')}</select></div><p class="permission-lock">Changer d’étape modifie uniquement l’exigibilité documentaire, pas le statut général du lancement.</p><div class="modal-actions"><button class="secondary" type="button" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('check')} Enregistrer</button></div></form>`);
  overlay.querySelector('#cancel-modal').onclick=closeModal;
  overlay.querySelector('#context-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/launches/'+state.detail.id+'/completeness/context',{method:'PATCH',body:JSON.stringify({profile_id:val('c-profile')||null,phase:val('c-phase')})});closeModal();toast('Contexte de complétude mis à jour');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}};
 }catch(err){showErr(err)}
}
function reviewCompleteness(ruleId){
 const r=state.completeness.rows.find(x=>x.id===ruleId);if(!r)return;
 const candidates=r.documents.filter(d=>!d.validated);
 modal('Valider la version documentaire',`<p class="modal-desc">Vous confirmez avoir examiné cette version du document. L’approbation sera conservée dans le journal d’audit. Elle ne s’appliquera pas automatiquement aux versions ultérieures.</p><form id="approve-form"><div class="field"><label>Exigence</label><strong>${e(r.title)}</strong></div><div class="field"><label>Document à valider</label><select id="approve-doc">${candidates.map(d=>`<option value="${e(d.id)}">${e(d.title)} · version ${d.version}</option>`).join('')}</select></div><div class="modal-actions"><button type="button" class="secondary" id="cancel-modal">Annuler</button><button type="submit" class="primary">${icon('check')} Confirmer la validation</button></div></form>`);
 overlay.querySelector('#cancel-modal').onclick=closeModal;
 overlay.querySelector('#approve-form').onsubmit=async ev=>{ev.preventDefault();try{await api(`/api/launches/${state.detail.id}/completeness/rules/${ruleId}/validate`,{method:'POST',body:JSON.stringify({document_id:val('approve-doc')})});closeModal();toast('Version validée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}};
}
function editCompletenessException(ruleId,clear){
 const r=state.completeness.rows.find(x=>x.id===ruleId);if(!r)return;
 if(clear){modal('Lever cette exception',`<p class="modal-desc">Le justificatif reste conservé dans le journal d’audit. L’exigence sera de nouveau signalée si la pièce est toujours absente.</p><div class="modal-actions"><button class="secondary" id="cancel-modal">Annuler</button><button class="primary" id="clear-exception">Lever l’exception</button></div>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#clear-exception').onclick=()=>submitCompletenessException(ruleId,'',false);return}
 modal('Documenter une exception',`<p class="modal-desc"><strong>${e(r.title)}</strong> : une exception documentée ne signifie pas que la pièce est présente ni que le contrôle est validé.</p><form id="exception-form"><div class="field"><label>Justification métier (au moins 12 caractères)</label><textarea id="exception-reason" rows="5" minlength="12" maxlength="2000" required placeholder="Pourquoi cette pièce n’est-elle pas disponible à cette étape ?"></textarea></div><div class="modal-actions"><button class="secondary" type="button" id="cancel-modal">Annuler</button><button type="submit" class="primary">${icon('check')} Enregistrer</button></div></form>`);
 overlay.querySelector('#cancel-modal').onclick=closeModal;
 overlay.querySelector('#exception-form').onsubmit=ev=>{ev.preventDefault();submitCompletenessException(ruleId,val('exception-reason'),true)};
}
async function submitCompletenessException(ruleId,reason,active){try{await api(`/api/launches/${state.detail.id}/completeness/rules/${ruleId}/exception`,{method:'PUT',body:JSON.stringify({reason,active})});closeModal();toast(active?'Exception justifiée et enregistrée':'Exception levée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}}

async function completenessAdminPanel(){
 const profiles=await api('/api/admin/completeness/profiles');state.completionProfiles=profiles;
 return renderCompletenessAdmin(profiles);
}

function bindCompletenessAdmin(){
 app.querySelector('#create-profile')?.addEventListener('click',createCompletionProfile);
 app.querySelectorAll('[data-add-complete-rule]').forEach(el=>el.addEventListener('click',()=>createCompletenessRule(el.dataset.addCompleteRule)));
 app.querySelectorAll('[data-toggle-complete-rule]').forEach(el=>el.addEventListener('click',async()=>{try{await api('/api/admin/completeness/rules/'+el.dataset.toggleCompleteRule,{method:'PATCH',body:JSON.stringify({active:el.dataset.nextActive==='true'})});toast('État de la règle modifié');await admin()}catch(err){showErr(err)}}));
}
function createCompletionProfile(){
 modal('Créer un profil documentaire',`<p class="modal-desc">Un profil regroupe les documents attendus pour un type de lancement. Il peut rester sans règles tant que les étapes ne sont pas validées.</p><form id="profile-form"><div class="field"><label>Nom du profil</label><input id="p-name" minlength="3" maxlength="120" required placeholder="Ex. Fabrication standard (pilote)" /></div><div class="field"><label>Champ d’application</label><textarea id="p-description" maxlength="1200" rows="3" placeholder="Types de lancements concernés et décisions à confirmer"></textarea></div><div class="modal-actions"><button class="secondary" type="button" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('plus')} Créer le profil</button></div></form>`);
 overlay.querySelector('#cancel-modal').onclick=closeModal;
 overlay.querySelector('#profile-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/admin/completeness/profiles',{method:'POST',body:JSON.stringify({name:val('p-name'),description:val('p-description')})});closeModal();toast('Profil créé');await admin()}catch(err){showErr(err)}};
}
function createCompletenessRule(profileId){
 const profile=state.completionProfiles.find(p=>p.id===profileId);if(!profile)return;
 modal('Nouvelle exigence · '+profile.name,`<form id="rule-form"><div class="field"><label>Nom affiché de l’exigence *</label><input id="r-title" required minlength="3" maxlength="160" placeholder="Ex. Fiche d’emploi validée" /></div><div class="two-fields"><div class="field"><label>Sous-dossier *</label><select id="r-folder">${['jaune','rose','bleu','vert'].map(x=>`<option value="${x}">${x[0].toUpperCase()+x.slice(1)}</option>`).join('')}</select></div><div class="field"><label>Type exact du document *</label><input id="r-doctype" minlength="2" maxlength="100" required placeholder="Ex. Fiche d’emploi" /></div></div><div class="two-fields"><div class="field"><label>Exigible dès</label><select id="r-phase">${state.completenessPhases.map(p=>`<option value="${p.code}">${e(p.label)}</option>`).join('')}</select></div><div class="field"><label>Validation de version</label><select id="r-review"><option value="no">Non, présence uniquement</option><option value="yes">Oui, validation requise</option></select></div></div><div class="field"><label>Consigne ou condition métier</label><textarea id="r-guidance" rows="3" maxlength="1600" placeholder="À préciser avec Framatex"></textarea></div><p class="permission-lock">Le type doit correspondre exactement à celui choisi lors du dépôt. Les règles ne bloquent jamais automatiquement le lancement.</p><div class="modal-actions"><button type="button" class="secondary" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('plus')} Ajouter cette règle</button></div></form>`,true);
 overlay.querySelector('#cancel-modal').onclick=closeModal;
 overlay.querySelector('#rule-form').onsubmit=async ev=>{ev.preventDefault();try{await api(`/api/admin/completeness/profiles/${profileId}/rules`,{method:'POST',body:JSON.stringify({title:val('r-title'),folder:val('r-folder'),document_type:val('r-doctype'),due_phase:val('r-phase'),requires_validation:val('r-review')==='yes',guidance:val('r-guidance')})});closeModal();toast('Règle ajoutée');await admin()}catch(err){showErr(err)}};
}
