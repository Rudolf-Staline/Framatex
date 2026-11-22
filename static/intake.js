'use strict';
// 0.5 — deux innovations complémentaires. Chaque suggestion reste révocable et vérifiée.
function renderIntake(){
 const docs=(state.detail?.folders||[]).filter(f=>f.can_read).flatMap(f=>f.documents);
 const editable=(state.detail?.folders||[]).some(f=>f.can_write);
 return `<section class="intake-section" aria-label="Lecture et classement assistés"><div class="section-heading workflow-head"><div><h2>Lecture et classement assistés</h2><small>OCR et extraction structurée · suggestions documentaires à confirmer</small></div></div><div class="panel intake-panel"><div><h3>Importer sans ressaisie inutile</h3><p>Analyse locale du fichier : propositions de classement, références, quantités, dates et montants. Aucun classement ni aucune valeur n'est enregistré sans confirmation.</p>${editable?`<button class="primary tiny" id="intake-open">Analyser un document</button>`:'<span class="tag">Dépôt non autorisé</span>'}</div><div><h3>Documents déjà enregistrés</h3>${docs.length?`<div class="intake-docs">${docs.slice(0,20).map(d=>`<button class="secondary tiny" data-intake-version="${e(d.latest.id)}">${e(d.title)} · v${d.latest.number}</button>`).join('')}</div>`:'<p>Aucune pièce accessible.</p>'}<p class="workflow-help">Les résultats de l’analyse n’équivalent pas à une validation métier. L’original reste la référence.</p></div></div></section>`;
}
function bindIntake(){
 app.querySelector('#intake-open')?.addEventListener('click',intakeOpen);
 app.querySelectorAll('[data-intake-version]').forEach(x=>x.addEventListener('click',()=>intakeExisting(x.dataset.intakeVersion)));
}
function renderCandidates(items){
 if(!items?.length)return `<p class="workflow-help">Aucun champ structuré détecté.</p>`;
 const source=x=>[x.page?`page ${x.page}`:'',x.sheet?`feuille ${x.sheet}`:'',x.cell?`cellule ${x.cell}`:'',x.paragraph?`paragraphe ${x.paragraph}`:''].filter(Boolean).join(' · ');
 return `<div class="intake-candidates">${items.map(x=>`<div class="intake-candidate"><strong>${e(x.key.replaceAll('_',' '))}</strong><span>${e(x.value)} ${e(x.unit||'')}</span><small>${e(source(x))}${source(x)?' · ':''}${e(x.source_excerpt||'')}</small></div>`).join('')}</div>`;
}
function intakeOpen() {
  return dossierUpload({folder: state.folder}).catch(showErr);
}
async function intakeExisting(versionId) {
  try {
    const launchId = state.detail.id;
    const folder = state.folder;
    const endpoint = '/api/document-versions/' + encodeURIComponent(versionId);
    const data = await api(endpoint + '/intake');
    const doc = state.detail.folders.flatMap(item => item.documents || []).find(item => item.versions.some(v => v.id === versionId));
    const folderAccess = state.detail?.folders?.find(folder => folder.slug === doc?.folder);
    const editable = doc && doc.latest.id === versionId && !!folderAccess?.can_value;
    const review = editable && ['to_verify', 'incompatible'].includes(data.identification?.status);
    const pending = data.fields.filter(field => !data.confirmed.some(item => item.key === field.key));
    const reached = data.classification.suggestions;
    const labels = {quantite: 'Quantité', quantite_commandee: 'Quantité commandée', quantite_produite: 'Quantité produite',
      quantite_livree: 'Quantité livrée', reference_commande: 'Référence de commande', reference_article: 'Référence article',
      reference_client: 'Référence client', consommation_matiere: 'Consommation matière', besoin_matiere: 'Besoin matière',
      prix_unitaire: 'Prix unitaire', prix_total: 'Prix total hors taxes', montant_total: 'Montant total'};
    const label = key => labels[key] || key.replaceAll('_', ' ');
    modal('Identification et valeurs documentaires', `<p class="modal-desc">${e(DOCUMENT_METHODS[data.method] || 'Vérification manuelle')}. Les valeurs explicitement confirmées peuvent alimenter les comparaisons sur cette version.</p>
      ${data.warnings.length ? `<p class="permission-lock">${e(data.warnings.join(' · '))}</p>` : ''}
      ${data.identification ? `<p><strong>${e(({matched: 'Type reconnu', confirmed: 'Type confirmé', incompatible: 'Type documentaire incompatible', to_verify: 'Déposé — à vérifier'})[data.identification.status])}</strong>${data.identification.justification ? ' · ' + e(data.identification.justification) : ''}</p>` : ''}
      ${reached.length ? `<ul>${reached.map(item => `<li><strong>${e(item.doc_type)}</strong> · ${e(item.reason)}</li>`).join('')}</ul>` : ''}
      ${review ? '<form id="du-review-type"><div class="field"><label for="du-review-note">Justifier le type après lecture du document</label><textarea id="du-review-note" required minlength="12" maxlength="1800" rows="2"></textarea></div><button class="primary tiny" type="submit">Confirmer le type</button></form>' : ''}
      <div class="field"><label for="du-source-text">Extrait du document</label><textarea id="du-source-text" readonly rows="4">${e(data.text_excerpt)}</textarea></div>
      <h3>Champs à vérifier</h3>
      ${pending.map(x => `<div class="intake-field-row"><div class="workflow-meta"><strong>${e(label(x.key))}</strong> · ${e([x.page&&'page '+x.page,x.sheet&&'feuille '+x.sheet,x.cell&&'cellule '+x.cell,x.paragraph&&'paragraphe '+x.paragraph].filter(Boolean).join(' · '))}${e(x.source_excerpt ? ' · '+x.source_excerpt : '')}${x.status === 'ambiguous' ? '<br>Plusieurs valeurs trouvées. Relevez la valeur dans la source.' : ''}</div>
        ${editable ? `<input aria-label="Valeur de ${e(label(x.key))}" id="if-${e(x.key)}" value="${x.status === 'ambiguous' ? '' : e(x.value)}" maxlength="140">
        <input aria-label="Unité de ${e(label(x.key))}" id="iu-${e(x.key)}" value="${x.status === 'ambiguous' ? '' : e(x.unit)}" maxlength="30" placeholder="Unité">
        <button class="secondary tiny" data-intake-confirm="${e(x.key)}">Valider la valeur</button>` : `<span>${e(x.value)} ${e(x.unit)}</span>`}</div>`).join('') || '<p>Aucun champ proposé.</p>'}
      <h3>Champs confirmés</h3>${data.confirmed.map(x => `<p class="workflow-meta" data-confirmed-field="${e(x.key)}">${e(label(x.key))} · ${e(x.value)} ${e(x.unit)}</p>`).join('') || '<p>Aucun champ confirmé.</p>'}`, true);
    const currentDialog = overlay.querySelector('.modal');
    async function refresh() {
      if (!currentDialog.isConnected || state.detail?.id !== launchId) return;
      await openLaunch(launchId, folder);
      if (currentDialog.isConnected) await intakeExisting(versionId);
    }
    overlay.querySelector('#du-review-type')?.addEventListener('submit', async event => {
      event.preventDefault();
      try {
        await api(endpoint + '/identification/confirm', {method: 'POST', body: JSON.stringify({justification: val('du-review-note')})});
        toast('Type documentaire confirmé');
        await refresh();
      } catch (error) { showErr(error); }
    });
    overlay.querySelectorAll('[data-intake-confirm]').forEach(button => button.addEventListener('click', async () => {
      const key = button.dataset.intakeConfirm;
      const candidate = pending.find(item => item.key === key);
      const value = val('if-' + key).trim();
      if (!value) { toast('Saisissez la valeur à confirmer.'); return; }
      button.disabled = true;
      try {
        await api(endpoint + '/intake/confirm', {method: 'POST', body: JSON.stringify({
          field_key: key, value, unit: val('iu-' + key), source_excerpt: candidate.source_excerpt,
        })});
        toast('Valeur confirmée sur cette version');
        await refresh();
      } catch (error) { showErr(error); }
      finally { button.disabled = false; }
    }));
  } catch (error) { showErr(error); }
}
