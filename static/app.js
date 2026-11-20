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
function niceDate(s){if(!s)return '—';const d=new Date(/Z$|[+-]\d{2}:\d{2}$/.test(s)?s:s+'Z');if(Number.isNaN(d.getTime()))return 'Date indisponible';return d.toLocaleDateString('fr-FR',{day:'2-digit',month:'short',year:'numeric'})}
function sizeText(n){return n>=1024*1024?`${(n/1024/1024).toFixed(1)} Mo`:`${Math.max(1,Math.ceil(n/1024))} Ko`}
const app=document.querySelector('#app'), overlay=document.querySelector('#overlay-root');
const state={me:null,view:'home',priorities:null,launches:[],dashboard:null,detail:null,completeness:null,completionProfiles:[],completenessPhases:[{code:'preparation',label:'Préparation'},{code:'approvisionnement',label:'Approvisionnement'},{code:'fabrication',label:'Fabrication'},{code:'expedition',label:'Expédition'},{code:'cloture',label:'Clôture'}],folder:'jaune',roles:[],users:[],audit:[],workflowReviews:[],workflowValues:[],workflowImpacts:[],workflowFields:[],workflowRules:[],qualityReport:null,excelInspections:[],specReport:null,mailReport:null,simGraph:null,simHistory:[],orliReconciliation:null,orliBatches:[],materials:null,approvalOverview:null,clientPublications:null,supplierRequests:null,approvalTemplates:[],approvalRoles:[],notifications:null,query:''};
const activeMutations=new Set();let pendingRequests=0;
// A later navigation owns the screen; an older dossier refresh must not remount it.
let navigationVersion=0;
async function api(path,options={}){
  const mutation=options.method&&options.method!=='GET'?options.method+':'+path:null;
  if(mutation&&activeMutations.has(mutation))throw new Error('Cette opération est déjà en cours.');
  if(mutation)activeMutations.add(mutation);
  const progress=document.querySelector('#operation-status');let completed=false;
  pendingRequests++;if(progress)progress.textContent='Chargement…';
  try{
    const headers={'X-Framatex-Request':'1',...options.headers};
    if(options.body && !(options.body instanceof FormData))headers['Content-Type']='application/json';
    const res=await fetch(path,{...options,headers,credentials:'same-origin'});
    if(!res.ok){let data;try{data=await res.json()}catch{};
      if(res.status===401 && !path.includes('/auth/login')){state.me=null;renderSpaceChoice()}
      throw new Error(typeof data?.detail==='string'?data.detail:`Opération refusée (HTTP ${res.status}). Vérifiez vos droits et les informations saisies.`);
    }
    const result=res.headers.get('content-type')?.includes('application/json')?await res.json():res;
    completed=true;return result;
  }catch(error){
    if(error instanceof TypeError)throw new Error('Connexion interrompue. Vérifiez le réseau avant de réessayer ; aucune opération ne sera relancée automatiquement.');
    throw error;
  }finally{
    if(mutation)activeMutations.delete(mutation);
    pendingRequests--;if(progress&&pendingRequests===0)progress.textContent=completed?'Opération terminée.':'Opération interrompue. Consultez le message d’erreur.';
  }
}

let timeout;function toast(msg){const el=document.querySelector('#toast');el.textContent=msg;el.classList.add('visible');clearTimeout(timeout);timeout=setTimeout(()=>el.classList.remove('visible'),3400)}
function showErr(err){toast(err.message||String(err))}
function can(action,folder=null){return !!state.me?.admin||state.me?.permissions?.some(p=>p.action===action&&(folder?p.folder===null||p.folder===folder:p.folder===null))}
function statusTag(s){return `<span class="tag ${s==='À compléter'?'orange':s==='Clôturé'?'green':s==='En validation'?'blue':''}">${e(s)}</span>`}
function topbar(label){
 return `<header class="topbar october-topbar" aria-label="${e(label)}">
   <button type="button" class="lc-global-search" id="global-search">${icon('search')}<span>Rechercher un dossier…</span></button>
   <div class="topbar-actions">
     <button type="button" class="rail-notifications" id="top-notifications" title="Notifications" aria-label="Voir les notifications">${icon('clock')}</button>
     <button type="button" class="lc-user-avatar" id="top-profile" aria-label="Voir mon compte">${e(accountInitials())}</button>
     <span class="lc-top-username">${e(state.me.name)}</span>
   </div>
 </header>`;
}

function accountInitials(){
 return state.me.name.trim().split(/\s+/).slice(0,2).map(part=>part[0]).join('').toUpperCase();
}

const openRailGroups=new Set();

function sidebar(){
 const primary=[['dossiers','folder','Dossiers Jaunes'],['clients','users','Clients'],['validations','check','Validations'],...(can('launch.read')?[['experience','file','Mémoire métier']]:[])];
 const workspace=[['orders','file','Commandes'],['home','grid','Vue d’ensemble'],['documents','search','Documents'],['suppliers','users','Fournisseurs'],['receipts','upload','Réceptions'],['launches','layers','Lancements'],['actions','activity','Mes actions'],['notifications','clock','Notifications'],['assistant','layers','Framatex Guide']];
 const tools=[['pilot','info','Aide & retours'],...(state.me.admin?[['orli','file','Imports ORLI'],['admin','users','Administration'],['audit','shield','Journal d’activité']]:[])];
 const items=list=>list.map(([view,ico,label])=>{
  const active=state.view===view||(state.view==='detail'&&view==='launches');
  return `<button type="button" class="nav-btn ${active?'active':''}" data-view="${view}" aria-current="${active?'page':'false'}">${icon(ico)}<span>${label}</span>${active?'<span class="nav-current" aria-hidden="true">›</span>':''}</button>`;
 }).join('');
 const group=(key,label,ico,links)=>{
  const open=openRailGroups.has(key)||links.some(([view])=>state.view===view);
  return `<details class="rail-management" data-rail-group="${key}" ${open?'open':''}>
    <summary>${icon(ico)}<span>${label}</span><span class="rail-chevron" aria-hidden="true">⌄</span></summary>
    <nav class="sidebar-nav" aria-label="${label}">${items(links)}${key==='workspace'?'<a class="nav-btn" href="/partners">Espace partenaires</a>':''}</nav>
  </details>`;
 };
 return `<aside class="sidebar sidebar-rail sidebar-light" aria-label="Navigation Dossier Jaune">
   <div class="rail-brand"><img class="rail-brand-mark" src="/assets/dossier-jaune-mark.svg" width="34" height="42" alt=""><span class="rail-brand-name">Dossier Jaune<small>par Framatex</small></span></div>
   <button type="button" class="mobile-navigation-toggle" aria-expanded="false" aria-controls="framat-navigation">${icon('grid')} Menu</button>
   <div class="rail-navigation-content" id="framat-navigation">
    <nav class="sidebar-nav rail-primary" aria-label="Navigation principale">${items(primary)}</nav>
    ${group('tools','Gestion','layers',tools)}
    ${group('workspace','Espace de travail','grid',workspace)}
    <div class="sidebar-bottom rail-account">
     <div class="user"><span class="avatar" aria-hidden="true">${e(accountInitials())}</span><span class="user-name" title="${e(state.me.name)}">${e(state.me.name)}</span></div>
     <button type="button" class="logout" id="logout" title="Déconnexion" aria-label="Déconnexion">${icon('out')}</button>
    </div>
   </div>
 </aside>`;
}
function mount(html,label,folderTheme=null){
 const theme=folderTheme||(state.view==='detail'?state.folder:null);
 app.innerHTML=`<div class="app-shell"${['jaune','rose','bleu','vert'].includes(theme)?` data-folder-theme="${theme}"`:''}>${sidebar()}<div class="main">${topbar(label)}<main class="content">${html}</main></div></div>`;
 app.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>navigate(n.dataset.view)));
 app.querySelectorAll('[data-rail-group]').forEach(group=>group.addEventListener('toggle',()=>{
  if(group.open)openRailGroups.add(group.dataset.railGroup);
  else openRailGroups.delete(group.dataset.railGroup);
 }));
 app.querySelector('.mobile-navigation-toggle').addEventListener('click',event=>{
  const button=event.currentTarget;
  const open=button.getAttribute('aria-expanded')!=='true';
  button.setAttribute('aria-expanded',String(open));
  button.closest('.sidebar').classList.toggle('is-mobile-open',open);
 });
 app.querySelector('#top-notifications')?.addEventListener('click',()=>navigate('notifications'));
 app.querySelector('#top-profile')?.addEventListener('click',()=>app.querySelector('.sidebar-bottom')?.scrollIntoView({behavior:'smooth',block:'center'}));
 app.querySelector('#global-search')?.addEventListener('click',async()=>{await navigate('dossiers');app.querySelector('#order-query')?.focus()});
 document.dispatchEvent(new Event('framat:guide-auth'));
 app.querySelector('#logout').addEventListener('click',async()=>{try{await api('/api/auth/logout',{method:'POST'})}catch{}state.me=null;state.detail=null;openRailGroups.clear();renderSpaceChoice()});
}
function renderSpaceChoice(){
 closeModal();
 document.dispatchEvent(new Event('framat:guide-auth'));
 app.innerHTML=`<div class="login-page login-rebalanced jauno-space-choice"><main class="login-stage">
  <div class="login-visual" aria-hidden="true"><div class="login-visual-orbit"></div><div class="login-visual-floor"></div><div class="login-folder login-folder-back"></div><div class="login-folder login-folder-middle"></div><div class="login-folder login-folder-front"><span class="login-folder-stripe"></span><span class="login-folder-line"></span><span class="login-folder-line login-folder-line-small"></span><span class="login-folder-dot"></span></div></div>
  <section class="login-form-wrap"><div class="login-auth-content">
    <div class="login-form-brand"><span class="login-form-brand-icon"><img class="jauno-brand-mark" src="/assets/dossier-jaune-mark.svg" alt=""></span><strong>Dossier Jaune</strong></div>
    <h1 id="space-title">Choisissez votre espace</h1>
    <div class="login-form jauno-space-actions" role="group" aria-labelledby="space-title">
      <button type="button" class="primary jauno-space-action" data-space="internal">Espace interne</button>
      <a class="primary jauno-space-action" href="/partners?space=client">Espace client</a>
      <a class="primary jauno-space-action" href="/partners?space=supplier">Espace fournisseur</a>
    </div>
  </div></section></main></div>`;
 app.querySelector('[data-space=internal]').addEventListener('click',renderLogin);
}
function renderLogin(){overlay.innerHTML='';app.innerHTML=`<div class="login-page login-rebalanced"><main class="login-stage">
  <div class="login-visual" aria-hidden="true"><div class="login-visual-orbit"></div><div class="login-visual-floor"></div><div class="login-folder login-folder-back"></div><div class="login-folder login-folder-middle"></div><div class="login-folder login-folder-front"><span class="login-folder-stripe"></span><span class="login-folder-line"></span><span class="login-folder-line login-folder-line-small"></span><span class="login-folder-dot"></span></div></div>
  <section class="login-form-wrap"><div class="login-auth-content"><button type="button" class="auth-return" id="change-space">← Changer d’espace</button><div class="login-form-brand"><span class="login-form-brand-icon"><img class="jauno-brand-mark" src="/assets/dossier-jaune-mark.svg" alt=""></span><strong>Dossier Jaune</strong></div>
    <h1 id="login-title">Connexion</h1>
    <form id="login-form" class="login-form" aria-labelledby="login-title">
      <div id="login-error" role="alert" aria-live="assertive"></div>
      <div class="field"><label for="email">Adresse email</label><input id="email" type="email" autocomplete="username" required /></div>
      <div class="field"><label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" required /></div>
      <button class="primary" type="submit">Se connecter</button>
    </form>
  </div></section></main></div>`;
  app.querySelector('#change-space').addEventListener('click',renderSpaceChoice);
  app.querySelector('#login-form').addEventListener('submit',async evt=>{evt.preventDefault();const btn=evt.target.querySelector('button');btn.disabled=true;try{state.me=await api('/api/auth/login',{method:'POST',body:JSON.stringify({email:app.querySelector('#email').value,password:app.querySelector('#password').value})});state.me=await api('/api/auth/me');if(!(await paperOpenDeepLink()))await navigate('dossiers')}catch(err){app.querySelector('#login-error').innerHTML=`<div class="error">${e(err.message)}</div>`}finally{btn.disabled=false}})
}
function tableLaunches(list){if(!list.length)return `<div class="empty"><div class="empty-icon">${icon('folder')}</div><strong>Aucun dossier pour l’instant</strong>Créez votre premier lancement de fabrication pour démarrer.</div>`;return `<div class="table-scroll"><table><thead><tr><th>Lancement</th><th>Client</th><th>Référence ORLI</th><th>Statut</th><th>Créé le</th><th></th></tr></thead><tbody>${list.map(l=>`<tr class="item-row" data-launch="${e(l.id)}"><td><button class="link" type="button" aria-label="Ouvrir le lancement ${e(l.name)}">${e(l.name)}</button><div class="row-sub">${e(l.order_ref||'Aucune référence de commande')}</div></td><td>${e(l.client_name||'—')}</td><td>${l.orli_ref?`<span class="tag">${e(l.orli_ref)}</span>`:'<span class="muted small">Non attribuée</span>'}</td><td>${statusTag(l.status)}</td><td class="small">${niceDate(l.created_at)}</td><td>${icon('arrow')}</td></tr>`).join('')}</tbody></table></div>`}
function bindLaunchRows(){app.querySelectorAll('[data-launch]').forEach(row=>row.addEventListener('click',()=>openLaunch(row.dataset.launch).catch(showErr)))}
async function home(){
 state.priorities=await api('/api/workspace/priorities');
 const d=state.dashboard=await api('/api/dashboard');state.launches=await api('/api/launches');state.view='home';
 const recent=(d.recent||[]).slice(0,5);
 mount(`<div class="home-dashboard"><div class="home-grid"><div class="home-primary">
  <section class="command-hero" aria-label="Accueil de Framatex"><div class="command-hero-content">
    <div class="hero-eyebrow"><span></span> VOTRE CENTRE D’OPÉRATIONS</div>
    <h1>Chaque document.<br><em>Au bon endroit.</em></h1>
    <p>Vos lancements, vos validations et les points à traiter.<br>L’essentiel de votre activité documentaire, en un coup d’œil.</p>
    <div class="hero-actions">${can('launch.create')?`<button type="button" class="hero-cta" id="create-launch">${icon('plus')} Nouveau dossier ${icon('arrow')}</button>`:''}<button type="button" class="hero-secondary" id="hero-see-docs">Explorer les dossiers ${icon('arrow')}</button></div>
    </div><div class="hero-art" aria-hidden="true"><div class="art-orbit-outline"></div><div class="art-document"><span class="art-document-icon">${icon('file')}</span><span class="art-document-line"></span><span class="art-document-line short"></span><span class="art-document-line"></span></div><span class="art-point point-a">${icon('folder')} Lancement</span><span class="art-point point-b">${icon('users')} Validation</span><span class="art-point point-c">${icon('file')} Classement</span><span class="art-point point-d">${icon('shield')} Traçabilité</span></div>
  </section>
  <div class="dashboard-strip-title"><div><span class="section-index">ACTIVITÉ EN TEMPS RÉEL</span><h2>Vue générale <span class="quiet-symbol">↗</span></h2></div><span class="dashboard-strip-note">Données accessibles selon vos droits</span></div>
  <section class="executive-grid" aria-label="Indicateurs documentaires"><article class="executive-card"><div class="executive-card-top">${icon('folder')}<span>01 / DOSSIERS</span></div><div class="executive-number">${d.launches}<small>total</small></div><div class="executive-card-foot">Lancements enregistrés <span>↗</span></div></article><article class="executive-card"><div class="executive-card-top">${icon('clock')}<span>02 / À COMPLÉTER</span></div><div class="executive-number">${d.incomplete}<small>en cours</small></div><div class="executive-card-foot">Dossiers non finalisés <span>↗</span></div></article><article class="executive-card"><div class="executive-card-top">${icon('file')}<span>03 / DOCUMENTS</span></div><div class="executive-number">${d.documents}<small>pièces</small></div><div class="executive-card-foot">Documents accessibles <span>↗</span></div></article><article class="executive-card"><div class="executive-card-top">${icon('copy')}<span>04 / VERSIONS</span></div><div class="executive-number">${d.versions}<small>archivées</small></div><div class="executive-card-foot">Historique préservé <span>↗</span></div></article></section>
  <section class="premium-section"><div class="premium-section-head"><div><span class="section-index">DOCUMENT WORKSPACE</span><h2>Lancements récents</h2></div><button type="button" class="text-arrow" id="all-launches">Tous les dossiers ${icon('arrow')}</button></div><div class="premium-table panel">${tableLaunches(recent)}</div></section>
  <div class="completion-dashboard-banner">${icon('info')} <span><strong>${d.completeness_actions}</strong> point(s) documentaires à vérifier. <strong>${d.completeness_unconfigured}</strong> dossier(s) sans règles actives.</span></div>
  <section class="premium-section premium-priorities"><div class="premium-section-head"><div><span class="section-index">À VOTRE ATTENTION</span><h2>Priorités du jour</h2></div><button class="text-arrow" type="button" id="workspace-all-hero">Voir toutes les actions ${icon('arrow')}</button></div>${renderPriorityWidget()}</section>
 </div><aside class="home-rail" aria-label="Assistant documentaire"><section class="home-rail-header"><span class="assistant-mark">${icon('layers')}</span><div><span class="section-index">VOTRE GUIDE UTILISATEUR</span><h2>Framatex Guide <i class="chat-online"></i></h2></div><button class="rail-expand" id="dashboard-guide" title="Ouvrir le guide en grand" aria-label="Ouvrir le guide">${icon('arrow')}</button></section><div class="inline-chat" id="inline-chat" aria-live="polite"><div class="assistant-msg assistant-msg-bot"><span class="assistant-msg-avatar">${icon('layers')}</span><div class="assistant-bubble"><strong>Bonjour !</strong><p>Je peux vous guider dans Framatex, retrouver une rubrique ou expliquer une procédure. Que souhaitez-vous faire ?</p></div></div></div><div class="rail-composer"><span class="section-index">QUESTIONS FRÉQUENTES</span><div class="rail-quick"><button type="button" data-rail-question="Où déposer une facture ?">Déposer une facture ${icon('arrow')}</button><button type="button" data-rail-question="Voir mes priorités">Mes priorités ${icon('arrow')}</button><button type="button" data-rail-question="Comment vérifier une exigence client ?">Exigences client ${icon('arrow')}</button></div><form id="rail-form"><label for="rail-question">Votre question</label><div class="rail-input"><input id="rail-question" autocomplete="off" maxlength="500" minlength="2" placeholder="Écrivez votre question..." required><button type="submit" aria-label="Envoyer">${icon('arrow')}</button></div></form><small>Procédures locales vérifiées, disponibles même sans Gemini.</small></div></aside></div></div>`,'Vue d’ensemble');
 bindLaunchRows();bindPriorityWidget();
 app.querySelector('#all-launches')?.addEventListener('click',()=>navigate('launches'));
 app.querySelector('#hero-see-docs')?.addEventListener('click',()=>navigate('launches'));
 app.querySelector('#create-launch')?.addEventListener('click',openNewLaunch);
 app.querySelector('#dashboard-guide')?.addEventListener('click',openGuide);
 app.querySelector('#workspace-all-hero')?.addEventListener('click',()=>navigate('actions'));
 if(typeof bindInlineAssistant==='function')bindInlineAssistant();
}

async function pagedSelect(select,endpoint,placeholder,label){
 const controls=document.createElement('div'), search=document.createElement('input');
 search.type='search';search.setAttribute('aria-label', 'Rechercher · '+select.labels[0].textContent);
 const prev=document.createElement('button'),next=document.createElement('button'),status=document.createElement('span');
 prev.type=next.type='button';prev.textContent='Précédents';next.textContent='Suivants';
 status.setAttribute('role','status');controls.append(search,prev,status,next);select.before(controls);
 let offset=0,sequence=0;
 async function load(start){
  const request=++sequence;select.replaceChildren(new Option(placeholder,''));prev.disabled=next.disabled=true;
  status.textContent='Chargement…';
  try{
   const data=await api(endpoint+'?'+new URLSearchParams({page:'true',q:search.value,offset:start,limit:50}));
   if(request!==sequence||!select.isConnected)return;
   for(const row of data.items)select.add(new Option(label(row),row.id));
   offset=start;prev.disabled=!offset;next.disabled=start+50>=data.total;
   status.textContent=`${data.total} résultat(s) · Page ${Math.floor(start/50)+1}`;
  }catch(error){if(request===sequence)status.textContent=error.message}
 }
 search.oninput=()=>load(0);prev.onclick=()=>load(Math.max(0,offset-50));next.onclick=()=>load(offset+50);
 await load(0);
}

async function launchList(){
 const navigation=navigationVersion;
 state.view='launches';
 mount(`<div class="page-heading"><h1>Lancements</h1>${can('launch.create')?'<button id="create-launch" class="primary">Nouveau dossier</button>':''}</div><label for="launch-search">Rechercher par nom, client, commande ou ORLI</label><input id="launch-search" type="search" maxlength="200" value="${e(state.query||'')}"><p id="launch-count" role="status"></p><div class="panel" id="launches-table"></div><button id="launch-prev">Précédent</button><button id="launch-next">Suivant</button>`,'Lancements');
 let offset=0,sequence=0;
 const load=async(start)=>{
  const request=++sequence;
  const result=await api('/api/launches?'+new URLSearchParams({page:'true',limit:'50',offset:String(start),q:state.query||''}));
  if(request!==sequence||navigation!==navigationVersion)return;
  offset=start;state.launches=result.items;
  app.querySelector('#launch-count').textContent=`${result.total} lancement(s) · Page ${Math.floor(offset/50)+1}`;
  app.querySelector('#launches-table').innerHTML=tableLaunches(result.items);bindLaunchRows();
  app.querySelector('#launch-prev').disabled=!offset;app.querySelector('#launch-next').disabled=offset+50>=result.total;
 };
 app.querySelector('#launch-search').oninput=event=>{state.query=event.target.value;load(0).catch(showErr)};
 app.querySelector('#launch-prev').onclick=()=>load(Math.max(0,offset-50)).catch(showErr);
 app.querySelector('#launch-next').onclick=()=>load(offset+50).catch(showErr);
 app.querySelector('#create-launch')?.addEventListener('click',openNewLaunch);
 await load(0);
}
async function openLaunch(id,folder=state.folder){const version=++navigationVersion;const [detail,completeness,reviews,values,impacts,fields,quality,excels,specs,mails,simGraph,simHistory,orliReconciliation,materials,approvalOverview]=await Promise.all([api('/api/launches/'+encodeURIComponent(id)),api('/api/launches/'+encodeURIComponent(id)+'/completeness'),api('/api/launches/'+encodeURIComponent(id)+'/reviews'),api('/api/launches/'+encodeURIComponent(id)+'/values'),api('/api/launches/'+encodeURIComponent(id)+'/impacts'),api('/api/business-value-fields'),api('/api/launches/'+encodeURIComponent(id)+'/quality'),api('/api/launches/'+encodeURIComponent(id)+'/excel-inspections'),api('/api/launches/'+encodeURIComponent(id)+'/specifications'),can('document.read','rose')?api('/api/launches/'+encodeURIComponent(id)+'/emails'):Promise.resolve(null),api('/api/launches/'+encodeURIComponent(id)+'/dependency-graph'),can('document.read','jaune')?api('/api/launches/'+encodeURIComponent(id)+'/impact-simulations'):Promise.resolve([]),api('/api/launches/'+encodeURIComponent(id)+'/orli-reconciliation'),can('document.read','jaune')&&can('document.read','rose')?api('/api/launches/'+encodeURIComponent(id)+'/materials'):Promise.resolve(null),api('/api/launches/'+encodeURIComponent(id)+'/approval-overview')]);if(version!==navigationVersion)return;const [clientPublications,supplierRequests]=await Promise.all([api(`/api/launches/${encodeURIComponent(id)}/client-publications`),api(`/api/launches/${encodeURIComponent(id)}/supplier-requests`)]);if(version!==navigationVersion)return;state.clientPublications=clientPublications;state.supplierRequests=supplierRequests;state.approvalOverview=approvalOverview;state.materials=materials;state.orliReconciliation=orliReconciliation;state.simGraph=simGraph;state.simHistory=simHistory;state.mailReport=mails;state.specReport=specs;state.qualityReport=quality;state.excelInspections=excels;state.detail=detail;state.completeness=completeness;state.workflowReviews=reviews;state.workflowValues=values;state.workflowImpacts=impacts;state.workflowFields=fields;state.view='detail';state.folder=folder;renderDetail()}
function installDetailNavigation(){
 app.querySelector('#open-order-canonical')?.addEventListener('click',()=>orderDossierPage(state.detail.order_id,state.folder).catch(showErr));
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

function renderDetail(){const d=state.detail;const f=d.folders.find(x=>x.slug===state.folder)||d.folders[0];const docs=f.can_read?f.documents:[];const allCount=d.folders.filter(x=>x.can_read).reduce((n,f)=>n+f.documents.length,0);mount(`<div class="detail-head"><div><button class="link" id="back-launches">${icon('back')} Tous les lancements</button>${d.order_id?`<button class="link" id="open-order-canonical">Ouvrir le Dossier Jaune de ${e(d.order_ref)}</button>`:''}<div class="page-kicker" style="margin-top:18px">${icon('layers')} LANCEMENT DE FABRICATION</div><h1 class="page-title">${e(d.name)}</h1><div class="detail-sub">${statusTag(d.status)}<span class="tag">${icon('calendar')} Créé le ${niceDate(d.created_at)}</span><span class="tag">${icon('file')} ${allCount} document(s) accessible(s)</span></div></div>${d.can_update?`<button class="secondary" id="edit-launch">${icon('pencil')} Modifier le dossier</button>`:''}</div><div class="section-heading"><h2>Les quatre sous-dossiers</h2><small>Organisation documentaire traditionnelle</small></div><div class="folder-grid">${d.folders.map((folder,i)=>`<button class="folder-card ${folder.slug===state.folder?'selected':''}" data-folder="${folder.slug}"><span class="fold-num">0${i+1}</span><div class="folder-glyph ${folder.slug}">${icon('folder')}</div><div class="folder-name">${['Jaune','Rose','Bleu','Vert'][i]} · ${e(folder.label)}</div><div class="folder-count">${folder.can_read?`${folder.documents.length} document(s)`:'Accès restreint'}</div></button>`).join('')}</div>${renderCompleteness()}<div class="detail-layout"><section><div class="section-heading" style="margin-top:0"><h2>Documents · ${e(f.label)}</h2>${f.can_write?`<button class="primary tiny" id="upload-doc">${icon('upload')} Déposer un document</button>`:''}</div><div class="panel">${!f.can_read?`<div class="denied">${icon('lock')}<p>Vous n’avez pas accès à cette rubrique.</p></div>`:docs.length?`<div class="table-scroll"><table><thead><tr><th>Document</th><th>Type</th><th>Version</th><th>Action</th></tr></thead><tbody>${docs.map(doc=>`<tr><td><div class="file-name"><div class="doc-icon">${icon('file')}</div><div><div class="row-title">${e(doc.title)}</div><div class="row-sub">${e(doc.latest.original_name)} · ${sizeText(doc.latest.size)}</div></div></div></td><td class="small">${e(doc.doc_type)}</td><td><span class="tag">v${doc.latest.number}</span></td><td><div class="doc-actions"><button class="link" data-history="${e(doc.id)}">${icon('clock')} Historique</button><button class="link" data-download="${e(doc.id)}" data-ver="${doc.latest.number}" title="Télécharger">${icon('download')}</button></div></td></tr>`).join('')}</tbody></table></div>`:`<div class="empty"><div class="empty-icon">${icon('file')}</div><strong>Ce sous-dossier est vide</strong>Déposez une première pièce pour enrichir ce lancement.</div>`}</div></section><aside class="panel detail-side"><h3>Informations du lancement</h3><div class="info-pair"><label>IDENTIFIANT TECHNIQUE</label><span style="font-family:monospace;font-size:10px;">${e(d.id)}</span></div><div class="info-pair"><label>RÉFÉRENCE ORLI</label><span>${e(d.orli_ref||'Non renseignée — liaison ultérieure possible')}</span></div><div class="info-pair"><label>COMMANDE ASSOCIÉE</label><span>${e(d.order_ref||'Non renseignée')}</span></div><div class="info-pair"><label>CLIENT</label><span>${e(d.client_name||'Non renseigné')}</span></div><div class="info-pair"><label>ÉTAT</label>${statusTag(d.status)}</div><div class="info-pair"><label>DERNIÈRE MISE À JOUR</label><span>${niceDate(d.updated_at)}</span></div></aside></div>${renderWorkflow()}${renderQuality()}${renderIntake()}${renderPaper()}${renderSpec()}${renderMail()}${renderImpactSimulation()}${renderOrliReconciliation()}${renderMaterialReport()}${renderApprovals()}${renderSharing()}`,'Dossiers jaunes / '+d.name);
 installDetailNavigation();
 app.querySelector('#back-launches').onclick=()=>navigate('launches');app.querySelector('#edit-launch')?.addEventListener('click',openEditLaunch);app.querySelectorAll('[data-folder]').forEach(el=>el.addEventListener('click',()=>{state.folder=el.dataset.folder;renderDetail()}));app.querySelector('#upload-doc')?.addEventListener('click',openUpload);app.querySelectorAll('[data-history]').forEach(el=>el.addEventListener('click',()=>openVersions(el.dataset.history)));app.querySelectorAll('[data-download]').forEach(el=>el.addEventListener('click',()=>download(el.dataset.download,+el.dataset.ver)));bindCompleteness();bindWorkflow();bindQuality();bindIntake();bindPaper();bindSpec();bindMail();bindImpactSimulation();bindOrliReconciliation();bindMaterialReport();bindApprovals();bindSharing();}
function modal(title,content,wide=false){overlay.innerHTML=`<div class="modal-scrim"><div class="modal ${wide?'wide':''}" role="dialog" aria-modal="true" aria-label="${e(title)}"><div class="modal-head"><h2>${e(title)}</h2><button id="close-modal" aria-label="Fermer">${icon('x')}</button></div><div class="modal-body">${content}</div></div></div>`;overlay.querySelector('#close-modal').onclick=closeModal;overlay.querySelector('.modal-scrim').addEventListener('click',evt=>{if(evt.target.classList.contains('modal-scrim'))closeModal()});manageDialogFocus()}
function closeModal(){
 const dialog=overlay.querySelector('[role=dialog]');
 if(dialog?.beforeClose&&!dialog.beforeClose())return;
 overlay.innerHTML='';
 dialog?.afterClose?.();
}
function val(id){return overlay.querySelector('#'+id)?.value.trim()||''}
function openNewLaunch(){modal('Créer un lancement historique',`<p class="modal-desc">Vous pouvez ouvrir un dossier avant d’obtenir son numéro ORLI. Pour partager un Dossier Jaune, créez le lancement depuis sa commande. Un lancement historique sans commande reste isolé.</p><form id="new-launch-form"><div class="field"><label>Nom du lancement *</label><input id="l-name" maxlength="180" required placeholder="Ex. Vestes coton · lot automne" /></div><div class="two-fields"><div class="field"><label>Client</label><input id="l-client" maxlength="150" placeholder="Facultatif" /></div><div class="field"><label>Référence commande</label><input id="l-order" maxlength="100" placeholder="Facultatif" /></div></div><div class="field"><label>Référence ORLI</label><input id="l-orli" maxlength="100" placeholder="Facultative, à compléter plus tard" /></div><div class="modal-actions"><button class="secondary" type="button" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('plus')} Créer le dossier</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#new-launch-form').onsubmit=async ev=>{ev.preventDefault();try{const created=await api('/api/launches',{method:'POST',body:JSON.stringify({name:val('l-name'),client_name:val('l-client')||null,order_ref:val('l-order')||null,orli_ref:val('l-orli')||null})});closeModal();toast('Lancement historique créé');await openLaunch(created.id,'jaune')}catch(err){showErr(err)}}}
function openEditLaunch(){const d=state.detail;modal('Mettre à jour le lancement',`<p class="modal-desc">La référence ORLI peut être ajoutée ou modifiée sans perdre les documents ni les versions existantes.</p><form id="edit-launch-form"><div class="field"><label>Nom du lancement</label><input id="e-name" maxlength="180" required value="${e(d.name)}" /></div><div class="two-fields"><div class="field"><label>Client</label><input id="e-client" maxlength="150" value="${e(d.client_name||'')}" /></div><div class="field"><label>Référence commande</label><input id="e-order" maxlength="100" value="${e(d.order_ref||'')}" /></div></div><div class="field"><label>Référence ORLI</label><input id="e-orli" maxlength="100" value="${e(d.orli_ref||'')}" /></div><div class="field"><label>Statut</label><select id="e-status">${['À compléter','En cours','En validation','Clôturé'].map(s=>`<option ${s===d.status?'selected':''}>${s}</option>`).join('')}</select></div><div class="modal-actions"><button type="button" id="cancel-modal" class="secondary">Annuler</button><button class="primary" type="submit">${icon('check')} Enregistrer</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#edit-launch-form').onsubmit=async ev=>{ev.preventDefault();try{await api('/api/launches/'+d.id,{method:'PATCH',body:JSON.stringify({name:val('e-name'),client_name:val('e-client')||null,order_ref:val('e-order')||null,orli_ref:val('e-orli')||null,status:val('e-status')})});closeModal();toast('Informations mises à jour');await openLaunch(d.id,state.folder)}catch(err){showErr(err)}}}
function openUpload(){openUploadBatch();}
function findDoc(id){return state.detail.folders.flatMap(f=>f.documents).find(d=>d.id===id)}
function openVersions(id){const d=findDoc(id);if(!d)return;modal('Versions · '+d.title,`<p class="modal-desc">Les versions antérieures restent accessibles. Aucun remplacement destructif n’est effectué.</p>${[...d.versions].reverse().map(v=>`<div class="version-row"><div><strong>Version ${v.number}</strong> ${v.number===d.latest.number?'<span class="tag green">Courante</span>':''}<div class="version-meta">${e(v.original_name)} · ${sizeText(v.size)} · ${niceDate(v.created_at)}</div><div class="version-meta">SHA-256 : ${e(v.sha256.slice(0,20))}…</div></div><button class="secondary tiny" data-vdownload="${v.number}">${icon('download')} Télécharger</button>${/\.pdf$/i.test(v.original_name)?`<button class="secondary tiny" data-launch-pdf="${e(v.id)}">Lire le PDF · v${v.number}</button>`:''}</div>`).join('')}${can('document.write',d.folder)?`<form id="new-version-form" style="padding-top:20px;margin-top:10px;border-top:1px solid #edf0ed"><div class="field"><label>Ajouter une nouvelle version</label><input type="file" id="version-file" accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.txt,.eml" required /></div><button class="primary" type="submit">${icon('plus')} Enregistrer la nouvelle version</button></form>`:''}`,true);overlay.querySelectorAll('[data-vdownload]').forEach(el=>el.onclick=()=>download(d.id,+el.dataset.vdownload));const launchId=state.detail.id,folder=state.folder;overlay.querySelectorAll('[data-launch-pdf]').forEach(el=>el.onclick=()=>openPdfReader(d.id,el.dataset.launchPdf,()=>openLaunch(launchId,folder)).catch(showErr));overlay.querySelector('#new-version-form')?.addEventListener('submit',async ev=>{ev.preventDefault();const fd=new FormData();fd.append('file',overlay.querySelector('#version-file').files[0]);try{await api('/api/documents/'+d.id+'/versions',{method:'POST',body:fd});closeModal();toast('Nouvelle version conservée');await openLaunch(state.detail.id,state.folder)}catch(err){showErr(err)}})}
async function download(docId,number){try{const r=await api(`/api/documents/${docId}/versions/${number}/download`);const blob=await r.blob();const d=findDoc(docId);const v=d?.versions.find(x=>x.number===number);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=v?.original_name||'document';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(err){showErr(err)}}
async function admin(){state.view='admin';[state.roles,state.users]=await Promise.all([api('/api/admin/roles'),api('/api/admin/users')]);const completionHtml=await completenessAdminPanel();const workflowHtml=await workflowAdminPanel();const approvalHtml=await approvalAdminPanel();mount(`<div class="page-heading"><div><div class="page-kicker">${icon('shield')} GESTION DES ACCÈS</div><h1 class="page-title">Administration<span class="brand-accent">.</span></h1><p class="page-lead">Créez les rôles et attribuez les autorisations nécessaires aux collaborateurs. Le rôle initial Administrateur reste protégé.</p></div></div><div class="section-heading"><h2>Collaborateurs</h2><button class="primary tiny" id="add-user">${icon('plus')} Ajouter un utilisateur</button></div><div class="panel table-scroll"><table><thead><tr><th>Utilisateur</th><th>Email</th><th>Rôle(s)</th><th>État</th></tr></thead><tbody>${state.users.map(u=>`<tr><td class="row-title">${e(u.name)}</td><td>${e(u.email)}</td><td>${e(u.roles.join(', '))}</td><td><span class="tag green">${u.active?'Actif':'Désactivé'}</span> <button class="secondary tiny" data-user-access="${e(u.id)}">Modifier les accès</button></td></tr>`).join('')}</tbody></table></div><div class="section-heading"><h2>Rôles configurés</h2><button class="secondary tiny" id="add-role">${icon('plus')} Nouveau rôle</button></div><div class="panel table-scroll"><table><thead><tr><th>Rôle</th><th>Nombre d’autorisations</th><th>Portée</th></tr></thead><tbody>${state.roles.map(r=>`<tr><td class="row-title">${e(r.name)}</td><td>${r.name==='Administrateur'?'Toutes':r.permissions.length}</td><td class="small">${r.name==='Administrateur'?'Administration complète':e(r.permissions.map(p=>p.action+(p.folder?' ('+p.folder+')':'')).join(', ')||'Aucune permission')}</td></tr>`).join('')}</tbody></table></div><p class="permission-lock">Le contrôle des autorisations s’effectue côté serveur, y compris lors des téléchargements. Les droits par lancement peuvent maintenant être restreints depuis la fiche de chaque dossier. Les permissions par rôle et sous-dossier s’appliquent toujours.</p>${completionHtml}${workflowHtml}${approvalHtml}`,'Administration');bindEmployeeAccess();app.querySelector('#add-user').onclick=openNewUser;app.querySelector('#add-role').onclick=openNewRole;bindCompletenessAdmin();bindWorkflowAdmin();bindApprovalAdmin()}
function openNewRole(){const folderChecks=['jaune','rose','bleu','vert'].map(s=>`<label class="checkbox-line"><input type="checkbox" name="grant" value="document.read:${s}"> Lecture · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="document.write:${s}"> Dépôt · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="completeness.review:${s}"> Contrôle de complétude · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="document.review:${s}"> Décision documentaire · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="value.write:${s}"> Valeurs métier · ${s}</label><label class="checkbox-line"><input type="checkbox" name="grant" value="impact.review:${s}"> Suivi des impacts · ${s}</label>${s==='rose'?`<label class="checkbox-line"><input type="checkbox" name="grant" value="commitment.review:rose"> Confirmation des engagements email · rose</label>`:''}`).join('');modal('Créer un rôle',`<form id="role-form"><div class="field"><label>Nom du rôle</label><input id="r-name" maxlength="80" required placeholder="Ex. Gestion documentaire" /></div><p class="modal-desc">Autorisations globales</p><div class="permission-grid">${[['launch.read','Voir les lancements'],['launch.create','Créer les lancements'],['launch.update','Modifier les lancements']].map(([v,label])=>`<label class="checkbox-line"><input type="checkbox" name="grant" value="${v}"> ${label}</label>`).join('')}</div><p class="modal-desc" style="margin-top:20px">Autorisations documentaires par rubrique</p><div class="permission-grid">${folderChecks}</div><div class="modal-actions"><button type="button" class="secondary" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('check')} Créer le rôle</button></div></form>`,true);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#role-form').onsubmit=async evt=>{evt.preventDefault();const permissions=[...overlay.querySelectorAll('[name=grant]:checked')].map(el=>{const [action,folder]=el.value.split(':');return {action,folder:folder||null}});try{await api('/api/admin/roles',{method:'POST',body:JSON.stringify({name:val('r-name'),permissions})});closeModal();toast('Rôle créé');await admin()}catch(err){showErr(err)}}}
function openNewUser(){modal('Créer un collaborateur',`<form id="user-form"><div class="field"><label>Nom complet</label><input id="u-name" required maxlength="120" /></div><div class="field"><label>Email</label><input id="u-email" type="email" required maxlength="254" /></div><div class="field"><label>Mot de passe initial (12 caractères minimum)</label><input id="u-pass" type="password" minlength="12" required autocomplete="new-password" /></div><div class="field"><label>Rôle</label><select id="u-role">${state.roles.map(r=>`<option value="${e(r.id)}">${e(r.name)}</option>`).join('')}</select></div><div class="modal-actions"><button type="button" class="secondary" id="cancel-modal">Annuler</button><button class="primary" type="submit">${icon('check')} Créer le compte</button></div></form>`);overlay.querySelector('#cancel-modal').onclick=closeModal;overlay.querySelector('#user-form').onsubmit=async evt=>{evt.preventDefault();try{await api('/api/admin/users',{method:'POST',body:JSON.stringify({name:val('u-name'),email:val('u-email'),password:overlay.querySelector('#u-pass').value,role_ids:[val('u-role')]})});closeModal();toast('Compte collaborateur créé');await admin()}catch(err){showErr(err)}}}
async function auditView(offset=0){const navigation=navigationVersion;const rows=await api('/api/admin/audit?limit=100&offset='+offset);if(navigation!==navigationVersion)return;state.view='audit';state.audit=rows;mount(`<div class="page-heading"><div><div class="page-kicker">${icon('activity')} TRAÇABILITÉ</div><h1 class="page-title">Journal d’activité<span class="brand-accent">.</span></h1><p class="page-lead">Journal chronologique · Page ${Math.floor(offset/100)+1}</p></div></div><div class="panel table-scroll"><table><thead><tr><th>Action</th><th>Utilisateur</th><th>Élément</th><th>Date</th></tr></thead><tbody>${state.audit.map(x=>`<tr><td class="row-title">${e(x.action)}</td><td class="audit-item">${e((x.actor_id||'—').slice(0,12))}</td><td class="audit-item">${e(x.target_type)} · ${e(x.target_id.slice(0,12))}</td><td class="small">${niceDate(x.occurred_at)}</td></tr>`).join('')}</tbody></table></div><button id="audit-prev" ${offset===0?'disabled':''}>Précédent</button><button id="audit-next" ${rows.length<100?'disabled':''}>Suivant</button>`,'Journal d’activité');
 app.querySelector('#audit-prev').onclick=()=>auditView(Math.max(0,offset-100)).catch(showErr);
 app.querySelector('#audit-next').onclick=()=>auditView(offset+100).catch(showErr);
}
async function navigate(view){++navigationVersion;try{if(view==='home')await home();else if(view==='orders'||view==='dossiers')await ordersPage(view);else if(view==='documents')location.assign('/search');else if(view==='suppliers'||view==='clients')await directoryPage(view==='suppliers'?'supplier':'client');else if(view==='receipts')await receiptsPage();else if(view==='validations')await validationsPage();else if(view==='experience')await experiencePage();else if(view==='launches')await launchList();else if(view==='actions')await workspaceActions();else if(view==='assistant')await assistantPage();else if(view==='notifications')await notificationsPage();else if(view==='pilot')await pilotPage();else if(view==='orli'&&state.me.admin)await orliAdmin();else if(view==='admin'&&state.me.admin)await admin();else if(view==='audit'&&state.me.admin)await auditView()}catch(err){showErr(err)}}
window.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
// Partie intégrée dans app.js lors de la construction du MVP 0.2.
// Defer startup until every feature script (including paper.js) is evaluated.
(async function init(){await new Promise(resolve=>document.addEventListener('DOMContentLoaded',resolve,{once:true}));try{state.me=await api('/api/auth/me');if(!(await paperOpenDeepLink()))await navigate('dossiers')}catch{renderSpaceChoice()}})();
