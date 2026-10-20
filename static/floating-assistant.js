/* Framatex Assist · persistent floating guide.
   Keeps permissions and document context in the existing FastAPI endpoint. */
'use strict';
let floatingAssistantMessages=[];
let floatingAssistantOpen=false;
let floatingAssistantBusy=false;
let floatingAssistantPriorFocus=null;
const FLOATING_QUESTIONS=[
  ['Où déposer une facture ?','Déposer une facture'],
  ['Comment trouver les pièces manquantes ?','Pièces manquantes'],
  ['Comment interroger la mémoire métier ?','Mémoire métier']
];
const FLOATING_CHAT_ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.4a8.2 8.2 0 0 1-8.6 8.2 9.5 9.5 0 0 1-3.5-.8L3.5 20l1.3-4.2a8.3 8.3 0 1 1 15.2-4.4Z"/><path d="M8 11.6h8M8 14.5h5.2"/></svg>';
const FLOATING_SPARK_ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 1.7 6.3L20 10l-6.3 1.7L12 18l-1.7-6.3L4 10l6.3-1.7L12 2Z"/><path d="m19 16 .6 2.4L22 19l-2.4.6L19 22l-.6-2.4L16 19l2.4-.6L19 16Z"/></svg>';

function floatingAssistantHost(){return document.querySelector('#floating-assistant-root')}

function buildFloatingAssistant(){
 const host=floatingAssistantHost();
 if(!host||host.dataset.ready==='1')return;
 host.dataset.ready='1';
 host.innerHTML=[
  '<button type="button" class="floating-assistant-trigger" id="floating-assistant-trigger" aria-label="Ouvrir Framatex Assist" aria-controls="floating-assistant-panel" aria-expanded="false" title="Ouvrir Framatex Assist">',
    '<span class="floating-assistant-trigger-icon">',FLOATING_CHAT_ICON,'</span>',
    '<span class="floating-assistant-trigger-spark">',FLOATING_SPARK_ICON,'</span>',
    '<span class="floating-assistant-trigger-tip" aria-hidden="true">Besoin d’aide ?</span>',
  '</button>',
  '<div class="floating-assistant-backdrop" id="floating-assistant-backdrop" hidden></div>',
  '<section class="floating-assistant-panel" id="floating-assistant-panel" role="dialog" aria-modal="true" aria-labelledby="floating-assistant-title" aria-describedby="floating-assistant-intro" hidden>',
    '<header class="floating-assistant-head">',
      '<div class="floating-assistant-brand-icon">',FLOATING_SPARK_ICON,'</div>',
      '<div class="floating-assistant-brand-copy"><span class="floating-assistant-eyebrow">ASSISTANCE DOCUMENTAIRE</span>',
      '<h2 id="floating-assistant-title">Framatex Assist <span class="floating-assistant-status" title="Guide disponible"></span></h2></div>',
      '<button type="button" id="floating-assistant-reset" class="floating-assistant-icon-button" title="Nouvelle conversation" aria-label="Nouvelle conversation">',icon('plus'),'</button>',
      '<button type="button" id="floating-assistant-close" class="floating-assistant-icon-button" title="Fermer" aria-label="Fermer l’assistant">',icon('x'),'</button>',
    '</header>',
    '<div id="floating-assistant-chat" class="floating-assistant-chat" role="log" aria-live="polite" aria-label="Conversation avec Framatex Assist"></div>',
    '<div class="floating-assistant-bottom">',
      '<label class="floating-assistant-mode-label" for="floating-assistant-mode">Rechercher dans<select id="floating-assistant-mode"><option value="auto">L’aide et la mémoire métier</option><option value="memory">Les retours d’expérience</option></select></label>',
      '<div class="floating-assistant-questions" aria-label="Questions suggérées">',
      FLOATING_QUESTIONS.map((question,index)=>'<button type="button" data-floating-question="'+index+'">'+e(question[1])+'</button>').join(''),
      '</div>',
      '<form id="floating-assistant-form" class="floating-assistant-form">',
        '<label for="floating-assistant-input" class="sr-only">Votre question</label>',
        '<input type="text" id="floating-assistant-input" minlength="2" maxlength="500" required autocomplete="off" placeholder="Votre question…" />',
        '<button type="submit" id="floating-assistant-send" aria-label="Envoyer la question">',icon('arrow'),'</button>',
      '</form>',
      '<p class="floating-assistant-disclaimer">Réponses fondées sur les procédures locales, sans IA générative.</p>',
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
 host.querySelectorAll('[data-floating-question]').forEach(button=>button.addEventListener('click',()=>{
   askFloatingAssistant(FLOATING_QUESTIONS[+button.dataset.floatingQuestion][0]);
 }));
}
function syncFloatingAssistant(){
 const host=floatingAssistantHost();
 if(!host)return;
 if(!state.me){
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
 host.querySelector('#floating-assistant-trigger').setAttribute('aria-label','Framatex Assist ouvert');
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
   trigger?.setAttribute('aria-label','Ouvrir Framatex Assist');
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
 const focusables=[...panel.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled])')];
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
  follow+'</div></div>';
}
function paintFloatingAssistant(){
 const host=floatingAssistantHost();
 const chat=host?.querySelector('#floating-assistant-chat');if(!chat)return;
 chat.innerHTML=[
  '<div class="floating-assistant-intro" id="floating-assistant-intro"><span class="floating-assistant-intro-icon">',
   FLOATING_SPARK_ICON,'</span><div><strong>Bonjour !</strong>',
  '<p>Je peux vous guider dans Framatex et retrouver les problèmes déjà rencontrés, leurs solutions et leurs fiches sources.</p></div></div>',
  ...floatingAssistantMessages.map(floatingAssistantMessageMarkup),
  ...(floatingAssistantBusy?['<div class="floating-assistant-typing" role="status">Recherche dans l’aide et les fiches accessibles…</div>']:[])
 ].join('');
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
 if(input){input.value='';input.disabled=true}
 if(send)send.disabled=true;
 paintFloatingAssistant();
 const launchId=state.view==='detail'&&state.detail?.id?state.detail.id:null;
 try{
   const response=await api('/api/assistant/chat',{
     method:'POST',body:JSON.stringify({question:q,launch_id:launchId,mode:host.querySelector('#floating-assistant-mode')?.value||'auto'})
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
