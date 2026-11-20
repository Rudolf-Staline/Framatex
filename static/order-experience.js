'use strict';

const experienceStatuses={ouvert:'Ouvert',en_cours:'En cours',resolu:'Résolu'};

async function experiencePage(scope=null){
 const navigation=++navigationVersion;
 state.view='experience';
 mount(`<div class="page-heading"><div><h1>Mémoire métier</h1><p>Retours d’expérience des commandes auxquelles vous avez accès.</p></div><button class="primary" id="experience-new" hidden>${icon('plus')} Nouveau retour</button></div>
  ${scope?`<p><button type="button" class="link" id="experience-back">${icon('back')} Dossier ${e(scope.reference)}</button> <button type="button" class="link" id="experience-all">Toutes les commandes</button></p>`:''}
  <form class="panel atelier-experience-search" id="experience-search">
   <label>Rechercher un problème, une solution ou une commande <input name="q" type="search" maxlength="180"></label>
   <label>Statut <select name="status"><option value="">Tous</option>${Object.entries(experienceStatuses).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select></label>
   <button class="secondary">Rechercher</button>
  </form>
  <p id="experience-status" role="status"></p><div id="experience-results" class="atelier-experience-list"></div>
  <nav class="order-pagination" aria-label="Pagination des retours"><button type="button" id="experience-prev" disabled>Précédent</button><button type="button" id="experience-next" disabled>Suivant</button></nav>`,'Mémoire métier');
 const form=app.querySelector('#experience-search');
 const notice=app.querySelector('#experience-status');
 const results=app.querySelector('#experience-results');
 const create=app.querySelector('#experience-new');
 const previous=app.querySelector('#experience-prev');
 const next=app.querySelector('#experience-next');
 let request=0,offset=0,pageSize=15;
 async function load(start=0){
  const current=++request;
  const params=new URLSearchParams(new FormData(form));
  if(!params.get('status'))params.delete('status');
  if(scope)params.set('order_id',scope.id);
  params.set('offset',start);
  previous.disabled=next.disabled=true;
  notice.textContent='Chargement des retours…';
  try{
   const data=await api('/api/order-experience?'+params);
   if(navigation!==navigationVersion||current!==request)return;
   offset=start;pageSize=data.limit;
   notice.textContent=data.total?`${data.total} retour(s) · Page ${Math.floor(start/pageSize)+1}`:'Aucun retour ne correspond à cette recherche.';
   previous.disabled=start===0;next.disabled=start+pageSize>=data.total;
   create.hidden=!data.writable_folders.length;
   create.onclick=()=>experienceEditor({scope,folders:data.writable_folders,onSaved:()=>load(0)});
   results.innerHTML=data.items.map(row=>`<article class="panel atelier-experience-card"><div class="atelier-experience-card-head"><div><p class="small muted">${e(row.reference)} · ${e(row.folder)} · ${niceDate(row.updated_at)}</p><h2>${e(row.title)}</h2></div><span class="tag ${row.status==='resolu'?'green':'orange'}">${experienceStatuses[row.status]}</span></div>
    <p class="atelier-experience-text">${e(row.problem)}</p>
    ${row.solution?`<h3>Solution</h3><p class="atelier-experience-text">${e(row.solution)}</p>`:''}
    ${row.lesson?`<h3>Enseignement</h3><p class="atelier-experience-text">${e(row.lesson)}</p>`:''}
    <button class="link" type="button" data-experience-order="${e(row.order_id)}" data-folder-slug="${e(row.folder)}">Ouvrir le dossier</button>
    ${row.can_edit?`<button class="secondary tiny" type="button" data-experience-edit="${e(row.id)}">Modifier</button>`:''}</article>`).join('');
   for(const button of results.querySelectorAll('[data-experience-order]')){
    button.onclick=()=>orderDossierPage(button.dataset.experienceOrder,button.dataset.folderSlug).catch(showErr);
   }
   for(const button of results.querySelectorAll('[data-experience-edit]')){
    button.onclick=()=>experienceEditor({row:data.items.find(item=>item.id===button.dataset.experienceEdit),onSaved:()=>load(offset)});
   }
  }catch(err){
   if(navigation!==navigationVersion||current!==request)return;
   notice.textContent=err.message;
   results.replaceChildren();
   create.hidden=true;
  }
 }
 form.onsubmit=event=>{event.preventDefault();load(0)};
 previous.onclick=()=>load(Math.max(0,offset-pageSize));next.onclick=()=>load(offset+pageSize);
 app.querySelector('#experience-back')?.addEventListener('click',()=>orderDossierPage(scope.id,scope.folder,null,'tools').catch(showErr));
 app.querySelector('#experience-all')?.addEventListener('click',()=>experiencePage().catch(showErr));
 await load();
}

function experienceEditor({scope,folders,row,onSaved}){
 modal(row?'Modifier le retour':'Nouveau retour d’expérience',`<form class="atelier-experience-editor">
  ${row||scope?'':`<label for="experience-order">Commande</label><select id="experience-order" name="order_id" required></select>`}
  ${row?'':`<label for="experience-folder">Sous-dossier</label><select id="experience-folder" name="folder" required>${folders.map(folder=>`<option value="${folder}" ${folder===scope?.folder?'selected':''}>${folder[0].toUpperCase()+folder.slice(1)}</option>`).join('')}</select>`}
  <label for="experience-title">Titre</label><input id="experience-title" name="title" minlength="3" maxlength="180" value="${e(row?.title||'')}" required>
  <label for="experience-problem">Problème observé</label><textarea id="experience-problem" name="problem" minlength="12" maxlength="8000" rows="4" required>${e(row?.problem||'')}</textarea>
  <label for="experience-solution">Solution</label><textarea id="experience-solution" name="solution" maxlength="6000" rows="3">${e(row?.solution||'')}</textarea>
  <label for="experience-lesson">Enseignement pour la suite</label><textarea id="experience-lesson" name="lesson" maxlength="4000" rows="3">${e(row?.lesson||'')}</textarea>
  <label for="experience-state">Statut</label><select id="experience-state" name="status">${Object.entries(experienceStatuses).map(([key,label])=>`<option value="${key}" ${key===row?.status?'selected':''}>${label}</option>`).join('')}</select>
  <button class="primary">Enregistrer le retour</button></form>`);
 const form=overlay.querySelector('form');
 const order=overlay.querySelector('#experience-order');
 if(order)pagedSelect(order,'/api/orders','Choisir une commande',item=>`${item.reference} · ${item.client_name}`);
 form.onsubmit=event=>{
  event.preventDefault();
  orderSubmit(form,async()=>{
   const payload=Object.fromEntries(new FormData(form));
   if(row)payload.revision=row.revision;
   else if(scope)payload.order_id=scope.id;
   await api('/api/order-experience'+(row?'/'+encodeURIComponent(row.id):''),{method:row?'PATCH':'POST',body:JSON.stringify(payload)});
   closeModal();toast('Retour enregistré');await onSaved();
  });
 };
}
