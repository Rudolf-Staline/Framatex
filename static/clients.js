'use strict';
let clientDirectory=[];
async function clientsPage(){
 state.view='clients';
 clientDirectory=await api('/api/clients');
 mount(`<div class="page-heading"><div><div class="page-kicker">RELATIONS CLIENTS</div><h1 class="page-title">Vos clients<span class="brand-accent">.</span></h1><p class="page-lead">Un interlocuteur, ses dossiers jaunes, un espace de suivi dédié.</p></div><button class="primary" id="new-client">${icon('plus')} Inscrire un client</button></div><div class="client-summary"><div><strong>${clientDirectory.filter(c=>c.active).length}</strong><span>clients actifs</span></div><div><strong>${clientDirectory.reduce((n,c)=>n+c.launch_count,0)}</strong><span>dossiers associés</span></div><div><strong>${clientDirectory.reduce((n,c)=>n+c.contacts.filter(u=>u.active).length,0)}</strong><span>accès au portail</span></div></div><div class="toolbar"><label class="searchbar">${icon('search')}<input id="client-search" placeholder="Rechercher une société ou un contact…" aria-label="Rechercher un client"></label></div><div id="client-directory" class="client-grid"></div>`,'Clients');
 const draw=()=>{
  const q=app.querySelector('#client-search').value.toLocaleLowerCase('fr');
  const rows=clientDirectory.filter(c=>[c.name,c.contact_email,...c.contacts.map(u=>u.email)].join(' ').toLocaleLowerCase('fr').includes(q));
  app.querySelector('#client-directory').innerHTML=rows.length?rows.map(c=>`<article class="panel client-card"><div class="client-card-top"><div class="client-monogram">${e(c.name.slice(0,2).toUpperCase())}</div>${statusTag(c.active?'Actif':'Désactivé')}</div><h2>${e(c.name)}</h2><p>${e(c.contact_email||'Contact principal à renseigner')}</p><div class="client-card-counts"><span>${c.launch_count} dossier(s)</span><span>${c.contacts.filter(u=>u.active).length} accès actif(s)</span></div><div class="client-card-actions"><button class="primary tiny" data-client-open="${e(c.id)}">Gérer le client ${icon('arrow')}</button><button class="secondary tiny" data-client-folders="${e(c.id)}">Dossiers</button></div></article>`).join(''):`<div class="panel empty"><strong>${q?'Aucun client trouvé':'Votre répertoire commence ici'}</strong><p>${q?'Essayez le nom de la société ou une adresse email.':'Inscrivez une société, puis créez ses accès à l’espace client.'}</p></div>`;
  app.querySelectorAll('[data-client-open]').forEach(b=>b.onclick=()=>clientEditor(clientDirectory.find(c=>c.id===b.dataset.clientOpen)));
  app.querySelectorAll('[data-client-folders]').forEach(b=>b.onclick=async()=>{await launchList();const search=app.querySelector('#launch-search');search.value=clientDirectory.find(c=>c.id===b.dataset.clientFolders).name;search.dispatchEvent(new Event('input'))});
 };
 app.querySelector('#new-client').onclick=()=>clientEditor();
 app.querySelector('#client-search').oninput=draw;draw();
}
function clientEditor(client=null){
 modal(client?'Gérer le client':'Inscrire un client',`<p class="modal-desc">Les dossiers sont rattachés à une société. Chaque contact dispose de son propre compte client.</p><form id="client-form"><div class="field"><label for="company-name">Société</label><input id="company-name" required minlength="2" maxlength="150" value="${e(client?.name||'')}" autocomplete="organization"></div><div class="field"><label for="company-email">Email de contact</label><input id="company-email" type="email" maxlength="254" value="${e(client?.contact_email||'')}" autocomplete="email"></div><div id="client-form-error" role="alert"></div><div class="modal-actions"><button class="secondary" type="button" id="cancel-client">Fermer</button><button class="primary" type="submit">${client?'Enregistrer':'Créer le client'}</button></div></form>${client?`<hr><div class="section-heading"><h3>Accès à l’espace client</h3><button class="secondary tiny" id="add-client-contact" ${client.active?'':'disabled'}>${icon('plus')} Créer un accès</button></div><p class="muted small">Le contact se connecte sur la même page et accède uniquement à son portail.</p><div class="client-contact-list">${client.contacts.length?client.contacts.map(u=>`<div><span><strong>${e(u.name)}</strong><small>${e(u.email)}</small></span><button class="secondary tiny" data-contact-active="${e(u.id)}">${u.active?'Désactiver':'Réactiver'}</button></div>`).join(''):'<p>Aucun accès créé.</p>'}</div><div class="modal-actions"><button class="secondary" id="toggle-client">${client.active?'Désactiver tous les accès de cette société':'Réactiver la société'}</button></div>`:''}`);
 overlay.querySelector('#cancel-client').onclick=closeModal;
 overlay.querySelector('#client-form').onsubmit=async ev=>{
  ev.preventDefault();const btn=ev.submitter;btn.disabled=true;
  try{await api('/api/clients'+(client?'/'+client.id:''),{method:client?'PATCH':'POST',body:JSON.stringify({name:val('company-name'),contact_email:val('company-email')||null})});closeModal();toast(client?'Client mis à jour':'Client inscrit');await clientsPage()}
  catch(err){overlay.querySelector('#client-form-error').textContent=err.message}finally{btn.disabled=false}
 };
 overlay.querySelector('#add-client-contact')?.addEventListener('click',()=>clientContactForm(client));
 overlay.querySelector('#toggle-client')?.addEventListener('click',async()=>{try{await api(`/api/clients/${client.id}/active`,{method:'PATCH',body:JSON.stringify({active:!client.active})});closeModal();await clientsPage()}catch(err){showErr(err)}});
 overlay.querySelectorAll('[data-contact-active]').forEach(b=>b.onclick=async()=>{const u=client.contacts.find(u=>u.id===b.dataset.contactActive);try{await api(`/api/clients/${client.id}/contacts/${u.id}/active`,{method:'PATCH',body:JSON.stringify({active:!u.active})});closeModal();await clientsPage()}catch(err){showErr(err)}});
}
function clientContactForm(client){
 modal('Créer un accès · '+client.name,`<form id="contact-form"><p class="modal-desc">Transmettez ces identifiants à votre contact par votre canal habituel.</p><div class="field"><label for="contact-name">Nom du contact</label><input id="contact-name" minlength="2" maxlength="120" required autocomplete="name"></div><div class="field"><label for="contact-email">Adresse email de connexion</label><input id="contact-email" type="email" maxlength="254" required autocomplete="email"></div><div class="field"><label for="contact-password">Mot de passe (12 caractères minimum)</label><input id="contact-password" type="password" minlength="12" maxlength="256" required autocomplete="new-password"></div><div id="contact-error" role="alert"></div><div class="modal-actions"><button type="button" class="secondary" id="cancel-contact">Annuler</button><button type="submit" class="primary">Créer l’accès</button></div></form>`);
 overlay.querySelector('#cancel-contact').onclick=()=>clientEditor(client);
 overlay.querySelector('#contact-form').onsubmit=async ev=>{ev.preventDefault();ev.submitter.disabled=true;try{await api(`/api/clients/${client.id}/contacts`,{method:'POST',body:JSON.stringify({name:val('contact-name'),email:val('contact-email'),password:val('contact-password')})});closeModal();toast('Accès client créé');await clientsPage()}catch(err){overlay.querySelector('#contact-error').textContent=err.message;ev.submitter.disabled=false}};
}
async function clientSelect(id, selected){
 const rows=await api('/api/clients');
 return `<div class="field"><label for="${id}">Client du répertoire</label><select id="${id}"><option value="">Aucun rattachement au portail</option>${rows.filter(c=>c.active||c.id===selected).map(c=>`<option value="${e(c.id)}" ${c.id===selected?'selected':''}>${e(c.name)}${c.active?'':' (désactivé)'}</option>`).join('')}</select><small>Le client choisi retrouve ce dossier dans son espace.</small></div>`;
}
async function clientPortal(){
 state.view='home';const data=await api('/api/portal/home');
 state.portal=data;
 mount(`<div class="portal-welcome"><span class="page-kicker">VOTRE ESPACE CLIENT</span><h1>${e(data.client.name)}<span class="brand-accent">.</span></h1><p>Retrouvez l’avancement de vos dossiers et les documents partagés par Framatex.</p><div class="portal-count"><strong>${data.launches.length}</strong> dossier(s) de fabrication</div></div><div class="section-heading"><h2>Vos dossiers jaunes</h2><small>Mis à jour par votre équipe Framatex</small></div><div class="toolbar"><label class="searchbar">${icon('search')}<input id="portal-search" aria-label="Rechercher vos dossiers" placeholder="Nom du dossier ou référence de commande…"></label></div><div id="portal-folders" class="client-grid"></div>`,'Espace client');
 const draw=()=>{const q=app.querySelector('#portal-search').value.toLowerCase();const rows=data.launches.filter(l=>[l.name,l.order_ref].join(' ').toLowerCase().includes(q));app.querySelector('#portal-folders').innerHTML=rows.length?rows.map(l=>`<button class="panel portal-folder" data-portal-launch="${e(l.id)}"><div>${icon('folder')}${statusTag(l.status)}</div><h2>${e(l.name)}</h2><p>${e(l.order_ref||'Référence de commande à venir')}</p><span>Mis à jour le ${niceDate(l.updated_at)} ${icon('arrow')}</span></button>`).join(''):'<div class="panel empty"><strong>Aucun dossier à afficher</strong><p>Votre interlocuteur Framatex peut associer un dossier à votre société.</p></div>';app.querySelectorAll('[data-portal-launch]').forEach(b=>b.onclick=()=>portalDetail(b.dataset.portalLaunch))};app.querySelector('#portal-search').oninput=draw;draw();
}
async function portalDetail(id){
 const d=await api('/api/portal/launches/'+id);state.view='launches';
 mount(`<button class="link" id="portal-back">${icon('back')} Mes dossiers</button><div class="page-heading"><div><div class="page-kicker">DOSSIER JAUNE</div><h1 class="page-title">${e(d.name)}</h1><p class="page-lead">${e(d.order_ref||'Sans référence de commande')} · Mise à jour le ${niceDate(d.updated_at)}</p></div>${statusTag(d.status)}</div><div class="section-heading"><h2>Documents partagés</h2><small>Versions validées par Framatex</small></div><section class="panel">${d.documents.length?`<div class="client-document-list">${d.documents.map(doc=>`<div>${icon('file')}<span><strong>${e(doc.title)}</strong><small>Version ${doc.version} · Partagée le ${niceDate(doc.published_at)}</small></span><a class="secondary tiny" href="/api/portal/documents/${encodeURIComponent(doc.id)}/download">${icon('download')} Télécharger</a></div>`).join('')}</div>`:'<div class="empty"><strong>Les documents arrivent bientôt</strong><p>Les pièces apparaissent ici lorsque votre équipe Framatex les publie.</p></div>'}</section>`,'Mon dossier');
 app.querySelector('#portal-back').onclick=()=>clientPortal();
}

function bindClientChoice(prefix){
 const select=overlay.querySelector('#'+prefix+'-client-id');
 const freeText=overlay.querySelector('#'+prefix+'-client');
 if(!select||!freeText)return;
 const update=()=>{freeText.disabled=!!select.value;freeText.closest('.field').hidden=!!select.value};
 select.addEventListener('change',update);update();
}
