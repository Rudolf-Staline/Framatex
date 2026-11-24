'use strict';
/* Espace interne FRAMATEX — refonte premium (dernière couche, chargée en dernier).
   - Coque : menu latéral bleu FRAMATEX regroupé, réductible, barre supérieure en français.
     Les boutons existants (et leurs gestionnaires) sont déplacés, jamais recréés :
     aucune fonction ni aucune permission n'est modifiée.
   - Accueils administrateur et technicien sans statistiques : listes de travail
     construites uniquement à partir des API existantes et des droits du compte. */

document.body.classList.add('fx-pro');

const FX_FOLDERS = [['jaune', 'Sous-dossier jaune'], ['rose', 'Sous-dossier rose'], ['bleu', 'Sous-dossier bleu'], ['vert', 'Sous-dossier vert']];
const FX_FOLDER_NAME = Object.fromEntries(FX_FOLDERS);
const fxStore = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* stockage indisponible : préférence non conservée */ } },
};
const fxNotes = {value: null, at: 0};
const FX_SVG = {
  collapse: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m11 17-5-5 5-5M18 17l-5-5 5-5"/></svg>',
  go: '<svg class="fx-row-go" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>',
  bell: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
  user: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
};

function fxInitials(name) {
  return String(name || '').split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || 'FX';
}
function fxFirstName(name) { return String(name || '').split(/\s+/)[0] || ''; }
function fxToday() {
  const text = new Date().toLocaleDateString('fr-FR', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'});
  return text.charAt(0).toUpperCase() + text.slice(1);
}
function fxHasView(view) { return Boolean(app.querySelector(`.sidebar [data-view="${view}"], .sidebar [data-ops-view="${view}"], .sidebar [data-acc-view="${view}"]`)); }

async function fxUnread(force = false) {
  if (!force && fxNotes.value && Date.now() - fxNotes.at < 60000) return fxNotes.value;
  try { fxNotes.value = await api('/api/notifications'); fxNotes.at = Date.now(); } catch { fxNotes.value = null; }
  return fxNotes.value;
}

// ------------------------------------------------------------------ coque
const fxPreviousMount = mount;
mount = function(html, label) {
  fxPreviousMount(html, label);
  fxShell();
};

function fxShell() {
  const shell = app.querySelector('.app-shell');
  const sidebar = shell?.querySelector('.sidebar');
  if (!sidebar || !state.me) return;
  const admin = state.me.admin;
  if (fxStore.get('fx-sidebar') === 'mini') shell.classList.add('fx-collapsed');

  const keyOf = button => button.dataset.view || button.dataset.opsView || button.dataset.accView;
  const buttons = new Map([...sidebar.querySelectorAll('.nav-btn')].map(button => [keyOf(button), button]));
  const labels = admin
    ? {home: 'Accueil', launches: 'Commandes', search: 'Recherche documentaire', experience: 'Mémoire métier', admin: 'Rôles et checklists', audit: 'Historique et audit', pilot: 'Recette pilote'}
    : {home: 'Mon accueil', launches: 'Mes commandes', search: 'Recherche documentaire', experience: 'Mémoire métier', notifications: 'Mes notifications', actions: 'Mes actions', audit: 'Historique et audit'};
  const groups = [
    ['Travail quotidien', ['home', 'launches', 'myfolders', 'actions', 'notifications', 'search']],
    ['Ressources', ['experience', 'assistant', 'pilot']],
    [admin ? 'Administration' : 'Contrôle', ['access', 'clients', 'orli', 'admin', 'audit']],
  ];
  const account = buttons.get('account');
  buttons.delete('account');
  const nav = document.createElement('nav');
  nav.className = 'fx-nav';
  nav.setAttribute('aria-label', 'Navigation principale');
  const placed = new Set();
  for (const [title, keys] of groups) {
    const present = keys.filter(key => buttons.has(key));
    if (!present.length) continue;
    const group = document.createElement('div');
    group.className = 'fx-nav-group';
    group.innerHTML = `<p class="fx-nav-title">${e(title)}</p>`;
    for (const key of present) { group.append(buttons.get(key)); placed.add(key); }
    nav.append(group);
  }
  // Toute entrée ajoutée par un autre module reste accessible.
  const rest = [...buttons.keys()].filter(key => !placed.has(key));
  if (rest.length) nav.querySelector('.fx-nav-group')?.append(...rest.map(key => buttons.get(key)));
  for (const [key, button] of buttons) {
    const span = button.querySelector('span');
    if (labels[key] && span) span.textContent = labels[key];
    button.title = span?.textContent || '';
    button.classList.toggle('active', fxActive(key));
    if (fxActive(key)) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  }
  sidebar.querySelectorAll('.sidebar-nav, .nav-label, .sidebar-divider, .sidebar-assistant').forEach(node => node.remove());
  const context = document.createElement('div');
  context.className = 'fx-side-context';
  context.innerHTML = `<span>${admin ? 'Dossier jaune numérique' : 'Espace technicien'}</span><button type="button" class="fx-collapse" aria-label="Réduire le menu" title="Réduire le menu">${FX_SVG.collapse}</button>`;
  sidebar.querySelector('.brand').after(context, nav);
  context.querySelector('.fx-collapse').onclick = () => {
    const mini = !shell.classList.contains('fx-collapsed');
    shell.classList.toggle('fx-collapsed', mini);
    context.querySelector('.fx-collapse').setAttribute('aria-label', mini ? 'Déployer le menu' : 'Réduire le menu');
    fxStore.set('fx-sidebar', mini ? 'mini' : 'full');
  };

  // Profil et actions de compte, en bas du menu.
  const bottom = sidebar.querySelector('.sidebar-bottom');
  if (bottom) {
    const role = bottom.querySelector('.user-role');
    if (role) role.textContent = state.me.job_title || (admin ? 'Chef — Administrateur' : state.me.roles.join(', '));
    const avatar = bottom.querySelector('.avatar');
    if (avatar) avatar.textContent = fxInitials(state.me.name);
    const actions = document.createElement('div');
    actions.className = 'fx-side-actions';
    const accountButton = document.createElement('button');
    accountButton.type = 'button';
    accountButton.className = state.view === 'account' ? 'is-active' : '';
    accountButton.title = 'Mon compte';
    accountButton.innerHTML = `${FX_SVG.user}<span>Mon compte</span>`;
    accountButton.onclick = () => navigate('account');
    const logout = bottom.querySelector('#logout');
    actions.append(accountButton);
    if (logout) { logout.title = 'Déconnexion'; actions.append(logout); }
    bottom.append(actions);
    account?.remove();
  }

  // Barre supérieure : libellés français, recherche, notifications, profil.
  const topbar = app.querySelector('.topbar');
  const home = topbar?.querySelector('.breadcrumb-home');
  if (home) home.textContent = 'Espace FRAMATEX';
  const search = topbar?.querySelector('#global-search');
  if (search) {
    search.setAttribute('aria-label', 'Recherche documentaire');
    const text = search.querySelector('span');
    if (text) text.textContent = 'Rechercher un document, une commande…';
    const kbd = search.querySelector('kbd');
    if (kbd) kbd.textContent = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘ K' : 'Ctrl K';
  }
  const bell = topbar?.querySelector('#top-notifications');
  if (bell) { bell.innerHTML = FX_SVG.bell; bell.title = 'Notifications'; }
  const profile = topbar?.querySelector('#top-profile');
  if (profile) {
    const fresh = profile.cloneNode(false);
    fresh.innerHTML = `<span class="fx-initials">${e(fxInitials(state.me.name))}</span><span class="fx-user-name">${e(fxFirstName(state.me.name))}</span>`;
    fresh.title = 'Mon compte';
    fresh.setAttribute('aria-label', 'Mon compte');
    fresh.onclick = () => navigate('account');
    profile.replaceWith(fresh);
  }
  // Fil d'Ariane : « Dossiers jaunes / Commande » devient « Commandes › Commande ».
  const crumb = topbar?.querySelector('.breadcrumb strong');
  if (crumb && crumb.textContent.includes(' / ')) {
    const parts = crumb.textContent.split(' / ').map(part => part === 'Dossiers jaunes' ? 'Commandes' : part);
    const last = parts.pop();
    crumb.textContent = last;
    for (const part of parts) crumb.insertAdjacentHTML('beforebegin', `<span class="fx-crumb">${e(part)}</span>${icon('arrow')}`);
  }
  fxUnread(state.view === 'notifications').then(data => fxBadges(data?.unread || 0));
  if (['launches', 'experience'].includes(state.view)) fxCompactFilters();
  fxGroupActions();
}

// Fiche commande : actions principales visibles, actions secondaires dans un menu.
// Les boutons arrivent de plusieurs modules (parfois après le rendu) : un observateur
// regroupe ceux qui suivent le bouton principal dès qu'il y en a plus de cinq.
function fxGroupActions() {
  const bar = app.querySelector('.dj-head-actions');
  if (!bar) return;
  const loose = [...bar.children].filter(node => node.matches('button, a'));
  let menu = bar.querySelector(':scope > .fx-more');
  const total = loose.length + (menu ? menu.querySelectorAll('.fx-more-menu > *').length : 0);
  if (total <= 5) return;
  const primary = loose.find(button => button.classList.contains('primary'));
  const extra = primary ? loose.slice(loose.indexOf(primary) + 1) : loose.slice(4);
  if (!extra.length || (!menu && extra.length < 2)) return;
  if (!menu) {
    menu = document.createElement('details');
    menu.className = 'fx-more';
    menu.innerHTML = '<summary>Plus d’actions</summary><div class="fx-more-menu" role="menu"></div>';
    menu.querySelector('.fx-more-menu').addEventListener('click', () => menu.removeAttribute('open'));
    bar.append(menu);
  }
  const list = menu.querySelector('.fx-more-menu');
  for (const button of extra) { button.setAttribute('role', 'menuitem'); list.append(button); }
}
document.addEventListener('click', event => {
  app.querySelectorAll('.fx-more[open]').forEach(menu => { if (!menu.contains(event.target)) menu.removeAttribute('open'); });
});
let fxGroupPending = false;
new MutationObserver(() => {
  if (fxGroupPending || !app.querySelector('.dj-head-actions')) return;
  fxGroupPending = true;
  requestAnimationFrame(() => { fxGroupPending = false; fxGroupActions(); });
}).observe(app, {childList: true, subtree: true});

function fxActive(key) {
  return state.view === key || (state.view === 'detail' && key === 'launches');
}

function fxBadges(unread) {
  const nav = app.querySelector('.sidebar [data-view="notifications"]');
  nav?.querySelector('.fx-badge')?.remove();
  if (nav && unread) nav.insertAdjacentHTML('beforeend', `<span class="fx-badge" aria-label="${unread} non lue${unread > 1 ? 's' : ''}">${unread > 99 ? '99+' : unread}</span>`);
  const bell = app.querySelector('#top-notifications');
  bell?.querySelector('.fx-top-count')?.remove();
  if (bell) {
    bell.setAttribute('aria-label', unread ? `Notifications : ${unread} non lue${unread > 1 ? 's' : ''}` : 'Notifications');
    if (unread) bell.insertAdjacentHTML('beforeend', `<span class="fx-top-count">${unread > 99 ? '99+' : unread}</span>`);
  }
}

// Commandes : filtres principaux sur une ligne, critères secondaires repliés.
function fxCompactFilters() {
  const form = app.querySelector('form.ops-filters');
  if (!form || form.closest('.fx-filterbar')) return;
  const fields = [...form.querySelectorAll(':scope > .field, :scope > label, :scope > div:not(.ops-filter-actions)')].filter(node => node.querySelector('input, select'));
  if (fields.length <= 4) return;
  const bar = document.createElement('div');
  bar.className = 'fx-filterbar is-compact';
  form.before(bar);
  bar.append(form);
  fields.slice(4).forEach(node => node.classList.add('fx-filter-more'));
  // Un critère secondaire déjà renseigné garde les filtres dépliés.
  const active = fields.slice(4).some(node => [...node.querySelectorAll('input, select')].some(input =>
    input.tagName === 'SELECT' ? input.selectedIndex > 0 : Boolean(input.value)));
  if (active) bar.classList.remove('is-compact');
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'secondary fx-filter-toggle';
  const sync = () => { toggle.textContent = bar.classList.contains('is-compact') ? 'Plus de filtres' : 'Moins de filtres'; toggle.setAttribute('aria-expanded', String(!bar.classList.contains('is-compact'))); };
  toggle.onclick = () => { bar.classList.toggle('is-compact'); sync(); };
  sync();
  const submit = form.querySelector('[type=submit]');
  if (submit) submit.before(toggle); else form.append(toggle);
}

// ------------------------------------------------------------------ accueils
function fxSection(id, title, text, body, link = '') {
  return `<section class="fx-section" id="${id}" aria-labelledby="${id}-title"><header><div><h2 id="${id}-title">${e(title)}</h2>${text ? `<p>${e(text)}</p>` : ''}</div>${link}</header><div class="fx-section-body">${body}</div></section>`;
}
function fxEmpty(text) { return `<div class="ops-empty">${e(text)}</div>`; }
function fxLink(view, text) { return `<button type="button" class="link" data-fx-go="${view}">${e(text)}</button>`; }

function fxActionRows(items) {
  if (!items.length) return fxEmpty('Aucune action prioritaire pour vos habilitations.');
  return `<ul class="fx-list">${items.map(item => {
    const tone = item.priority === 'urgent' ? 'urgent' : 'warn';
    return `<li><button type="button" class="fx-row" data-ops-target="${opsTargetData(item)}"><span class="fx-mark is-${item.folder || tone}"></span>
      <span><strong>${e(item.title)}</strong><small>${e(item.launch_name)}${item.description ? ' · ' + e(item.description) : ''}</small></span>
      <span class="fx-state is-${tone}">${e(item.priority === 'urgent' ? (item.priority_reason || 'Échéance dépassée') : 'À traiter')}</span>${FX_SVG.go}</button></li>`;
  }).join('')}</ul>`;
}

const FX_DOC_TABS = [
  ['pending', 'En attente de validation', 'pending_validation_documents', 'Validation attendue', 'info'],
  ['missing', 'Manquants', 'missing_documents', 'Pièce manquante', 'warn'],
  ['identification', 'Types à vérifier', 'identification_documents', 'Type à confirmer', 'warn'],
  ['duplicate', 'Doublons', 'duplicate_documents', 'Doublon à examiner', 'warn'],
];
function fxDocRows(report, key) {
  const [, , field, stateLabel, tone] = FX_DOC_TABS.find(tab => tab[0] === key);
  const rows = (report[field] || []).slice(0, 8);
  if (!rows.length) return fxEmpty({pending: 'Aucun document en attente de validation.', missing: 'Aucune pièce obligatoire manquante.', identification: 'Aucun type documentaire à confirmer.', duplicate: 'Aucun doublon à examiner.'}[key]);
  return `<ul class="fx-list">${rows.map(row => {
    const target = opsTargetData({launch_id: row.launch_id, folder: row.folder, document_id: row.document_id || row.documents?.[0]?.document_id});
    return `<li><button type="button" class="fx-row" data-ops-target="${target}"><span class="fx-mark is-${e(row.folder)}"></span>
      <span><strong>${e(row.title)}</strong><small>${e(row.order_ref || row.launch_name)} · ${e(FX_FOLDER_NAME[row.folder] || row.folder)}${row.article ? ' · ' + e(row.article) : ''}</small></span>
      <span class="fx-state is-${tone}">${e(stateLabel)}</span>${FX_SVG.go}</button></li>`;
  }).join('')}</ul>`;
}
function fxDocuments(report) {
  const available = FX_DOC_TABS.filter(([key, , field]) => key === 'pending' || (report[field] || []).length);
  const current = state.fxDocTab && available.some(tab => tab[0] === state.fxDocTab) ? state.fxDocTab : 'pending';
  const tabs = available.length > 1 ? `<div class="dj-subnav fx-doc-tabs" role="tablist" aria-label="Documents à traiter">${available.map(([key, label, field]) =>
    `<button type="button" role="tab" class="dj-chip" aria-selected="${key === current}" data-fx-doc="${key}">${e(label)} <span aria-hidden="true">${(report[field] || []).length}</span></button>`).join('')}</div>` : '';
  return `${tabs}<div id="fx-doc-body">${fxDocRows(report, current)}</div>`;
}

function fxFolderTags(row) {
  const tags = (row.folders || []).filter(folder => folder.can_read).map(folder => {
    const c = folder.completion || {};
    const due = c.due_count ? `<b>${c.present_due}/${c.due_count}</b>` : '';
    return `<span class="fx-folder-tag is-${folder.slug} ${c.due_count && c.present_due < c.due_count ? 'is-missing' : ''}" title="${e(FX_FOLDER_NAME[folder.slug])}${c.due_count ? ` : ${c.present_due} pièce(s) exigible(s) présente(s) sur ${c.due_count}` : ''}">${e(folder.slug.charAt(0).toUpperCase() + folder.slug.slice(1))} ${due}</span>`;
  }).join('');
  return `<div class="fx-folders">${tags || '<span class="ops-muted">—</span>'}</div>`;
}
function fxOrders(launches) {
  const rows = [...launches].sort((a, b) => String(b.updated_at || b.created_at).localeCompare(String(a.updated_at || a.created_at))).slice(0, 6);
  if (!rows.length) return fxEmpty(state.me.admin ? 'Aucune commande enregistrée.' : 'Aucune commande attribuée.');
  const stateLabel = c => ({complete: ['Complet', 'ok'], incomplete: ['Incomplet', 'warn']}[c?.state] || [c?.state ? (OPS_STATES[c.state] || c.state) : '—', '']);
  return `<div class="table-scroll"><table class="fx-orders"><thead><tr><th scope="col">Commande</th><th scope="col" class="fx-col-client">Client</th><th scope="col" class="fx-col-folders">Sous-dossiers</th><th scope="col">État</th></tr></thead><tbody>${rows.map(row => {
    const [label, tone] = stateLabel(row.completion);
    return `<tr data-fx-launch="${e(row.id)}" tabindex="0"><td><strong>${e(row.order_ref || row.name)}</strong><small>${e(row.article || row.name)}</small></td>
      <td class="fx-col-client">${e(row.client_name || '—')}</td><td class="fx-col-folders">${fxFolderTags(row)}</td>
      <td><span class="fx-state ${tone ? 'is-' + tone : ''}">${e(label)}</span><small class="ops-muted" style="display:block;margin-top:4px">${e(row.status || '')}</small></td></tr>`;
  }).join('')}</tbody></table></div>`;
}

function fxAlerts(report) {
  const rows = report.launches.filter(row => row.alerts);
  if (!rows.length) return fxEmpty('Aucune alerte ouverte.');
  return `<ul class="fx-list">${rows.slice(0, 6).map(row => {
    const parts = [row.inconsistencies?.length ? `${row.inconsistencies.length} incohérence${row.inconsistencies.length > 1 ? 's' : ''}` : '',
      row.unacknowledged_changes ? `${row.unacknowledged_changes} modification${row.unacknowledged_changes > 1 ? 's' : ''} à examiner` : ''].filter(Boolean).join(' · ');
    const target = opsTargetData({launch_id: row.id, area: row.inconsistencies?.length ? 'quality' : 'workflow'});
    return `<li><button type="button" class="fx-row" data-ops-target="${target}"><span class="fx-mark is-urgent"></span>
      <span><strong>${e(row.order_ref || row.name)}</strong><small>${e(parts || 'Alerte à examiner')}</small></span><span class="fx-state is-urgent">Intervention</span>${FX_SVG.go}</button></li>`;
  }).join('')}</ul>`;
}

function fxNotifications(data) {
  const items = (data?.items || []).slice(0, 5);
  if (!items.length) return fxEmpty('Aucune notification.');
  return `<ul class="fx-list">${items.map(item => {
    const target = item.launch_id ? opsTargetData({launch_id: item.launch_id, folder: item.folder}) : '';
    return `<li><button type="button" class="fx-row" ${target ? `data-ops-target="${target}"` : 'data-fx-go="notifications"'}><span class="fx-mark is-${item.read_at ? '' : 'info'}"></span>
      <span><strong>${e(item.title)}</strong><small>${e(item.message || '')}</small></span><span class="fx-state ${item.read_at ? '' : 'is-info'}">${item.read_at ? niceDate(item.created_at) : 'Non lue'}</span>${FX_SVG.go}</button></li>`;
  }).join('')}</ul>`;
}

function fxRequests(requests) {
  const open = (requests || []).filter(row => ['submitted', 'under_review'].includes(row.status));
  if (!open.length) return fxEmpty('Aucune demande client en attente.');
  return `<ul class="fx-list">${open.slice(0, 5).map(row => `<li><button type="button" class="fx-row" data-fx-request="${e(row.id)}"><span class="fx-mark is-info"></span>
    <span><strong>${e(row.request_number)} · ${e(row.article)}</strong><small>${e(row.client?.raison_sociale || '')} · ${e(row.quantite)} pièces · souhaitée le ${e(opsDay(row.date_souhaitee))}</small></span>
    <span class="fx-state is-info">${e(OPS_ORDER_LABELS[row.status] || row.status)}</span>${FX_SVG.go}</button></li>`).join('')}</ul>`;
}

function fxLevel(actions) {
  const set = new Set(actions || []);
  const depot = ['document.read', 'document.download', 'document.write', 'document.version', 'document.comment', 'controls.read'];
  if (!set.size) return 'Aucun accès';
  if (set.size === 1 && set.has('document.read')) return 'Lecture seule';
  if (set.size === depot.length && depot.every(a => set.has(a))) return 'Dépôt sans validation';
  if (set.size >= 10) return 'Responsable';
  return 'Personnalisé';
}
function fxAssigned(account) {
  if (!account.assignments.length) return '';
  return `<div class="fx-assigned">${account.assignments.map(item => `<div class="fx-assigned-row"><div><strong>${e(item.launch.order_ref || item.launch.name)}</strong>
      <small>${e(item.launch.name)}${item.launch.client_name ? ' · ' + e(item.launch.client_name) : ''}</small>
      <div class="fx-folder-links">${FX_FOLDERS.filter(([slug]) => item.folders[slug]?.length).map(([slug, name]) => `<button type="button" class="fx-folder-link is-${slug}" data-fx-open="${e(item.launch.id)}" data-fx-folder="${slug}"><i aria-hidden="true"></i>${e(name)} <em>· ${e(fxLevel(item.folders[slug]))}</em></button>`).join('')}</div></div>
    <button type="button" class="secondary tiny" data-fx-open="${e(item.launch.id)}">Ouvrir la commande</button></div>`).join('')}</div>`;
}

function fxQuick(items) {
  return `<div class="fx-quick">${items.map(([view, ico, title, text]) => `<button type="button" data-fx-go="${view}">${icon(ico)}<span><span>${e(title)}</span><small>${e(text)}</small></span>${FX_SVG.go}</button>`).join('')}</div>`;
}

function fxMemory(notes) {
  const rows = (notes?.items || []).slice(0, 4);
  if (!rows.length) return fxEmpty('Aucun retour enregistré dans vos sous-dossiers.');
  const tone = {critique: 'urgent', important: 'warn', surveiller: 'warn'};
  return `<ul class="fx-list">${rows.map(note => `<li><button type="button" class="fx-row" data-fx-go="experience"><span class="fx-mark is-${e(note.folder_slug || 'info')}"></span>
    <span><strong>${e(note.party_name)}</strong><small>${e(String(note.body || '').slice(0, 110))}${String(note.body || '').length > 110 ? '…' : ''}</small><small>${e(note.order_ref || 'Note générale')}${note.folder_slug ? ' · ' + e(FX_FOLDER_NAME[note.folder_slug]) : ''}</small></span>
    <span class="fx-state ${tone[note.importance] ? 'is-' + tone[note.importance] : ''}">${e(note.category || 'Retour')}</span>${FX_SVG.go}</button></li>`).join('')}</ul>`;
}

function fxWelcome(title, text, shortcuts) {
  return `<section class="fx-welcome" aria-labelledby="fx-welcome-title"><span class="fx-welcome-eyebrow">Espace FRAMATEX</span>
    <h1 id="fx-welcome-title">${e(title)}</h1><p>${e(text)}</p>
    ${shortcuts.length ? `<div class="fx-shortcuts">${shortcuts.map(([action, ico, label, main]) => `<button type="button" class="fx-shortcut ${main ? 'is-main' : ''}" data-fx-shortcut="${action}">${icon(ico)}${e(label)}</button>`).join('')}</div>` : ''}</section>`;
}

async function fxHome() {
  const admin = state.me.admin;
  const [report, account, notifications, requests] = await Promise.all([
    api('/api/workspace/dashboard'),
    admin ? Promise.resolve(null) : api('/api/account'),
    fxUnread(true),
    admin ? api('/api/admin/client-order-requests').catch(() => []) : Promise.resolve(null),
  ]);
  state.view = 'home'; state.operationsDashboard = report; state.priorities = report.priorities;
  const label = admin ? 'Accueil' : 'Mon accueil';
  const name = fxFirstName(state.me.name);
  if (admin) {
    const shortcuts = [
      ...(can('launch.create') ? [['new', 'plus', 'Nouvelle commande', true]] : []),
      ['search', 'search', 'Recherche documentaire'],
      ['access', 'users', 'Collaborateurs et habilitations'], ['clients', 'users', 'Clients et demandes'], ['experience', 'file', 'Mémoire métier'],
    ];
    mount(`<div class="fx-home">
      ${fxWelcome(`Bonjour ${name}`, `${fxToday()}. Commandes, documents et demandes qui attendent une intervention.`, shortcuts)}
      <div class="fx-home-grid"><div class="fx-home-col">
        ${fxSection('fx-priorities', 'Actions prioritaires', 'Pièces à déposer, validations et vérifications à mener.', fxActionRows(report.priorities.items.slice(0, 6)), fxLink('actions', 'Toutes les actions'))}
        ${fxSection('fx-documents', 'Documents à traiter', 'Pièces déposées à valider, pièces exigibles absentes et contrôles de classement.', fxDocuments(report))}
        ${fxSection('fx-orders', 'Commandes récentes', 'Dernières commandes modifiées, avec l’avancement de chaque sous-dossier.', fxOrders(report.launches), fxLink('launches', 'Toutes les commandes'))}
      </div><div class="fx-home-col fx-home-side">
        ${fxSection('fx-requests', 'Demandes clients à traiter', 'Demandes envoyées depuis l’Espace Client.', fxRequests(requests), fxLink('clients', 'Clients et demandes'))}
        ${fxSection('fx-alerts', 'Alertes à traiter', 'Incohérences et modifications qui demandent une décision.', fxAlerts(report))}
        ${fxSection('fx-notifications', 'Notifications', '', fxNotifications(notifications), fxLink('notifications', 'Toutes les notifications'))}
      </div></div></div>`, label);
  } else if (!account.assignments.length) {
    mount(`<div class="fx-home">
      ${fxWelcome(`Bonjour ${name}`, 'Votre compte est actif. Vos commandes et vos sous-dossiers apparaîtront ici dès qu’un responsable vous les attribuera.', [])}
      <div class="fx-home-grid"><div class="fx-home-col">
        <section class="fx-section acc-empty" aria-live="polite"><header><div><h2>Aucune commande ne vous est attribuée pour le moment</h2>
          <p>Le chef FRAMATEX choisit, commande par commande, les sous-dossiers sur lesquels vous travaillez et les actions autorisées.</p></div></header>
          <div class="fx-section-body">${fxQuick([['account', 'users', 'Mon compte', 'Mot de passe et préférences de notification'], ['assistant', 'layers', 'Assistant FRAMATEX', 'Procédures et bons écrans']])}</div></section>
      </div><div class="fx-home-col fx-home-side">${fxSection('fx-notifications', 'Mes notifications', '', fxNotifications(notifications), fxLink('notifications', 'Toutes les notifications'))}</div></div></div>`, label);
  } else {
    // La mémoire métier applique ses propres droits (lecture du sous-dossier) : un refus masque la section.
    const memory = await api('/api/workspace/business-memory').catch(() => null);
    const pending = (report.pending_validation_documents || []).length;
    const quick = [['myfolders', 'folder', 'Mes sous-dossiers', 'Commande par commande, avec vos actions autorisées'],
      ['search', 'search', 'Recherche documentaire', 'Uniquement dans vos sous-dossiers'],
      ...(memory ? [['experience', 'file', 'Mémoire métier', 'Retours sur vos sous-dossiers']] : []),
      ['assistant', 'layers', 'Assistant', 'Procédures et bons écrans'], ['account', 'users', 'Mon compte', 'Mot de passe et préférences']];
    mount(`<div class="fx-home">
      ${fxWelcome(`Bonjour ${name}`, `${fxToday()}. Vos commandes attribuées et ce qui vous attend dans vos sous-dossiers.`,
        [['launches', 'folder', 'Mes commandes', true], ['myfolders', 'folder', 'Mes sous-dossiers'], ['search', 'search', 'Recherche documentaire']])}
      <div class="fx-home-grid"><div class="fx-home-col">
        ${fxSection('fx-assigned', 'Mes commandes attribuées', 'Ouvrez directement le sous-dossier sur lequel vous travaillez.', fxAssigned(account), fxLink('myfolders', 'Mes sous-dossiers'))}
        ${fxSection('fx-priorities', 'Mes actions prioritaires', 'Limitées à vos sous-dossiers et à vos actions autorisées.', fxActionRows(report.priorities.items.slice(0, 6)), fxLink('actions', 'Toutes mes actions'))}
        ${pending ? fxSection('fx-documents', 'Documents à traiter', 'Dans vos sous-dossiers.', fxDocuments(report)) : ''}
      </div><div class="fx-home-col fx-home-side">
        ${fxSection('fx-notifications', 'Mes notifications', '', fxNotifications(notifications), fxLink('notifications', 'Toutes les notifications'))}
        ${fxSection('fx-quick', 'Accès rapides', '', fxQuick(quick))}
        ${memory ? fxSection('fx-memory', 'Mémoire métier', 'Derniers retours sur vos sous-dossiers.', fxMemory(memory), fxLink('experience', 'Ouvrir la mémoire métier')) : ''}
      </div></div></div>`, label);
  }
  fxBindHome(report);
}

function fxBindHome(report) {
  const root = app.querySelector('.fx-home');
  if (!root) return;
  bindOpsTargets(root);
  root.querySelectorAll('[data-fx-go]').forEach(button => button.addEventListener('click', () => navigate(button.dataset.fxGo)));
  root.querySelectorAll('[data-fx-shortcut]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.fxShortcut === 'new') openNewLaunch(); else navigate(button.dataset.fxShortcut);
  }));
  root.querySelectorAll('[data-fx-launch]').forEach(row => {
    const open = () => openLaunch(row.dataset.fxLaunch);
    row.addEventListener('click', open);
    row.addEventListener('keydown', event => { if (event.key === 'Enter') open(); });
  });
  root.querySelectorAll('[data-fx-open]').forEach(button => button.addEventListener('click', () => openLaunch(button.dataset.fxOpen, button.dataset.fxFolder || undefined)));
  root.querySelectorAll('[data-fx-request]').forEach(button => button.addEventListener('click', () => operationsClientRequest(button.dataset.fxRequest).catch(showErr)));
  root.querySelectorAll('[data-fx-doc]').forEach(button => button.addEventListener('click', () => {
    state.fxDocTab = button.dataset.fxDoc;
    root.querySelectorAll('[data-fx-doc]').forEach(tab => tab.setAttribute('aria-selected', String(tab === button)));
    const body = root.querySelector('#fx-doc-body');
    body.innerHTML = fxDocRows(report, state.fxDocTab);
    bindOpsTargets(body);
  }));
}

home = fxHome;
operationsHome = fxHome;
// Technicien sans affectation : même accueil, état vide explicite.
accEmptyHome = function() { return fxHome().catch(showErr); };
