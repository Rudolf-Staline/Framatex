'use strict';
let internal = false;
const $ = id => document.getElementById(id);
const labels = {requested:'Document attendu', pending:'Vérification en attente', rejected:'Correction demandée', approved:'Approuvé', closed:'Clôturé'};
function node(tag, text) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; return n; }
function button(text, action) {const b=node('button',text); b.type='button'; b.onclick=()=>run(action); return b;}
async function api(path, method='GET', data) {
 const options={method,headers:{'X-Framatex-Request':'1'}};
 if(data instanceof FormData)options.body=data;
 else if(data!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}
 const r=await fetch(path,options); let body; try{body=await r.json();}catch{body={detail:'Réponse serveur invalide'};}
 if(!r.ok)throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail)); return body;
}
async function run(action){$('notice').textContent='Chargement…';try{await action();if($('notice').textContent==='Chargement…')$('notice').textContent='Opération confirmée.';}catch(e){$('notice').textContent=e.message;}}
function form(id, action){$(id).onsubmit=e=>{e.preventDefault();const b=e.target.querySelector('button');b.disabled=true;run(()=>action(Object.fromEntries(new FormData(e.target)))).finally(()=>b.disabled=false);};}
form('login',async data=>{await api('/api/partner-auth/login','POST',data);internal=false;await refresh();});
form('activate',async data=>{await api('/api/partner-auth/activate','POST',data);$('activate').reset();$('notice').textContent='Compte activé. Vous pouvez vous connecter.';});
$('staff').onclick=()=>run(async()=>{await api('/api/partners/organizations');internal=true;await refresh();});
$('refresh').onclick=()=>run(refresh);
$('logout').onclick=()=>run(async()=>{await api('/api/partner-auth/logout','POST');location.reload();});
form('organization',async data=>{await api('/api/partners/organizations','POST',data);$('organization').reset();await refresh();});
form('request',async data=>{if(!data.due_date)data.due_date=null;await api('/api/partners/requests','POST',data);$('request').reset();await refresh();});
form('publication',async data=>{await api('/api/partners/publications','POST',data);$('publication').reset();});
async function refresh(){
 const who=internal?{organization:'Administration Framatex'}:await api('/api/partner/home');
 $('identity').textContent=who.organization;$('auth').hidden=true;$('workspace').hidden=false;$('admin').hidden=!internal;$('detail').replaceChildren();
 if(internal){
  const orgs=await api('/api/partners/organizations');$('organizations').replaceChildren();$('supplier-options').replaceChildren();$('order-supplier-options').replaceChildren();$('client-options').replaceChildren();
  for(const o of orgs){const a=node('article');a.append(node('h4',`${o.name} · ${o.kind} · ${o.active?'Actif':'Suspendu'}`));
   const email=node('input');email.type='email';email.placeholder='Email du contact';email.setAttribute('aria-label',`Email du contact ${o.name}`);a.append(email);
   a.append(button('Créer / renouveler invitation',async()=>{const r=await api(`/api/partners/organizations/${o.id}/invitations`,'POST',{email:email.value});$('notice').textContent=`${r.instruction}\nCode (valable 24 h) : ${r.activation_token}`;}));
   a.append(button(o.active?'Suspendre':'Réactiver',async()=>{if(!confirm('Confirmer le changement d’accès ?'))return;await api(`/api/partners/organizations/${o.id}`,'PATCH',{active:!o.active});await refresh();}));
   const accounts=await api(`/api/partners/organizations/${o.id}/accounts`);
   for(const acc of accounts){const line=node('p',`${acc.email} · ${acc.active?'Actif':'Révoqué'} `);line.append(button(acc.active?'Révoquer':'Réactiver',async()=>{if(!confirm('Confirmer la révocation des sessions et le changement de statut ?'))return;await api(`/api/partners/accounts/${acc.id}`,'PATCH',{active:!acc.active});await refresh();}));a.append(line);}
   $('organizations').append(a);if(o.active){const opt=node('option',o.name);opt.value=o.id;$(o.kind==='supplier'?'supplier-options':'client-options').append(opt);if(o.kind==='supplier')$('order-supplier-options').append(opt.cloneNode(true));}
  }
 }
 await renderDeliveries();
 const rows=await api(internal?'/api/partners/requests':'/api/partner/requests');$('items').replaceChildren();
 if(!rows.length)$('items').append(node('p','Aucune demande accessible.'));
 for(const r of rows){const a=node('article');a.append(node('h4',`${r.order_ref} · ${r.title}`),node('p',`${labels[r.status]} · Échéance : ${r.due_date||'non définie'}`),button('Ouvrir',()=>openRequest(r.id)));$('items').append(a);}
 if(rows.length===100)$('items').append(node('p','Les 100 demandes les plus récentes sont affichées. Les suivantes sont disponibles via la pagination API.'));
 if(!internal){for(const p of await api('/api/partner/publications')){const a=node('article');a.append(node('h4',`${p.title} · version ${p.version}`));const link=node('a','Télécharger la version publiée');link.href=`/api/partner/publications/${p.id}/download`;a.append(link);$('items').append(a);}}
}
async function openRequest(id){
 const base=internal?'/api/partners':'/api/partner'; const r=await api(`${base}/requests/${id}`);const box=$('detail');box.replaceChildren(node('h3',r.title),node('p',labels[r.status]));
 for(const v of r.versions){const a=node('article');a.append(node('p',`Version ${v.number} · ${labels[v.status]} · ${v.reason}`),node('p',`Identifiant de pièce : ${v.id} · Preuve de dépôt : ${v.created_at} · SHA256 ${v.sha256}`));const link=node('a','Télécharger');link.href=`${base}/requests/${id}/versions/${v.id}/download`;a.append(link);box.append(a);}
 if(!internal&&['requested','rejected'].includes(r.status)){const f=node('input');f.type='file';f.setAttribute('aria-label','Document à transmettre');box.append(f,button('Transmettre une version',async()=>{if(!f.files.length)throw new Error('Choisir un fichier');const data=new FormData();data.append('file',f.files[0]);await api(`${base}/requests/${id}/versions`,'POST',data);await openRequest(id);}));}
 if(internal&&r.status==='pending'){const reason=node('textarea');reason.setAttribute('aria-label','Motif de la décision');box.append(reason);for(const [value,label] of [['approved','Approuver'],['rejected','Demander une correction']])box.append(button(label,async()=>{await api(`${base}/requests/${id}/decision`,'POST',{version_id:r.versions.at(-1).id,decision:value,reason:reason.value});await openRequest(id);}));}
 if(internal&&r.status==='approved')box.append(button('Clôturer',async()=>{await api(`${base}/requests/${id}/close`,'POST');await openRequest(id);}));
 box.append(node('h4','Historique et échanges'));const history=node('ul');for(const e of r.history)history.append(node('li',`${e.created_at} · ${e.author} · ${e.kind} : ${e.message}`));box.append(history);
 const message=node('textarea');message.setAttribute('aria-label','Votre message');box.append(message,button('Enregistrer le message',async()=>{await api(`${base}/requests/${id}/messages`,'POST',{message:message.value});await openRequest(id);$('notice').textContent='Message enregistré. Aucun email externe envoyé.';}));
}
api('/api/partner/home').then(()=>run(refresh)).catch(()=>{});

form('order-line',async data=>{if(!data.expected_date)data.expected_date=null;await api('/api/partners/order-lines','POST',data);$('order-line').reset();await refresh();});
async function renderDeliveries(){
 const base=internal?'/api/partners':'/api/partner';const rows=await api(`${base}/order-lines`);$('deliveries').replaceChildren();
 if(!rows.length)$('deliveries').append(node('p','Aucune commande matière accessible.'));
 for(const r of rows){const a=node('article');a.append(node('h4',`${r.order_ref} · ${r.material_ref}`),node('p',`Commandé : ${r.ordered} ${r.unit} · Déclaré : ${r.declared} · Réceptionné net : ${r.received} · Restant : ${r.remaining}`));
 const history=node('ul');for(const m of r.movements)history.append(node('li',`${m.occurred_on} · ${m.kind} : ${m.quantity} ${r.unit} · ${m.note} · Pièce ${m.source_id}`));a.append(history);
 const f=node('form');const fields={};for(const [name,label,type] of [['quantity','Quantité','number'],['source_id','Identifiant de la version du justificatif fournisseur','text'],['note','Justification','text'],['occurred_on','Date effective','date']]){const l=node('label',label);const input=node('input');input.name=name;input.type=type;input.required=true;if(type==='number'){input.min='0.001';input.step='0.001';}l.append(input);f.append(l);fields[name]=input;}
 if(internal){const l=node('label','Opération');const kind=node('select');kind.name='kind';for(const [value,label] of [['received','Confirmer réception'],['returned','Enregistrer retour']]){const opt=node('option',label);opt.value=value;kind.append(opt);}l.append(kind);f.append(l);}
 const submit=node('button',internal?'Confirmer le mouvement':'Déclarer une livraison');f.append(submit);let operationKey=crypto.randomUUID();
 f.onsubmit=e=>{e.preventDefault();submit.disabled=true;run(async()=>{const data=Object.fromEntries(new FormData(f));data.operation_key=operationKey;await api(`${base}/order-lines/${r.id}/${internal?'receipts':'declarations'}`,'POST',data);operationKey=crypto.randomUUID();await renderDeliveries();}).finally(()=>submit.disabled=false);};a.append(f);$('deliveries').append(a);
 }
}
