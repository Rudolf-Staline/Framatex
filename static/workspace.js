'use strict';
// 0.9 — navigation et priorisation, sans décision automatique.
const PRIORITY_LABELS={urgent:'Échéance dépassée',high:'À examiner',normal:'À suivre'};
const AREA_TARGETS={documents:'.detail-layout',workflow:'.workflow-root',spec:'.spec-section',mail:'.mail-section'};

function priorityCard(item){
 const label=PRIORITY_LABELS[item.priority]||'À suivre';
 return `<button type="button" class="priority-item" data-workspace-launch="${e(item.launch_id)}" data-workspace-area="${e(item.area)}"><span class="priority-dot ${e(item.priority)}"></span><span class="priority-content"><span class="priority-title">${e(item.title)}</span><span class="priority-description">${e(item.launch_name)} · ${e(item.description)}</span>${item.deadline?`<span class="priority-date">Échéance : ${e(item.deadline)}</span>`:''}</span><span class="priority-side"><span class="priority-label ${e(item.priority)}">${e(label)}</span>${icon('arrow')}</span></button>`;
}
function prioritySummary(report){
 if(!report)return '';
 return `<div class="priority-header"><div><div class="page-kicker">POINTS À TRAITER</div><h2>Mes actions</h2><p>Priorités fondées sur les règles et sur les échéances connues, sans score arbitraire.</p></div><button class="secondary tiny" id="workspace-all">Tout consulter ${icon('arrow')}</button></div><div class="priority-kpis"><div><strong>${report.counts.urgent}</strong><span>Échéances dépassées</span></div><div><strong>${report.counts.high}</strong><span>Vérifications</span></div><div><strong>${report.counts.normal}</strong><span>À suivre sous 7 jours</span></div></div><div class="priority-list">${report.items.length?report.items.slice(0,5).map(priorityCard).join(''):'<div class="priority-empty">Aucune action prioritaire visible pour vos habilitations.</div>'}</div>${report.truncated?'<p class="priority-hint">La liste complète est limitée aux 100 premières actions.</p>':''}`;
}
function renderPriorityWidget(){return `<section class="workspace-priorities" aria-label="Actions prioritaires">${prioritySummary(state.priorities)}</section>`}
function bindPriorityWidget(){
 app.querySelector('#workspace-all')?.addEventListener('click',()=>navigate('actions'));
 app.querySelectorAll('[data-workspace-launch]').forEach(button=>button.addEventListener('click',async()=>{
   const launchId=button.dataset.workspaceLaunch;
   const area=button.dataset.workspaceArea;
   try{await openLaunch(launchId,area==='mail'?'rose':state.folder);focusWorkspaceArea(area)}catch(err){showErr(err)}
 }));
}
function focusWorkspaceArea(area){
 const target=app.querySelector(AREA_TARGETS[area]||'.detail-layout');
 target?.scrollIntoView?.({behavior:'smooth',block:'start'});
}
async function workspaceActions(){
 state.priorities=await api('/api/workspace/priorities');state.view='actions';
 const report=state.priorities;
 mount(`<div class="page-heading"><div><div class="page-kicker">SUIVI DES ACTIONS</div><h1 class="page-title">Mes actions<span style="color:#3e926e">.</span></h1><p class="page-lead">Les actions visibles respectent vos habilitations. Un dossier clôturé n'apparaît pas.</p></div></div><div class="workspace-priorities">${prioritySummary(report)}</div><div class="priority-toolbar"><label for="priority-filter">Afficher</label><select id="priority-filter"><option value="all">Toutes les priorités</option><option value="urgent">Échéances dépassées</option><option value="high">Vérifications à effectuer</option><option value="normal">À suivre</option></select><span>${report.total} action(s) détectée(s)</span></div><div id="workspace-full-list" class="priority-list"></div><p class="priority-hint">${e(report.method)} Les droits sur chaque document sont contrôlés par le serveur. Les alertes ne constituent pas une preuve d'erreur.</p>`,'Mes actions');
 const listing=app.querySelector('#workspace-full-list');
 const select=app.querySelector('#priority-filter');
 const draw=()=>{const data=report.items.filter(row=>select.value==='all'||row.priority===select.value);listing.innerHTML=data.length?data.map(priorityCard).join(''):'<div class="priority-empty">Aucune action dans ce filtre.</div>';bindPriorityWidget()};
 select.addEventListener('change',draw);draw();
 app.querySelector('#workspace-all')?.addEventListener('click',()=>app.querySelector('#priority-filter')?.focus());
}
function openGuide(){
 const current=state.detail?.id||null;
 modal('Assistant de navigation',`<div class="guide-intro">Une aide pratique pour retrouver les écrans et comprendre les procédures. Les réponses sont fondées sur des règles locales vérifiées : aucun document n’est transmis à un modèle externe.</div><form id="guide-form"><div class="field"><label for="guide-question">Que souhaitez-vous faire ?</label><input id="guide-question" maxlength="500" minlength="2" required placeholder="Ex. Où retrouver les engagements email ?" autocomplete="off"/></div><div class="guide-examples"><button type="button" class="secondary tiny" data-guide-example="Où déposer une facture ?">Déposer une facture</button><button type="button" class="secondary tiny" data-guide-example="Voir les priorités">Mes priorités</button><button type="button" class="secondary tiny" data-guide-example="Comment vérifier une exigence client ?">Exigences client</button></div><div class="modal-actions"><button class="primary" type="submit">${icon('search')} Rechercher</button></div></form><div id="guide-result" role="status" aria-live="polite"></div>`,true);
 overlay.querySelectorAll('[data-guide-example]').forEach(x=>x.addEventListener('click',()=>{overlay.querySelector('#guide-question').value=x.dataset.guideExample;overlay.querySelector('#guide-form').requestSubmit()}));
 overlay.querySelector('#guide-form').addEventListener('submit',async evt=>{
   evt.preventDefault();const form=overlay.querySelector('#guide-form');const result=overlay.querySelector('#guide-result');
   try{const response=await api('/api/assistant/guide',{method:'POST',body:JSON.stringify({question:form.querySelector('#guide-question').value,launch_id:current})});
       result.innerHTML=`<section class="guide-answer"><strong>${e(response.title)}</strong><p>${e(response.answer)}</p><small>${e(response.source)}</small>${response.destination?`<div class="modal-actions"><button id="guide-destination" type="button" class="primary tiny">Accéder à la rubrique ${icon('arrow')}</button></div>`:''}</section>`;
       result.querySelector('#guide-destination')?.addEventListener('click',async()=>{try{closeModal();if(response.destination==='detail'&&response.launch_id){await openLaunch(response.launch_id,response.folder||state.folder);focusWorkspaceArea(response.area)}else await navigate(response.destination)}catch(err){showErr(err)}})
   }catch(err){result.innerHTML=`<div class="error">${e(err.message)}</div>`}
 });
 overlay.querySelector('#guide-question')?.focus();
}
