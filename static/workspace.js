'use strict';
// 0.9 — navigation et priorisation, sans décision automatique.
const PRIORITY_LABELS={urgent:'Échéance dépassée',high:'À examiner',normal:'À suivre'};
const AREA_TARGETS={documents:'.simple-document-section',completeness:'[data-detail-tool-panel="completeness"]',workflow:'.workflow-root',spec:'.spec-section',mail:'.mail-section'};

function priorityCard(item){
 const label=PRIORITY_LABELS[item.priority]||'À suivre';
 const hint=item.next_step||'Ouvrir le dossier pour examiner la situation.';
 const canAct=item.can_act===true;
 return `<button type="button" class="priority-item" data-workspace-launch="${e(item.launch_id)}" data-workspace-area="${e(item.area)}" data-workspace-folder="${e(item.folder||'')}"><span class="priority-dot ${e(item.priority)}"></span><span class="priority-content"><span class="priority-title">${e(item.title)}</span><span class="priority-description">${e(item.launch_name)} · ${e(item.description)}</span><span class="priority-guidance">${e(hint)}</span>${item.deadline?`<span class="priority-date">Échéance : ${e(item.deadline)}</span>`:''}</span><span class="priority-side"><span class="priority-label ${e(item.priority)}">${e(label)}</span><span class="priority-action-state">${canAct?'Je peux agir':'À suivre'}</span>${icon('arrow')}</span></button>`;
}
function prioritySummary(report){
 if(!report)return '';
 const actionable=(report.items||[]).filter(item=>item.can_act===true);
 const preview=actionable.slice(0,4);
 return `<div class="priority-header"><div><div class="page-kicker">TRAVAIL EN COURS</div><h2>Ce que vous pouvez traiter</h2><p>Seulement les points sur lesquels vos droits vous permettent d'intervenir. Cela ne constitue pas une affectation personnelle.</p></div><button class="secondary tiny" id="workspace-all">Tout consulter ${icon('arrow')}</button></div><div class="priority-list">${preview.length?preview.map(priorityCard).join(''):'<div class="priority-empty">Aucune intervention possible pour le moment. Vous pouvez consulter les points à suivre.</div>'}</div>`;
}
function renderPriorityWidget(){return `<section class="workspace-priorities" aria-label="Actions prioritaires">${prioritySummary(state.priorities)}</section>`}
function bindPriorityWidget(){
 app.querySelector('#workspace-all')?.addEventListener('click',()=>navigate('actions'));
 app.querySelectorAll('[data-workspace-launch]').forEach(button=>button.addEventListener('click',async()=>{
   const launchId=button.dataset.workspaceLaunch;
   const area=button.dataset.workspaceArea;
   const folder=button.dataset.workspaceFolder||(area==='mail'?'rose':state.folder);
   try{await openLaunch(launchId,folder);focusWorkspaceArea(area)}catch(err){showErr(err)}
 }));
}
function focusWorkspaceArea(area){
 // Workspace links select the correct tab and tool before scrolling.
 const moduleByArea={workflow:'workflow',spec:'spec',mail:'mail',completeness:'completeness'};
 if(state.view==='detail'){
  if(moduleByArea[area]){
   switchDetailView('tools');
   selectDetailTool(moduleByArea[area]);
  }else{
   switchDetailView('documents');
  }
 }
 const selector=AREA_TARGETS[area]||'.simple-document-section';
 const target=app.querySelector(selector);
 target?.scrollIntoView?.({behavior:'smooth',block:'start'});
}
async function workspaceActions(){
 state.priorities=await api('/api/workspace/priorities');state.view='actions';
 const report=state.priorities;
 const possible=(report.items||[]).filter(row=>row.can_act===true);
 const followup=(report.items||[]).filter(row=>row.can_act!==true);
 mount(`<div class="page-heading"><div><div class="page-kicker">MON TRAVAIL</div><h1 class="page-title">À traiter</h1><p class="page-lead">Ce qui demande une intervention et ce qui doit simplement être surveillé.</p></div></div>
  <section class="ux-explainer" aria-label="Comprendre les tâches"><div><strong>Comment lire cette page ?</strong><p>« Je peux agir » signifie que vous disposez des droits nécessaires, pas qu'une tâche vous a été personnellement attribuée. « À suivre » désigne un point visible que vous ne pouvez pas résoudre directement.</p></div></section>
  <div class="ux-task-metrics"><div><strong>${report.actionable_count??possible.length}</strong><span>Interventions possibles</span></div><div><strong>${report.followup_count??followup.length}</strong><span>Points à suivre</span></div></div>
  <div class="ux-task-tabs" role="group" aria-label="Type de suivi"><button type="button" class="selected" data-task-scope="possible" aria-pressed="true">Je peux agir <span>${possible.length}</span></button><button type="button" data-task-scope="followup" aria-pressed="false">À suivre <span>${followup.length}</span></button></div>
  <div class="ux-filter-row"><label for="priority-filter">Priorité</label><select id="priority-filter"><option value="all">Toutes</option><option value="urgent">Échéance dépassée</option><option value="high">Vérification nécessaire</option><option value="normal">À venir</option></select></div>
  <div id="workspace-full-list" class="priority-list" aria-live="polite"></div>
  <details class="ux-context-details"><summary>Comment les priorités sont-elles calculées ?</summary><p>Les rappels proviennent des documents attendus, des contrôles configurés, des changements signalés et des engagements datés. Ils ne sont ni des consignes automatiques ni une preuve d'erreur. Les habilitations sont vérifiées par le serveur avant chaque opération.</p></details>`,'À traiter');
 const listing=app.querySelector('#workspace-full-list');
 const select=app.querySelector('#priority-filter');
 const draw=()=>{const scope=app.querySelector('[data-task-scope].selected')?.dataset.taskScope||'possible';const pool=scope==='possible'?possible:followup;const data=pool.filter(row=>select.value==='all'||row.priority===select.value);listing.innerHTML=data.length?data.map(priorityCard).join(''):`<div class="priority-empty">${scope==='possible'?'Aucune action possible dans cette catégorie.':'Aucun point à suivre dans cette catégorie.'}</div>`;bindPriorityWidget()};
 app.querySelectorAll('[data-task-scope]').forEach(button=>button.addEventListener('click',()=>{app.querySelectorAll('[data-task-scope]').forEach(b=>{const selected=b===button;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected))});draw()}));
 select.addEventListener('change',draw);draw();
}
// Backward compatibility for existing assistance actions.
function openGuideDrawer(){return openFloatingAssistant()}
