'use strict';
// Optional identification and comments reuse the existing API, dialogs and roles.
function identificationField(field,values){
 const value=values[field.key]??'',id='identification-'+field.key;
 const attrs=`id="${e(id)}" name="${e(field.key)}"${field.max_length?` maxlength="${field.max_length}"`:''}${field.min!==undefined?` min="${field.min}"`:''}${field.step?` step="${field.step}"`:''}`;
 return `<label for="${e(id)}">${e(field.label)}</label>${field.type==='textarea'?`<textarea ${attrs}>${e(value)}</textarea>`:`<input ${attrs} type="${e(field.type)}" value="${e(value)}">`}`;
}
async function identificationDialog(kind,id){
 const url=`/api/${kind==='order'?'orders':'launches'}/${encodeURIComponent(id)}/identification`;
 const data=await api(url);
 const label=kind==='order'?'Fiche d’identification de la commande':'Fiche d’identification du lancement';
 modal(label,`<p>${e(data.canonical.reference||data.canonical.name||'')} · ${e(data.canonical.client||'Client non renseigné')}${data.canonical.orli_ref?` · ORLI ${e(data.canonical.orli_ref)}`:''}</p><p>Les informations sont facultatives et évolutives. ${kind==='order'?'Les ateliers et références ORLI se renseignent pour chaque lancement.':'Les informations de ce lancement complètent la fiche commune de la commande.'}</p><form id="identification-form"><fieldset ${data.can_write?'':'disabled'}>${data.fields.map(f=>identificationField(f,data.values)).join('')}</fieldset><p id="identification-error" class="error" role="alert" hidden></p>${data.can_write?'<button class="primary">Enregistrer la fiche</button>':''}</form>`,true);
 overlay.querySelector('form').onsubmit=async event=>{
  event.preventDefault();const form=event.target,button=form.querySelector('button');if(!button||button.disabled)return;
  button.disabled=true;const values={};
  for(const field of data.fields){const raw=form.elements.namedItem(field.key).value.trim();values[field.key]=raw||null}
  try{await api(url,{method:'PATCH',body:JSON.stringify({expected_revision:data.revision,values})});closeModal();toast('Fiche enregistrée, historique conservé')}
  catch(err){const error=form.querySelector('[role="alert"]');error.textContent=err.message;error.hidden=false;button.disabled=false}
 };
}
function mountOrderIdentification(id,order){
 const heading=app.querySelector('.page-heading');if(!heading)return;
 const button=document.createElement('button');button.className='secondary';button.textContent='Fiche d’identification';
 button.onclick=()=>identificationDialog('order',id).catch(showErr);heading.append(button);
 app.querySelectorAll('[data-linked-launch]').forEach(link=>{
  const button=document.createElement('button');button.className='link';button.textContent='Fiche du lancement';
  button.setAttribute('aria-label',`Fiche d’identification de ${order.launches.find(l=>l.id===link.dataset.linkedLaunch)?.name||'ce lancement'}`);
  button.onclick=()=>identificationDialog('launch',link.dataset.linkedLaunch).catch(showErr);link.parentElement.append(button);
 });
}
const documentTypeCatalogues=new Map();
async function documentTypeOptions(folder){
 if(!documentTypeCatalogues.has(folder))documentTypeCatalogues.set(folder,api('/api/document-types?folder='+encodeURIComponent(folder)).then(r=>r.items).catch(error=>{documentTypeCatalogues.delete(folder);throw error}));
 return documentTypeCatalogues.get(folder);
}
async function decorateOrderUpload(form,folder){
 if(!form)return;
 const input=form.querySelector('[name="doc_type"]');if(!input)return;
 input.disabled=true;
 try{
  const items=await documentTypeOptions(folder);if(!input.isConnected)return;
  const select=document.createElement('select');select.id=input.id;select.name=input.name;select.required=true;
  select.innerHTML=items.map(row=>`<option value="${e(row.label)}" ${row.id==='unclassified'?'selected':''}>${e(row.label)}</option>`).join('');input.replaceWith(select);
  const note=document.createElement('p');note.textContent='Choisissez un type de cette rubrique. « À classer » conserve le document et signale le classement à reprendre.';select.after(note);
 }catch(err){if(input.isConnected){input.disabled=false;const note=document.createElement('p');note.className='error';note.setAttribute('role','alert');note.textContent='Référentiel indisponible : le type saisi sera conservé et devra être vérifié.';input.after(note)}}
}
async function documentClassificationDialog(doc,folder){
 const items=await documentTypeOptions(folder);
 modal('Classer le document',`<p>${e(doc.title)} · Type enregistré : ${e(doc.doc_type)}. L’ancien libellé et les décisions restent conservés.</p><form><label for="classification-type">Type de cette rubrique</label><select id="classification-type">${items.map(row=>`<option value="${e(row.id)}" ${row.id===doc.classification?.id?'selected':''}>${e(row.label)}</option>`).join('')}</select><button class="primary">Confirmer le classement</button></form>`);
 overlay.querySelector('form').onsubmit=event=>{event.preventDefault();orderSubmit(event.target,async()=>{await api(`/api/documents/${encodeURIComponent(doc.id)}/classification`,{method:'PATCH',body:JSON.stringify({type_id:document.getElementById('classification-type').value,expected_label:doc.doc_type})});closeModal();await orderDossierPage(state.orderDossier.order_id,folder);toast('Classement enregistré')})};
}
async function documentCommentDialog(doc,version,offset=0){
 const url=`/api/document-versions/${encodeURIComponent(version.id)}/comments`;
 const data=await api(url+`?offset=${offset}&limit=25`);
 modal(`Commentaires · ${doc.title} · v${version.number}`,`<p>Commentaires internes sur cette version. Une demande de correction ou une décision s’enregistre dans le circuit de validation.</p><div>${data.items.map(row=>`<article><p><strong>${e(row.author)}</strong> · ${niceDate(row.created_at)}</p><p style="white-space:pre-wrap">${e(row.text)}</p></article>`).join('')||'<p>Aucun commentaire pour cette version.</p>'}</div><nav aria-label="Pagination des commentaires"><button id="comment-prev" ${offset===0?'disabled':''}>Précédent</button><span role="status">${data.total} commentaire(s) · Page ${Math.floor(offset/25)+1}</span><button id="comment-next" ${offset+25>=data.total?'disabled':''}>Suivant</button></nav>${data.can_write?'<form id="document-comment-form"><label for="document-comment-text">Commentaire interne</label><textarea id="document-comment-text" required maxlength="4000"></textarea><p id="document-comment-error" class="error" role="alert" hidden></p><button class="primary">Enregistrer sur cette version</button></form>':''}`,true);
 overlay.querySelector('#comment-prev').onclick=()=>documentCommentDialog(doc,version,Math.max(0,offset-25)).catch(showErr);
 overlay.querySelector('#comment-next').onclick=()=>documentCommentDialog(doc,version,offset+25).catch(showErr);
 overlay.querySelector('form')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.target,text=form.querySelector('textarea').value.trim(),button=form.querySelector('button');if(!text||button.disabled)return;button.disabled=true;
  try{await api(url,{method:'POST',body:JSON.stringify({text})});await documentCommentDialog(doc,version,Math.floor(data.total/25)*25);toast('Commentaire conservé sur cette version')}
  catch(err){if(form.isConnected){form.querySelector('[role="alert"]').textContent=err.message;form.querySelector('[role="alert"]').hidden=false;button.disabled=false}}
 });
}
