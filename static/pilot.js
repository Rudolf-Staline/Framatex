'use strict';
/* MVP 0.17 — retours pilote sans accès aux documents des autres utilisateurs. */
const PILOT_STATUS = {ouvert:'À examiner',en_cours:'En cours',resolu:'Résolu',ecarte:'Écarté'};
const PILOT_SEVERITY = {bloquant:'Bloquant',majeur:'Majeur',mineur:'Mineur',suggestion:'Suggestion'};

async function pilotPage(){
  const rows=await api('/api/pilot/reports');
  const launches=await api('/api/launches').catch(()=>[]);
  state.view='pilot';
  state.pilotReports=rows;
  state.pilotLaunches=launches;
  const counts={ouvert:0,en_cours:0,resolu:0,ecarte:0};
  rows.forEach(r=>{if(counts[r.status]!==undefined)counts[r.status]++});
  const items=rows.length?rows.map(r=>`<article class="pilot-card panel">
    <div class="pilot-card-head"><div><div class="page-kicker">${e(r.module)} · ${niceDate(r.created_at)}</div><h3>${e(r.title)}</h3></div><div class="pilot-tags"><span class="tag">${e(PILOT_SEVERITY[r.severity]||r.severity)}</span><span class="tag ${r.status==='resolu'?'green':r.status==='ouvert'?'orange':''}">${e(PILOT_STATUS[r.status]||r.status)}</span></div></div>
    <details><summary>Lire le signalement</summary><dl class="pilot-detail"><dt>Étapes de reproduction</dt><dd>${e(r.steps)}</dd><dt>Résultat attendu</dt><dd>${e(r.expected)}</dd><dt>Résultat observé</dt><dd>${e(r.observed)}</dd>${r.resolution_note?`<dt>Décision de traitement</dt><dd>${e(r.resolution_note)}</dd>`:''}</dl></details>
    ${state.me.admin?`<button class="secondary tiny" data-pilot-triage="${e(r.id)}">${icon('pencil')} Traiter le signalement</button>`:''}</article>`).join(''):'<div class="panel pilot-empty">Aucun signalement pour le moment. Commencez par exécuter un scénario de recette avec des données fictives.</div>';
  mount(`<div class="page-heading"><div><div class="page-kicker">QUALITÉ DU PILOTE</div><h1 class="page-title">Retours de recette<span style="color:#3e926e">.</span></h1><p class="page-lead">Consignez les difficultés constatées pendant les essais pour pouvoir les reproduire et suivre leur correction.</p></div><button class="primary" id="pilot-new">${icon('plus')} Signaler un problème</button></div>
    <div class="pilot-notice">Ce registre sert aux <strong>essais internes</strong>. N’y copiez pas de données clients, de mots de passe ni d’informations commerciales confidentielles.</div>
    <div class="pilot-summary"><div><strong>${rows.length}</strong><span>Signalements visibles</span></div><div><strong>${counts.ouvert}</strong><span>À examiner</span></div><div><strong>${counts.en_cours}</strong><span>En cours</span></div><div><strong>${counts.resolu}</strong><span>Résolus</span></div></div>
    <div class="pilot-list">${items}</div>`, 'Recette pilote');
  app.querySelector('#pilot-new').onclick=()=>openPilotReport();
  app.querySelectorAll('[data-pilot-triage]').forEach(b=>b.onclick=()=>openPilotTriage(b.dataset.pilotTriage));
}

function openPilotReport(){
  const launches=state.pilotLaunches||[];
  modal('Signaler un problème de recette', `<p class="modal-desc">Décrivez un comportement observé, pas une hypothèse. Ne joignez aucune donnée confidentielle.</p>
    <form id="pilot-report-form">
      <div class="two-fields"><div class="field"><label for="pilot-module">Fonctionnalité testée *</label><select id="pilot-module" required><option>Création de dossier</option><option>Documents et versions</option><option>Autorisations</option><option>OCR et classement</option><option>Validations et notifications</option><option>ORLI et matières</option><option>Navigation mobile</option><option>Autre fonctionnalité</option></select></div>
      <div class="field"><label for="pilot-severity">Impact constaté *</label><select id="pilot-severity"><option value="mineur">Mineur</option><option value="majeur">Majeur</option><option value="bloquant">Bloquant</option><option value="suggestion">Suggestion</option></select></div></div>
      <div class="field"><label for="pilot-launch">Lancement concerné (facultatif)</label><select id="pilot-launch"><option value="">Aucun / problème général</option>${launches.map(l=>`<option value="${e(l.id)}">${e(l.name)}</option>`).join('')}</select></div>
      <div class="field"><label for="pilot-title">Problème observé *</label><input id="pilot-title" maxlength="180" minlength="6" required placeholder="Ex. La nouvelle version n’apparaît pas après dépôt"></div>
      <div class="field"><label for="pilot-steps">Étapes précises pour reproduire *</label><textarea id="pilot-steps" rows="4" minlength="12" maxlength="4000" required placeholder="1. Ouvrir un lancement fictif... 2. Déposer un fichier... 3. Cliquer..."></textarea></div>
      <div class="field"><label for="pilot-expected">Comportement attendu *</label><textarea id="pilot-expected" rows="2" minlength="5" maxlength="2000" required></textarea></div>
      <div class="field"><label for="pilot-observed">Résultat réellement constaté *</label><textarea id="pilot-observed" rows="2" minlength="5" maxlength="2000" required></textarea></div>
      <div class="modal-actions"><button type="button" class="secondary" id="cancel-pilot">Annuler</button><button class="primary" type="submit">${icon('check')} Enregistrer le signalement</button></div>
    </form>`,true);
  overlay.querySelector('#cancel-pilot').onclick=closeModal;
  overlay.querySelector('#pilot-report-form').onsubmit=async ev=>{
    ev.preventDefault();const button=overlay.querySelector('button[type=submit]');button.disabled=true;
    try{await api('/api/pilot/reports',{method:'POST',body:JSON.stringify({module:val('pilot-module'),severity:val('pilot-severity'),launch_id:val('pilot-launch')||null,title:val('pilot-title'),steps:val('pilot-steps'),expected:val('pilot-expected'),observed:val('pilot-observed')})});closeModal();toast('Signalement enregistré');await pilotPage()}
    catch(err){button.disabled=false;showErr(err)}
  }
}

function openPilotTriage(id){
  if(!state.me.admin)return;
  const r=(state.pilotReports||[]).find(r=>r.id===id);if(!r)return;
  modal('Traiter un retour de recette',`<p class="modal-desc">${e(r.title)}</p><form id="pilot-triage-form">
    <div class="field"><label for="pilot-status">État du traitement</label><select id="pilot-status">${Object.entries(PILOT_STATUS).map(([k,v])=>`<option value="${k}" ${r.status===k?'selected':''}>${e(v)}</option>`).join('')}</select></div>
    <div class="field"><label for="pilot-note">Justification (obligatoire pour résoudre ou écarter)</label><textarea id="pilot-note" rows="4" maxlength="2000">${e(r.resolution_note)}</textarea></div>
    <div class="modal-actions"><button class="secondary" type="button" id="cancel-pilot">Annuler</button><button class="primary" type="submit">Enregistrer la décision</button></div></form>`);
  overlay.querySelector('#cancel-pilot').onclick=closeModal;
  overlay.querySelector('#pilot-triage-form').onsubmit=async ev=>{
    ev.preventDefault();try{await api(`/api/pilot/reports/${id}`,{method:'PATCH',body:JSON.stringify({status:val('pilot-status'),resolution_note:val('pilot-note')})});closeModal();toast('Décision enregistrée');await pilotPage()}catch(err){showErr(err)}
  }
}
