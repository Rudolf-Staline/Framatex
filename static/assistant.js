/* Framatex Guide adapter. Legacy /api/assistant/guide remains a backend adapter. */
'use strict';
function openGuide(){return window.FramatexGuide.open()}
function assistantPage(){return openGuide()}
function bindInlineAssistant(){
 const form=app.querySelector('#rail-form');
 form?.addEventListener('submit',async event=>{event.preventDefault();await openGuide();await FramatexGuide.search(form.querySelector('input').value)});
 app.querySelectorAll('[data-rail-question]').forEach(b=>b.onclick=async()=>{await openGuide();await FramatexGuide.search(b.dataset.railQuestion)});
}
function guideMarkInternal(){
 const main=app.querySelector('main.content');if(!main)return;
 main.dataset.guideTarget=state.view+'-screen';
 for(const n of app.querySelectorAll('[data-view]'))n.dataset.guideTarget='nav-'+n.dataset.view;
 for(const id of ['order-create','canonical-reference','order-document-form','order-origin','order-document-query','order-completeness-configure']){const node=document.getElementById(id);if(node)node.dataset.guideTarget=id}
 if(state.view==='dossiers'&&state.orderDossier&&app.querySelector('#order-section-title'))main.dataset.guideTarget='order-dossier';
 app.querySelectorAll('[data-order-section]').forEach(n=>n.dataset.guideTarget='order-section-'+n.dataset.orderSection);
 for(const node of app.querySelectorAll('[id^="section-"]'))node.dataset.guideTarget=node.id;
}
FramatexGuide.register({
 surface:()=> 'internal',
 context:()=>({page:state.view==='dossiers'&&state.orderDossier&&app.querySelector('#order-section-title')?'dossiers':state.view, ...(state.view==='detail'?{launch_id:state.detail.id,...(state.detail.order_id?{order_id:state.detail.order_id}:{})}:state.view==='dossiers'&&state.orderDossier&&app.querySelector('#order-section-title')?{order_id:state.orderDossier.order_id}:{})}),
 welcomeHost:()=>state.me?app.querySelector('main.content'):null,
 ready:async()=>{for(let i=0;i<100;i++){if(state.me&&app.querySelector('.sidebar'))return;await new Promise(r=>setTimeout(r,60))}throw new Error('Espace interne en cours de chargement.')},
 go:async(d,ctx,folder)=>{
  if(d.handler==='view'){
   if(state.view!==d.view)await navigate(d.view);
   guideMarkInternal();return true;
  }
  if(d.handler==='order'||d.handler==='order_upload'){
   if(!ctx.order_id)throw new Error('Choisissez une commande.');
   const slug=['jaune','rose','bleu','vert'].includes(folder)?folder:'jaune';
   if(state.view!=='dossiers'||!app.querySelector('#order-section-title')||state.orderDossier?.order_id!==ctx.order_id||app.querySelector('[data-order-section][aria-pressed="true"]')?.dataset.orderSection!==slug)await orderDossierPage(ctx.order_id,slug);guideMarkInternal();
   if(d.handler==='order_upload'){const details=document.querySelector('#order-document-form')?.closest('details');if(details)details.open=true;guideMarkInternal()}
   return true;
  }
  if(d.handler==='launch'){await openLaunch(ctx.launch_id);guideMarkInternal();return true}
  return false;
 }
});
new MutationObserver(guideMarkInternal).observe(app,{childList:true,subtree:true});
guideMarkInternal();
