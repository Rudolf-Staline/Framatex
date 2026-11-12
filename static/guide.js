/* Framatex Guide: one shared catalogue, read-only navigation and resumable tours. */
'use strict';
window.FramatexGuide=(()=>{
 let adapter=null,catalog=null,contextOverride={},currentProcedure=null,driver=null,tourState=null,opened=false,focusBefore=null;
 const audienceLabels={admin:'Administrateur',employee:'Employé',supplier:'Fournisseur',client:'Client',public:'Visiteur'};
 const categoryLabels={decouverte:'Découverte',commandes:'Commandes',documents:'Documents',recherche:'Recherche',controles:'Contrôles',administration:'Administration',receptions:'Réceptions',validations:'Validations',suivi:'Suivi',partenaires:'Partenaires',orli:'ORLI',connexion:'Connexion',fournisseurs:'Fournisseurs',clients:'Clients'};
 const progressLabels={started:'Commencée',paused:'En pause',finished:'Terminée',skipped:'Ignorée',missing:'Étape indisponible'};
 const seen=new Set(),root=document.createElement('div');root.id='framat-guide-root';document.body.append(root);
 const $=selector=>root.querySelector(selector);
 const el=(tag,text,attrs={})=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n};
 const button=(text,fn,attrs={})=>{const b=el('button',text,{type:'button',...attrs});b.addEventListener('click',()=>Promise.resolve(fn()).catch(showError));return b};
 let resumeSurface=null;try{resumeSurface=JSON.parse(sessionStorage.getItem('framat-guide-pending')||'null')?.surface}catch{}
 const surface=()=>resumeSurface||adapter?.surface?.()||new URLSearchParams(location.search).get('surface')||'internal';
 const context=()=>({page:location.pathname==='/help'?'help':'unknown',...contextOverride,...adapter?.context?.()});
 async function api(path,options={}){
  const res=await fetch(path,{...options,headers:{'X-Framatex-Request':'1','X-Framatex-Guide-Surface':surface(),...(options.body?{'Content-Type':'application/json'}:{})},credentials:'same-origin'});
  const body=await res.json().catch(()=>({}));if(!res.ok)throw Object.assign(new Error(typeof body.detail==='string'?body.detail:'Vérifiez les informations et vos habilitations.'),{status:res.status});return body;
 }
 function showError(error){const status=$('#guide-status');if(status)status.textContent=error instanceof TypeError?'Connexion interrompue. Réessayez lorsque le réseau est disponible.':error.message;else{open().then(()=>showError(error)).catch(()=>{})}}
 async function load(){
  const previousProfile=catalog?.profile_key,previousSession=catalog?.session_key;
  try{catalog=await api('/api/guide/catalog')}catch(e){if(e.status!==401)throw e;catalog=await api('/api/guide/public')}
  if(previousProfile&&(previousProfile!==catalog.profile_key||previousSession!==catalog.session_key)){contextOverride={};tourState=null;driver?.destroy();close()}
  return catalog;
 }
 function register(value){adapter=value;document.dispatchEvent(new Event('framat:guide-adapter'))}
 function close(){opened=false;$('#guide-panel')?.remove();if(focusBefore?.isConnected)focusBefore.focus()}
 function shell(full=false){
  $('#guide-panel')?.remove();opened=true;focusBefore=document.activeElement;
  const panel=el(full?'section':'aside',undefined,{id:'guide-panel','aria-label':'Framatex Guide',...(full?{}:{role:'dialog','aria-modal':'true'})});
  panel.className=full?'guide-full':'guide-panel';
  const head=el('header');head.append(el('h2','Framatex Guide'),button('Fermer',close,{'aria-label':'Fermer Framatex Guide'}));panel.append(head);
  const nav=el('nav',undefined,{'aria-label':'Navigation de l’aide'});nav.append(button('Centre d’aide',()=>home()));if(catalog?.audience!=='public')nav.append(button('Mes visites',()=>showTours()),button('Aide de cette page',()=>recommend()));
  if(catalog?.audience==='admin')nav.append(button('Statistiques',stats));const fullLink=el('a','Centre d’aide en pleine page',{href:'/help?surface='+surface()});fullLink.onclick=()=>sessionStorage.setItem('framat-guide-help-context',JSON.stringify({profile:catalog.profile_key,context:context()}));nav.append(fullLink);panel.append(nav);
  const label=el('label','Rechercher dans l’aide',{for:'guide-search'}),input=el('input',undefined,{id:'guide-search',type:'search',maxlength:'500',placeholder:'Ex. ajouter une fiche technique'});
  const form=el('form');form.append(label,input,el('button','Rechercher',{type:'submit'}));
  form.onsubmit=async event=>{event.preventDefault();await busy(form,()=>search(input.value))};panel.append(form);
  const status=el('p','Procédures locales disponibles sans Gemini.',{id:'guide-status',role:'status','aria-live':'polite'});panel.append(status,el('div',undefined,{id:'guide-content'}));root.append(panel);
  panel.addEventListener('keydown',event=>{
   if(event.key==='Escape'){event.stopPropagation();close()}
   if(event.key==='Tab'&&!full){const nodes=[...panel.querySelectorAll('button,input,select,textarea,a[href]')].filter(n=>!n.disabled&&n.getClientRects().length);const first=nodes[0],last=nodes[nodes.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
  });
  input.focus();return panel;
 }
 async function busy(form,fn){if(form.dataset.busy)return;form.dataset.busy='1';const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{await fn()}catch(e){showError(e)}finally{delete form.dataset.busy;buttons.forEach(b=>b.disabled=false)}}
 function cards(items,title){
  const container=$('#guide-content');container.replaceChildren(el('h3',title));
  if(!items.length)container.append(el('p','Aucune procédure autorisée ne correspond. Précisez votre demande ou consultez une catégorie.'));
  for(const p of items){const card=el('article');card.append(el('h4',p.title),el('p',p.description),button('Consulter la procédure',()=>procedure(p.id),{'data-guide-procedure':p.id}));container.append(card)}
 }
 async function home(){
  if(!opened)shell(location.pathname==='/help');
  cards(catalog.procedures.filter(p=>(catalog.popular||[]).includes(p.id)),'Procédures populaires');
  const content=$('#guide-content');
  const categories=[...new Set(catalog.procedures.map(p=>p.category))];const list=el('nav',undefined,{'aria-label':'Catégories de l’aide'});
  for(const category of categories)list.append(button(categoryLabels[category]||category,()=>cards(catalog.procedures.filter(p=>p.category===category),categoryLabels[category]||category)));
  content.prepend(list);
  if(catalog.recent?.length){const recent=el('section');recent.append(el('h3','Consultées récemment'));for(const id of catalog.recent){const p=catalog.procedures.find(p=>p.id===id);if(p)recent.append(button(p.title,()=>procedure(id)))}content.append(recent)}
  const recommendItems=catalog.procedures.filter(p=>p.destination===(context().page||'home')).slice(0,3);
  if(recommendItems.length){const rec=el('section');rec.append(el('h3','Pour cette page'));recommendItems.forEach(p=>rec.append(button(p.title,()=>procedure(p.id))));content.append(rec)}
 }
 async function open(){await load();shell(location.pathname==='/help');await home()}
 async function recommend(){const r=await api('/api/guide/search?'+new URLSearchParams({page:context().page||'home'}));cards(r.items,'Aide de cette page')}
 async function search(question){
  if(catalog.audience==='public'){cards(catalog.procedures,'Connexion et activation');return}
  $('#guide-status').textContent='Recherche dans les procédures vérifiées…';
  const result=await api('/api/guide/ask',{method:'POST',body:JSON.stringify({question,context:context()})});
  cards(result.procedures,result.title);
  if(result.procedure_ids.length===1&&!result.requires_clarification)contextOverride.procedure_id=result.procedure_ids[0];
  const answer=el('p',result.answer);answer.className='guide-answer';$('#guide-content').prepend(answer);
  if(result.requires_clarification)$('#guide-content').prepend(el('p','Choisissez la procédure qui correspond à votre besoin, ou précisez votre question.'));
  const bar=el('div');for(const action of result.actions)bar.append(button(action.label,()=>execute(action.id)));
  $('#guide-content').append(bar);
  $('#guide-status').textContent=result.source==='gemini'?'Procédures sélectionnées avec Gemini, actions vérifiées par Framatex.':'Procédures locales vérifiées'+(result.fallback_reason&&result.fallback_reason!=='disabled'?' · enrichissement IA indisponible.':'.');
 }
 async function procedure(id){
  const p=catalog.procedures.find(p=>p.id===id);if(!p)throw new Error('Procédure inaccessible : rechargez le guide.');
  currentProcedure=p;contextOverride.procedure_id=id;const content=$('#guide-content');content.replaceChildren(el('h3',p.title),el('p',p.description),el('p','Public concerné : '+p.audience.map(a=>audienceLabels[a]||a).join(', ')),el('h4','Prérequis'));
  const prereq=el('ul');p.prerequisites.forEach(s=>prereq.append(el('li',s)));content.append(prereq);
  let step=0;const stepArea=el('div'),list=el('ol');p.steps.forEach(s=>list.append(el('li',s.description)));content.append(list,stepArea);
  const render=()=>{stepArea.replaceChildren(el('p',`Étape ${step+1} / ${p.steps.length} : ${p.steps[step].description}`),button('Étape précédente',()=>{step=Math.max(0,step-1);render()}),button('Étape suivante',()=>{step=Math.min(p.steps.length-1,step+1);render()}))};render();
  content.append(el('h4','Résultat attendu'),el('p',p.result),el('h4','Problèmes fréquents'));p.problems.forEach(x=>content.append(el('p',x.problem+' : '+x.solution)));
  if(p.limitations.length){content.append(el('h4','Limites'));p.limitations.forEach(s=>content.append(el('p',s)))}
  if(catalog.audience!=='public'){
   for(const id of p.actions)if(!id.startsWith('read_'))content.append(button(id.startsWith('show_')?'Me montrer comment faire':'Ouvrir la fonctionnalité',()=>execute(id)));
   await api('/api/guide/procedures/'+p.id+'/visit',{method:'POST'});
   const feedback=el('section');feedback.append(el('h4','Cette explication vous a-t-elle aidé ?'));
   const send=async helpful=>{await api('/api/guide/feedback',{method:'POST',body:JSON.stringify({procedure_id:p.id,helpful,reason:helpful?'none':'unclear'})});feedback.replaceChildren(el('p',helpful?'Merci pour votre retour.':'Merci. Vous pouvez consulter une autre procédure ou signaler une explication imprécise.'));if(!helpful){feedback.append(button('Voir d’autres procédures',home),button('Signaler une explication obsolète',async()=>{await api('/api/guide/feedback',{method:'POST',body:JSON.stringify({procedure_id:p.id,helpful:false,reason:'outdated'})});feedback.append(el('p','Signalement enregistré sans texte confidentiel.'))}))}};
   feedback.append(button('Oui',()=>send(true)),button('Non',()=>send(false)));content.append(feedback);
  }
  if(location.pathname==='/help')history.replaceState(null,'','#procedure/'+id);
 }
 function pending(data){sessionStorage.setItem('framat-guide-pending',JSON.stringify({...data,profile:catalog.profile_key,session:catalog.session_key,surface:surface()}))}
 async function selectContext(kind){
  const suffix=kind==='launch'&&context().order_id?'?order_id='+encodeURIComponent(context().order_id):'';
  const rows=await api('/api/guide/contexts/'+kind+suffix);if(!rows.length)throw new Error('Aucun objet autorisé disponible. Créez-le ou demandez les droits nécessaires avant de poursuivre.');
  if(!opened)shell();const content=$('#guide-content');content.replaceChildren(el('h3','Choisir le contexte de la visite'),el('p','Sélectionnez vous-même l’objet concerné. Le guide ne choisit aucune commande à votre place.'));
  return new Promise(resolve=>{
   const select=el('select',undefined,{id:'guide-context-choice'});select.append(el('option','Choisir…',{value:''}));rows.forEach(row=>select.append(el('option',row.label,{value:row.id})));
   content.append(el('label','Objet autorisé',{for:'guide-context-choice'}),select,button('Utiliser cette sélection',()=>{if(!select.value)return;contextOverride[{order:'order_id',launch:'launch_id',supplier_request:'supplier_request_id',client_order:'client_order_id'}[kind]]=select.value;resolve(true)}),button('Annuler',()=>resolve(false)));
  });
 }
 async function go(d,ctx,folder){
  if(adapter?.go&&await adapter.go(d,ctx,folder)!==false)return true;
  pending(tourState?{tour:tourState.tour.id,index:tourState.index,context:ctx}:{destination:d.id,context:ctx,folder});
  location.assign(d.route||(d.surface==='partner'?'/partners':'/'));return false;
 }
 async function execute(id){
  let action=await api('/api/guide/actions/'+encodeURIComponent(id)+'/resolve',{method:'POST',body:JSON.stringify(context())});
  if(action.type==='open_procedure')return procedure(action.procedure_id);
  if(action.type==='start_tour')return startTour(action.destination);
  if(action.requires_selection){if(!await selectContext(action.requires_selection))return;action=await api('/api/guide/actions/'+encodeURIComponent(id)+'/resolve',{method:'POST',body:JSON.stringify(context())})}
  if(await go(action.navigation,action.context,action.folder)){close();const target=await waitTarget(action.navigation.target);target.tabIndex=-1;target.focus();target.scrollIntoView({block:'center'})}
 }
 function waitTarget(id,timeout=5000){return new Promise((resolve,reject)=>{const end=Date.now()+timeout;const poll=()=>{const n=document.querySelector('[data-guide-target="'+CSS.escape(id)+'"]');if(n&&n.getClientRects().length)return resolve(n);if(Date.now()>end)return reject(new Error('L’étape n’est pas encore disponible. Ouvrez le formulaire indiqué puis réessayez, ou consultez la procédure. La visite est suspendue.'));setTimeout(poll,60)};poll()})}
 async function save(status){if(!tourState)return;await api('/api/guide/progress',{method:'PUT',body:JSON.stringify({tour_id:tourState.tour.id,version:tourState.tour.version,step:tourState.index,status})})}
 async function prepareStep(index){
  tourState.index=index;const step=tourState.tour.steps[index];const d=catalog.navigation[step.destination];if(!d)throw new Error('Destination de visite indisponible pour votre profil.');
  const resource=d.context,key={order:'order_id',launch:'launch_id',supplier_request:'supplier_request_id',client_order:'client_order_id'}[resource];
  if(key&&!context()[key]){driver?.destroy();if(!await selectContext(resource))return false}
  // Resolve against the server again: changed roles cannot reuse a cached action.
  if(tourState.tour.procedure_id)await api('/api/guide/actions/open_'+tourState.tour.procedure_id+'/resolve',{method:'POST',body:JSON.stringify(context())});
  await save('started');if(!await go(d,context(),step.destination==='order_upload'?'jaune':step.destination.replace('order_','')))return false;
  close();await waitTarget(step.target);return true;
 }
 async function pauseTour(){try{await save('paused')}finally{driver?.destroy();tourState=null}}
 async function startTour(id,index=0){
  const t=await api('/api/guide/tours/'+encodeURIComponent(id));await load();tourState={tour:t,index:Math.min(index,t.steps.length-1)};
  try{
   if(!await prepareStep(tourState.index))return;
   driver=window.driver.js.driver({animate:!matchMedia('(prefers-reduced-motion: reduce)').matches,allowClose:true,showProgress:true,allowKeyboardControl:true,disableActiveInteraction:false,
    nextBtnText:'Suivant',prevBtnText:'Retour',doneBtnText:'Terminer',progressText:'{{current}} / {{total}}',popoverClass:'framat-guide-tour',
    steps:t.steps.map(s=>({element:()=>document.querySelector('[data-guide-target="'+CSS.escape(s.target)+'"]'),popover:{title:s.title,description:s.description}})),
    onNextClick:async()=>{try{if(tourState.index===t.steps.length-1){await save('finished');driver.destroy();tourState=null;return}if(await prepareStep(tourState.index+1))driver.drive(tourState.index)}catch(e){await missing(e)}},
    onPrevClick:async()=>{try{if(tourState.index>0&&await prepareStep(tourState.index-1))driver.drive(tourState.index)}catch(e){await missing(e)}},
    onCloseClick:pauseTour,onDestroyStarted:pauseTour,
   });driver.drive(tourState.index);
  }catch(e){await missing(e)}
 }
 async function missing(error){driver?.destroy();await save('missing').catch(()=>{});await open();showError(error);const content=$('#guide-content');content.prepend(button('Réessayer cette étape',()=>startTour(tourState.tour.id,tourState.index)),button('Quitter la visite',()=>{tourState=null;close()}))}
 async function showTours(){
  const [tours,progress]=await Promise.all([api('/api/guide/tours'),api('/api/guide/progress')]);const content=$('#guide-content');content.replaceChildren(el('h3','Mes visites interactives'));
  if(!tours.length)content.append(el('p','Aucune visite disponible pour vos habilitations actuelles.'));
  for(const t of tours){const previous=progress.find(p=>p.tour_id===t.id&&p.version===t.version);const row=el('article');row.append(el('h4',t.procedure_id?catalog.procedures.find(p=>p.id===t.procedure_id)?.title:'Découvrir mon espace'),el('p',previous?`${progressLabels[previous.status]||previous.status} · étape ${previous.step+1}/${t.steps.length}`:'Pas encore commencée'),button(previous&&!['finished','skipped'].includes(previous.status)?'Reprendre':'Commencer',()=>startTour(t.id,['finished','skipped'].includes(previous?.status)?0:previous?.step||0)),button('Recommencer la visite',()=>startTour(t.id,0)),button('Ignorer cette visite',async()=>{await api('/api/guide/progress',{method:'PUT',body:JSON.stringify({tour_id:t.id,version:t.version,step:previous?.step||0,status:'skipped'})});await showTours()}));content.append(row)}
 }
 async function stats(){const report=await api('/api/guide/stats');const content=$('#guide-content');content.replaceChildren(el('h3','Statistiques agrégées du guide'),el('p','Aucun texte de question ni contenu documentaire n’est conservé.'));const list=el('ul');for(const p of report.procedure_views)list.append(el('li',p.procedure_id+' : '+p.views+' consultation(s)'));content.append(list);for(const [kind,count] of Object.entries(report.events))content.append(el('p',kind+' : '+count));for(const row of report.insufficient)content.append(el('p','À améliorer : '+row.procedure_id+' · '+row.count));for(const row of report.abandonment)content.append(el('p','Interruption : '+row.tour_id+' · étape '+(row.step+1)+' · '+row.count))}
 async function welcome(){
  const welcomeKey='framat-guide-welcome:'+catalog?.profile_key+':'+catalog?.session_key;
  if(!catalog||catalog.audience==='public'||!catalog.welcome_available||!['new','later'].includes(catalog.automatic)||seen.has(welcomeKey)||sessionStorage.getItem(welcomeKey))return;
  const host=adapter?.welcomeHost?.();if(!host)return;seen.add(welcomeKey);sessionStorage.setItem(welcomeKey,'1');
  const banner=el('section',undefined,{'aria-label':'Bienvenue sur Framatex'});banner.className='guide-welcome';banner.append(el('p','Bienvenue sur Framatex ! Souhaitez-vous découvrir votre espace de travail ?'));
  const decide=async choice=>{await api('/api/guide/preferences',{method:'PUT',body:JSON.stringify({automatic:choice})});banner.remove();if(choice==='accepted')await startTour('welcome_'+catalog.audience)};
  banner.append(button('Commencer la visite',()=>decide('accepted')),button('Plus tard',()=>decide('later')),button('Ne plus proposer automatiquement',()=>decide('never')));host.prepend(banner);
 }
 async function refresh(){try{await load();await welcome()}catch{}}
 async function init(){
  const access=button('Framatex Guide',open,{'data-guide-target':'guide-access','aria-label':'Ouvrir Framatex Guide'});access.id='guide-access';root.append(access);
  await load();
  if(location.pathname==='/help'){try{const saved=JSON.parse(sessionStorage.getItem('framat-guide-help-context')||'null');if(saved?.profile===catalog.profile_key)contextOverride=saved.context||{}}catch{};shell(true);await home();const match=location.hash.match(/^#procedure\/([a-z0-9_]+)$/);if(match)await procedure(match[1]);}
  let stored=null;try{stored=JSON.parse(sessionStorage.getItem('framat-guide-pending')||'null')}catch{}
  if(stored&&stored.profile===catalog.profile_key&&stored.session===catalog.session_key){sessionStorage.removeItem('framat-guide-pending');contextOverride=stored.context||{};await adapter?.ready?.();if(stored.tour)await startTour(stored.tour,stored.index);else if(stored.destination){const d=catalog.navigation[stored.destination];if(d)await go(d,contextOverride,stored.folder)}}
  resumeSurface=null;
  await welcome();
 }
 document.addEventListener('framat:guide-auth',refresh);
 document.addEventListener('DOMContentLoaded',()=>init().catch(showError));
 return {register,open,close,startTour,execute,refresh,search,procedure,waitTarget,get catalog(){return catalog},get context(){return context()}};
})();
