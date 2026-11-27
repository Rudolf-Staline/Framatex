'use strict';
/* Visionneuse documentaire intégrée à la fiche « Ouvrir » : le contenu réel de la version
   sélectionnée (PDF, Excel, Word, images, CSV/TXT, emails), à côté des actions existantes.
   Les aperçus sont rendus par le serveur, qui revérifie les droits à chaque requête. */
const DV_ICONS = {
  prev: '<path d="m15 18-6-6 6-6"/>', next: '<path d="m9 18 6-6-6-6"/>', plus: '<path d="M5 12h14M12 5v14"/>', minus: '<path d="M5 12h14"/>',
  full: '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
};
const dvIcon = name => `<svg class="fx-ico" viewBox="0 0 24 24" aria-hidden="true">${DV_ICONS[name]}</svg>`;

const dvBaseDocument = operationsDocument;
operationsDocument = async function(id, versionId = null) {
  await dvBaseDocument(id, versionId);
  const doc = typeof findDoc === 'function' ? findDoc(id) : null;
  const version = doc && (doc.versions.find(v => v.id === versionId) || doc.latest);
  const body = overlay.querySelector('.modal-body');
  if (!doc || !version || !body || body.querySelector('.dv-layout')) return;
  overlay.querySelector('.modal')?.classList.add('dv-modal');
  const layout = document.createElement('div');
  layout.className = 'dv-layout';
  layout.innerHTML = `<section class="dv-viewer" aria-label="Contenu de ${e(version.original_name)} · V${version.number}"><div class="dv-stage"><div class="fx-loading">Chargement de l’aperçu…</div></div></section><div class="dv-side"></div>`;
  const side = layout.querySelector('.dv-side');
  while (body.firstChild) side.append(body.firstChild);
  body.append(layout);
  if (state.me?.admin) dvClientMail(side, version);
  dvRender(layout.querySelector('.dv-viewer'), version).catch(error => {
    layout.querySelector('.dv-stage').innerHTML = `<div class="ops-empty">Aperçu indisponible : ${e(error.message)}</div>`;
  });
};

async function dvRender(viewer, version) {
  const meta = await api(`/api/document-versions/${version.id}/preview`);
  const stage = viewer.querySelector('.dv-stage');
  const head = `<header class="dv-head"><div><strong>${e(meta.name)}</strong><small>Version ${meta.version}${version.is_current === false ? ' · version historique' : ''}</small></div><div class="dv-tools"></div></header>`;
  viewer.insertAdjacentHTML('afterbegin', head);
  const tools = viewer.querySelector('.dv-tools');
  const fullscreen = () => { tools.insertAdjacentHTML('beforeend', `<button type="button" class="dv-btn" data-dv-full title="Plein écran" aria-label="Plein écran">${dvIcon('full')}</button>`);
    tools.querySelector('[data-dv-full]').onclick = () => (document.fullscreenElement ? document.exitFullscreen() : viewer.requestFullscreen?.()).catch?.(() => {}); };
  const base = `/api/document-versions/${version.id}/preview`;
  if (meta.kind === 'pdf') return dvPdf(stage, tools, base, meta, fullscreen);
  if (meta.kind === 'excel') { fullscreen(); return dvExcel(stage, tools, base, meta); }
  fullscreen();
  if (meta.kind === 'image') stage.innerHTML = `<div class="dv-scroll dv-center"><img class="dv-image" src="${base}/image" alt="Aperçu de ${e(meta.name)}"></div>`;
  else if (meta.kind === 'word') stage.innerHTML = `<p class="dv-notice">${e(meta.notice)}</p><article class="dv-scroll dv-doc">${meta.blocks.map(b => b.type === 'table'
    ? `<div class="dv-table-wrap"><table>${b.rows.map(r => `<tr>${r.map(c => `<td>${e(c)}</td>`).join('')}</tr>`).join('')}</table></div>`
    : `<${b.type}>${e(b.text)}</${b.type}>`).join('') || '<p>Document sans texte lisible.</p>'}${meta.truncated ? '<p class="dv-notice">Aperçu limité : document long.</p>' : ''}</article>`;
  else if (meta.kind === 'text') stage.innerHTML = `<pre class="dv-scroll dv-text">${e(meta.text)}</pre>${meta.truncated ? '<p class="dv-notice">Aperçu limité aux 300 premiers Ko.</p>' : ''}`;
  else if (meta.kind === 'csv') stage.innerHTML = `<div class="dv-scroll dv-grid"><table>${meta.rows.map((r, i) => `<tr>${r.map(c => i ? `<td>${e(c)}</td>` : `<th>${e(c)}</th>`).join('')}</tr>`).join('')}</table></div>${meta.truncated ? '<p class="dv-notice">Aperçu limité aux 2 000 premières lignes.</p>' : ''}`;
  else if (meta.kind === 'email') {
    const m = meta.email;
    stage.innerHTML = `<article class="dv-scroll dv-mail"><dl><div><dt>Objet</dt><dd>${e(m.subject || '—')}</dd></div><div><dt>Expéditeur</dt><dd>${e(m.from || '—')}</dd></div><div><dt>Destinataires</dt><dd>${e(m.to || '—')}</dd></div><div><dt>Date</dt><dd>${e(m.date || '—')}</dd></div></dl>
      <pre class="dv-text">${e(m.body || 'Message sans texte.')}</pre>${m.attachments.length ? `<h4>Pièces jointes</h4><ul>${m.attachments.map(a => `<li>${e(a.name)} <small>${e(a.type)} · ${Math.ceil(a.size / 1024)} Ko</small></li>`).join('')}</ul><p class="dv-notice">Les pièces jointes ne sont pas ouvertes depuis l’email : déposez-les comme documents pour les consulter.</p>` : ''}</article>`;
  } else stage.innerHTML = `<div class="ops-empty">Ce format ne peut pas être prévisualisé dans la plateforme.${meta.can_download ? ' Utilisez « Télécharger » pour l’ouvrir avec l’application adaptée.' : ' Le téléchargement n’est pas autorisé pour votre compte.'}</div>`;
}

function dvPdf(stage, tools, base, meta, fullscreen) {
  let page = 1, zoom = 1.3, hits = [];
  tools.innerHTML = `<button type="button" class="dv-btn" data-dv="prev" aria-label="Page précédente">${dvIcon('prev')}</button>
    <span class="dv-page"><input type="number" min="1" max="${meta.pages}" value="1" aria-label="Page" data-dv-page> / ${meta.pages}</span>
    <button type="button" class="dv-btn" data-dv="next" aria-label="Page suivante">${dvIcon('next')}</button>
    <button type="button" class="dv-btn" data-dv="out" aria-label="Zoom arrière">${dvIcon('minus')}</button><span class="dv-zoom" data-dv-zoom>130 %</span>
    <button type="button" class="dv-btn" data-dv="in" aria-label="Zoom avant">${dvIcon('plus')}</button>
    <form class="dv-search" data-dv-search>${dvIcon('search')}<input type="search" placeholder="Rechercher dans le PDF" aria-label="Rechercher dans le PDF" minlength="2"></form>`;
  fullscreen();
  stage.innerHTML = `<div class="dv-hits" data-dv-hits hidden></div><div class="dv-scroll dv-center"><div class="dv-page-frame"><img class="dv-pdf" alt=""><div class="dv-marks"></div></div></div>`;
  const img = stage.querySelector('.dv-pdf');
  const draw = () => {
    img.alt = `Page ${page} sur ${meta.pages}`;
    img.src = `${base}/page/${page}?zoom=${zoom}`;
    tools.querySelector('[data-dv-page]').value = page;
    tools.querySelector('[data-dv-zoom]').textContent = `${Math.round(zoom * 100)} %`;
    const marks = (hits.find(h => h.page === page)?.boxes || []).map(([x, y, w, h]) => `<i style="left:${x * 100}%;top:${y * 100}%;width:${w * 100}%;height:${h * 100}%"></i>`).join('');
    stage.querySelector('.dv-marks').innerHTML = marks;
  };
  const go = n => { page = Math.min(meta.pages, Math.max(1, n)); draw(); };
  tools.querySelector('[data-dv="prev"]').onclick = () => go(page - 1);
  tools.querySelector('[data-dv="next"]').onclick = () => go(page + 1);
  tools.querySelector('[data-dv="in"]').onclick = () => { zoom = Math.min(2.6, +(zoom + .3).toFixed(1)); draw(); };
  tools.querySelector('[data-dv="out"]').onclick = () => { zoom = Math.max(.6, +(zoom - .3).toFixed(1)); draw(); };
  tools.querySelector('[data-dv-page]').onchange = event => go(Number(event.target.value) || 1);
  tools.querySelector('[data-dv-search]').onsubmit = async event => {
    event.preventDefault();
    const q = event.target.querySelector('input').value.trim();
    const box = stage.querySelector('[data-dv-hits]');
    if (q.length < 2) return;
    const result = await api(`${base}/search?q=${encodeURIComponent(q)}`);
    hits = result.hits;
    box.hidden = false;
    box.innerHTML = hits.length ? `${hits.length} page(s) : ${hits.map(h => `<button type="button" data-dv-hit="${h.page}">p. ${h.page} (${h.boxes.length})</button>`).join('')}`
      : 'Aucune occurrence (le PDF peut ne pas contenir de texte, par exemple s’il est scanné).';
    box.querySelectorAll('[data-dv-hit]').forEach(b => b.onclick = () => go(Number(b.dataset.dvHit)));
    if (hits.length) go(hits[0].page); else draw();
  };
  draw();
}

async function dvExcel(stage, tools, base, meta) {
  let sheet = meta.sheets[0]?.name, offset = 0, formulas = false;
  tools.insertAdjacentHTML('afterbegin', `<label class="dv-toggle"><input type="checkbox" data-dv-formulas> Formules</label>`);
  tools.querySelector('[data-dv-formulas]').onchange = event => { formulas = event.target.checked; stage.querySelectorAll('td[data-f]').forEach(td => { td.textContent = formulas ? td.dataset.f : td.dataset.v; }); };
  stage.innerHTML = `<nav class="dv-sheets" role="tablist" aria-label="Feuilles">${meta.sheets.map(s => `<button type="button" role="tab" data-dv-sheet="${e(s.name)}">${e(s.name)}</button>`).join('')}</nav>
    <div class="dv-scroll dv-grid" data-dv-grid></div><div class="dv-more" data-dv-more></div>`;
  const grid = stage.querySelector('[data-dv-grid]');
  const load = async (append = false) => {
    const data = await api(`${base}/sheet?sheet=${encodeURIComponent(sheet)}&offset=${offset}&limit=200`);
    const rows = data.rows.map((row, i) => `<tr><th>${data.offset + i + 1}</th>${row.map(c => {
      const value = c.v === null || c.v === undefined ? '' : String(c.v);
      return c.f ? `<td data-f="${e(c.f)}" data-v="${e(value)}" title="${e(c.f)}" class="has-f">${e(formulas ? c.f : value)}</td>` : `<td>${e(value)}</td>`;
    }).join('')}</tr>`).join('');
    if (!append) grid.innerHTML = `<table><thead><tr><th></th>${data.columns.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`;
    else grid.querySelector('tbody').insertAdjacentHTML('beforeend', rows);
    const more = stage.querySelector('[data-dv-more]');
    more.innerHTML = `${data.total_rows} ligne(s)${data.truncated_cols ? ' · colonnes affichées : 60 premières' : ''}${data.has_more ? ' <button type="button" class="secondary tiny" data-dv-next>Charger 200 lignes de plus</button>' : ''}`;
    more.querySelector('[data-dv-next]')?.addEventListener('click', () => { offset += 200; load(true).catch(showErr); });
  };
  const select = name => {
    sheet = name; offset = 0;
    stage.querySelectorAll('[data-dv-sheet]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.dvSheet === name)));
    load().catch(showErr);
  };
  stage.querySelectorAll('[data-dv-sheet]').forEach(b => b.onclick = () => select(b.dataset.dvSheet));
  if (sheet) select(sheet); else grid.innerHTML = '<div class="ops-empty">Classeur sans feuille lisible.</div>';
}


// Explicit human action: load the linked client and open a new draft in Outlook.
// No document bytes, internal notes, attachments or authentication data are transmitted.
function dvClientMail(side, version) {
  const panel = document.createElement('section');
  panel.className = 'ops-panel dv-client-mail';
  panel.innerHTML = '<h3>Clarification client</h3><p class="workflow-meta">Rédigez vous-même un courrier au client concernant cette version.</p><button type="button" class="secondary tiny" data-dv-mail>Préparer un email Outlook</button><div data-dv-mail-result aria-live="polite"></div>';
  side.prepend(panel);
  const button = panel.querySelector('[data-dv-mail]');
  const result = panel.querySelector('[data-dv-mail-result]');
  button.onclick = async () => {
    button.disabled = true;
    result.textContent = 'Vérification du destinataire…';
    try {
      const context = await api('/api/document-versions/' + encodeURIComponent(version.id) + '/client-mail-context');
      if (!context.available) { result.textContent = context.reason; return; }
      result.replaceChildren();
      const info = document.createElement('p');
      info.className = 'workflow-meta';
      info.textContent = 'Destinataire : ' + context.client_name + ' · ' + context.email;
      const subject = document.createElement('p');
      subject.className = 'workflow-meta'; subject.textContent = 'Objet : ' + context.subject;
      const web = document.createElement('a');
      const url = new URL('https://outlook.office.com/mail/deeplink/compose');
      url.searchParams.set('to', context.email);
      url.searchParams.set('subject', context.subject);
      web.href = url.toString(); web.target = '_blank'; web.rel = 'noopener noreferrer';
      web.className = 'secondary tiny'; web.textContent = 'Ouvrir Outlook Web';
      const local = document.createElement('a');
      local.href = 'mailto:' + encodeURIComponent(context.email).replace(/%40/g, '@') + '?subject=' + encodeURIComponent(context.subject);
      local.className = 'secondary tiny'; local.textContent = 'Ouvrir la messagerie installée';
      const notice = document.createElement('p');
      notice.className = 'workflow-meta'; notice.textContent = 'Aucun message envoyé. Vérifiez le destinataire et rédigez le message dans votre messagerie. Aucun fichier n’est joint automatiquement.';
      const actions = document.createElement('div'); actions.className = 'mail-actions';
      actions.append(web, local); result.append(info, subject, actions, notice);
    } catch (error) {
      result.textContent = error.message || 'Impossible de préparer le courrier.';
    } finally { button.disabled = false; }
  };
}
