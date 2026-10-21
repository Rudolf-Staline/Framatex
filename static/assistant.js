/* Dossier Jaune Assist 0.19 — white/blue UI, locally verified guide only.
 * This module never sends document contents to an external model. */
'use strict';
const FRAMAT_GUIDE_QUICK = [
 ['Où déposer une facture ?', 'Déposer une facture','folder'],
 ['Voir mes priorités', 'Mes priorités','activity'],
 ['Comment vérifier une exigence client ?', 'Exigences client','file'],
 ['Comment retrouver une pièce ?', 'Retrouver un document','search'],
 ['Expliquer le statut d’un dossier', 'Comprendre un statut','info'],
];
let assistantThread = [];
let assistantContextLaunch = null;
function openGuide(){return openFloatingAssistant()}
function assistantQuickButtons(className='assistant-quick-chip'){
 return FRAMAT_GUIDE_QUICK.map(([question,label,ico])=>`<button type="button" class="${className}" data-assistant-question="${e(question)}">${icon(ico)} ${e(label)}</button>`).join('');
}
function guideNavigation(response){
 if(!response?.destination)return '';
 return `<button class="assistant-followup" type="button" data-guide-destination>${icon('folder')} Ouvrir la rubrique ${icon('arrow')}</button>`;
}
function guideMessage(kind, value, response=null){
 const isBot=kind==='bot';
 return `<div class="assistant-msg assistant-msg-${isBot?'bot':'user'}">${isBot?`<span class="assistant-msg-avatar">${icon('layers')}</span>`:''}<div class="assistant-bubble">${isBot?`<strong>${e(response?.title||'Dossier Jaune Assist')}</strong><p>${e(value)}</p>${response?.source?`<small>${e(response.source)}</small>`:''}${guideNavigation(response)}`:`<p>${e(value)}</p>`}</div></div>`;
}
function paintAssistantThread(){
 const area=app.querySelector('#assistant-thread');if(!area)return;
 area.innerHTML=`<div class="assistant-msg assistant-msg-bot"><span class="assistant-msg-avatar">${icon('layers')}</span><div class="assistant-bubble"><strong>Bonjour !</strong><p>Je peux vous guider dans Dossier Jaune, retrouver une rubrique ou expliquer une procédure. Que souhaitez-vous faire ?</p></div></div>`+assistantThread.map(item=>guideMessage(item.kind,item.text,item.response)).join('');
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
 area.scrollTop=area.scrollHeight;
}
async function askGuide(question, area='assistant'){
 const q=String(question||'').trim();if(q.length<2)return;
 const isMain=area==='assistant';
 const input=app.querySelector(isMain?'#assistant-question':'#rail-question');
 const form=app.querySelector(isMain?'#assistant-form':'#rail-form');
 if(form?.dataset.busy==='1')return;
 if(form)form.dataset.busy='1';if(input)input.disabled=true;
 const submit=form?.querySelector('button[type="submit"]');if(submit)submit.disabled=true;
 let miniResult=null;
 if(isMain){assistantThread.push({kind:'user',text:q});paintAssistantThread()}
 else {
  const panel=app.querySelector('#inline-chat');if(panel){
   panel.insertAdjacentHTML('beforeend',guideMessage('user',q));
   panel.insertAdjacentHTML('beforeend',`<div class="assistant-msg assistant-msg-bot pending"><span class="assistant-msg-avatar">${icon('layers')}</span><div class="assistant-bubble"><p>Je vérifie la procédure…</p></div></div>`);
   miniResult=panel.querySelector('.pending:last-child');panel.scrollTop=panel.scrollHeight;
  }
 }
 try{
  const response=await api('/api/assistant/guide',{method:'POST',body:JSON.stringify({question:q,launch_id:assistantContextLaunch})});
  if(isMain){assistantThread.push({kind:'bot',text:response.answer,response});paintAssistantThread()}
  else if(miniResult){
   const b=miniResult.querySelector('.assistant-bubble');
   b.innerHTML=`<strong>${e(response.title)}</strong><p>${e(response.answer)}</p>${response.destination?`<button class="assistant-followup" type="button">Ouvrir la rubrique ${icon('arrow')}</button>`:''}`;
   b.querySelector('.assistant-followup')?.addEventListener('click',async()=>{try{
    if(response.destination==='detail'&&response.launch_id){await openLaunch(response.launch_id,response.folder||state.folder);focusWorkspaceArea(response.area)}
    else await navigate(response.destination)
   }catch(err){showErr(err)}});
   miniResult.classList.remove('pending');miniResult.parentElement.scrollTop=miniResult.parentElement.scrollHeight;
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
 assistantContextLaunch=(state.view==='detail'&&state.detail?.id)?state.detail.id:null;
 state.view='assistant';
 if(!state.launches?.length)try{state.launches=await api('/api/launches')}catch{state.launches=[]}
 const recent=state.launches.slice(0,3);
 mount(`<div class="assistant-page"><div class="assistant-main"><div class="assistant-page-heading"><div><div class="page-kicker"><span class="assistant-page-dot"></span> VOTRE ASSISTANT DOCUMENTAIRE</div><h1>Dossier Jaune <span>Assist</span></h1><p>Je vous aide à retrouver une information, comprendre une procédure<br> ou naviguer dans Dossier Jaune.</p></div><button type="button" id="assistant-reset" class="secondary">${icon('plus')} Nouvelle conversation</button></div><div class="assistant-thread" id="assistant-thread" role="log" aria-live="polite" aria-label="Conversation"></div><div class="assistant-composer-sticky"><div class="assistant-quick">${assistantQuickButtons()}</div><form id="assistant-form" class="assistant-chat-form"><label for="assistant-question" class="sr-only">Votre question</label>${icon('file')}<input id="assistant-question" autocomplete="off" maxlength="500" minlength="2" required placeholder="Écrivez votre question..."/><button type="submit" aria-label="Envoyer">${icon('arrow')}</button></form><small>Réponses basées sur les procédures locales, sans IA générative.</small></div></div></div>`,'Dossier Jaune Assist');
 paintAssistantThread();
 app.querySelector('#assistant-form')?.addEventListener('submit',ev=>{ev.preventDefault();askGuide(app.querySelector('#assistant-question')?.value)});
 app.querySelectorAll('[data-assistant-question]').forEach(b=>b.addEventListener('click',()=>askGuide(b.dataset.assistantQuestion)));
 app.querySelector('#assistant-reset')?.addEventListener('click',()=>{assistantThread=[];paintAssistantThread();app.querySelector('#assistant-question')?.focus()});
 app.querySelector('#assistant-show-launches')?.addEventListener('click',()=>navigate('launches'));
 app.querySelectorAll('[data-assistant-launch]').forEach(b=>b.addEventListener('click',()=>openLaunch(b.dataset.assistantLaunch)));
}
