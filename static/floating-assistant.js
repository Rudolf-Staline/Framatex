/* Dossier Jaune Assist · persistent floating guide.
   Keeps permissions and document context in the existing FastAPI endpoint. */
'use strict';
let floatingAssistantMessages=[];
let floatingAssistantOpen=false;
let floatingAssistantBusy=false;
let floatingAssistantPriorFocus=null;
const FLOATING_QUESTIONS=[
  ['Comment déposer un document ?','Déposer un document','file'],
  ['Comment retrouver un problème déjà résolu ?','Trouver une solution déjà utilisée','book'],
  ['Comment consulter les procédures ?','Consulter une procédure','search'],
  ['Comment inscrire un client et le rattacher à une commande ?','Gérer les clients','users'],
  ['Recherche une commande ou un document','Rechercher une pièce','search']
];
const FLOATING_CHAT_ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.4a8.2 8.2 0 0 1-8.6 8.2 9.5 9.5 0 0 1-3.5-.8L3.5 20l1.3-4.2a8.3 8.3 0 1 1 15.2-4.4Z"/><path d="M8 11.6h8M8 14.5h5.2"/></svg>';
const FLOATING_SEND_ICON='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5m-6 6 6-6 6 6"/></svg>';
const FLOATING_SPARK_ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 1.7 6.3L20 10l-6.3 1.7L12 18l-1.7-6.3L4 10l6.3-1.7L12 2Z"/><path d="m19 16 .6 2.4L22 19l-2.4.6L19 22l-.6-2.4L16 19l2.4-.6L19 16Z"/></svg>';

function floatingAssistantHost(){return document.querySelector('#floating-assistant-root')}

function buildFloatingAssistant(){
 const host=floatingAssistantHost();
 if(!host||host.dataset.ready==='1')return;
 host.dataset.ready='1';
 host.innerHTML=[
  '<button type="button" class="floating-assistant-trigger" id="floating-assistant-trigger" aria-label="Ouvrir Dossier Jaune Assist" aria-controls="floating-assistant-panel" aria-expanded="false">',
    '<span class="floating-assistant-trigger-icon">',FLOATING_CHAT_ICON,'</span>',
    '<span class="floating-assistant-trigger-spark">',FLOATING_SPARK_ICON,'</span>',
    '<span class="floating-assistant-trigger-tip" aria-hidden="true">Besoin d’aide ?</span>',
  '</button>',
  '<div class="floating-assistant-backdrop" id="floating-assistant-backdrop" hidden></div>',
  '<section class="floating-assistant-panel" id="floating-assistant-panel" role="dialog" aria-modal="true" aria-labelledby="floating-assistant-title"  hidden>',
    '<header class="floating-assistant-head">',
      '<div class="floating-assistant-brand-icon" aria-hidden="true">',FLOATING_CHAT_ICON,'</div>',
      '<div class="floating-assistant-brand-copy">',
        '<span class="floating-assistant-head-label">VOTRE ESPACE D’AIDE</span>',
        '<h2 id="floating-assistant-title">Assistant Dossier Jaune</h2>',
      '</div>',
      '<button type="button" id="floating-assistant-reset" class="floating-assistant-icon-button floating-assistant-reset" aria-label="Nouvelle discussion" hidden>',
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11a9 9 0 1 1 2.8 6.5M3 4v7h7"/></svg>',
      '</button>',
      '<button type="button" id="floating-assistant-close" class="floating-assistant-icon-button floating-assistant-close" aria-label="Fermer l’assistant">',icon('x'),'</button>',
    '</header>',
    '<div id="floating-assistant-chat" class="floating-assistant-chat" role="log" aria-live="polite" aria-label="Conversation avec Dossier Jaune Assist"></div>',
    '<div class="floating-assistant-bottom">',
      '<form id="floating-assistant-form" class="floating-assistant-form">',
        '<label for="floating-assistant-input" class="sr-only">Votre question</label>',
        '<textarea id="floating-assistant-input" rows="1" minlength="2" maxlength="500" required placeholder="Posez votre question…" aria-label="Posez votre question"></textarea>',
        '<button type="submit" id="floating-assistant-send" aria-label="Envoyer la question">',FLOATING_SEND_ICON,'</button>',
      '</form>',
      '<p class="floating-assistant-compose-hint">Entrée pour envoyer <span aria-hidden="true">·</span> Maj + Entrée pour une nouvelle ligne</p>',
    '</div>',
  '</section>'
 ].join('');
 host.querySelector('#floating-assistant-trigger').addEventListener('click',openFloatingAssistant);
 host.querySelector('#floating-assistant-close').addEventListener('click',closeFloatingAssistant);
 host.querySelector('#floating-assistant-backdrop').addEventListener('click',closeFloatingAssistant);
 host.querySelector('#floating-assistant-reset').addEventListener('click',()=>{
   floatingAssistantMessages=[];paintFloatingAssistant();
   host.querySelector('#floating-assistant-input')?.focus();
 });
 host.querySelector('#floating-assistant-form').addEventListener('submit',event=>{
   event.preventDefault();
   askFloatingAssistant(host.querySelector('#floating-assistant-input')?.value);
 });
 host.querySelector('#floating-assistant-input').addEventListener('input',event=>{
   const field=event.currentTarget;
   field.style.height='auto';
   field.style.height=Math.min(field.scrollHeight,116)+'px';
 });
 host.querySelector('#floating-assistant-input').addEventListener('keydown',event=>{
   if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();askFloatingAssistant(event.currentTarget.value)}
 });
}
function syncFloatingAssistant(){
 const host=floatingAssistantHost();
 if(!host)return;
 if(!state.me || state.me.client_account){
   if(floatingAssistantOpen)closeFloatingAssistant(false);
   floatingAssistantMessages=[];
   floatingAssistantBusy=false;
   host.hidden=true;
   return;
 }
 buildFloatingAssistant();
 host.hidden=false;
}
function openFloatingAssistant(){
 if(!state.me)return;
 const host=floatingAssistantHost();if(!host)return;
 buildFloatingAssistant();
 if(floatingAssistantOpen)return;
 // Do not replace a currently open edit/confirmation dialog.
 if(overlay?.querySelector('.modal-scrim'))return;
 floatingAssistantPriorFocus=document.activeElement;
 floatingAssistantOpen=true;
 host.classList.add('is-open');
 host.querySelector('#floating-assistant-backdrop').hidden=false;
 host.querySelector('#floating-assistant-panel').hidden=false;
 host.querySelector('#floating-assistant-trigger').setAttribute('aria-expanded','true');
 host.querySelector('#floating-assistant-trigger').setAttribute('aria-label','Dossier Jaune Assist ouvert');
 paintFloatingAssistant();
 document.addEventListener('keydown',floatingAssistantKeydown);
 host.querySelector('#floating-assistant-input')?.focus();
}
function closeFloatingAssistant(restoreFocus=true){
 if(!floatingAssistantOpen)return;
 const host=floatingAssistantHost();
 floatingAssistantOpen=false;
 document.removeEventListener('keydown',floatingAssistantKeydown);
 if(host){
   host.classList.remove('is-open');
   const panel=host.querySelector('#floating-assistant-panel');
   const backdrop=host.querySelector('#floating-assistant-backdrop');
   if(panel)panel.hidden=true;
   if(backdrop)backdrop.hidden=true;
   const trigger=host.querySelector('#floating-assistant-trigger');
   trigger?.setAttribute('aria-expanded','false');
   trigger?.setAttribute('aria-label','Ouvrir Dossier Jaune Assist');
   if(restoreFocus)(floatingAssistantPriorFocus?.isConnected?floatingAssistantPriorFocus:trigger)?.focus?.();
 }
 floatingAssistantPriorFocus=null;
}
function floatingAssistantKeydown(event){
 if(event.key==='Escape'){event.preventDefault();closeFloatingAssistant();return}
 if(event.key!=='Tab')return;
 const host=floatingAssistantHost();
 const panel=host?.querySelector('#floating-assistant-panel');
 if(!panel)return;
 const focusables=[...panel.querySelectorAll('button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled])')];
 if(!focusables.length)return;
 const first=focusables[0],last=focusables[focusables.length-1];
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
 else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
}
function floatingAssistantMessageMarkup(item,index){
 const isBot=item.kind==='bot';
 const follow=item.response?.destination?
  '<button class="floating-assistant-follow" type="button" data-floating-destination="'+index+'">Ouvrir la rubrique '+icon('arrow')+'</button>':'';
 return '<div class="floating-assistant-message '+(isBot?'is-bot':'is-user')+'">'+
  (isBot?'<span class="floating-assistant-message-avatar">'+FLOATING_SPARK_ICON+'</span>':'')+
  '<div class="floating-assistant-bubble">'+
  (isBot&&item.response?.title?'<strong>'+e(item.response.title)+'</strong>':'')+
  '<p>'+e(item.text)+'</p>'+
  (isBot&&item.response?.source?'<small>'+e(item.response.source)+'</small>':'')+
  (isBot&&item.response?.sources?.length?rexSourceButtons(item.response.sources):'')+
  (isBot&&item.response?.results?.length?'<div class="floating-assistant-results">'+item.response.results.map((r,j)=>'<button type="button" data-floating-result="'+index+'-'+j+'">'+icon('folder')+'<span><strong>'+e(r.label)+'</strong><small>'+e(r.description||'Ouvrir le dossier')+'</small></span>'+icon('arrow')+'</button>').join('')+'</div>':'')+
  follow+'</div></div>';
}
function paintFloatingAssistant(){
 const host=floatingAssistantHost();
 const chat=host?.querySelector('#floating-assistant-chat');if(!chat)return;
 const reset=host.querySelector('#floating-assistant-reset');
 if(reset)reset.hidden=!floatingAssistantMessages.length;
 chat.innerHTML=[
  ...(!floatingAssistantMessages.length?[
   '<div class="floating-assistant-welcome">',
     '<div class="floating-assistant-welcome-top">',
       '<span class="floating-assistant-welcome-symbol" aria-hidden="true">',FLOATING_SPARK_ICON,'</span>',
       '<span class="floating-assistant-welcome-kicker">ASSISTANCE DOCUMENTAIRE</span>',
     '</div>',
     '<h3>Comment puis-je vous aider ?</h3>',
     '<p>Retrouvez rapidement un document, une procédure ou un retour d’expérience.</p>',
     '<div class="floating-assistant-suggestions" aria-label="Actions proposées">',
       FLOATING_QUESTIONS.map((q,i)=>
         '<button type="button" class="floating-assistant-suggestion" data-floating-question="'+i+'">'+
           '<span class="floating-assistant-suggestion-icon" aria-hidden="true">'+icon(q[2])+'</span>'+
           '<span class="floating-assistant-suggestion-label">'+e(q[1])+'</span>'+
           '<span class="floating-assistant-suggestion-arrow" aria-hidden="true">'+icon('forward')+'</span>'+
         '</button>'
       ).join(''),
     '</div>',
     '<div class="floating-assistant-welcome-note">Ou posez simplement votre question ci-dessous.</div>',
   '</div>'

  ]:[]),
  ...floatingAssistantMessages.map(floatingAssistantMessageMarkup),
  ...(floatingAssistantBusy?['<div class="floating-assistant-typing" role="status">Recherche dans l’aide et les fiches accessibles…</div>']:[])
 ].join('');
 chat.querySelectorAll('[data-floating-question]').forEach(button=>button.addEventListener('click',()=>askFloatingAssistant(FLOATING_QUESTIONS[+button.dataset.floatingQuestion][0])));
 chat.querySelectorAll('[data-floating-result]').forEach(button=>button.addEventListener('click',async()=>{
   const [i,j]=button.dataset.floatingResult.split('-').map(Number);
   const target=floatingAssistantMessages[i]?.response?.results?.[j];
   if(!target?.launch_id)return;
   closeFloatingAssistant(false);
   try{await openLaunch(target.launch_id,target.folder||'jaune')}catch(err){showErr(err)}
 }));
 chat.querySelectorAll('[data-floating-destination]').forEach(button=>button.addEventListener('click',async()=>{
   const response=floatingAssistantMessages[+button.dataset.floatingDestination]?.response;
   if(!response?.destination)return;
   closeFloatingAssistant(false);
   try{
     if(response.destination==='detail'&&response.launch_id){
       await openLaunch(response.launch_id,response.folder||state.folder);
       focusWorkspaceArea(response.area);
     }else if(response.destination==='dossier'&&response.folder)await openGlobalFolder(response.folder);
     else await navigate(response.destination);
   }catch(err){showErr(err)}
 }));
 if(typeof bindRexSources==='function')bindRexSources(chat);
 chat.scrollTop=chat.scrollHeight;
}
async function askFloatingAssistant(question){
 const q=String(question??'').trim();
 if(q.length<2||floatingAssistantBusy||!state.me)return;
 const host=floatingAssistantHost();if(!host||!floatingAssistantOpen)return;
 floatingAssistantBusy=true;
 floatingAssistantMessages.push({kind:'user',text:q});
 const input=host.querySelector('#floating-assistant-input');
 const send=host.querySelector('#floating-assistant-send');
 if(input){input.value='';if(input.style)input.style.height='';input.disabled=true}
 if(send)send.disabled=true;
 paintFloatingAssistant();
 const activeLaunch=state.view==='detail'&&state.detail?.id?state.detail.id:null;
 const isFollowUp=/^(et\b|dans (le|la)\b|pour ce dossier|pour cette commande|quels fichiers|quelles pieces)/i.test(q)||/\b(ce dossier|cette commande|ces documents|dans le (rose|bleu|vert|jaune))\b/i.test(q);
 const previousLaunch=[...floatingAssistantMessages].reverse().find(message=>message.kind==='bot'&&message.response?.launch_id)?.response?.launch_id;
 const launchId=activeLaunch||(isFollowUp?previousLaunch:null)||null;
 try{
   const response=await api('/api/assistant/chat',{
     method:'POST',body:JSON.stringify({question:q,launch_id:launchId,mode:'auto'})
   });
   if(state.me)floatingAssistantMessages.push({kind:'bot',text:response.answer||'Aucune réponse disponible.',response});
 }catch(err){
   if(state.me)floatingAssistantMessages.push({kind:'bot',text:'Je ne peux pas répondre pour le moment. '+(err.message||'Réessayez.')});
 }finally{
   floatingAssistantBusy=false;
   if(input)input.disabled=false;
   if(send)send.disabled=false;
   if(state.me){
     paintFloatingAssistant();
     if(floatingAssistantOpen)input?.focus();
   }
 }
}
