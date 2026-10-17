/* Portée des lancements, module 0.15 : actions strictement administrateur. */
'use strict';
(function(){
  function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  async function openAccess(){
    if(!state.me?.admin||!state.detail?.id)return;
    const id=state.detail.id;
    try{
      const [data,users]=await Promise.all([api(`/api/launches/${id}/access`),api('/api/admin/users')]);
      const selected=new Set(data.members.map(x=>x.user_id));
      const eligibles=users.filter(x=>x.active&&x.id!==data.creator_id&&!selected.has(x.id));
      modal('Accès au lancement',`<div class="field"><label>Visibilité</label><p>${data.restricted?'Restreint aux membres et au créateur':'Ouvert selon les autorisations globales par rôle'}</p></div>
        <div class="modal-actions"><button class="secondary" id="toggle-scope">${data.restricted?'Retirer la restriction':'Activer la restriction'}</button></div>
        <div class="field"><label>Collaborateurs explicitement autorisés</label><p>Le créateur conserve son accès. Les droits sur les sous-dossiers restent contrôlés par rôle.</p>
        <div>${data.members.map(m=>`<div class="row" style="display:flex;justify-content:space-between;gap:8px;margin:8px 0"><span>${escapeHtml(m.name)}</span><button class="secondary tiny" data-remove-member="${escapeHtml(m.user_id)}">Retirer</button></div>`).join('')||'<p>Aucun membre ajouté.</p>'}</div></div>
        ${eligibles.length?`<div class="field"><label>Ajouter un collaborateur</label><select id="add-scope-user">${eligibles.map(x=>`<option value="${escapeHtml(x.id)}">${escapeHtml(x.name)}</option>`).join('')}</select><button class="primary" id="add-scope-member" style="margin-top:10px">Autoriser</button></div>`:''}
        <p class="small">Le mode restreint masque ce dossier dans les recherches, tableaux de bord et accès directs aux fichiers pour les non-membres.</p>`);
      overlay.querySelector('#toggle-scope').onclick=async()=>{try{await api(`/api/launches/${id}/access`,{method:'PUT',body:JSON.stringify({restricted:!data.restricted})});closeModal();toast('Portée mise à jour');await openAccess();}catch(err){showErr(err)}};
      overlay.querySelector('#add-scope-member')?.addEventListener('click',async()=>{try{await api(`/api/launches/${id}/access/members`,{method:'POST',body:JSON.stringify({user_id:overlay.querySelector('#add-scope-user').value})});closeModal();await openAccess();}catch(err){showErr(err)}});
      overlay.querySelectorAll('[data-remove-member]').forEach(el=>el.onclick=async()=>{try{await api(`/api/launches/${id}/access/members/${el.dataset.removeMember}`,{method:'DELETE'});closeModal();await openAccess();}catch(err){showErr(err)}});
    }catch(err){showErr(err)}
  }
  function inject(){
    if(!state?.me?.admin||state.view!=='detail'||!state.detail?.id||document.querySelector('#manage-launch-access'))return;
    const header=document.querySelector('.page-heading');
    if(!header)return;
    const btn=document.createElement('button');btn.id='manage-launch-access';btn.className='secondary tiny';btn.textContent='Gérer les accès';btn.addEventListener('click',openAccess);header.appendChild(btn);
  }
  new MutationObserver(inject).observe(document.querySelector('#app'),{childList:true,subtree:true});
})();
