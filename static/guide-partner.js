'use strict';
function guideMarkPartner(){
 const mapping={'partner-home':'workspace','supplier-history':'detail','supplier-deliveries':'deliveries','partner-documents':'administrative-files','partner-notifications':'notice-center','client-orders':'client-orders','partner-activation':'activate','partner-login':'login','partner_admin-screen':'admin'};
 for(const [target,id] of Object.entries(mapping)){const n=document.getElementById(id);if(n)n.dataset.guideTarget=target}
 const items=document.getElementById('items');items.dataset.guideTarget=FramatexGuide.catalog?.audience==='client'?'client-publications':'supplier-requests';
 const input=document.querySelector('input[aria-label="Document à transmettre"]');if(input)input.dataset.guideTarget='supplier-upload';
 const message=document.querySelector('textarea[aria-label="Votre message"]');if(message)message.dataset.guideTarget='partner-messages';
 document.querySelectorAll('[data-guide-target="client-questions"]').forEach(n=>delete n.dataset.guideTarget);
 if(guideClientOrderId){const card=document.querySelector('[data-guide-order="'+CSS.escape(guideClientOrderId)+'"]');if(card)card.dataset.guideTarget='client-questions'}
}
FramatexGuide.register({
 surface:()=>internal?'internal':'partner',
 context:()=>({page:internal?'partner_admin':FramatexGuide.catalog?.audience==='client'?'client':'supplier',...(!internal&&FramatexGuide.catalog?.audience==='supplier'&&guidePartnerRequestId?{supplier_request_id:guidePartnerRequestId}:{}),...(!internal&&FramatexGuide.catalog?.audience==='client'&&guideClientOrderId?{client_order_id:guideClientOrderId}:{})}),
 welcomeHost:()=>!document.getElementById('workspace').hidden?document.getElementById('workspace'):null,
 ready:async()=>{},
 go:async(d,ctx)=>{
  if(d.handler==='partner_admin'){if(!internal){internal=true;await refresh()}guideMarkPartner();return true}
  if(d.surface!=='partner')return false;
  if(document.getElementById('workspace').hidden&&FramatexGuide.catalog?.audience!=='public')await refresh();
  if(d.handler==='partner_request')await openRequest(ctx.supplier_request_id);
  if(d.handler==='partner_order'){guideClientOrderId=ctx.client_order_id;await renderClientOrders()}
  guideMarkPartner();const target=document.querySelector('[data-guide-target="'+d.target+'"]');
  const details=target?.closest('details');if(details)details.open=true;
  return true;
 }
});
new MutationObserver(guideMarkPartner).observe(document.getElementById('workspace'),{childList:true,subtree:true});guideMarkPartner();
