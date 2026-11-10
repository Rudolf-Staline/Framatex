'use strict';
let internal = false;
let rights = [];
let requestOffset=0;
let requestFilters={q:"",status:"",sort:"newest"};
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
 rights=who.permissions||[];
 $('identity').textContent=who.organization;$('auth').hidden=true;$('workspace').hidden=false;$('admin').hidden=!internal;$('detail').replaceChildren();
 if(internal){
  const orgs=await api('/api/partners/organizations');$('organizations').replaceChildren();$('supplier-options').replaceChildren();$('order-supplier-options').replaceChildren();$('client-options').replaceChildren();$('order-client-options').replaceChildren();
  for(const o of orgs){const a=node('article');a.append(node('h4',`${o.name} · ${o.kind} · ${o.active?'Actif':'Suspendu'}`));
   const email=node('input');email.type='email';email.placeholder='Email du contact';email.setAttribute('aria-label',`Email du contact ${o.name}`);a.append(email);
   a.append(button('Créer / renouveler invitation',async()=>{const r=await api(`/api/partners/organizations/${o.id}/invitations`,'POST',{email:email.value});$('notice').textContent=`${r.instruction}\nCode (valable 24 h) : ${r.activation_token}`;}));
   a.append(button(o.active?'Suspendre':'Réactiver',async()=>{if(!confirm('Confirmer le changement d’accès ?'))return;await api(`/api/partners/organizations/${o.id}`,'PATCH',{active:!o.active});await refresh();}));
   const accounts=await api(`/api/partners/organizations/${o.id}/accounts`);
   for(const acc of accounts){const line=node('p',`${acc.email} · ${acc.active?'Actif':'Révoqué'} `);line.append(button(acc.active?'Révoquer':'Réactiver',async()=>{if(!confirm('Confirmer la révocation des sessions et le changement de statut ?'))return;await api(`/api/partners/accounts/${acc.id}`,'PATCH',{active:!acc.active});await refresh();}));a.append(line);}
   await renderProfile(o,a);
   $('organizations').append(a);if(o.active){const opt=node('option',o.name);opt.value=o.id;$(o.kind==='supplier'?'supplier-options':'client-options').append(opt);if(o.kind==='supplier')$('order-supplier-options').append(opt.cloneNode(true));else $('order-client-options').append(opt.cloneNode(true));}
  }
 }
 $('mail-state').replaceChildren();
 if(internal){const queue=await api('/api/partners/mail');$('mail-state').append(node('h4','File email (accepté ≠ livré ou lu)'));for(const m of queue)$('mail-state').append(node('p',`${m.status} · Tentatives : ${m.attempts} · ${m.last_error}`));}
 else {const pref=await api('/api/partner/mail-preference');$('mail-state').append(node('p',`Emails : ${pref.enabled?'préférence activée':'préférence désactivée'} · Transport ${pref.transport_configured?'activé par administrateur':'désactivé'}`),button(pref.enabled?'Désactiver les emails':'Activer la préférence email',async()=>{await api('/api/partner/mail-preference','PUT',{active:!pref.enabled});await refresh();}));}
 if(internal){const options=await api('/api/partners/launch-options');for(const select of document.querySelectorAll('.launch-options')){select.replaceChildren();for(const row of options){const option=node('option',row.label);option.value=row.id;select.append(option);}}const pubs=await api('/api/partners/publication-options');$('publication-options').replaceChildren();for(const row of pubs){const option=node('option',row.label);option.value=row.id;$('publication-options').append(option);}}
 await renderClientOrders();
 await renderDeliveries();
 const params=new URLSearchParams({...requestFilters,offset:String(requestOffset),limit:'20'});
 const rows=await api(`${internal?'/api/partners/requests':'/api/partner/requests'}?${params}`);$('request-prev').disabled=requestOffset===0;$('request-next').disabled=rows.length<20;
 $('partner-notifications').replaceChildren();if(!internal){for(const n of await api('/api/partner/notifications')){const line=node('p',`${n.read?'Lu':'Nouveau'} · ${n.created_at} · ${n.message}`);line.append(button('Ouvrir la demande',()=>openRequest(n.request_id)));if(!n.read)line.append(button('Marquer lu',async()=>{await api(`/api/partner/notifications/${n.id}/read`,'POST');await refresh();}));$('partner-notifications').append(line);}}$('items').replaceChildren();
 if(!rows.length)$('items').append(node('p','Aucune demande accessible.'));
 for(const r of rows){const a=node('article');a.append(node('h4',`${r.order_ref} · ${r.title}`),node('p',`${labels[r.status]} · Échéance : ${r.due_date||'non définie'}`),button('Ouvrir',()=>openRequest(r.id)));$('items').append(a);}
 if(rows.length===100)$('items').append(node('p','Les 100 demandes les plus récentes sont affichées. Les suivantes sont disponibles via la pagination API.'));
 if(!internal){for(const p of await api('/api/partner/publications')){const a=node('article');a.append(node('h4',`${p.title} · version ${p.version}`));const link=node('a','Télécharger la version publiée');link.href=`/api/partner/publications/${p.id}/download`;a.append(link);$('items').append(a);}}
}
async function openRequest(id){
 const base=internal?'/api/partners':'/api/partner'; const r=await api(`${base}/requests/${id}`);const box=$('detail');box.replaceChildren(node('h3',r.title),node('p',labels[r.status]));
 for(const v of r.versions){const a=node('article');a.append(node('p',`Version ${v.number} · ${labels[v.status]} · ${v.reason}`),node('p',`Identifiant de pièce : ${v.id} · Preuve de dépôt : ${v.created_at} · SHA256 ${v.sha256}`));const link=node('a','Télécharger');link.href=`${base}/requests/${id}/versions/${v.id}/download`;a.append(link);box.append(a);}
 if(!internal&&rights.includes('document.write')&&['requested','rejected'].includes(r.status)){const f=node('input');f.type='file';f.setAttribute('aria-label','Document à transmettre');box.append(f,button('Transmettre une version',async()=>{if(!f.files.length)throw new Error('Choisir un fichier');const data=new FormData();data.append('file',f.files[0]);await api(`${base}/requests/${id}/versions`,'POST',data);await openRequest(id);}));}
 if(internal&&r.status==='pending'){const reason=node('textarea');reason.setAttribute('aria-label','Motif de la décision');box.append(reason);for(const [value,label] of [['approved','Approuver'],['rejected','Demander une correction']])box.append(button(label,async()=>{await api(`${base}/requests/${id}/decision`,'POST',{version_id:r.versions.at(-1).id,decision:value,reason:reason.value});await openRequest(id);}));}
 if(internal&&r.status==='approved')box.append(button('Clôturer',async()=>{await api(`${base}/requests/${id}/close`,'POST');await openRequest(id);}));
 if(internal&&['approved','closed'].includes(r.status)){
  const folder=node('select');folder.setAttribute('aria-label','Rubrique interne');for(const value of ['jaune','rose','bleu','vert']){const option=node('option',value);option.value=value;folder.append(option);}box.append(folder,button('Intégrer au dossier interne',async()=>{const result=await api(`${base}/requests/${id}/integrate`,'POST',{submission_id:r.versions.at(-1).id,folder:folder.value,document_id:r.integrated_document_id||null});$('notice').textContent=`Document intégré : ${result.document.title}`;await openRequest(id);}));
  const reason=node('input');reason.setAttribute('aria-label','Motif de réouverture');box.append(reason,button('Demander une nouvelle version',async()=>{await api(`${base}/requests/${id}/reopen`,'POST',{reason:reason.value});await openRequest(id);}));
 }
 if(internal&&r.integrated_document_id){const doc=await api(`/api/documents/${r.integrated_document_id}/supplier-detail`);const origin=await api(`/api/document-versions/${doc.latest.id}/supplier-origin`);box.append(button('Vérifier les champs extraits',async()=>{const intake=await api(`/api/document-versions/${doc.latest.id}/intake`);const panel=node('article');panel.append(node('h4','Champs confirmés exploitables'));for(const field of intake.confirmed.filter(x=>x.key==='quantite')){panel.append(node('p',`${field.value} ${field.unit}`));const choices=field.unit==='pièce'?['quantite_lancement']:field.unit==='m'?['besoin_matiere_total']:[];for(const key of choices)panel.append(button(`Utiliser pour ${key}`,async()=>{const full=await api(`/api/document-versions/${doc.latest.id}/intake`);const source=full.confirmed.find(x=>x.key===field.key);await api(`/api/document-versions/${doc.latest.id}/data-from-confirmed`,'POST',{confirmed_id:source.id,field_key:key});}));}panel.append(node('p','Confirmer les valeurs dans le panneau documentaire interne avant de les utiliser. Aucune valeur OCR brute n’est injectée.'));box.append(panel);}));box.append(node('p',`Provenance fournisseur : version ${origin.source_version}, ${origin.submitted_at}, intégration ${origin.active?'active':'retirée'}`));if(origin.active){const reason=node('input');reason.setAttribute('aria-label','Motif du retrait interne');box.append(reason,button('Retirer le justificatif métier',async()=>{await api(`/api/document-versions/${doc.latest.id}/supplier-withdrawal`,'POST',{reason:reason.value});await openRequest(id);}));}}
 renderAttachments(box,r.attachments||[],`${base}/requests/${id}/attachments`,()=>openRequest(id));
 box.append(node('h4','Historique et échanges'));const history=node('ul');for(const e of r.history)history.append(node('li',`${e.created_at} · ${e.author} · ${e.kind} : ${e.message}`));box.append(history);
 if(!internal&&!rights.includes('message.write'))return;
 const message=node('textarea');message.setAttribute('aria-label','Votre message');box.append(message,button('Enregistrer le message',async()=>{await api(`${base}/requests/${id}/messages`,'POST',{message:message.value});await openRequest(id);$('notice').textContent='Message enregistré. Aucun email externe envoyé.';}));
}
api('/api/partner/home').then(()=>run(refresh)).catch(()=>{});

form('order-line',async data=>{if(!data.expected_date)data.expected_date=null;await api('/api/partners/order-lines','POST',data);$('order-line').reset();await refresh();});
async function renderDeliveries(){
 const base=internal?'/api/partners':'/api/partner';const rows=await api(`${base}/order-lines`);$('deliveries').replaceChildren();
 if(!rows.length)$('deliveries').append(node('p','Aucune commande matière accessible.'));
 for(const r of rows){const a=node('article');a.append(node('h4',`${r.order_ref} · ${r.material_ref}`),node('p',`Prévu : ${r.planned||"non renseigné"} · Annoncé : ${r.announced} · Retourné : ${r.returned} · Commandé : ${r.ordered} ${r.unit} · Déclaré : ${r.declared} · Réceptionné net : ${r.received} · Restant : ${r.remaining}`));
 const history=node('ul');for(const m of r.movements){const line=node('li',`${m.occurred_on} · ${m.kind} : ${m.quantity} ${r.unit} · ${m.note} · ${m.cancelled?'Annulé : '+m.cancellation_reason:''}`);if(!m.cancelled&&(internal||(['announced','declared'].includes(m.kind)&&rights.includes('delivery.write')))){const reason=node('input');reason.setAttribute('aria-label','Motif d’annulation');line.append(reason,button('Annuler ce mouvement',async()=>{await api(`${base}/order-lines/${r.id}/movements/${m.id}/cancel`,'POST',{reason:reason.value});await renderDeliveries();}));}history.append(line);}a.append(history);
 if(!internal&&!rights.includes('delivery.write')){$('deliveries').append(a);continue;}
 const f=node('form');const fields={};for(const [name,label,type] of [['quantity','Quantité','number'],['source_id','Identifiant de la version du justificatif fournisseur','text'],['note','Justification','text'],['occurred_on','Date effective','date']]){const l=node('label',label);const input=node('input');input.name=name;input.type=type;input.required=true;if(type==='number'){input.min='0.001';input.step='0.001';}l.append(input);f.append(l);fields[name]=input;}
 if(internal){const l=node('label','Opération');const kind=node('select');kind.name='kind';for(const [value,label] of [['received','Confirmer réception'],['returned','Enregistrer retour'],['planned','Réviser la quantité prévue']]){const opt=node('option',label);opt.value=value;kind.append(opt);}l.append(kind);f.append(l);}
 if(!internal){const label=node('label','Nature de la déclaration'),select=node('select');select.name='kind';for(const [value,label] of [['declared','Livraison effectuée'],['announced','Livraison annoncée']]){const opt=node('option',label);opt.value=value;select.append(opt);}label.append(select);f.append(label);}
 const submit=node('button',internal?'Confirmer le mouvement':'Déclarer une livraison');f.append(submit);let operationKey=crypto.randomUUID();
 f.onsubmit=e=>{e.preventDefault();submit.disabled=true;run(async()=>{const data=Object.fromEntries(new FormData(f));data.operation_key=operationKey;await api(`${base}/order-lines/${r.id}/${internal?'receipts':data.kind==='announced'?'announcements':'declarations'}`,'POST',data);operationKey=crypto.randomUUID();await renderDeliveries();}).finally(()=>submit.disabled=false);};a.append(f);$('deliveries').append(a);
 }
}

async function renderProfile(org,container){
 const data=await api(`/api/partners/organizations/${org.id}/profile`);const roles=await api(`/api/partners/organizations/${org.id}/roles`);
 const details=node('details');details.append(node('summary','Fiche administrative, historique et rôles'));
 const f=node('form');
 for(const [name,label,value] of [['name','Nom légal',data.name],['trade_name','Nom commercial',data.trade_name],['contact','Coordonnées / contacts',data.contact],['address','Adresse',data.address],['domains','Domaines email autorisés (séparés par des virgules)',data.domains.join(',')],['administrative','Informations administratives (une ligne clé=valeur)',Object.entries(data.administrative).map(([k,v])=>`${k}=${v}`).join('\n')]]){
  const l=node('label',label),input=node(name==='administrative'?'textarea':'input');input.name=name;input.value=value;l.append(input);f.append(l);
 }
 f.append(node('button','Enregistrer la fiche'));f.onsubmit=e=>{e.preventDefault();run(async()=>{const values=Object.fromEntries(new FormData(f));values.domains=values.domains.split(',').map(s=>s.trim()).filter(Boolean);values.administrative=Object.fromEntries(values.administrative.split('\n').filter(Boolean).map(line=>{const at=line.indexOf('=');if(at<1)throw new Error('Utiliser clé=valeur');return [line.slice(0,at),line.slice(at+1)];}));await api(`/api/partners/organizations/${org.id}/profile`,'PUT',values);await refresh();});};details.append(f);
 const roleForm=node('form'),nameLabel=node('label','Nom du rôle'),nameInput=node('input');nameInput.name='name';nameInput.required=true;nameLabel.append(nameInput);roleForm.append(nameLabel);
 for(const [permission,label] of [['document.write','Déposer des documents'],['message.write','Écrire des messages'],['delivery.write','Déclarer des livraisons']]){const l=node('label',label),input=node('input');input.type='checkbox';input.name=permission;l.append(input);roleForm.append(l);}
 roleForm.append(node('button','Créer ce rôle (lecture incluse)'));roleForm.onsubmit=e=>{e.preventDefault();run(async()=>{const values=Object.fromEntries(new FormData(roleForm));await api(`/api/partners/organizations/${org.id}/roles`,'POST',{name:values.name,permissions:['read',...Object.keys(values).filter(k=>k!=='name')]});await refresh();});};details.append(roleForm);
 for(const account of await api(`/api/partners/organizations/${org.id}/accounts`)){const label=node('label',`Rôle de ${account.email}`),select=node('select');const current=node('option','Choisir un rôle configuré');current.value='';select.append(current);for(const role of roles){const option=node('option',`${role.name} (${role.permissions.join(', ')})`);option.value=role.id;select.append(option);}label.append(select);details.append(label,button('Attribuer le rôle',async()=>{if(!select.value)throw new Error('Choisir un rôle');await api(`/api/partners/accounts/${account.id}/role`,'PUT',{role_id:select.value});$('notice').textContent='Rôle attribué. Les droits sont immédiatement appliqués.';}));}
 for(const event of data.history)details.append(node('p',`${event.date} · ${event.action} · ${JSON.stringify(event.detail)}`));container.append(details);
}

form('client-order',async data=>{if(!data.confirmed_due)data.confirmed_due=null;await api('/api/partners/client-orders','POST',data);$('client-order').reset();await renderClientOrders();});
function renderAttachments(container,attachments,endpoint,refreshView){
 for(const a of attachments){const link=node('a',`Pièce jointe : ${a.name} (${a.size} octets)`);link.href=`${internal?'/api/partners':'/api/partner'}/attachments/${a.id}/download`;const paragraph=node('p');paragraph.append(link);container.append(paragraph);}
 if(!internal&&!rights.includes('message.write'))return;
 const form=node('form'),label=node('label','Pièce jointe privée'),file=node('input');file.type='file';file.name='file';file.required=true;label.append(file);form.append(label);
 const messageLabel=node('label','Description de la pièce'),message=node('input');message.name='message';message.required=true;messageLabel.append(message);form.append(messageLabel,node('button','Joindre le fichier'));
 form.onsubmit=e=>{e.preventDefault();run(async()=>{await api(endpoint,'POST',new FormData(form));await refreshView();});};container.append(form);
}
async function renderClientOrders(){
 const base=internal?'/api/partners':'/api/partner';const rows=await api(`${base}/client-orders`);$('client-orders').replaceChildren();if(!rows.length)return;$('client-orders').append(node('h3','Commandes client autorisées'));
 for(const order of rows){const card=node('article');card.append(node('h4',order.reference),node('p',`${order.status} · Échéance confirmée : ${order.confirmed_due||'non renseignée'} · Avancement chiffré non renseigné`));
 if(internal){const label=node('label','Mettre à jour le statut'),status=node('select');for(const value of ['Non renseigné','Confirmée','En préparation','En fabrication','Expédiée','Terminée']){const option=node('option',value);option.value=value;option.selected=value===order.status;status.append(option);}label.append(status);card.append(label,button('Confirmer ce statut',async()=>{await api(`${base}/client-orders/${order.id}`,'PUT',{partner_id:order.partner_id,launch_id:order.launch_id,reference:order.reference,status:status.value,confirmed_due:order.confirmed_due,active:order.active});await renderClientOrders();}),button(order.active?'Retirer l’accès commande':'Rétablir l’accès commande',async()=>{if(!confirm('Confirmer le changement d’accès ?'))return;await api(`${base}/client-orders/${order.id}`,'PUT',{partner_id:order.partner_id,launch_id:order.launch_id,reference:order.reference,status:order.status,confirmed_due:order.confirmed_due,active:!order.active});await renderClientOrders();}));}
 const threads=await api(`${base}/client-orders/${order.id}/threads`);
 for(const thread of threads){const panel=node('section');panel.append(node('h4',`${thread.title} · ${thread.status}`));for(const message of thread.messages)panel.append(node('p',`${message.created_at} · ${message.author} : ${message.message}`));
 if(thread.status!=='closed'){
  const f=node('form'),l=node('label','Réponse à la clarification'),input=node('textarea');input.name='message';input.required=true;l.append(input);f.append(l,node('button','Répondre'));f.onsubmit=e=>{e.preventDefault();run(async()=>{await api(`${base}/threads/${thread.id}/messages`,'POST',{message:input.value});await renderClientOrders();});};if(internal||rights.includes('message.write'))panel.append(f);
  renderAttachments(panel,thread.attachments,`${base}/threads/${thread.id}/attachments`,renderClientOrders);
 }else{for(const a of thread.attachments){const link=node('a',a.name);link.href=`${base}/attachments/${a.id}/download`;panel.append(link);}}
 if(internal){const l=node('label','Motif du changement de traitement'),reason=node('input');l.append(reason);panel.append(l);for(const [state,label] of [['waiting_client','Demander une précision'],['closed','Clôturer l’échange'],['open','Rouvrir l’échange']])panel.append(button(label,async()=>{await api(`${base}/threads/${thread.id}/status`,'POST',{status:state,reason:reason.value});await renderClientOrders();}));}card.append(panel);
 }
 if(!internal&&rights.includes('message.write')){const f=node('form');for(const [name,label] of [['title','Objet de la demande'],['message','Votre question']]){const l=node('label',label),input=node('input');input.name=name;input.required=true;l.append(input);f.append(l);}f.append(node('button','Poser une question'));f.onsubmit=e=>{e.preventDefault();run(async()=>{await api(`${base}/client-orders/${order.id}/threads`,'POST',Object.fromEntries(new FormData(f)));await renderClientOrders();});};card.append(f);}$('client-orders').append(card);
 }
}

form('request-search',async data=>{requestFilters=data;requestOffset=0;await refresh();});
$('request-prev').onclick=()=>run(async()=>{requestOffset=Math.max(0,requestOffset-20);await refresh();});
$('request-next').onclick=()=>run(async()=>{requestOffset+=20;await refresh();});
