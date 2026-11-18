'use strict';
function orderValue(id){return document.getElementById(id)?.value.trim()||''}
let dossierNavigation=0;
// Canonical navigation: order -> unique dossier -> section -> documents.
async function ordersPage(view='orders'){
 ++dossierNavigation;const appNavigation=++navigationVersion;state.view=view;let page=0,requestSequence=0;const pageSize=20;
 mount(`<div class="page-heading"><div><h1>${view==='dossiers'?'Dossiers Jaunes':'Commandes'}</h1><p>Une commande, un Dossier Jaune unique, quatre rubriques et plusieurs lancements possibles.</p></div>${can('order.create')?'<button class="primary" id="order-create">Créer une commande</button>':''}</div><section class="panel order-panel"><label for="order-query">Rechercher une commande ou un client</label><input id="order-query" type="search" maxlength="200"><label for="order-sort">Trier</label><select id="order-sort"><option value="newest">Plus récentes</option><option value="reference">Référence</option><option value="client">Client</option></select><div id="order-results"></div><div class="order-pagination"><button id="order-prev">Précédent</button><p id="order-count" role="status"></p><button id="order-next">Suivant</button></div></section>`,view==='dossiers'?'Dossiers Jaunes':'Commandes');
 const render=async()=>{
  const request=++requestSequence;
  app.querySelector('#order-count').textContent='Chargement…';
  try{
   const result=await api('/api/orders?'+new URLSearchParams({page:'true',q:orderValue('order-query'),sort:orderValue('order-sort'),offset:String(page*pageSize),limit:String(pageSize)}));
   if(request!==requestSequence||state.view!==view||navigationVersion!==appNavigation)return;
   const subset=result.items;
   app.querySelector('#order-results').innerHTML=subset.length?`<div class="table-scroll"><table><caption>Commandes autorisées et leur Dossier Jaune</caption><thead><tr><th>Commande</th><th>Client</th><th>Création</th><th class="numeric">Lancements</th><th>Action</th></tr></thead><tbody>${subset.map(r=>`<tr><td>${e(r.reference)}</td><td>${e(r.client_name)}</td><td>${niceDate(r.created_at)}</td><td class="numeric">${r.launches.length}</td><td><button class="secondary" data-order="${e(r.id)}">Ouvrir le Dossier Jaune de ${e(r.reference)}</button></td></tr>`).join('')}</tbody></table></div>`:'<p class="empty">Aucune commande autorisée ne correspond à la recherche.</p>';
   app.querySelector('#order-count').textContent=`${result.total} commande(s) · Page ${page+1}`;
   app.querySelector('#order-prev').disabled=page===0;app.querySelector('#order-next').disabled=(page+1)*pageSize>=result.total;
   app.querySelectorAll('[data-order]').forEach(b=>b.onclick=()=>orderDossierPage(b.dataset.order).catch(showErr));
  }catch(err){if(request===requestSequence&&state.view===view&&navigationVersion===appNavigation&&app.querySelector('#order-count'))app.querySelector('#order-count').textContent=err.message||'Chargement impossible. Relancez la recherche.'}
 };
 let queryTimer;
 app.querySelector('#order-query').oninput=()=>{clearTimeout(queryTimer);queryTimer=setTimeout(()=>{page=0;render()},200)};app.querySelector('#order-sort').onchange=()=>{page=0;render()};
 app.querySelector('#order-prev').onclick=()=>{page--;render()};app.querySelector('#order-next').onclick=()=>{page++;render()};
 app.querySelector('#order-create')?.addEventListener('click',async()=>{try{
  modal('Créer une commande',`<form id="canonical-order-create"><label for="canonical-client">Client</label><select id="canonical-client" required></select><label for="canonical-reference">Référence de commande</label><input id="canonical-reference" required maxlength="100"><p>Un Dossier Jaune unique et ses quatre rubriques seront créés pour cette commande.</p><button class="primary">Créer la commande et son dossier</button></form>`);
  pagedSelect(overlay.querySelector('#canonical-client'),'/api/order-clients','Choisir un client',c=>`${c.name} · ${c.id}`);
  overlay.querySelector('form').onsubmit=async event=>{event.preventDefault();await orderSubmit(event.target,async()=>{const row=await api('/api/orders',{method:'POST',body:JSON.stringify({client_id:orderValue('canonical-client'),reference:orderValue('canonical-reference')})});closeModal();await orderDossierPage(row.id);toast('Commande et dossier créés')})};
 }catch(err){showErr(err)}});
 await render();
}
async function orderSubmit(form,action){
 if(form.dataset.busy)return;form.dataset.busy='1';form.setAttribute('aria-busy','true');const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
 try{await action()}catch(err){showErr(err)}finally{delete form.dataset.busy;form.removeAttribute('aria-busy');buttons.forEach(b=>b.disabled=false)}
}
async function orderDossierPage(id,section='jaune',focusDocument=null){
 const navigation=++dossierNavigation;const appNavigation=++navigationVersion;
 const [root,order,approvalReport,coverage]=await Promise.all([api(`/api/orders/${encodeURIComponent(id)}/dossier?summary=true`),api(`/api/orders/${encodeURIComponent(id)}?summary=true`),Promise.resolve({items:[]}),api(`/api/orders/${encodeURIComponent(id)}/completeness`)]);
 if(navigation!==dossierNavigation||navigationVersion!==appNavigation)return;
 state.view='dossiers';state.orderDossier=root;
 mount(`<nav aria-label="Fil d’Ariane"><button class="link" id="order-back">Commandes</button> → ${e(root.reference)} → Dossier Jaune</nav><div class="page-heading"><div><h1>Dossier Jaune · ${e(root.reference)}</h1><p>${e(order.client_name)} · Un dossier partagé par les ${order.launches.length} lancement(s) de cette commande.</p></div></div><div class="folder-grid">${root.sections.map(s=>`<button class="folder-card ${s.slug===section?'selected':''}" data-order-section="${s.slug}" aria-pressed="${s.slug===section}"><strong>${e(s.slug[0].toUpperCase()+s.slug.slice(1))}</strong><span>${e(s.label)}</span><small>${s.can_read?(s.total??s.documents.length)+' document(s)':'Accès restreint'}</small></button>`).join('')}</div><section class="panel order-panel"><h2 id="order-section-title"></h2><div class="order-filters"><label>Filtrer par lancement <select id="order-origin"><option value="">Tous les lancements et pièces de commande</option>${order.launches.map(l=>`<option value="${e(l.id)}">${e(l.name)}</option>`).join('')}<option value="unassigned">Pièces sans lancement</option></select></label><label>Rechercher un document <input type="search" id="order-document-query" maxlength="200"></label></div><div id="order-documents" aria-live="polite"></div><div class="order-pagination"><button id="document-prev">Précédent</button><p id="document-count" role="status"></p><button id="document-next">Suivant</button></div><div id="order-upload"></div></section><section class="panel order-panel"><h2>Complétude de ${e(root.reference)}</h2><p>${coverage.configured?`${coverage.counts.missing} pièce(s) manquante(s) · ${coverage.counts.pending_validation} validation(s) en attente · ${coverage.counts.ready} exigence(s) satisfaite(s) · ${coverage.counts.pending_publication||0} publication(s) en attente${coverage.partial_visibility?' · visibilité partielle':''}`:'Aucun profil configuré : la complétude ne peut pas être déclarée.'}</p><ul>${coverage.items.map(r=>`<li>${e(r.folder)} · ${e(r.title)} : ${e({ready:'Satisfait',present:'Satisfait',missing:'Manquant exigible',pending_validation:'Validation en attente',pending_publication:'Publication en attente',not_applicable:'Non applicable',optional:'Facultatif',not_due:'Non encore exigible',exception:'Dérogation justifiée'}[r.status]||r.status)}${r.launch_id?' · obligation du lancement':''}${r.due?' · exigible':''}${r.deadline_reference_missing?' · événement de référence absent':''}${r.exception_reason?' · '+e(r.exception_reason):''}${r.can_review?` <button type="button" class="secondary tiny" data-order-waiver="${e(r.rule_id)}" data-waiver-launch="${e(r.launch_id||'')}" data-waiver-active="${r.status==='exception'?'true':'false'}">${r.status==='exception'?'Retirer la dérogation':'Justifier une dérogation'}</button>`:''}</li>`).join('')}</ul><p>Les règles métier doivent être confirmées par Framatex.</p>${state.me.admin?'<button id="order-completeness-configure" class="secondary">Configurer la complétude de la commande</button><button id="order-member-grant" class="secondary">Habiliter un collaborateur</button>':''}</section><section class="panel order-panel"><h2>Lancements de ${e(root.reference)}</h2><p><a href="/api/orders/${e(id)}/paper-qr.png" target="_blank" rel="noopener">QR du Dossier Jaune de ${e(root.reference)}</a></p>${order.launches.map(l=>`<p><button class="link" data-linked-launch="${e(l.id)}">${e(l.name)}</button> · ${e(l.status)}</p>`).join('')||'<p>Aucun lancement associé.</p>'}${can('launch.create')?'<button id="order-launch-create" class="secondary">Ajouter un lancement à cette commande</button>':''}${state.me.admin?'<button id="order-launch-link" class="secondary">Rattacher un lancement historique</button>':''}</section>`,`Commande ${root.reference} / Dossier Jaune`);
 mountOrderIdentification(id,order);
 app.querySelector('#order-back').onclick=()=>ordersPage().catch(showErr);
 app.querySelectorAll('[data-linked-launch]').forEach(b=>b.onclick=()=>openLaunch(b.dataset.linkedLaunch).catch(showErr));
 let current=section,documentOffset=0,documentRequest=0;
 async function renderDocuments(){
  const s=root.sections.find(s=>s.slug===current);const origin=orderValue('order-origin'),term=orderValue('order-document-query').toLocaleLowerCase('fr');
  const request=++documentRequest;
  const destination = current;
  app.querySelector('#order-upload').replaceChildren();
  app.querySelector('#order-documents').textContent='Chargement…';
  let result;
  try{result=await api(`/api/orders/${id}/document-page?`+new URLSearchParams({folder:current,origin,q:term,offset:String(documentOffset),limit:'25',...(focusDocument?{document_id:focusDocument}:{})}))}
  catch(err){if(request===documentRequest && state.orderDossier===root && navigationVersion===appNavigation)app.querySelector('#order-documents').textContent=err.message||'Chargement impossible. Modifiez un filtre pour réessayer.';return}
  if(request!==documentRequest||state.orderDossier!==root||navigationVersion!==appNavigation)return;
  const docs=result.items;approvalReport.items=result.approvals;
  app.querySelector('#document-count').textContent=`${result.total} document(s) · Page ${Math.floor(documentOffset/25)+1}`;
  app.querySelector('#document-prev').disabled=documentOffset===0;app.querySelector('#document-next').disabled=documentOffset+25>=result.total;
  app.querySelector('#order-section-title').textContent=`${s.label} · ${root.reference}`;
  app.querySelectorAll('[data-order-section]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.orderSection===current));b.classList.toggle('selected',b.dataset.orderSection===current)});
  app.querySelector('#order-documents').innerHTML=!s.can_read?'<p>Accès restreint à cette rubrique.</p>':!docs.length?'<p class="empty">Aucun document ne correspond à ces filtres.</p>':`<div class="table-scroll"><table><caption>Documents de ${e(root.reference)} · ${e(s.label)}</caption><thead><tr><th>Document</th><th>Type</th><th>Lancement d’origine</th><th>Date</th><th>Version</th><th>Validation</th><th>Actions</th></tr></thead><tbody>${docs.map(d=>`<tr><td>${e(d.title)}</td><td>${e(d.doc_type)}</td><td>${e(order.launches.find(l=>l.id===d.launch_id)?.name||'Pièce de commande')}</td><td>${niceDate(d.created_at)}</td><td class="numeric">${d.latest?'v'+d.latest.number:'Sans version'}</td><td>${e(approvalReport.items.find(x=>x.document_id===d.id)?.run?.status ? (APPROVAL_STATUSES[approvalReport.items.find(x=>x.document_id===d.id).run.status]||'À vérifier') : 'Sans circuit actif')}</td><td>${d.latest?`<a href="/api/documents/${e(d.id)}/versions/${d.latest.number}/download">Télécharger ${e(d.title)}</a>`:''}<button class="link" data-order-history="${e(d.id)}">Versions et historique</button>${approvalReport.items.find(x=>x.document_id===d.id)?.can_start?`<button class="secondary" data-order-approval="${e(d.id)}">Soumettre à validation</button>`:''}${approvalReport.items.find(x=>x.document_id===d.id)?.run?.can_decide?`<button class="secondary" data-order-decide="${e(d.id)}">Décider de la validation</button>`:''}${approvalReport.items.find(x=>x.document_id===d.id)?.run?.can_reopen?`<button class="secondary" data-order-reopen="${e(d.id)}">Réouvrir la validation</button>`:''}</td></tr>`).join('')}</tbody></table></div>`;
  app.querySelectorAll('[data-order-approval]').forEach(b=>b.onclick=async()=>{try{await api(`/api/documents/${b.dataset.orderApproval}/approval-runs`,{method:'POST'});await orderDossierPage(id,current);toast('Circuit de validation démarré')}catch(err){showErr(err)}});
  const decisionDialog=(docId,reopen)=>{
   const item=approvalReport.items.find(x=>x.document_id===docId),run=item.run;
   modal(reopen?'Réouvrir la validation':'Décider de la validation',`<p>${e(run.document_title)} · Version ${run.version}. ${reopen?'Une nouvelle séquence sera créée ; les décisions précédentes seront conservées et la publication sera révoquée.':'La décision concerne uniquement cette version et cette étape.'}</p><form>${reopen?'':'<label for="order-approval-choice">Décision</label><select id="order-approval-choice"><option value="approved">Approuver</option><option value="rejected">Rejeter</option><option value="changes_requested">À corriger</option></select>'}<label for="order-approval-reason">Justification</label><textarea id="order-approval-reason" minlength="12" maxlength="1800" required></textarea><button class="primary">Confirmer cette opération</button></form>`,true);
   overlay.querySelector('form').onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api(`/api/approval-runs/${run.id}/${reopen?'reopen':'decisions'}`,{method:'POST',body:JSON.stringify(reopen?{expected_version_id:run.version_id,reason:orderValue('order-approval-reason')}:{decision:orderValue('order-approval-choice'),comment:orderValue('order-approval-reason')})});closeModal();await orderDossierPage(id,current);toast('Validation mise à jour')})};
  };
  app.querySelectorAll('[data-order-decide]').forEach(b=>b.onclick=()=>decisionDialog(b.dataset.orderDecide,false));
  app.querySelectorAll('[data-order-reopen]').forEach(b=>b.onclick=()=>decisionDialog(b.dataset.orderReopen,true));
  app.querySelectorAll('[data-order-history]').forEach(b=>b.onclick=async()=>{try{
   const d=docs.find(d=>d.id===b.dataset.orderHistory);
   modal(`Historique · ${d.title}`,'<p role="status">Chargement de l’historique…</p>',true);const pendingDialog=overlay.firstElementChild;
   const history=await api(`/api/documents/${d.id}/history?limit=25`);if(!pendingDialog?.isConnected||state.orderDossier!==root)return;d.versions=history.items;
   const historyHtml=versions=>versions.map(v=>`<p>Version ${v.number} · ${niceDate(v.created_at)} · <a href="/api/documents/${e(d.id)}/versions/${v.number}/download">Télécharger ${e(v.original_name)}</a><small class="hash">SHA-256 : ${e(v.sha256)}</small><button class="link" data-document-comments="${e(v.id)}">Commentaires de la version ${v.number}</button></p>`).join('');
   pendingDialog.querySelector('.modal-body').innerHTML=`<p>Commande ${e(root.reference)} · ${e(s.label)}</p><div id="order-history-items">${historyHtml(d.versions)}</div>${history.total>25?'<button id="order-history-more" class="secondary">Versions précédentes</button>':''}${s.can_write?'<button class="secondary" id="document-classify">Classer le document</button><form id="order-version-form"><label for="order-version-file">Nouvelle version</label><input id="order-version-file" type="file" required><p>Les anciennes versions seront conservées. Une ancienne approbation ne valide pas cette version.</p><button class="primary">Enregistrer la nouvelle version</button></form>':''}`;
   const bindComments=()=>overlay.querySelectorAll('[data-document-comments]').forEach(button=>button.onclick=()=>documentCommentDialog(d,d.versions.find(v=>v.id===button.dataset.documentComments)).catch(showErr));
   bindComments();
   overlay.querySelector('#document-classify')?.addEventListener('click',()=>documentClassificationDialog(d,s.slug).catch(showErr));
   let historyOffset=25;
   overlay.querySelector('#order-history-more')?.addEventListener('click',async event=>{
    const button=event.currentTarget;button.disabled=true;
    try{const more=await api(`/api/documents/${d.id}/history?offset=${historyOffset}&limit=25`);d.versions.push(...more.items);overlay.querySelector('#order-history-items').insertAdjacentHTML('beforeend',historyHtml(more.items));historyOffset+=more.items.length;button.hidden=historyOffset>=more.total;bindComments()}
    catch(err){showErr(err)}finally{button.disabled=false}
   });
   overlay.querySelector('form')?.addEventListener('submit',event=>{event.preventDefault();orderSubmit(event.target,async()=>{const body=new FormData();body.append('file',overlay.querySelector('input').files[0]);await api(`/api/documents/${d.id}/versions`,{method:'POST',body});closeModal();await orderDossierPage(id,current);toast('Nouvelle version conservée')})});
  }catch(err){showErr(err)}});
  app.querySelector('#order-upload').innerHTML=s.can_write?`<details><summary>Déposer un document dans ${e(root.reference)} · ${e(s.label)}</summary><form id="order-document-form"><label for="order-document-title">Titre</label><input id="order-document-title" name="title" maxlength="220" required><label for="order-document-type">Type documentaire</label><input id="order-document-type" name="doc_type" maxlength="100" required><label for="order-document-origin">Lancement d’origine (facultatif)</label><select id="order-document-origin" name="launch_id"><option value="">Pièce de commande</option>${order.launches.map(l=>`<option value="${e(l.id)}">${e(l.name)}</option>`).join('')}</select><label for="order-document-file">Fichier privé (20 Mo maximum)</label><input id="order-document-file" name="file" type="file" accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.txt,.eml" required><button class="primary">Déposer dans cette rubrique</button></form></details>`:'';
  decorateOrderUpload(app.querySelector('#order-document-form'),current);
  app.querySelector('#order-document-form')?.addEventListener('submit',event=>{event.preventDefault();orderSubmit(event.target,async()=>{const body=new FormData(event.target);body.append('folder',destination);if(!body.get('launch_id'))body.delete('launch_id');await api(`/api/orders/${id}/documents`,{method:'POST',body});await orderDossierPage(id,current);toast('Document déposé et conservé')})});
 }
 app.querySelectorAll('[data-order-section]').forEach(b=>b.onclick=()=>{focusDocument=null;current=b.dataset.orderSection;documentOffset=0;renderDocuments()});
 app.querySelector('#document-prev').onclick=()=>{documentOffset=Math.max(0,documentOffset-25);renderDocuments()};app.querySelector('#document-next').onclick=()=>{documentOffset+=25;renderDocuments()};
 let documentTimer;app.querySelector('#order-origin').onchange=()=>{documentOffset=0;renderDocuments()};app.querySelector('#order-document-query').oninput=()=>{focusDocument=null;clearTimeout(documentTimer);documentTimer=setTimeout(()=>{documentOffset=0;renderDocuments()},200)};
 app.querySelectorAll('[data-order-waiver]').forEach(button=>button.addEventListener('click',()=>{
  const active=button.dataset.waiverActive!=='true';
  modal(active?'Justifier une dérogation':'Retirer la dérogation',`<form><p>La dérogation concerne uniquement cette obligation et ne crée aucun document. Elle reste historisée.</p>${active?'<label>Justification <textarea id="order-waiver-reason" required minlength="12" maxlength="2000"></textarea></label>':'<p>Cette obligation sera réévaluée avec les pièces et décisions actuelles.</p>'}<button class="primary">${active?'Enregistrer la dérogation':'Retirer la dérogation'}</button></form>`,true);
  overlay.querySelector('form').onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api(`/api/orders/${id}/completeness/rules/${button.dataset.orderWaiver}/exception`,{method:'PUT',body:JSON.stringify({active,reason:active?orderValue('order-waiver-reason'):'',launch_id:button.dataset.waiverLaunch||null})});closeModal();await orderDossierPage(id,current)})};
 }));
 app.querySelector('#order-completeness-configure')?.addEventListener('click',async()=>{try{
  const profiles=await api('/api/completeness/profiles');
  modal('Configurer la complétude de la commande',`<form><label for="order-profile">Profil documentaire</label><select id="order-profile"><option value="">Aucun profil</option>${profiles.map(p=>`<option value="${e(p.id)}" ${p.id===coverage.profile_id?'selected':''}>${e(p.name)}</option>`).join('')}</select><label for="order-phase">Phase de la commande</label><select id="order-phase">${state.completenessPhases.map(p=>`<option value="${p.code}" ${p.code===coverage.phase?'selected':''}>${e(p.label)}</option>`).join('')}</select><label for="order-type">Type de commande (facultatif)</label><input id="order-type" value="${e(coverage.order_type)}" maxlength="100"><p>Une exigence de commande vérifie une pièce commune. Une exigence de lancement vérifie sa pièce d’origine ; les dérogations historiques restent limitées à leur lancement. La portée et l’événement des délais se configurent dans Conditions de complétude.</p><button class="primary">Enregistrer ce contexte</button></form>`,true);
  overlay.querySelector('form').onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api(`/api/orders/${id}/completeness/context`,{method:'PUT',body:JSON.stringify({profile_id:orderValue('order-profile')||null,phase:orderValue('order-phase'),order_type:orderValue('order-type')})});closeModal();await orderDossierPage(id,current)})};
 }catch(err){showErr(err)}});
 app.querySelector('#order-member-grant')?.addEventListener('click',async()=>{try{
  const [users,members]=await Promise.all([api('/api/admin/users'),api(`/api/orders/${id}/members`)]);
  const permissions=members.map(member=>`<li>${e(member.name)} · ${e(member.email)} ${member.independent_access?'(accès propre conservé)':''} <button type="button" data-revoke-member="${e(member.id)}">Retirer l’habilitation</button></li>`).join('');
  modal('Habiliter un collaborateur',`<h3>Habilitations explicites</h3><ul>${permissions||'<li>Aucune</li>'}</ul><form><label for="order-member">Collaborateur</label><select id="order-member">${users.filter(u=>u.active).map(u=>`<option value="${e(u.id)}">${e(u.name)}</option>`).join('')}</select><label for="order-member-reason">Motif de l’habilitation</label><textarea id="order-member-reason" required minlength="12" maxlength="1500"></textarea><p>Cette habilitation permet la consultation des commandes sans lancement, selon les droits de rubrique du collaborateur. Pour une commande avec lancements, les restrictions historiques de chaque lancement restent obligatoires.</p><button class="primary">Confirmer cette habilitation</button></form>`,true);
  overlay.querySelectorAll('[data-revoke-member]').forEach(button=>button.onclick=async()=>{
   if(!confirm('Retirer cette habilitation explicite ?'))return;
   button.disabled=true;
   try{const result=await api(`/api/orders/${id}/members/${button.dataset.revokeMember}`,{method:'DELETE'});
       closeModal();toast(result.effective_access?'Habilitation retirée. Accès propre conservé.':'Habilitation retirée');}
   catch(error){button.disabled=false;showErr(error)}
  });
  overlay.querySelector('form').onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api(`/api/orders/${id}/members`,{method:'POST',body:JSON.stringify({user_id:orderValue('order-member'),reason:orderValue('order-member-reason')})});closeModal();toast('Habilitation enregistrée')})};
 }catch(err){showErr(err)}});
 app.querySelector('#order-launch-create')?.addEventListener('click',()=>{
  modal(`Ajouter un lancement · ${root.reference}`,`<form><label for="order-launch-name">Nom du lancement</label><input id="order-launch-name" required minlength="2" maxlength="180"><p>Ce lancement partagera le Dossier Jaune de ${e(root.reference)}.</p><button class="primary">Créer le lancement</button></form>`);
  overlay.querySelector('form').onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api('/api/launches',{method:'POST',body:JSON.stringify({name:orderValue('order-launch-name'),order_id:id})});closeModal();await orderDossierPage(id,current)})};
 });
 app.querySelector('#order-launch-link')?.addEventListener('click',async()=>{try{
  modal('Rattacher un lancement historique',`<form><label for="order-historical-query">Rechercher un lancement historique</label><input id="order-historical-query" type="search" maxlength="200" placeholder="Nom, client, commande ou ORLI"><label for="order-historical-launch">Lancement</label><select id="order-historical-launch" required disabled></select><p id="order-historical-status" role="status">Chargement…</p><button type="button" id="order-historical-prev" disabled>Précédents</button><button type="button" id="order-historical-next" disabled>Suivants</button><p>Ses documents rejoindront les rubriques de ${e(root.reference)} sans perte de versions. Les références et le client seront contrôlés par le serveur. Ce rattachement ne sera pas détachable implicitement si le lancement porte des documents.</p><label><input type="checkbox" required> J’ai vérifié la commande et les conséquences de ce rattachement.</label><button class="primary" disabled>Confirmer le rattachement</button></form>`,true);
  const form=overlay.querySelector('form'),select=form.querySelector('#order-historical-launch'),status=form.querySelector('#order-historical-status'),previous=form.querySelector('#order-historical-prev'),next=form.querySelector('#order-historical-next'),submit=form.querySelector('.primary');let offset=0,sequence=0,timer;
  const load=async(requestOffset=0)=>{
   const request=++sequence;select.disabled=true;previous.disabled=true;next.disabled=true;submit.disabled=true;status.textContent='Recherche des lancements…';
   try{const report=await api('/api/launches?'+new URLSearchParams({page:'true',q:form.querySelector('#order-historical-query').value,offset:String(requestOffset),limit:'100'}));if(request!==sequence||!form.isConnected)return;offset=requestOffset;select.innerHTML=report.items.map(l=>`<option value="${e(l.id)}">${e(l.name)} · ${e(l.client_name||'Client non renseigné')} · ${e(l.order_ref||'Sans référence')}</option>`).join('');select.disabled=!report.items.length;submit.disabled=!report.items.length;previous.disabled=offset===0;next.disabled=offset+report.items.length>=report.total;status.textContent=`${report.total} lancement(s) autorisé(s) · Page ${Math.floor(offset/100)+1}`;}
   catch(error){if(request!==sequence||!form.isConnected)return;select.replaceChildren();status.textContent=error.message||'Recherche impossible. Modifiez la recherche pour réessayer.';}
  };
  form.querySelector('#order-historical-query').oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>load(0),200)};previous.onclick=()=>load(Math.max(0,offset-100));next.onclick=()=>load(offset+100);
  form.onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api(`/api/orders/${id}/launches`,{method:'POST',body:JSON.stringify({launch_id:select.value})});closeModal();await orderDossierPage(id,current)})};
  await load();
 }catch(err){showErr(err)}});
 await renderDocuments();
}

async function directoryPage(kind){
 state.view=kind==='supplier'?'suppliers':'clients';const label=kind==='supplier'?'Fournisseurs':'Clients';let pageOffset=0;let requestNumber=0;let timer;
 mount(`<div class="page-heading"><h1>${label}</h1></div><section class="panel order-panel"><label for="directory-query">Rechercher ${kind==='supplier'?'un fournisseur':'un client'}</label><input id="directory-query" type="search" maxlength="150"><p id="directory-page-status" role="status"></p><div id="directory-results"></div><div id="directory-pager"></div>${state.me.admin?'<p><a href="/partners">Administrer les organisations, les contacts et les accès</a></p>':''}</section>`,label);
 async function load(offset=0){
  const sequence=++requestNumber;const term=orderValue('directory-query');app.querySelector('#directory-page-status').textContent='Chargement…';
  const report=await api(`/api/directory/${kind}?page=true&limit=25&offset=${offset}&q=${encodeURIComponent(term)}`);if(sequence!==requestNumber||state.view!==(kind==='supplier'?'suppliers':'clients'))return;pageOffset=offset;
  app.querySelector('#directory-page-status').textContent=`${report.total} organisation(s) autorisée(s) · ${report.items.length?offset+1:0} à ${offset+report.items.length}`;
  app.querySelector('#directory-results').innerHTML=report.items.map(r=>`<article><h2>${e(r.name)}</h2><p>${r.active?'Actif':'Suspendu'}</p>${r.orders.map(o=>`<p><button class="link" data-directory-order="${e(o.id)}">Commande ${e(o.reference)} · Ouvrir le Dossier Jaune</button></p>`).join('')}${r.requests.map(q=>`<p>${e(q.order_ref)} · ${e(q.title)} · ${e({requested:'Document attendu',pending:'Vérification en attente',approved:'Approuvé',rejected:'À corriger',closed:'Terminé'}[q.status]||q.status)} · ${q.due_date?niceDate(q.due_date):'Sans échéance'} <button class="link" data-directory-launch="${e(q.launch_id)}">Ouvrir le lancement associé</button></p>`).join('')}${r.orders_total>r.orders.length||r.requests_total>r.requests.length?'<p>Les dix éléments récents sont affichés. Retrouvez les autres dans les commandes ou l’espace partenaires.</p>':''}</article>`).join('')||'<p class="empty">Aucun résultat autorisé.</p>';
  app.querySelector('#directory-pager').innerHTML=`<button id="directory-prev" ${offset?'':'disabled'}>Précédents</button><button id="directory-next" ${offset+report.items.length<report.total?'':'disabled'}>Suivants</button>`;
  app.querySelector('#directory-prev').onclick=()=>load(Math.max(0,pageOffset-25)).catch(showErr);app.querySelector('#directory-next').onclick=()=>load(pageOffset+25).catch(showErr);
  app.querySelectorAll('[data-directory-order]').forEach(b=>b.onclick=()=>orderDossierPage(b.dataset.directoryOrder).catch(showErr));
  app.querySelectorAll('[data-directory-launch]').forEach(b=>b.onclick=()=>openLaunch(b.dataset.directoryLaunch).catch(showErr));
 }
 app.querySelector('#directory-query').oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>load().catch(showErr),250);};await load();
}
async function receiptsPage(offset=0){
 const report=await api(`/api/receipts?page=true&limit=25&offset=${offset}`);const rows=report.items;state.view='receipts';
 mount(`<div class="page-heading"><h1>Réceptions</h1></div><section class="panel order-panel"><p>Réceptions enregistrées avec leurs sources. Une déclaration fournisseur ne constitue pas une réception validée.</p>${rows.length?`<div class="table-scroll"><table><caption>Suivi des réceptions autorisées</caption><thead><tr><th>Commande</th><th>Matière</th><th class="numeric">Commandé</th><th class="numeric">Reçu</th><th class="numeric">Restant</th><th>Action</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${e(r.order_ref)}</td><td>${e(r.material_ref)}</td><td class="numeric">${e(r.ordered)} ${e(r.unit)}</td><td class="numeric">${e(r.received)} ${e(r.unit)}</td><td class="numeric">${e(r.remaining)} ${e(r.unit)}</td><td><button class="link" data-receipt-id="${e(r.id)}">Ouvrir les pièces de réception</button></td></tr>`).join('')}</tbody></table></div>`:'<p class="empty">Aucune réception autorisée.</p>'}<p>${report.total} ligne(s) autorisée(s)</p><button id="receipts-prev" ${offset?'':'disabled'}>Précédentes</button><button id="receipts-next" ${offset+rows.length<report.total?'':'disabled'}>Suivantes</button>${can('receipt.write')?'<a href="/partners">Enregistrer une réception à partir d’une pièce fournisseur</a>':''}</section>`,'Réceptions');
 app.querySelector('#receipts-prev').onclick=()=>receiptsPage(Math.max(0,offset-25)).catch(showErr);app.querySelector('#receipts-next').onclick=()=>receiptsPage(offset+25).catch(showErr);
 app.querySelectorAll('[data-receipt-id]').forEach(b=>b.onclick=()=>{const row=rows.find(r=>r.id===b.dataset.receiptId);(row.order_id?orderDossierPage(row.order_id,'rose'):openLaunch(row.launch_id,'rose')).catch(showErr)});
}

async function validationsPage(offset=0){
 const report=await api(`/api/validation-queue?limit=25&offset=${offset}`);state.view='validations';
 mount(`<div class="page-heading"><h1>Validations</h1><p>${report.pending} circuit(s) en attente parmi vos documents autorisés.</p></div><section class="panel order-panel">${report.items.length?`<div class="table-scroll"><table><caption>Circuits des versions courantes</caption><thead><tr><th>Document</th><th>Rubrique</th><th>Version</th><th>État</th><th>Action</th></tr></thead><tbody>${report.items.map(r=>`<tr><td>${e(r.document_title)}</td><td>${e(r.folder)}</td><td class="numeric">v${r.version} · séquence ${r.cycle}</td><td>${e(APPROVAL_STATUSES[r.status]||r.status)}</td><td><button class="secondary" data-validation-index="${e(r.id)}">${r.can_decide?'Examiner et décider':'Consulter le circuit'}</button></td></tr>`).join('')}</tbody></table></div>`:'<p class="empty">Aucun circuit de validation accessible.</p>'}<p>${report.total} circuit(s) autorisé(s)</p><button id="validations-prev" ${offset?'':'disabled'}>Précédents</button><button id="validations-next" ${offset+report.items.length<report.total?'':'disabled'}>Suivants</button></section>`,'Validations');
 app.querySelector('#validations-prev').onclick=()=>validationsPage(Math.max(0,offset-25)).catch(showErr);app.querySelector('#validations-next').onclick=()=>validationsPage(offset+25).catch(showErr);
 app.querySelectorAll('[data-validation-index]').forEach(b=>b.onclick=async()=>{
  const row=report.items.find(item=>item.id===b.dataset.validationIndex);
  try{
   if(row.order_id){
    await orderDossierPage(row.order_id,row.folder,row.document_id);
    app.querySelector(`[data-order-decide="${CSS.escape(row.document_id)}"]`)?.focus();
   }else{
    await openLaunch(row.launch_id,row.folder);
    const item=app.querySelector(`[data-approval-run="${CSS.escape(row.id)}"]`);
    if(item){item.scrollIntoView({block:'center'});item.focus()}
   }
  }catch(error){showErr(error)}
 });
}
