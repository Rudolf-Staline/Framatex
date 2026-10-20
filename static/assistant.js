/* Framatex Assist 0.19 — white/blue UI, locally verified guide only.
 * This module never sends document contents to an external model. */
'use strict';
const FRAMAT_GUIDE_QUICK = [
 ['Comment créer un client et son espace client ?', 'Espace client','users'],
 ['Résume ce dossier', 'Résumer le dossier','info'],
 ['Où déposer une facture ?', 'Déposer une facture','folder'],
 ['Voir mes priorités', 'Mes priorités','activity'],
 ['Comment vérifier une exigence client ?', 'Exigences client','file'],
 ['Comment retrouver une pièce ?', 'Retrouver un document','search'],
 ['Expliquer le statut d’un dossier', 'Comprendre un statut','info'],
];
let assistantThread = [];
let assistantContextLaunch = null;
function openGuide(){return assistantPage()}
function assistantQuickButtons(className='assistant-quick-chip'){
 return FRAMAT_GUIDE_QUICK.map(([question,label,ico])=>`<button type="button" class="${className}" data-assistant-question="${e(question)}">${icon(ico)} ${e(label)}</button>`).join('');
}
function guideNavigation(response){
 if(!response?.destination)return '';
 return `<button class="assistant-followup" type="button" data-guide-destination>${icon('folder')} Ouvrir la rubrique ${icon('arrow')}</button>`;
}
function guideResults(response){
 return response?.results?.length?`<div class="guide-results">${response.results.map(r=>`<button type="button" data-guide-launch="${e(r.launch_id)}" data-guide-folder="${e(r.folder||'jaune')}">${icon('file')}<span><strong>${e(r.label)}</strong><small>${e(r.description)}</small></span>${icon('arrow')}</button>`).join('')}</div>`:'';
}
function bindGuideResults(area){
 area?.querySelectorAll('[data-guide-launch]').forEach(b=>b.onclick=async()=>{try{await openLaunch(b.dataset.guideLaunch,b.dataset.guideFolder)}catch(err){showErr(err)}});
}
function guideMessage(kind, value, response=null){
 const isBot=kind==='bot';
 return `<div class="assistant-msg assistant-msg-${isBot?'bot':'user'}">${isBot?`<span class="assistant-msg-avatar">${icon('layers')}</span>`:''}<div class="assistant-bubble">${isBot?`<strong>${e(response?.title||'Framatex Assist')}</strong><p>${e(value)}</p>${response?.source?`<small>${e(response.source)}</small>`:''}${guideNavigation(response)}${guideResults(response)}`:`<p>${e(value)}</p>`}</div></div>`;
}
function paintAssistantThread(){
 const area=app.querySelector('#assistant-thread');if(!area)return;
 area.innerHTML=`<div class="assistant-msg assistant-msg-bot"><span class="assistant-msg-avatar">${icon('layers')}</span><div class="assistant-bubble"><strong>Bonjour !</strong><p>Je peux vous guider dans Framatex, retrouver une rubrique ou expliquer une procédure. Que souhaitez-vous faire ?</p></div></div>`+assistantThread.map(item=>guideMessage(item.kind,item.text,item.response)).join('');
 area.querySelectorAll('[data-guide-destination]').forEach((button,i)=>{
  /* Each button lives inside its corresponding message; pair by DOM position. */
  const parent=button.closest('.assistant-msg');
  const index=[...area.querySelectorAll('.assistant-msg')].indexOf(parent)-1;
  const response=assistantThread[index]?.response;
  button.addEventListener('click',async()=>{if(!response?.destination)return;try{
   if(response.destination==='detail'&&response.launch_id){await openLaunch(response.launch_id,response.folder||state.folder);focusWorkspaceArea(response.area)}
   else await navigate(response.destination);
  }catch(err){showErr(err)}});
 });
 bindGuideResults(area);area.scrollTop=area.scrollHeight;
}
async function askGuide(question, area='assistant'){
 const q=String(question||'').trim();if(q.length<2)return;
 const isMain=area==='assistant';
 const input=app.querySelector(isMain?'#assistant-question':'#rail-question');
 const form=app.querySelector(isMain?'#assistant-form':'#rail-form');
 if(form?.dataset.busy==='1')return;
 if(form)form.dataset.busy='1';if(input)input.disabled=true;
 const submit=form?.querySelector('button[type="submit"]');if(submit)submit.disabled=true;
 let miniResult=null;const previousQuestion=[...assistantThread].reverse().find(item=>item.kind==='user')?.text||null;
 if(isMain){assistantThread.push({kind:'user',text:q});paintAssistantThread()}
 else {
  const panel=app.querySelector('#inline-chat');if(panel){
   panel.insertAdjacentHTML('beforeend',guideMessage('user',q));
   panel.insertAdjacentHTML('beforeend',`<div class="assistant-msg assistant-msg-bot pending"><span class="assistant-msg-avatar">${icon('layers')}</span><div class="assistant-bubble"><p>Je vérifie la procédure…</p></div></div>`);
   miniResult=panel.querySelector('.pending:last-child');panel.scrollTop=panel.scrollHeight;
  }
 }
 try{
  const response=await api('/api/assistant/guide',{method:'POST',body:JSON.stringify({question:q,launch_id:assistantContextLaunch,previous_question:previousQuestion})});
  if(isMain){assistantThread.push({kind:'bot',text:response.answer,response});paintAssistantThread()}
  else if(miniResult){
   const b=miniResult.querySelector('.assistant-bubble');
   b.innerHTML=`<strong>${e(response.title)}</strong><p>${e(response.answer)}</p>${guideResults(response)}${response.destination?`<button class="assistant-followup" type="button">Ouvrir la rubrique ${icon('arrow')}</button>`:''}`;
   b.querySelector('.assistant-followup')?.addEventListener('click',async()=>{try{
    if(response.destination==='detail'&&response.launch_id){await openLaunch(response.launch_id,response.folder||state.folder);focusWorkspaceArea(response.area)}
    else await navigate(response.destination)
   }catch(err){showErr(err)}});
   bindGuideResults(miniResult);miniResult.classList.remove('pending');miniResult.parentElement.scrollTop=miniResult.parentElement.scrollHeight;
  }
 }catch(err){
  if(isMain){assistantThread.push({kind:'bot',text:'Impossible de traiter cette question pour le moment. '+(err.message||'')});paintAssistantThread()}
  else if(miniResult)miniResult.querySelector('.assistant-bubble').textContent=err.message||'Réponse indisponible.';
 }finally{
  if(form)form.dataset.busy='0';if(input)input.disabled=false;if(submit)submit.disabled=false;
  if(input){input.value='';input.focus()}
 }
}
function bindInlineAssistant(){
 const form=app.querySelector('#rail-form');
 form?.addEventListener('submit',ev=>{ev.preventDefault();askGuide(form.querySelector('input')?.value,'rail')});
 app.querySelectorAll('[data-rail-question]').forEach(b=>b.addEventListener('click',()=>askGuide(b.dataset.railQuestion,'rail')));
}
async function assistantPage(){
 assistantContextLaunch=(state.view==='detail'&&state.detail?.id)?state.detail.id:assistantContextLaunch;
 state.view='assistant';
 try{state.launches=await api('/api/launches')}catch{state.launches=[]}
 if(!state.launches.some(l=>l.id===assistantContextLaunch))assistantContextLaunch=null;
 const recent=state.launches.slice(0,3);
 mount(`<div class="assistant-page"><div class="assistant-main"><div class="assistant-page-heading"><div><div class="page-kicker"><span class="assistant-page-dot"></span> VOTRE ASSISTANT DOCUMENTAIRE</div><h1>Framatex <span>Assist</span></h1><p>Je vous aide à retrouver une information, comprendre une procédure<br> ou naviguer dans Framatex.</p></div><button type="button" id="assistant-reset" class="secondary">${icon('plus')} Nouvelle conversation</button></div><section class="assistant-scope"><label class="section-index" for="assistant-context-select">DOSSIER À EXAMINER</label><select id="assistant-context-select"><option value="">Tous les dossiers accessibles</option>${state.launches.map(l=>`<option value="${e(l.id)}" ${l.id===assistantContextLaunch?'selected':''}>${e(l.name)}</option>`).join('')}</select><p class="muted small">Le résumé et la recherche utilisent ce contexte.</p></section><div class="assistant-thread" id="assistant-thread" role="log" aria-live="polite" aria-label="Conversation"></div><div class="assistant-composer-sticky"><div class="assistant-quick">${assistantQuickButtons()}</div><form id="assistant-form" class="assistant-chat-form"><label for="assistant-question" class="sr-only">Votre question</label>${icon('file')}<input id="assistant-question" autocomplete="off" maxlength="500" minlength="2" required placeholder="Écrivez votre question..."/><button type="submit" aria-label="Envoyer">${icon('arrow')}</button></form><small>Réponses basées sur les procédures locales et les métadonnées autorisées.</small></div></div><aside class="assistant-context"><section class="assistant-context-card assistant-context-top"><span class="assistant-context-brand">${icon('layers')}</span><div><span class="section-index">CONTEXTE DANS FRAMATEX</span><h3>Framatex Assist <i class="chat-online"></i></h3><p>Connecté à votre espace de travail</p></div></section><section class="assistant-context-card"><span class="section-index">RUBRIQUES FRÉQUENTES</span><div class="assistant-context-links"><button data-assistant-question="Où déposer une facture ?">${icon('folder')}<span><strong>Déposer une facture</strong><small>Procédure et emplacements</small></span>${icon('arrow')}</button><button data-assistant-question="Comment retrouver une pièce ?">${icon('search')}<span><strong>Rechercher un document</strong><small>Filtres et critères</small></span>${icon('arrow')}</button><button data-assistant-question="Expliquer le statut d’un dossier">${icon('file')}<span><strong>Comprendre un statut</strong><small>En validation, en cours, à compléter…</small></span>${icon('arrow')}</button><button data-assistant-question="Quelles sont les règles de classement ?">${icon('folder')}<span><strong>Règles de classement</strong><small>Arborescence et types de pièces</small></span>${icon('arrow')}</button></div></section><section class="assistant-context-card"><div class="assistant-context-card-head"><span class="section-index">DOSSIERS RÉCENTS</span><button class="text-arrow" id="assistant-show-launches">Tous les dossiers ${icon('arrow')}</button></div><div class="assistant-context-links">${recent.length?recent.map(l=>`<button data-assistant-launch="${e(l.id)}">${icon('folder')}<span><strong>${e(l.name)}</strong><small>${e(l.order_ref||'Lancement sans référence de commande')}</small></span>${icon('arrow')}</button>`).join(''):'<p class="assistant-context-empty">Aucun dossier accessible.</p>'}</div></section><section class="assistant-context-card assistant-context-help">${icon('info')}<div><span class="section-index">BESOIN D’AIDE ?</span><h3>Une autre question ?</h3><p>Je peux vous guider vers une fonction ou expliquer une procédure existante.</p></div></section></aside></div>`,'Framatex Assist');
 paintAssistantThread();
 app.querySelector('#assistant-context-select').onchange=ev=>{assistantContextLaunch=ev.target.value||null;toast('Contexte de l’assistant mis à jour')};
 app.querySelector('#assistant-form')?.addEventListener('submit',ev=>{ev.preventDefault();askGuide(app.querySelector('#assistant-question')?.value)});
 app.querySelectorAll('[data-assistant-question]').forEach(b=>b.addEventListener('click',()=>askGuide(b.dataset.assistantQuestion)));
 app.querySelector('#assistant-reset')?.addEventListener('click',()=>{assistantThread=[];paintAssistantThread();app.querySelector('#assistant-question')?.focus()});
 app.querySelector('#assistant-show-launches')?.addEventListener('click',()=>navigate('launches'));
 app.querySelectorAll('[data-assistant-launch]').forEach(b=>b.addEventListener('click',()=>openLaunch(b.dataset.assistantLaunch)));
}
