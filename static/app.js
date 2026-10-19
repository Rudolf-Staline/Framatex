'use strict';
const ICON = {
  layers:'<rect x="4" y="5" width="16" height="14" rx="3"/><path d="M8 9h8M8 13h5"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3Z"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  out:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 17v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  download:'<path d="M12 3v13m-5-5 5 5 5-5M4 17v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  check:'<path d="m4 12 5 5L20 6"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  back:'<path d="m15 18-6-6 6-6"/>',
  arrow:'<path d="m9 18 6-6-6-6"/>',
  pencil:'<path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L9 17l-4 1 1-4Z"/>',
  x:'<path d="M18 6 6 18M6 6l12 12"/>',
  lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3"/>',
  activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
};
function icon(name){return `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[name]||ICON.file}</svg>`}
function e(s){return String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function niceDate(value){if(!value)return '—';const s=String(value).trim();const hasZone=/(?:Z|[+-]\d{2}:?\d{2})$/i.test(s);const normalized=/^\d{4}-\d\d-\d\dT/.test(s)&&!hasZone?s+'Z':s;const date=new Date(normalized);if(Number.isNaN(date.getTime()))return '—';return date.toLocaleDateString('fr-FR',{day:'2-digit',month:'short',year:'numeric'})}
function sizeText(n){return n>=1024*1024?`${(n/1024/1024).toFixed(1)} Mo`:`${Math.max(1,Math.ceil(n/1024))} Ko`}
const app=document.querySelector('#app'), overlay=document.querySelector('#overlay-root');
const state={me:null,view:'home',priorities:null,launches:[],dashboard:null,detail:null,completeness:null,completionProfiles:[],completenessPhases:[{code:'preparation',label:'Préparation'},{code:'approvisionnement',label:'Approvisionnement'},{code:'fabrication',label:'Fabrication'},{code:'expedition',label:'Expédition'},{code:'cloture',label:'Clôture'}],folder:'jaune',roles:[],users:[],audit:[],workflowReviews:[],workflowValues:[],workflowImpacts:[],workflowFields:[],workflowRules:[],qualityReport:null,excelInspections:[],specReport:null,mailReport:null,simGraph:null,simHistory:[],orliReconciliation:null,orliBatches:[],materials:null,approvalOverview:null,clientPublications:null,supplierRequests:null,approvalTemplates:[],approvalRoles:[],notifications:null,query:''};
async function api(path,options={}){
  const headers={'X-Framatex-Request':'1',...options.headers};
  if(options.body && !(options.body instanceof FormData))headers['Content-Type']='application/json';
  const res=await fetch(path,{...options,headers,credentials:'same-origin'});
  if(!res.ok){let data;try{data=await res.json()}catch{};if(res.status===401 && !path.includes('/auth/login')){state.me=null;renderLogin()}
    const error=typeof data?.detail==='string'?data.detail:`Erreur HTTP ${res.status}`;throw new Error(error)}
  if(res.headers.get('content-type')?.includes('application/json'))return await res.json();return res;
}
let timeout;function toast(msg){const el=document.querySelector('#toast');el.textContent=msg;el.classList.add('visible');clearTimeout(timeout);timeout=setTimeout(()=>el.classList.remove('visible'),3400)}
function showErr(err){toast(err.message||String(err))}
function can(action,folder=null){return !!state.me?.admin||state.me?.permissions?.some(p=>p.action===action&&(folder?p.folder===null||p.folder===folder:p.folder===null))}
function statusTag(s){return `<span class="tag ${s==='À compléter'?'orange':s==='Clôturé'?'green':s==='En validation'?'blue':''}">${e(s)}</span>`}
function topbar(label){
 return `<header class="topbar"><button type="button" class="lc-global-search" id="global-search" title="Rechercher un dossier">${icon('search')}<span>Rechercher un dossier, un document…</span></button><div class="topbar-actions"><button type="button" class="lc-notification-btn" id="top-notifications" title="Notifications" aria-label="Consulter les notifications">${icon('clock')}</button><span class="lc-user-avatar" aria-hidden="true">${e((state.me?.name||'?').trim().split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase())}</span><span class="lc-top-username">${e(state.me?.name||'Utilisateur')}</span></div></header>`;
}
function sidebar(){
 const primary=[['home','grid','Accueil'],['launches','folder','Dossiers'],['actions','clock','À traiter'],['notifications','info','Notifications']];
 const tools=[['pilot','info','Aide & retours'],...(state.me.admin?[['orli','file','Imports ORLI'],['admin','users','Administration'],['audit','shield','Journal d’activité']]:[])];
 const active=view=>state.view===view||(state.view==='detail'&&view==='launches');
 const items=list=>list.map(([view,ico,label])=>`<button type="button" class="nav-btn ${active(view)?'active':''}" data-view="${view}" title="${label}" aria-current="${active(view)?'page':'false'}">${icon(ico)}<span class="nav-text">${label}</span>${active(view)?'<span class="nav-current" aria-hidden="true">›</span>':''}</button>`).join('');
 const toolsOpen=!!state.sidebarAdminOpen||tools.some(([view])=>active(view));
 return `<aside class="sidebar sidebar-rail sidebar-light" aria-label="Navigation Framatex">
   <div class="rail-brand"><div class="rail-logo" aria-hidden="true">${icon('folder')}</div><span class="rail-brand-name">Framatex</span></div>
   <nav class="sidebar-nav rail-primary" aria-label="Navigation principale">${items(primary)}</nav>
   <details class="rail-management" ${toolsOpen?'open':''}><summary title="Outils de gestion">${icon('users')}<span class="nav-text">Gestion</span><span class="rail-chevron" aria-hidden="true">⌄</span></summary>
     <nav class="sidebar-nav rail-management-links" aria-label="Gestion et contrôle">${items(tools)}</nav>
   </details>
   <div class="sidebar-bottom rail-account"><div class="user"><div class="avatar" aria-hidden="true">${e(state.me.name.slice(0,2).toUpperCase())}</div><span class="user-name" title="${e(state.me.name)}">${e(state.me.name)}</span></div>
     <button type="button" class="logout" id="logout" title="Déconnexion" aria-label="Déconnexion">${icon('out')}<span>Quitter</span></button></div>
 </aside>`;
}
function mount(html,label){
 app.innerHTML=`<div class="app-shell"${state.view==='detail'&&['jaune','rose','bleu','vert'].includes(state.folder)?` data-folder-theme="${state.folder}"`:''}>${sidebar()}<div class="main">${topbar(label)}<main class="content">${html}</main></div></div>`;
 app.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>navigate(n.dataset.view)));
 app.querySelector('.rail-management')?.addEventListener('toggle',event=>{state.sidebarAdminOpen=event.currentTarget.open});
 syncFloatingAssistant();
 app.querySelector('#global-search')?.addEventListener('click',async()=>{await navigate('launches');app.querySelector('#launch-search')?.focus()});
 app.querySelector('#top-notifications')?.addEventListener('click',()=>navigate('notifications'));

 app.querySelector('#logout').addEventListener('click',async()=>{try{await api('/api/auth/logout',{method:'POST'})}catch{}state.me=null;state.detail=null;renderLogin()});
}
function renderLogin(){overlay.innerHTML='';syncFloatingAssistant();app.innerHTML=`<div class="login-page login-rebalanced"><main class="login-stage">
  <div class="login-visual" aria-hidden="true"><div class="login-visual-orbit"></div><div class="login-visual-floor"></div><div class="login-folder login-folder-back"></div><div class="login-folder login-folder-middle"></div><div class="login-folder login-folder-front"><span class="login-folder-stripe"></span><span class="login-folder-line"></span><span class="login-folder-line login-folder-line-small"></span><span class="login-folder-dot"></span></div></div>
  <section class="login-form-wrap"><div class="login-auth-content"><div class="login-form-brand"><span class="login-form-brand-icon">${icon('folder')}</span><strong>Framatex</strong></div>
    <h1 id="login-title">Connexion</h1>
    <form id="login-form" class="login-form" aria-labelledby="login-title">
      <div id="login-error" role="alert" aria-live="assertive"></div>
      <div class="field"><label for="email">Adresse e-mail</label><input id="email" type="email" autocomplete="username" required /></div>
      <div class="field"><label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" required /></div>
      <button class="primary" type="submit">Se connecter</button>
    </form>
  </div></section></main></div>`;
  app.querySelector('#login-form').addEventListener('submit',async evt=>{evt.preventDefault();const btn=evt.target.querySelector('button');btn.disabled=true;try{state.me=await api('/api/auth/login',{method:'POST',body:JSON.stringify({email:app.querySelector('#email').value,password:app.querySelector('#password').value})});state.me=await api('/api/auth/me');if(!(await paperOpenDeepLink()))await navigate('home')}catch(err){app.querySelector('#login-error').innerHTML=`<div class="error">${e(err.message)}</div>`}finally{btn.disabled=false}})
}
function tableLaunches(list){if(!list.length)return `<div class="empty"><div class="empty-icon">${icon('folder')}</div><strong>Aucun dossier pour l’instant</strong>Créez votre premier lancement de fabrication pour démarrer.</div>`;return `<div class="table-scroll"><table><thead><tr><th>Lancement</th><th>Client</th><th>Référence ORLI</th><th>Statut</th><th>Créé le</th><th></th></tr></thead><tbody>${list.map(l=>`<tr class="item-row" data-launch="${e(l.id)}" tabindex="0" aria-label="Ouvrir ${e(l.name)}"><td><div class="row-title">${e(l.name)}</div><div class="row-sub">${e(l.order_ref||'Aucune référence de commande')}</div></td><td>${e(l.client_name||'—')}</td><td>${l.orli_ref?`<span class="tag">${e(l.orli_ref)}</span>`:'<span class="muted small">Non attribuée</span>'}</td><td>${statusTag(l.status)}</td><td class="small">${niceDate(l.created_at)}</td><td>${icon('arrow')}</td></tr>`).join('')}</tbody></table></div>`}
function bindLaunchRows(){
 app.querySelectorAll('[data-launch]').forEach(row=>{
   const open=()=>openLaunch(row.dataset.launch).catch(showErr);
   row.addEventListener('click',open);
   row.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();open()}});
 });
}
function dashboardLaunchRows(list){
 if(!list.length)return `<div class="dash-no-results">${icon('folder')}<strong>Aucun lancement à afficher</strong><p>Essayez un autre filtre ou créez votre premier lancement.</p></div>`;
 return `<div class="dash-table-scroll"><table class="dash-table"><thead><tr><th>Lancement</th><th>Client</th><th>Référence ORLI</th><th>Statut</th><th>Dernière activité</th><th><span class="sr-only">Ouvrir</span></th></tr></thead><tbody>${list.map(l=>`<tr class="item-row" data-launch="${e(l.id)}" tabindex="0" aria-label="Ouvrir ${e(l.name)}">
 <td><strong><span class="lc-table-folder" aria-hidden="true">${icon('folder')}</span>${e(l.name)}</strong><small>${e(l.order_ref||'Lancement de fabrication')}</small></td>
 <td>${e(l.client_name||'—')}</td><td>${l.orli_ref?e(l.orli_ref):'<span class="muted">Non attribuée</span>'}</td>
 <td>${statusTag(l.status)}</td><td class="dash-date">${niceDate(l.updated_at||l.created_at)}</td><td class="dash-row-arrow">${icon('arrow')}</td>
 </tr>`).join('')}</tbody></table></div>`;
}
async function home(){
 // Every metric comes from the same permission-filtered API as the business screens.
 const [priorities,d,launches]=await Promise.all([
   api('/api/workspace/priorities'),api('/api/dashboard'),api('/api/launches')]);
 state.priorities=priorities;state.dashboard=d;state.launches=launches;state.view='home';
 if(typeof assistantContextLaunch!=='undefined')assistantContextLaunch=null;
 if(!launches.some(l=>l.id===state.quickLaunchId))state.quickLaunchId=launches[0]?.id||null;
 
 
 const priorityPreview=(priorities.items||[]).slice(0,5);
 mount(`<div class="simple-home dashboard-022 iw-home">
  <header class="iw-page-head"><div><span class="iw-eyebrow">DOSSIERS DE FABRICATION</span><h1>Suivi des lancements</h1><p class="iw-description">${launches.filter(l=>l.status!=='Clôturé').length} en cours · ${launches.filter(l=>l.status==='À compléter').length} à compléter</p></div>${can('launch.create')?`<button type="button" class="primary" id="create-launch">${icon('plus')} Créer un dossier</button>`:''} </header>
  <div class="dash-main-grid">
   <section class="dash-card dash-launches" aria-labelledby="dash-launch-heading">
    <div class="dash-card-head"><h2 id="dash-launch-heading">Lancements</h2><button type="button" class="dash-link" id="all-launches">Voir tous ${icon('arrow')}</button></div>
    <div class="dash-filter-bar"><div class="dash-segments" aria-label="Filtrer les lancements">
      <button type="button" data-home-tab="all" class="selected" aria-pressed="true">Tous</button>
      <button type="button" data-home-tab="recent" aria-pressed="false">Récents</button>
      <button type="button" data-home-tab="incomplete" aria-pressed="false">À compléter</button>
    </div><div class="dash-filter-tools">
      <label class="dash-filter-search">${icon('search')}<input id="home-search" type="search" placeholder="Rechercher..." autocomplete="off" aria-label="Rechercher un lancement" /></label>
      <select id="home-status" aria-label="Filtrer par statut"><option value="all">Tous les statuts</option>
        <option value="À compléter">À compléter</option><option value="En cours">En cours</option>
        <option value="En validation">En validation</option><option value="Clôturé">Clôturé</option></select>
    </div></div>
    <div id="home-launch-table">${dashboardLaunchRows(launches.slice(0,8))}</div>
    <div class="dash-table-foot"><span id="home-result-count">${Math.min(8,launches.length)} lancement(s) affiché(s)</span></div>
   </section>
   <aside class="dash-side-panels" aria-label="Raccourcis et actions">
    <section class="dash-card dash-to-do"><div class="dash-card-head"><h2>Points signalés</h2><button type="button" class="dash-link" id="workspace-all-hero">Tout voir ${icon('arrow')}</button></div>
      <p class="iw-attention-note">Documents à vérifier, échéances et points de suivi. Ils ne sont pas nécessairement attribués à votre compte.</p>
      ${priorityPreview.length?`<div class="dash-priority-list">${priorityPreview.map(item=>`<button type="button" class="dash-priority-row" data-workspace-launch="${e(item.launch_id)}" data-workspace-area="${e(item.area)}" data-workspace-folder="${e(item.folder||'')}">
        <span class="dash-priority-dot ${e(item.priority)}"></span><span><strong>${e(item.title)}</strong><small>${e(item.launch_name)}</small></span>${icon('arrow')}</button>`).join('')}</div>`:'<div class="dash-empty-actions">Aucun point signalé.</div>'}
    </section>
   </aside>
  </div>

 </div>`,'Accueil');
 const draw=()=>{
   let result=[...state.launches];
   const active=app.querySelector('[data-home-tab].selected')?.dataset.homeTab||'all';
   if(active==='recent')result=result.slice(0,5);
   if(active==='incomplete')result=result.filter(l=>l.status==='À compléter');
   const status=app.querySelector('#home-status')?.value||'all';
   if(status!=='all')result=result.filter(l=>l.status===status);
   const query=(app.querySelector('#home-search')?.value||'').trim().toLocaleLowerCase('fr');
   if(query)result=result.filter(l=>[l.name,l.order_ref,l.orli_ref,l.client_name].join(' ').toLocaleLowerCase('fr').includes(query));
   const shown=result.slice(0,8);
   app.querySelector('#home-launch-table').innerHTML=dashboardLaunchRows(shown);
   app.querySelector('#home-result-count').textContent=`${shown.length} sur ${result.length} lancement(s)`;
   bindLaunchRows();
 };
 app.querySelectorAll('[data-home-tab]').forEach(button=>button.addEventListener('click',()=>{
   app.querySelectorAll('[data-home-tab]').forEach(tab=>{const selected=tab===button;tab.classList.toggle('selected',selected);tab.setAttribute('aria-pressed',String(selected))});
   draw();
 }));
 app.querySelector('#home-search').addEventListener('input',draw);
 app.querySelector('#home-status').addEventListener('change',draw);
 app.querySelector('#all-launches')?.addEventListener('click',()=>navigate('launches'));
 app.querySelector('#create-launch')?.addEventListener('click',openNewLaunch);
 app.querySelector('#workspace-all-hero')?.addEventListener('click',()=>navigate('actions'));
 bindPriorityWidget();
 bindLaunchRows();
}

async function launchList(){state.view='launches';state.launches=await api('/api/launches');mount(`<div class="page-heading"><div><div class="page-kicker">${icon('folder')} DOSSIERS DE FABRICATION</div><h1 class="page-title">Dossiers jaunes</h1><p class="page-lead">Un dossier par lancement de fabrication. Retrouvez les documents et leur suivi au même endroit.</p></div>${can('launch.create')?`<button class="primary" id="create-launch">${icon('plus')} Nouveau dossier</button>`:''}</div><div class="toolbar"><label class="searchbar">${icon('search')}<input id="launch-search" value="${e(state.query)}" placeholder="Rechercher par client, lancement, ORLI..." aria-label="Rechercher des dossiers" /></label><span class="muted small">${state.launches.length} dossier(s) au total</span></div><div class="panel" id="launches-table">${tableLaunches(state.launches)}</div>`,'Dossiers jaunes');bindLaunchRows();app.querySelector('#create-launch')?.addEventListener('click',openNewLaunch);app.querySelector('#launch-search').addEventListener('input',ev=>{state.query=ev.target.value;const term=state.query.toLowerCase();document.querySelector('#launches-table').innerHTML=tableLaunches(state.launches.filter(l=>[l.name,l.client_name,l.orli_ref,l.order_ref].join(' ').toLowerCase().includes(term)));bindLaunchRows()})}
async function openLaunch(id,folder=state.folder){const keepSection=state.view==='detail'&&state.detail?.id===id;const [detail,completeness,reviews,values,impacts,fields,quality,excels,specs,mails,simGraph,simHistory,orliReconciliation,materials,approvalOverview]=await Promise.all([api('/api/launches/'+encodeURIComponent(id)),api('/api/launches/'+encodeURIComponent(id)+'/completeness'),api('/api/launches/'+encodeURIComponent(id)+'/reviews'),api('/api/launches/'+encodeURIComponent(id)+'/values'),api('/api/launches/'+encodeURIComponent(id)+'/impacts'),api('/api/business-value-fields'),api('/api/launches/'+encodeURIComponent(id)+'/quality'),api('/api/launches/'+encodeURIComponent(id)+'/excel-inspections'),api('/api/launches/'+encodeURIComponent(id)+'/specifications'),can('document.read','rose')?api('/api/launches/'+encodeURIComponent(id)+'/emails'):Promise.resolve(null),api('/api/launches/'+encodeURIComponent(id)+'/dependency-graph'),can('document.read','jaune')?api('/api/launches/'+encodeURIComponent(id)+'/impact-simulations'):Promise.resolve([]),api('/api/launches/'+encodeURIComponent(id)+'/orli-reconciliation'),can('document.read','jaune')&&can('document.read','rose')?api('/api/launches/'+encodeURIComponent(id)+'/materials'):Promise.resolve(null),api('/api/launches/'+encodeURIComponent(id)+'/approval-overview')]);[state.clientPublications,state.supplierRequests]=await Promise.all([api(`/api/launches/${encodeURIComponent(id)}/client-publications`),api(`/api/launches/${encodeURIComponent(id)}/supplier-requests`)]);state.approvalOverview=approvalOverview;state.materials=materials;state.orliReconciliation=orliReconciliation;state.simGraph=simGraph;state.simHistory=simHistory;state.mailReport=mails;state.specReport=specs;state.qualityReport=quality;state.excelInspections=excels;state.detail=detail;state.completeness=completeness;state.workflowReviews=reviews;state.workflowValues=values;state.workflowImpacts=impacts;state.workflowFields=fields;state.view='detail';state.folder=folder;state.detailSection=keepSection?state.detailSection:'documents';renderDetail()}
function installDetailNavigation(){
 const content=app.querySelector('main.content');if(!content)return;
 const sections=[
  ['documents','Documents','.detail-layout'],
  ['completude','Complétude','.completion-shell, .completion-notice'],
  ['decisions','Décisions et impacts','.workflow-root'],
  ['fiabilite','Fiabilité documentaire','.quality-root'],
  ['lecture','OCR et classement','.intake-section'],
  ['passeports','QR et passeports','.paper-section'],
  ['exigences','Exigences client','.spec-section'],
  ['courriels','Emails et engagements','.mail-section'],
  ['simulation','Simulation','.sim-section'],
  ['orli','Rapprochement ORLI','.orli-reconciliation-section'],
  ['matieres','Matières','.material-section'],
  ['validations','Circuits de validation','.approval-section'],
  ['partage','Clients et fournisseurs','.sharing-section']
 ];
 const available=[];
 for(const [id,label,selector] of sections){const target=content.querySelector(selector);if(!target)continue;
   const anchor='section-'+id;target.id=target.id||anchor;
   available.push([target.id,label]);}
 if(available.length<2)return;
 const nav=document.createElement('nav');nav.className='detail-jump';nav.setAttribute('aria-label','Accès rapide aux rubriques du lancement');
 nav.innerHTML='<label for="detail-section-select">Aller à une rubrique</label><select id="detail-section-select"><option value="">Choisir une section…</option>'+available.map(([id,label])=>`<option value="${e(id)}">${e(label)}</option>`).join('')+'</select><button type="button" class="secondary tiny" id="detail-go-top">↑ Haut de page</button>';
 const heading=content.querySelector('.detail-head');heading?.insertAdjacentElement('afterend',nav);
 nav.querySelector('select').addEventListener('change',ev=>{const target=document.getElementById(ev.target.value);if(target){target.scrollIntoView({behavior:'smooth',block:'start'});}});
 nav.querySelector('#detail-go-top').addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
}


const DETAIL_TOOL_GROUPS=[
 {label:'Qualité',tools:[
  ['quality','Cohérence et Excel','shield','Écarts documentaires et vérifications Excel',()=>renderQuality()],
  ['completeness','Complétude','check','Exigences documentaires selon le contexte',()=>renderCompleteness()],
  ['workflow','Décisions et impacts','activity','Valeurs suivies et décisions humaines',()=>renderWorkflow()]
 ]},
 {label:'Documents',tools:[
  ['intake','Lecture et OCR','file','Lire et classer les pièces',()=>renderIntake()],
  ['paper','QR et versions','grid','Passerelle papier et traçabilité',()=>renderPaper()]
 ]},
 {label:'Exigences',tools:[
  ['spec','Exigences client','check','Couverture et ambiguïtés',()=>renderSpec()],
  ['mail','Engagements e-mail','file','Engagements issus des échanges',()=>renderMail()]
 ]},
 {label:'Suivi',tools:[
  ['sim','Simulation d’impact','activity','Conséquences potentielles des modifications',()=>renderImpactSimulation()],
  ['orli','Rapprochement ORLI','file','Références et rapprochements',()=>renderOrliReconciliation()],
  ['materials','Suivi matière','grid','Consommations et mouvements',()=>renderMaterialReport()],
  ['approvals','Faire valider un document','shield','Consulter et suivre les validations par version',()=>renderApprovals()],
  ['sharing','Partage externe','users','Clients et fournisseurs',()=>renderSharing()]
 ]}
];
function renderDetailToolWorkspace(){
 const tools=DETAIL_TOOL_GROUPS.flatMap(group=>group.tools);
 const chosen=tools.find(tool=>tool[0]===state.detailTool)||tools[0];
 const active=chosen[0];
 const groups=DETAIL_TOOL_GROUPS.map(group=>
  '<optgroup label="'+e(group.label)+'">'+group.tools.map(([id,label])=>
   '<option value="'+id+'"'+(active===id?' selected':'')+'>'+e(label)+'</option>'
  ).join('')+'</optgroup>'
 ).join('');
 const panels=tools.map(([id,label,ico,description,renderer])=>
  '<section id="detail-tool-'+id+'" class="detail-tool-panel" data-detail-tool-panel="'+id+'" role="region" aria-label="'+e(label)+'"'+(active===id?'':' hidden')+'>'+
   (renderer()||'<div class="detail-tool-unavailable">Aucune donnée accessible pour cette fonctionnalité.</div>')+
  '</section>'
 ).join('');
 return '<section class="detail-tool-workspace" id="detail-tool-workspace" aria-label="Outils du lancement">'+
  '<div class="detail-tool-toolbar"><div class="detail-tool-toolbar-heading"><h2>Contrôles et outils</h2></div>'+
   '<label class="detail-tool-picker" for="detail-tool-select"><span>Fonctionnalité</span><select id="detail-tool-select">'+groups+'</select></label>'+
  '</div><div class="detail-tool-panel-container">'+panels+'</div></section>';
}
function selectDetailTool(id){
 const chosen=DETAIL_TOOL_GROUPS.flatMap(group=>group.tools).find(tool=>tool[0]===id);
 if(!chosen)return;
 const container=app.querySelector('#detail-tool-workspace');
 if(!container)return;
 state.detailTool=id;
 const select=container.querySelector('#detail-tool-select');
 if(select)select.value=id;
 container.querySelectorAll('[data-detail-tool-panel]').forEach(panel=>{
  panel.hidden=panel.dataset.detailToolPanel!==id;
 });
}
function bindDetailToolWorkspace(){
 app.querySelector('#detail-tool-select')?.addEventListener('change',event=>selectDetailTool(event.target.value));
}
function switchDetailView(view){
 if(!['documents','tools'].includes(view))return;
 state.detailSection=view;
 app.querySelectorAll('[data-detail-view]').forEach(button=>{
  const active=button.dataset.detailView===view;
  button.setAttribute('aria-selected',String(active));
  button.tabIndex=active?0:-1;
 });
 app.querySelectorAll('[data-detail-view-panel]').forEach(panel=>{
  panel.hidden=panel.dataset.detailViewPanel!==view;
 });
}
function showLaunchInformation(){
 const d=state.detail;
 if(!d)return;
 const rows=[
  ['Client',d.client_name||'Non renseigné'],
  ['Commande',d.order_ref||'Non renseignée'],
  ['Référence ORLI',d.orli_ref||'Non renseignée'],
  ['Dernière mise à jour',niceDate(d.updated_at)],
  ['Identifiant technique',d.id]
 ];
 modal('Informations du lancement','<dl class="launch-information-list">'+rows.map(([label,value])=>
  '<div><dt>'+e(label)+'</dt><dd>'+e(value)+'</dd></div>'
 ).join('')+'</dl>');
}

function renderDossierSummary(folder,docs){
 const records=(state.approvalOverview?.items||[]).filter(x=>x.folder===folder.slug && docs.some(doc=>doc.id===x.document_id));
 const pending=records.filter(x=>x.run?.status==='pending');
 const approved=records.filter(x=>x.run?.status==='approved');
 const list=records.filter(x=>x.run||x.template).slice(0,3);
 return `<aside class="lc-detail-summary" aria-label="Suivi du sous-dossier">
 <section class="lc-summary-card"><div class="lc-summary-head"><h3>État du sous-dossier</h3></div>
  <div class="lc-summary-figure"><strong>${docs.length}</strong><span>document(s) accessible(s)</span></div>
  <div class="lc-summary-pair"><span>Versions approuvées</span><strong>${approved.length}</strong></div>
  <div class="lc-summary-pair"><span>Validations en cours</span><strong>${pending.length}</strong></div>
  <p class="lc-helper-note">Les validations concernent une version précise. Ce décompte ne mesure pas la complétude du dossier.</p></section>
 <section class="lc-summary-card"><div class="lc-summary-head"><h3>Circuits de validation</h3></div>
  ${list.length?`<div class="lc-approval-peek">${list.map(x=>`<div class="lc-peek-row"><span class="lc-peek-icon">${icon('file')}</span><div><strong>${e(x.document_title)}</strong><small>${x.run?.status==='approved'?'Approuvée':x.run?.status==='pending'?'Validation en cours':x.run?.status==='changes_requested'?'Corrections demandées':x.run?.status==='rejected'?'Refusée':x.run?.status==='stale'?'Ancienne version':'Demande non lancée'}</small></div></div>`).join('')}</div>`:'<p class="lc-summary-empty">Aucun circuit configuré pour les documents visibles.</p>'}
  <button type="button" class="secondary lc-summary-action" id="lc-open-validations">${icon('check')} Voir les validations ${icon('arrow')}</button></section>
 <section class="lc-summary-card lc-summary-info"><h3>Informations</h3>
  <div class="lc-summary-pair"><span>Sous-dossier</span><strong>${e(folder.label)}</strong></div>
  <div class="lc-summary-pair"><span>Lecture</span><strong>${folder.can_read?'Autorisée':'Limitée'}</strong></div>
  <div class="lc-summary-pair"><span>Dépôt</span><strong>${folder.can_write?'Autorisé':'Non autorisé'}</strong></div>
  <button type="button" class="link" id="lc-show-info">Informations du lancement ${icon('arrow')}</button></section>
 </aside>`;
}
function renderDetail(){
 const d=state.detail;
 const f=d.folders.find(x=>x.slug===state.folder)||d.folders[0];
 const docs=f.can_read?f.documents:[];
 const folderNames={jaune:'Jaune',rose:'Rose',bleu:'Bleu',vert:'Vert'};
 const count=f.can_read?docs.length:0;
 mount(`<div class="simple-detail">
 <header class="detail-head simple-detail-head detail-compact-header lc-detail-header">
  <div class="detail-identity"><button type="button" class="detail-back" id="back-launches" title="Tous les dossiers" aria-label="Revenir aux lancements">${icon('back')}</button><div>
  <h1 class="page-title">${e(d.name)}</h1><div class="detail-inline-meta">${statusTag(d.status)}${d.client_name?`<span>${e(d.client_name)}</span>`:''}${d.order_ref?`<span>Commande ${e(d.order_ref)}</span>`:''}</div>
  </div></div>
  <div class="detail-header-actions"><button type="button" class="secondary" id="launch-info">${icon('info')} Informations</button>
  ${d.can_update?`<button type="button" class="secondary" id="edit-launch">${icon('pencil')} Modifier</button>`:''}<button type="button" class="secondary" id="lc-header-validations">${icon('check')} Validations</button></div>
 </header>
 <nav class="detail-main-tabs" role="tablist" aria-label="Vue du dossier">
  <button type="button" role="tab" id="detail-tab-documents" data-detail-view="documents" aria-controls="detail-view-documents" aria-selected="${state.detailSection==='tools'?'false':'true'}">Documents</button>
  <button type="button" role="tab" id="detail-tab-tools" data-detail-view="tools" aria-controls="detail-view-tools" aria-selected="${state.detailSection==='tools'?'true':'false'}">Contrôles et outils</button>
 </nav>
 <section class="detail-view-panel lc-documents-layout" data-detail-view-panel="documents" id="detail-view-documents" role="tabpanel" aria-labelledby="detail-tab-documents" ${state.detailSection==='tools'?'hidden':''}>

 <nav class="folder-tabs" aria-label="Sous-dossiers du lancement">${d.folders.map(folder=>`<button type="button" class="folder-tab folder-${e(folder.slug)} ${folder.slug===state.folder?'selected':''}" data-folder="${e(folder.slug)}" aria-pressed="${folder.slug===state.folder?'true':'false'}">
 <span class="lc-folder-symbol" aria-hidden="true">${icon('folder')}</span><span class="folder-tab-title">${folderNames[folder.slug]||e(folder.slug)}</span><span class="folder-tab-count">${folder.can_read?folder.documents.length:'—'}</span></button>`).join('')}</nav>
 <section class="simple-document-section"><div class="simple-section-heading"><div><span class="section-index">${e(folderNames[f.slug]||f.slug)} · ${e(f.label)}</span><h2>Documents — ${e(folderNames[f.slug]||f.slug)} <span class="document-count">${count}</span></h2></div>
 ${f.can_write?`<button class="primary" id="upload-doc">${icon('plus')} Ajouter un document</button>`:''}</div>
 <div class="panel">${!f.can_read?`<div class="denied">${icon('lock')}<p>Vous n’avez pas accès à cette rubrique.</p></div>`:docs.length?`<div class="table-scroll"><table><thead><tr><th>Document</th><th>Type</th><th>Version</th><th>Validation</th><th>Action</th></tr></thead><tbody>${docs.map(doc=>`<tr><td><div class="file-name"><div class="doc-icon">${icon('file')}</div><div><div class="row-title">${e(doc.title)}</div><div class="row-sub">${e(doc.latest.original_name)} · ${sizeText(doc.latest.size)}</div></div></div></td><td class="small">${e(doc.doc_type)}</td><td><span class="tag">v${doc.latest.number}</span></td><td>${(()=>{const record=(state.approvalOverview?.items||[]).find(x=>x.document_id===doc.id);const approval=record?.run?.status;const status=approval==='approved'?'Approuvée':approval==='pending'?'En validation':approval==='changes_requested'?'À corriger':approval==='rejected'?'Refusée':approval==='stale'?'Version remplacée':'Non soumise';return `<span class="lc-document-status ${approval==='approved'?'approved':approval==='pending'?'pending':'neutral'}">${status}</span>`})()}</td><td><div class="doc-actions"><button class="link" data-history="${e(doc.id)}">${icon('clock')} Historique</button><button class="link" data-download="${e(doc.id)}" data-ver="${doc.latest.number}" title="Télécharger" aria-label="Télécharger ${e(doc.title)}">${icon('download')}</button></div></td></tr>`).join('')}</tbody></table></div>`:`<div class="empty"><div class="empty-icon">${icon('file')}</div><strong>Ce sous-dossier est vide</strong>${f.can_write?'Déposez un premier document pour commencer.':'Aucun document pour le moment.'}</div>`}</div></section>

 ${f.can_read?renderDossierSummary(f,docs):''}
 </section>
 <section class="detail-view-panel" data-detail-view-panel="tools" id="detail-view-tools" role="tabpanel" aria-labelledby="detail-tab-tools" ${state.detailSection==='tools'?'':'hidden'}>
   ${renderDetailToolWorkspace()}
 </section>
 </div>`,'Dossiers jaunes / '+d.name);
 app.querySelector('#back-launches').onclick=()=>navigate('launches');
 app.querySelector('#launch-info')?.addEventListener('click',showLaunchInformation);
 app.querySelector('#edit-launch')?.addEventListener('click',openEditLaunch);
 const showValidations=()=>{switchDetailView('tools');selectDetailTool('approvals')};
 app.querySelector('#lc-header-validations')?.addEventListener('click',showValidations);
 app.querySelector('#lc-open-validations')?.addEventListener('click',showValidations);
 app.querySelector('#lc-show-info')?.addEventListener('click',showLaunchInformation);
 app.querySelectorAll('[data-detail-view]').forEach(button=>{
  button.addEventListener('click',()=>switchDetailView(button.dataset.detailView));
  button.addEventListener('keydown',event=>{
   if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
   event.preventDefault();
   const order=['documents','tools'];
   const current=order.indexOf(button.dataset.detailView);
   const next=event.key==='Home'?0:event.key==='End'?order.length-1:
     (current+(event.key==='ArrowRight'?1:-1)+order.length)%order.length;
   switchDetailView(order[next]);
   app.querySelector('[data-detail-view="'+order[next]+'"]')?.focus();
  });
 });
 app.querySelectorAll('[data-folder]').forEach(el=>el.addEventListener('click',()=>{state.folder=el.dataset.folder;state.detailSection='documents';renderDetail()}));
 switchDetailView(state.detailSection==='tools'?'tools':'documents');
 app.querySelector('#upload-doc')?.addEventListener('click',openUpload);
 app.querySelectorAll('[data-history]').forEach(el=>el.addEventListener('click',()=>openVersions(el.dataset.history)));
 app.querySelectorAll('[data-download]').forEach(el=>el.addEventListener('click',()=>download(el.dataset.download,+el.dataset.ver)));
 bindCompleteness();bindWorkflow();bindQuality();bindIntake();bindPaper();bindSpec();bindMail();bindImpactSimulation();bindOrliReconciliation();bindMaterialReport();bindApprovals();bindSharing();
 bindDetailToolWorkspace();
}
function modal(title,content,wide=false){overlay.innerHTML=`<div class="modal-scrim"><div class="modal ${wide?'wide':''}" role="dialog" aria-modal="true" aria-label="${e(title)}"><div class="modal-head"><h2>${e(title)}</h2><button id="close-modal" aria-label="Fermer">${icon('x')}</button></div><div class="modal-body">${content}</div></div></div>`;overlay.querySelector('#close-modal').onclick=closeModal;overlay.querySelector('.modal-scrim').addEventListener('click',evt=>{if(evt.target.classList.contains('modal-scrim'))closeModal()})}
function closeModal(){overlay.innerHTML=''}
function val(id){return overlay.querySelector('#'+id)?.value.trim()||''}
function openNewLaunch(){modal('Créer un dossier de lancement',`<p class="modal-desc">Vous pouvez ouvrir un dossier avant d’obtenir son numéro ORLI. Les quatre sous-dossiers seront créés automatiquement.</p><form id="new-launch-form"><div class="field"><label>Nom du lancement *</label><input id="l-name" maxlength="180" required placeholder="Ex. Vestes coton · lot automne" /></div><div class="two-fields"><div class="field"><label>Client</label><input id="l-client" maxlength="150" placeholder="Facultatif" /></div><div class="field"><label>Référence commande</label><input id="l-order" maxlength="100" placeholder="Facultatif" /></div></div><div class="field"><label>Référence ORLI</label><input id="l-orli" maxlength="100" placeholder="Facultative, à compléter plus tard" /></div><div class="modal-actions"><button class="secondary" type="button" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('plus')} Créer le dossier</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#new-launch-form').onsubmit=async ev=>{ev.preventDefault();try{const created=await api('/api/launches',{method:'POST',body:JSON.stringify({name:val('l-name'),client_name:val('l-client')||null,order_ref:val('l-order')||null,orli_ref:val('l-orli')||null})});closeModal();toast('Dossier créé avec ses quatre sous-dossiers');await openLaunch(created.id,'jaune')}catch(err){showErr(err)}}}
function openEditLaunch(){const d=state.detail;modal('Mettre à jour le lancement',`<p class="modal-desc">La référence ORLI peut être ajoutée ou modifiée sans perdre les documents ni les versions existantes.</p><form id="edit-launch-form"><div class="field"><label>Nom du lancement</label><input id="e-name" maxlength="180" required value="${e(d.name)}" /></div><div class="two-fields"><div class="field"><label>Client</label><input id="e-client" maxlength="150" value="${e(d.client_name||'')}" /></div><div class="field"><label>Référence commande</label><input id="e-order" maxlength="100" value="${e(d.order_ref||'')}" /></div></div><div class="field"><label>Référence ORLI</label><input id="e-orli" maxlength="100" value="${e(d.orli_ref||'')}" /></div><div class="field"><label>Statut</label><select id="e-status">${['À compléter','En cours','En validation','Clôturé'].map(s=>`<option ${s===d.status?'selected':''}>${s}</option>`).join('')}</select></div><div class="modal-actions"><button type="button" id="cancel-modal" class="secondary">Annuler</button><button class="primary" type="submit">${icon('check')} Enregistrer</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#edit-launch-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/launches/'+d.id,{method:'PATCH',body:JSON.stringify({name:val('e-name'),client_name:val('e-client')||null,order_ref:val('e-order')||null,orli_ref:val('e-orli')||null,status:val('e-status')})});closeModal();toast('Informations mises à jour');await openLaunch(d.id,state.folder)}catch(err){showErr(err)}}}
function openUpload(){const d=state.detail;modal('Déposer un document',`<p class="modal-desc">Le document sera rattaché au sous-dossier <strong>${e(state.folder)}</strong> du lancement <strong>${e(d.name)}</strong>.</p><form id="upload-form"><div class="field"><label>Titre du document *</label><input id="doc-title" maxlength="220" required placeholder="Ex. Fiche d’emploi — version initiale" /></div><div class="field"><label>Type de document</label><input id="doc-type" list="doc-types" value="Autre" maxlength="100" required /><datalist id="doc-types"><option value="Autre"><option value="Fiche d’emploi"><option value="Lancement provisoire"><option value="Lancement définitif"><option value="Fiche de prix"><option value="Besoin matière"><option value="Bon de livraison"><option value="Bon de réception"><option value="Pièce douanière"><option value="Facture"><option value="Email"><option value="Dossier technique client"></datalist></div><div class="field"><label>Fichier * (20 Mo maximum)</label><input id="doc-file" type="file" accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.txt,.eml" required /></div><p class="permission-lock">${icon('shield')} Formats autorisés et contrôlés à la réception. Le document original reste conservé.</p><div class="modal-actions"><button class="secondary" type="button" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('upload')} Ajouter la pièce</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#upload-form').onsubmit=async ev=>{ev.preventDefault();const fd=new FormData();fd.append('folder',state.folder);fd.append('title',val('doc-title'));fd.append('doc_type',val('doc-type'));fd.append('file',overlay.querySelector('#doc-file').files[0]);try{await api('/api/launches/'+d.id+'/documents',{method:'POST',body:fd});closeModal();toast('Document déposé avec sa version initiale');await openLaunch(d.id,state.folder)}catch(err){showErr(err)}}}
function findDoc(id){return state.detail.folders.flatMap(f=>f.documents).find(d=>d.id===id)}
function openVersions(id){const d=findDoc(id);if(!d)return;modal('Versions · '+d.title,`<p class="modal-desc">Les versions antérieures restent accessibles. Aucun remplacement destructif n’est effectué.</p>${[...d.versions].reverse().map(v=>`<div class="version-row"><div><strong>Version ${v.number}</strong> ${v.number===d.latest.number?'<span class="tag green">Courante</span>':''}<div class="version-meta">${e(v.original_name)} · ${sizeText(v.size)} · ${niceDate(v.created_at)}</div><div class="version-meta">SHA-256 : ${e(v.sha256.slice(0,20))}…</div></div><button class="secondary tiny" data-vdownload="${v.number}">${icon('download')} Télécharger</button></div>`).join('')}${can('document.write',d.folder)?`<form id="new-version-form" style="padding-top:20px;margin-top:10px;border-top:1px solid #edf0ed"><div class="field"><label>Ajouter une nouvelle version</label><input type="file" id="version-file" accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.txt,.eml" required /></div><button class="primary" type="submit">${icon('plus')} Enregistrer la nouvelle version</button></form>`:''}`,true);overlay.querySelectorAll('[data-vdownload]').forEach(el=>el.onclick=()=>download(d.id,+el.dataset.vdownload));overlay.querySelector('#new-version-form')?.addEventListener('submit',async ev=>{ev.preventDefault();const fd=new FormData();fd.append('file',overlay.querySelector('#version-file').files[0]);try{await api('/api/documents/'+d.id+'/versions',{method:'POST',body:fd});closeModal();toast('Nouvelle version conservée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}})}
async function download(docId,number){try{const r=await api(`/api/documents/${docId}/versions/${number}/download`);const blob=await r.blob();const d=findDoc(docId);const v=d?.versions.find(x=>x.number===number);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=v?.original_name||'document';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(err){showErr(err)}}
async function admin(){state.view='admin';[state.roles,state.users]=await Promise.all([api('/api/admin/roles'),api('/api/admin/users')]);const completionHtml=await completenessAdminPanel();const workflowHtml=await workflowAdminPanel();const approvalHtml=await approvalAdminPanel();mount(`<div class="page-heading"><div><div class="page-kicker">${icon('shield')} ACCÈS ET HABILITATIONS</div><h1 class="page-title">Administration</h1><p class="page-lead">Utilisateurs, rôles et autorisations.</p></div></div><div class="section-heading"><h2>Collaborateurs</h2><button class="primary tiny" id="add-user">${icon('plus')} Ajouter un utilisateur</button></div><div class="panel table-scroll"><table><thead><tr><th>Utilisateur</th><th>Email</th><th>Rôle(s)</th><th>État</th></tr></thead><tbody>${state.users.map(u=>`<tr><td class="row-title">${e(u.name)}</td><td>${e(u.email)}</td><td>${e(u.roles.join(', '))}</td><td><span class="tag green">${u.active?'Actif':'Désactivé'}</span></td></tr>`).join('')}</tbody></table></div><div class="section-heading"><h2>Rôles configurés</h2><button class="secondary tiny" id="add-role">${icon('plus')} Nouveau rôle</button></div><div class="panel table-scroll"><table><thead><tr><th>Rôle</th><th>Nombre d’autorisations</th><th>Portée</th></tr></thead><tbody>${state.roles.map(r=>`<tr><td class="row-title">${e(r.name)}</td><td>${r.name==='Administrateur'?'Toutes':r.permissions.length}</td><td class="small">${r.name==='Administrateur'?'Administration complète':e(r.permissions.map(p=>p.action+(p.folder?' ('+p.folder+')':'')).join(', ')||'Aucune permission')}</td></tr>`).join('')}</tbody></table></div><p class="permission-lock">Les autorisations sont vérifiées par le serveur, y compris pour les téléchargements.</p><details class="admin-advanced"><summary><span class="admin-advanced-title">${icon('settings')} Paramètres avancés</span><span class="admin-advanced-hint">Règles documentaires, circuits et validations</span></summary><div class="admin-advanced-content">${completionHtml}${workflowHtml}${approvalHtml}</div></details>`,'Administration');app.querySelector('#add-user').onclick=openNewUser;app.querySelector('#add-role').onclick=openNewRole;bindCompletenessAdmin();bindWorkflowAdmin();bindApprovalAdmin()}
function openNewRole(){const folderChecks=['jaune','rose','bleu','vert'].map(s=>`<label class="checkbox-line"><input type="checkbox" name="grant" value="document.read:${s}"> Lecture · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="document.write:${s}"> Dépôt · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="completeness.review:${s}"> Contrôle de complétude · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="document.review:${s}"> Décision documentaire · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="value.write:${s}"> Valeurs métier · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="impact.review:${s}"> Suivi des impacts · ${s}</label>${s==='rose'?`<label class="checkbox-line"><input type="checkbox" name="grant" value="commitment.review:rose"> Confirmation des engagements email · rose</label>`:''}`).join('');modal('Créer un rôle',`<form id="role-form"><div class="field"><label>Nom du rôle</label><input id="r-name" maxlength="80" required placeholder="Ex. Gestion documentaire" /></div><p class="modal-desc">Autorisations globales</p><div class="permission-grid">${[['launch.read','Voir les lancements'],['launch.create','Créer les lancements'],['launch.update','Modifier les lancements']].map(([v,label])=>`<label class="checkbox-line"><input type="checkbox" name="grant" value="${v}"> ${label}</label>`).join('')}</div><p class="modal-desc" style="margin-top:20px">Autorisations documentaires par rubrique</p><div class="permission-grid">${folderChecks}</div><div class="modal-actions"><button type="button" class="secondary" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('check')} Créer le rôle</button></div></form>`,true);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#role-form').onsubmit=async evt=>{evt.preventDefault();const permissions=[...overlay.querySelectorAll('[name=grant]:checked')].map(el=>{const [action,folder]=el.value.split(':');return {action,folder:folder||null}});try{await api('/api/admin/roles',{method:'POST',body:JSON.stringify({name:val('r-name'),permissions})});closeModal();toast('Rôle créé');await admin()}catch(err){showErr(err)}}}
function openNewUser(){modal('Créer un collaborateur',`<form id="user-form"><div class="field"><label>Nom complet</label><input id="u-name" required maxlength="120" /></div><div class="field"><label>Email</label><input id="u-email" type="email" required maxlength="254" /></div><div class="field"><label>Mot de passe initial (12 caractères minimum)</label><input id="u-pass" type="password" minlength="12" required autocomplete="new-password" /></div><div class="field"><label>Rôle</label><select id="u-role">${state.roles.map(r=>`<option value="${e(r.id)}">${e(r.name)}</option>`).join('')}</select></div><div class="modal-actions"><button type="button" class="secondary" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('check')} Créer le compte</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#user-form').onsubmit=async evt=>{evt.preventDefault();try{await api('/api/admin/users',{method:'POST',body:JSON.stringify({name:val('u-name'),email:val('u-email'),password:overlay.querySelector('#u-pass').value,role_ids:[val('u-role')]})});closeModal();toast('Compte collaborateur créé');await admin()}catch(err){showErr(err)}}}
async function auditView(){state.view='audit';state.audit=await api('/api/admin/audit');mount(`<div class="page-heading"><div><div class="page-kicker">${icon('activity')} TRAÇABILITÉ</div><h1 class="page-title">Journal d’activité</h1><p class="page-lead">100 dernières opérations sensibles.</p></div></div><div class="panel table-scroll"><table><thead><tr><th>Action</th><th>Utilisateur</th><th>Élément</th><th>Date</th></tr></thead><tbody>${state.audit.map(x=>`<tr><td class="row-title">${e(x.action)}</td><td class="audit-item">${e((x.actor_id||'—').slice(0,12))}</td><td class="audit-item">${e(x.target_type)} · ${e(x.target_id.slice(0,12))}</td><td class="small">${niceDate(x.occurred_at)}</td></tr>`).join('')}</tbody></table></div>`,'Journal d’activité')}
async function navigate(view){try{if(view==='home')await home();else if(view==='launches')await launchList();else if(view==='actions')await workspaceActions();else if(view==='assistant')openFloatingAssistant();else if(view==='notifications')await notificationsPage();else if(view==='pilot')await pilotPage();else if(view==='orli'&&state.me.admin)await orliAdmin();else if(view==='admin'&&state.me.admin)await admin();else if(view==='audit'&&state.me.admin)await auditView()}catch(err){showErr(err)}}
window.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
// Partie intégrée dans app.js lors de la construction du MVP 0.2.
function phaseLabel(code){return {'preparation':'Préparation','approvisionnement':'Approvisionnement','fabrication':'Fabrication','expedition':'Expédition','cloture':'Clôture'}[code]||code}
function completionBadge(code){const map={present:['Pièce disponible','green'],missing:['Pièce manquante','orange'],not_due:['Non encore exigible',''],pending_validation:['Validation attendue','blue'],exception:['Exception documentée','']};let [title,color]=map[code]||[code,''];return `<span class="tag ${color}">${e(title)}</span>`}
function renderCompleteness(){
 const c=state.completeness;if(!c)return '';
 const n=c.counts;
 const heading=`<div class="section-heading" style="margin-top:27px"><div><h2>Complétude documentaire</h2><small>Contrôle contextuel · ${e(phaseLabel(c.phase))}</small></div>${c.can_change_context?`<button class="secondary tiny" id="edit-completeness">${icon('pencil')} Profil et étape</button>`:''}</div>`;
 if(!c.configured)return `${heading}<div class="completion-notice">${icon('info')}<div><strong>Aucune règle métier active n’est appliquée à ce dossier.</strong><p>Choisissez un profil validé par Framatex et définissez son étape pour afficher les documents attendus. Un dossier sans règles n'est pas considéré comme complet.</p></div></div>`;
 const alerts=n.missing+n.pending_validation;
 const summary=`<div class="completion-summary"><div class="completion-metric"><strong>${n.present}</strong><span>Pièces disponibles${n.pending_validation?' et validées':''}</span></div><div class="completion-metric"><strong>${n.missing}</strong><span>Manquantes</span></div><div class="completion-metric"><strong>${n.pending_validation}</strong><span>À valider</span></div><div class="completion-metric"><strong>${n.not_due}</strong><span>Non exigibles</span></div><div class="completion-metric"><strong>${n.exception}</strong><span>Exceptions</span></div></div>`;
 const explanation=c.due_count===0?'Aucune pièce n’est encore exigible à cette étape.':alerts?`${alerts} point(s) exigent une vérification.`:'Aucun document manquant ou en attente de validation parmi les règles visibles.';
 return `${heading}<div class="completion-shell"><div class="completion-top"><div><span class="completion-eyebrow">${e(c.profile_name)}</span><p>${e(explanation)}</p></div><span class="tag">${c.visible_rules} règle(s) visible(s)</span></div>${summary}${c.partial_visibility?`<div class="completion-sensitive">${icon('lock')} Certaines exigences ne sont pas affichées selon vos habilitations. Le bilan ci-dessus est partiel.</div>`:''}<div class="completion-rule-list">${c.rows.map(r=>`<div class="completion-rule"><div class="completion-rule-main"><span class="completion-folder ${e(r.folder)}">${e(r.folder)}</span><div><div class="completion-rule-title">${e(r.title)}</div><div class="completion-rule-meta">${e(r.document_type)} · Exigible dès ${e(phaseLabel(r.due_phase))}${r.requires_validation?' · Validation requise':''}</div>${r.guidance?`<div class="completion-rule-hint">${e(r.guidance)}</div>`:''}${r.status==='exception'?`<div class="completion-rule-hint"><strong>Justification :</strong> ${e(r.exception_reason)}</div>`:''}${r.documents.length?`<div class="completion-rule-hint">${e(r.documents.map(d=>d.title+' (v'+d.version+')').join(', '))}</div>`:''}</div></div><div class="completion-rule-actions">${completionBadge(r.status)}${r.can_review&&r.status==='pending_validation'?`<button class="secondary tiny" data-complete-validate="${e(r.id)}">${icon('check')} Valider</button>`:''}${r.can_review&&r.status==='missing'?`<button class="link" data-complete-exception="${e(r.id)}">Justifier</button>`:''}${r.can_review&&r.status==='exception'?`<button class="link" data-complete-clear="${e(r.id)}">Lever l’exception</button>`:''}</div></div>`).join('')}</div><div class="completion-footer">Les contrôles sont indicatifs et ne bloquent pas le lancement. Une pièce disponible ne prouve pas à elle seule sa conformité métier.</div></div>`;
}
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
 return `<div class="section-heading"><h2>Règles de complétude documentaire</h2><button class="primary tiny" id="create-profile">${icon('plus')} Nouveau profil</button></div><p class="completion-admin-lead">Les profils et étapes ci-dessous sont paramétrables ; aucune règle n’est imposée à un lancement sans affectation explicite.</p>${profiles.length?profiles.map(profile=>`<div class="panel completion-admin-panel"><div class="completion-admin-head"><div><strong>${e(profile.name)}</strong><p>${e(profile.description||'Aucune description fournie')}</p></div><button class="secondary tiny" data-add-complete-rule="${e(profile.id)}">${icon('plus')} Ajouter une exigence</button></div><div class="table-scroll"><table><thead><tr><th>Pièce attendue</th><th>Rubrique</th><th>Exigible dès</th><th>Contrôle</th><th>État</th><th></th></tr></thead><tbody>${profile.rules.length?profile.rules.map(r=>`<tr><td><div class="row-title">${e(r.title)}</div><div class="row-sub">Type exact : ${e(r.document_type)}</div></td><td>${e(r.folder)}</td><td class="small">${e(phaseLabel(r.due_phase))}</td><td class="small">${r.requires_validation?'Validation requise':'Présence'}</td><td>${r.active?'<span class="tag green">Active</span>':'<span class="tag">Désactivée</span>'}</td><td><button class="link" data-toggle-complete-rule="${e(r.id)}" data-next-active="${r.active?'false':'true'}">${r.active?'Désactiver':'Réactiver'}</button></td></tr>`).join(''):`<tr><td colspan="6" class="muted small">Aucune règle définie. Ce profil ne produit aucune alerte.</td></tr>`}</tbody></table></div></div>`).join(''):`<div class="completion-notice">${icon('info')}<div><strong>Aucun profil métier configuré.</strong><p>Créez d'abord un profil (exemple fictif), puis saisissez les règles après validation par Framatex.</p></div></div>`}`;
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

(async function init(){try{state.me=await api('/api/auth/me');if(!(await paperOpenDeepLink()))await navigate('home')}catch{renderLogin()}})();
