const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));
}
function sevClass(sev) {
  return (sev || 'info').toLowerCase();
}

// Outline icons, one path set per sidebar/page role. Kept here rather than in
// the HTML so the sidebar markup stays about structure, not glyph soup.
const ICONS = {
  network: '<svg viewBox="0 0 24 24"><circle cx="12" cy="4" r="1.7"/><circle cx="19.2" cy="8" r="1.7"/><circle cx="19.2" cy="16" r="1.7"/><circle cx="12" cy="20" r="1.7"/><circle cx="4.8" cy="16" r="1.7"/><circle cx="4.8" cy="8" r="1.7"/><circle cx="12" cy="12" r="2.3"/><path d="M12 6v3.7M13.9 10.6l3.6-1.6M13.9 13.4l3.6 1.6M12 14.3V18M10.1 13.4l-3.6 1.6M10.1 10.6 6.5 9"/></svg>',
  chevrons: '<svg viewBox="0 0 24 24"><path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/></svg>',
  dashboard: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/></svg>',
  flows: '<svg viewBox="0 0 24 24"><circle cx="18" cy="5" r="2.3"/><circle cx="6" cy="12" r="2.3"/><circle cx="18" cy="19" r="2.3"/><path d="M8.1 10.9 15.9 6.1M8.1 13.1l7.8 4.8"/></svg>',
  chat: '<svg viewBox="0 0 24 24"><path d="M4 5h16a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9l-5 5V7a2 2 0 0 1 2-2z"/></svg>',
  templates: '<svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/></svg>',
  resources: '<svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  knowledges: '<svg viewBox="0 0 24 24"><path d="M4 4v16M8 6v14M12 6v14M16 6l4 13"/></svg>',
  clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  settings: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  user: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.6"/><path d="M5 20.2c0-3.5 3.1-6.2 7-6.2s7 2.7 7 6.2"/></svg>',
  plug: '<svg viewBox="0 0 24 24"><path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4Z"/></svg>',
  doc: '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 8h8M8 12h5"/></svg>',
  key: '<svg viewBox="0 0 24 24"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></svg>',
  'arrow-left': '<svg viewBox="0 0 24 24"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>',
  'panel-left': '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/></svg>',
  mail: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
  lock: '<svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
  pulse: '<svg viewBox="0 0 24 24"><path d="M2 12h4l2.5-7 4 14 3-9 2 2h4.5"/></svg>',
  chip: '<svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="2.5"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>',
  dollar: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v10"/><path d="M14.7 9.2c-.6-.8-1.6-1.2-2.7-1.2-1.6 0-2.8.9-2.8 2.1 0 2.9 5.6 1.4 5.6 4.3 0 1.3-1.3 2.2-2.9 2.2-1.2 0-2.2-.5-2.8-1.3"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  sun: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/></svg>',
  moon: '<svg viewBox="0 0 24 24"><path d="M20.5 14.5A8.5 8.5 0 1 1 9.5 3.5a7 7 0 0 0 11 11z"/></svg>',
};
document.querySelectorAll('[data-icon]').forEach((el) => {
  el.innerHTML = ICONS[el.dataset.icon] || '';
});

// ---- light / dark theme ---------------------------------------------------
const THEME_KEY = 'adaptix.theme';
function applyTheme(theme) {
  const dark = theme === 'dark';
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  const ico = document.getElementById('theme-toggle-ico');
  if (ico) ico.innerHTML = ICONS[dark ? 'sun' : 'moon'] || '';
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.title = dark ? 'Mode terang' : 'Mode gelap';
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* private mode */ }
}
function currentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}
$('theme-toggle').addEventListener('click', () => {
  applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
});
applyTheme(currentTheme());

// ---------------------------------------------------------------- top nav ---
const tabs = document.querySelectorAll('.nav-item');
const panels = document.querySelectorAll('.panel');

// A flow detail replaces the topbar + page panels. Leaving that view (top nav,
// + New Flow, empty-state CTA) must undo it first, otherwise the stale flow
// stays painted on top and the new tab looks "stuck" on the previous run.
function closeFlowView() {
  const full = $('flow-fullpage');
  if (full) full.classList.add('hidden');
  const topbar = document.querySelector('.topbar');
  if (topbar) topbar.classList.remove('hidden');
  panels.forEach((p) => p.classList.remove('hidden'));
}

function activateTab(tab) {
  closeFlowView();
  tabs.forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  panels.forEach((p) => p.classList.toggle('active', p.id === 'panel-' + tab));
}

tabs.forEach((btn) => btn.addEventListener('click', () => {
  activateTab(btn.dataset.tab);
  if (btn.dataset.tab === 'dashboard') loadDashboard();
  if (btn.dataset.tab === 'flows') loadFlows();
  if (btn.dataset.tab === 'chat') setTimeout(() => $('instruction').focus(), 60);
  if (btn.dataset.tab === 'templates') loadTemplates();
  if (btn.dataset.tab === 'resources') loadResources();
  if (btn.dataset.tab === 'knowledges') loadKnowledge();
}));
if (location.hash && location.hash !== '#settings') {
  const initial = Array.from(tabs).find((b) => b.dataset.tab === location.hash.slice(1));
  if (initial) initial.click();
}

function hostOf(target) {
  try {
    return new URL(target.includes('://') ? target : 'http://' + target).hostname;
  } catch (e) {
    return '';
  }
}

const ENGINE_META = {
  adaptix: { label: 'ADAPTIX', sub: 'Native agent' },
  opencode: { label: 'OpenCode', sub: 'Pentester' },
  code: { label: 'Code Audit', sub: 'ZIP / folder · static' },
};
let currentEngine = 'adaptix';

function engineTarget() {
  return currentEngine === 'opencode' ? 'target-opencode' : 'target';
}

function syncEngine() {
  currentEngine = $('b-engine').value;
  const meta = ENGINE_META[currentEngine] || ENGINE_META.adaptix;
  document.querySelectorAll('#engine-dock .engine-logo').forEach((btn) => {
    const on = btn.dataset.engine === currentEngine;
    btn.classList.toggle('on', on);
    btn.setAttribute('aria-pressed', String(on));
  });
  $('engine-current').textContent = meta.label + ' · ' + meta.sub;
  $('engine-modal-title').textContent = meta.label + ' settings';
  document.querySelectorAll('.engine-settings').forEach((box) => {
    box.classList.toggle('hidden', box.id !== 'settings-' + currentEngine);
  });
  $('full-offensive-panel').classList.toggle('hidden', !$('b-full-offensive').checked);
  if (currentEngine === 'opencode' && !$('b-opencode-model').dataset.loaded) loadOpencodeModels();
  if (currentEngine === 'code') syncCodeSource();
}

function openEngineModal(engine) {
  if (engine) { $('b-engine').value = engine; syncEngine(); }
  $('engine-modal').classList.remove('hidden');
  if (currentEngine === 'code' && !$('b-code-model').dataset.loaded) loadCodeModels();
  const focusId = currentEngine === 'code' ? 'b-code-path'
    : currentEngine === 'opencode' ? 'target-opencode' : 'target';
  setTimeout(() => { const el = $(focusId); if (el) el.focus(); }, 80);
}
function closeEngineModal() { $('engine-modal').classList.add('hidden'); }

document.querySelectorAll('#engine-dock .engine-logo').forEach((btn) => {
  btn.addEventListener('click', () => openEngineModal(btn.dataset.engine));
});
$('engine-modal-close').addEventListener('click', closeEngineModal);
$('engine-modal-done').addEventListener('click', closeEngineModal);
$('engine-modal').addEventListener('click', (e) => { if (e.target === $('engine-modal')) closeEngineModal(); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !$('engine-modal').classList.contains('hidden')) closeEngineModal();
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && $('panel-chat').classList.contains('active')
      && document.activeElement === $('instruction')) $('start-btn').click();
});

function codeSourceKind() {
  return $('b-code-source-folder').checked ? 'folder' : 'zip';
}

function syncCodeSource() {
  const folder = codeSourceKind() === 'folder';
  $('b-code-zip-row').classList.toggle('hidden', folder);
  $('b-code-folder-row').classList.toggle('hidden', !folder);
  $('b-code-patch-row').classList.toggle('hidden', !folder);
  preflightCodeFolder();
}

async function preflightCodeFolder() {
  const warn = $('b-code-skip-warning');
  if (!warn) return;
  warn.classList.add('hidden'); warn.textContent = '';
  renderScannerBadges();
  if (codeSourceKind() !== 'folder') return;
  const path = ($('b-code-path') || {}).value || '';
  if (!path.trim()) return;
  try {
    const kb = ($('b-code-file-limit') || {}).value || '1024';
    const res = await fetch(`/api/audit/preflight?source_path=${encodeURIComponent(path)}&max_file_kb=${kb}`);
    const data = await res.json();
    if (!res.ok || !data.warnings || !data.warnings.length) return;
    warn.textContent = data.warnings.join('; ');
    warn.classList.remove('hidden');
  } catch (e) { /* offline */ }
}

const _preflightDebounce = {};
['b-code-path', 'b-code-file-limit'].forEach((id) => {
  const el = $(id);
  if (el) el.addEventListener('change', () => { clearTimeout(_preflightDebounce[id]); _preflightDebounce[id] = setTimeout(preflightCodeFolder, 300); });
});

async function renderScannerBadges() {
  const box = $('b-code-scanner-badges');
  if (!box) return;
  try {
    const res = await fetch('/api/audit/scanners');
    const data = await res.json();
    const rows = data.scanners || [];
    box.innerHTML = rows.map((s) => {
      const badge = s.installed ? `<span class="pill ok">✓ ${esc(s.name)}</span>`
        : `<span class="pill warn" title="${esc(s.hint || '')}">✗ ${esc(s.name)}</span>`;
      return badge;
    }).join(' ') + `<span class="code-note" style="margin-left:6px">scanner deterministik: temuan pertama <5s; LLM hanya menilai konteks.</span>`;
  } catch (e) { /* offline */ }
}
renderScannerBadges();

$('b-engine').addEventListener('change', syncEngine);
$('b-full-offensive').addEventListener('change', syncEngine);
$('b-code-source-zip').addEventListener('change', syncCodeSource);
$('b-code-source-folder').addEventListener('change', syncCodeSource);
syncEngine();

// The target field lives in each engine's pop-up; keep both copies in sync so
// switching engine does not silently drop a target the operator already typed.
$('target').addEventListener('input', () => { $('target-opencode').value = $('target').value; });
$('target-opencode').addEventListener('input', () => { $('target').value = $('target-opencode').value; });

async function loadCodeModels(keepSelection) {
  const select = $('b-code-model');
  if (!select) return;
  const current = select.value;
  try {
    const res = await fetch('/api/audit/models');
    const data = await res.json();
    const models = data.models || [];
    select.innerHTML = '<option value="">(dari .env)</option>' +
      models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    if (keepSelection && current && models.includes(current)) select.value = current;
    else if (data.default) select.value = data.default;
    const list = $('b-model-list');
    if (list) list.innerHTML = models.map((m) => `<option value="${esc(m)}"></option>`).join('');
    select.dataset.loaded = '1';
  } catch (e) { /* keep the env default */ }
}

// The dropdown asks the local install what it can serve instead of making the
// operator retype a model id. The curated fallback comes from the server when
// `opencode models` is not reachable yet.
async function loadOpencodeModels(force) {
  const select = $('b-opencode-model');
  if (!select) return;
  const current = select.value;
  try {
    const res = await fetch('/api/opencode/models' + (force ? '?refresh=1' : ''));
    const data = await res.json();
    const models = data.models || [];
    if (!models.length) return;
    select.innerHTML = models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    const wanted = [current, data.default].find((m) => m && models.includes(m));
    select.value = wanted || models[0];
    select.dataset.loaded = '1';
  } catch (e) { /* keep the static DeepSeek option */ }
}

// ----------------------------------------------------------- sidebar/menu ---
function setRailMode(on) {
  document.querySelector('.shell').classList.toggle('sidebar-rail', !!on);
  try { localStorage.setItem('adaptix.sidebar', on ? 'rail' : 'full'); } catch (e) { /* private mode */ }
}
function toggleSidebar() { setRailMode(!document.querySelector('.shell').classList.contains('sidebar-rail')); }
$('sidebar-toggle').addEventListener('click', toggleSidebar);
$('sidebar-toggle-2').addEventListener('click', toggleSidebar);
try { if (localStorage.getItem('adaptix.sidebar') === 'rail') setRailMode(true); } catch (e) { /* private mode */ }
try {
  if (new URLSearchParams(location.search).get('rail') === '1') setRailMode(true);
} catch (e) { /* older engine */ }

$('brand-btn').addEventListener('click', async (e) => {
  e.stopPropagation();
  if (document.querySelector('.shell').classList.contains('sidebar-rail')) { setRailMode(false); return; }
  const pop = $('version-popover');
  if (!pop.classList.contains('hidden')) { pop.classList.add('hidden'); return; }
  pop.classList.remove('hidden');
  const v = await (await fetch('/api/version')).json();
  $('vp-body').innerHTML = `
    <div class="vp-row"><span>Version</span><span>${esc(v.version || 'unknown')}</span></div>
    ${v.commit ? `<div class="vp-row"><span>Commit</span><span>${esc(v.commit)}</span></div>` : ''}
    ${v.commit_date ? `<div class="vp-row"><span>Last commit</span><span>${new Date(v.commit_date).toLocaleDateString()}</span></div>` : ''}
    <div style="margin-top:8px">ADAPTIX has no update server; this is your local checkout, not a checked-for-updates status.</div>`;
  if (v.repo_url) { $('vp-repo').href = v.repo_url; $('vp-repo').classList.remove('hidden'); }
});
document.addEventListener('click', (e) => {
  if (!$('version-popover').contains(e.target) && e.target !== $('brand-btn'))
    $('version-popover').classList.add('hidden');
});

// ---------------------------------------------------------------- settings ---
$('sidebar-toggle-3').addEventListener('click', toggleSidebar);
$('open-settings').addEventListener('click', showSettings);
$('user-row').addEventListener('click', showSettings);
$('back-to-app').addEventListener('click', hideSettings);
document.querySelectorAll('[data-settings]').forEach((btn) => {
  btn.addEventListener('click', () => setSettingsPage(btn.dataset.settings));
});

const SETTINGS_PAGES = {
  account: { label: 'Account', icon: 'user' },
  providers: { label: 'Providers', icon: 'plug' },
  prompts: { label: 'Prompts', icon: 'doc' },
  tokens: { label: 'API Tokens', icon: 'key' },
};
let settingsData = null;
let settingsPage = 'account';

function showSettings() {
  document.querySelector('.topbar').classList.add('hidden');
  document.querySelectorAll('.panel').forEach((p) => p.classList.add('hidden'));
  $('flow-fullpage').classList.add('hidden');
  $('settings-fullpage').classList.remove('hidden');
  $('sidebar-main').classList.add('hidden');
  $('sidebar-settings').classList.remove('hidden');
  setSettingsPage(settingsPage);
  loadSettings();
}

function hideSettings() {
  $('settings-fullpage').classList.add('hidden');
  $('sidebar-settings').classList.add('hidden');
  $('sidebar-main').classList.remove('hidden');
  document.querySelector('.topbar').classList.remove('hidden');
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('hidden'));
}

function setSettingsPage(key) {
  if (!SETTINGS_PAGES[key]) key = 'account';
  settingsPage = key;
  document.querySelectorAll('[data-settings]').forEach((b) => {
    b.classList.toggle('active', b.dataset.settings === key);
  });
  $('settings-crumb').textContent = SETTINGS_PAGES[key].label;
  $('settings-crumb-ico').innerHTML = ICONS[SETTINGS_PAGES[key].icon] || '';
  renderSettingsPage();
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    settingsData = await res.json();
  } catch (e) {
    settingsData = null;
  }
  if (!settingsData) return;
  applyAccount(settingsData.account || {});
  if (!$('settings-fullpage').classList.contains('hidden')) renderSettingsPage();
}

function applyAccount(account) {
  $('user-name').textContent = account.display_name || 'admin';
  $('user-email').textContent = account.email || '';
  if (settingsData) settingsData.account = account;
}

function monthYear(iso) {
  if (!iso) return '';
  const d = new Date(String(iso).length === 10 ? iso + 'T00:00:00' : iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

function renderSettingsPage() {
  if (!settingsData) {
    $('settings-content').innerHTML = '<div class="set-card"><div class="set-empty"><div class="set-empty-title">Loading…</div></div></div>';
    return;
  }
  if (settingsPage === 'account') return renderAccount(settingsData.account || {});
  if (settingsPage === 'providers') return renderProviders();
  if (settingsPage === 'prompts') return renderPrompts();
  if (settingsPage === 'tokens') return renderTokens();
}

function renderAccount(account) {
  const name = account.display_name || 'admin';
  const email = account.email || '';
  const initial = (name.trim()[0] || 'A').toUpperCase();
  $('settings-content').innerHTML = `
    <div class="set-card">
      <div class="set-identity-row">
        <div class="set-identity">
          <div class="set-avatar">${esc(initial)}</div>
          <div>
            <div class="set-identity-name">${esc(name)}</div>
            <div class="set-identity-sub">Member since ${esc(monthYear(account.created_at))}</div>
          </div>
        </div>
        <span class="set-pill">Local account</span>
      </div>
    </div>
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">Display name</div>
          <div class="set-card-sub">The name shown across the app.</div>
        </div>
        <button class="set-btn" data-account-action="display_name">Change</button>
      </div>
      <div class="set-value"><span class="set-ico">${ICONS.user}</span>${esc(name)}</div>
    </div>
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">Email address</div>
          <div class="set-card-sub">The email you use to sign in.</div>
        </div>
        <button class="set-btn" data-account-action="email">Change</button>
      </div>
      <div class="set-value"><span class="set-ico">${ICONS.mail}</span>${esc(email)}</div>
    </div>
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">Password</div>
          <div class="set-card-sub">Change your account password.</div>
        </div>
        <button class="set-btn" data-account-action="password">Change</button>
      </div>
      <div class="set-value"><span class="set-ico">${ICONS.lock}</span><span class="dots">••••••••••••</span></div>
      <div class="set-note">ADAPTIX is a local single-operator app: there is no sign-in and no password to change.</div>
    </div>`;
  document.querySelectorAll('[data-account-action]').forEach((btn) => {
    btn.addEventListener('click', () => changeAccountField(btn.dataset.accountAction));
  });
}

async function changeAccountField(field) {
  if (field === 'password') {
    alert('ADAPTIX runs locally with no sign-in, so there is no password to change.');
    return;
  }
  const labels = { display_name: 'Display name', email: 'Email address' };
  const current = (settingsData && settingsData.account && settingsData.account[field]) || '';
  const value = prompt(labels[field], current);
  if (value === null) return;
  const res = await fetch('/api/settings', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [field]: value.trim() }),
  });
  const data = await res.json();
  if (!res.ok) { alert(data.error || 'could not save'); return; }
  applyAccount(data.account);
  renderSettingsPage();
}

function settingRows(rows) {
  return `<div class="set-list">${rows.map(([key, value]) => `
    <div class="set-list-row"><span class="k">${esc(key)}</span>
    <span class="v">${esc(value == null || value === '' ? '—' : value)}</span></div>`).join('')}</div>`;
}

function renderProviders() {
  const p = settingsData.providers || {};
  $('settings-content').innerHTML = `
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">LLM provider</div>
          <div class="set-card-sub">Read from .env when the web server starts. The API key is reported as set or unset, never its value.</div>
        </div>
      </div>
      ${settingRows([
        ['Model', p.model], ['Provider', p.provider], ['API base', p.api_base],
        ['API key', p.api_key], ['Context tokens', p.context_tokens],
        ['Call timeout', p.timeout ? p.timeout + 's' : ''], ['Reasoning effort', p.reasoning_effort],
      ])}
      <div class="set-note">Models look like <code>provider/model-name</code>, the string LiteLLM receives.</div>
    </div>
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">Ollama</div>
          <div class="set-card-sub">Local endpoint used when no API base is set and the model is an ollama family.</div>
        </div>
      </div>
      ${settingRows([['Base URL', p.ollama_base]])}
    </div>
    <div class="set-hint">Edit <code>.env</code> and restart <code>adaptix-web</code> to change these values.
      Per-provider API keys (Gemini, Groq, DeepSeek, Grok, OpenRouter) are managed on the
      <a href="#settings" data-open-tokens>API Tokens</a> page and take effect without a restart.</div>`;
  const tokensLink = document.querySelector('[data-open-tokens]');
  if (tokensLink) tokensLink.addEventListener('click', (event) => {
    event.preventDefault();
    setSettingsPage('tokens');
  });
}

function renderPrompts() {
  const rows = settingsData.prompts || [];
  $('settings-content').innerHTML = rows.map((p) => `
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">${esc(p.name)}</div>
          <div class="set-card-sub">${esc(p.purpose)}</div>
        </div>
      </div>
      <div class="set-value"><span class="set-ico">${ICONS.doc}</span><code>${esc(p.source)}</code></div>
    </div>`).join('') +
    '<div class="set-hint">Prompt text is compiled into the engine so a run\'s contract cannot drift from its validator. ADAPTIX has no editable prompt store.</div>';
}

let tokenFormOpen = false;
let tokenFormProvider = '';

function tokenRow(t) {
  const badge = t.source === 'saved' ? 'saved' : (t.source === 'env' ? 'env' : '');
  const badgeText = t.source === 'saved' ? 'web' : (t.source === 'env' ? '.env' : 'belum diset');
  return `<div class="set-token-row">
    <div class="set-token-main">
      <div class="set-token-name">${esc(t.label)} <span class="set-badge ${badge}">${badgeText}</span></div>
      <div class="set-token-meta">${esc(t.env)} · ${t.key_set ? esc(t.masked) : 'belum diset'} · ${esc(t.model)}</div>
    </div>
    <div class="set-token-actions">
      <button class="set-btn" data-token-edit="${esc(t.id)}">${t.key_set ? 'Ubah' : 'Tambah'}</button>
      <button class="set-btn" data-token-test="${esc(t.id)}" ${t.key_set ? '' : 'disabled'}>Tes</button>
      <button class="set-btn" data-token-del="${esc(t.id)}" ${t.source === 'saved' ? '' : 'disabled'}>Hapus</button>
    </div>
  </div>`;
}

function tokenModelOptions(row) {
  const models = (row.models || []).slice();
  if (row.model && !models.includes(row.model)) models.unshift(row.model);
  return models;
}

function tokenForm(rows) {
  const selected = rows.find((t) => t.id === tokenFormProvider) || rows[0] || {};
  const models = tokenModelOptions(selected);
  const custom = selected.model && !(selected.catalog || []).includes(selected.model);
  return `<div class="set-token-form">
    <div class="row">
      <label>Provider
        <select id="token-provider">
          ${rows.map((t) => `<option value="${esc(t.id)}" ${t.id === selected.id ? 'selected' : ''}>${esc(t.label)}</option>`).join('')}
        </select>
      </label>
      <label>API key ${selected.key_set ? '<span class="set-badge saved">tersimpan</span>' : ''}
        <input id="token-value" type="password" autocomplete="off" spellcheck="false"
               placeholder="${selected.key_set ? 'biarkan kosong untuk mempertahankan token' : 'tempel API key ' + esc(selected.label || '')}">
      </label>
    </div>
    <div class="row">
      <label>Model
        <select id="token-model">
          ${models.map((m) => `<option value="${esc(m)}" ${(!custom && m === selected.model) ? 'selected' : ''}>${esc(m)}</option>`).join('')}
          <option value="__custom__" ${custom ? 'selected' : ''}>model lain (ketik sendiri)…</option>
        </select>
      </label>
      <label id="token-model-custom-row" class="${custom ? '' : 'hidden'}">Model kustom
        <input id="token-model-custom" type="text" autocomplete="off" spellcheck="false"
               placeholder="${esc(selected.prefix || '')}nama-model" value="${custom ? esc(selected.model) : ''}">
      </label>
    </div>
    <div class="row token-form-actions">
      <button class="set-btn" data-token-save>Simpan</button>
      <button class="set-btn" data-token-cancel>Batal</button>
      <button class="set-btn" data-token-load>Muat daftar model</button>
      <a id="token-docs" class="set-hint" href="${esc(selected.docs || '#')}" target="_blank" rel="noreferrer">cara mendapatkan key</a>
      <span id="token-status" class="set-token-status"></span>
    </div>
  </div>`;
}

function currentTokenRow() {
  return (settingsData.tokens || []).find((t) => t.id === tokenFormProvider) || {};
}

function syncTokenModelRow() {
  const select = $('token-model');
  const row = $('token-model-custom-row');
  if (!select || !row) return;
  row.classList.toggle('hidden', select.value !== '__custom__');
}

function renderTokens() {
  const rows = settingsData.tokens || [];
  $('settings-content').innerHTML = `
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">API tokens</div>
          <div class="set-card-sub">API key + model default per provider untuk engine ADAPTIX — termasuk Code Audit.
          OpenRouter: tempel key, klik <b>Muat daftar model</b>, pilih model mana pun (mis. <code>openrouter/anthropic/claude-3.5-sonnet</code>),
          lalu model itu muncul di dropdown Code Audit tanpa restart.
          Disimpan lokal di mesin ini; key hanya ditampilkan tersamar.</div>
        </div>
        <button class="set-btn" data-token-new>+ New Token</button>
      </div>
      ${rows.length ? `<div class="set-token-list">${rows.map(tokenRow).join('')}</div>` : `
        <div class="set-empty">
          <div class="set-empty-title">No API tokens</div>
          <div class="set-empty-sub">Tambahkan key Gemini, Groq, DeepSeek, Grok (xAI), atau OpenRouter.</div>
        </div>`}
      ${tokenFormOpen ? tokenForm(rows) : ''}
      <div class="set-note">Token yang disimpan langsung dipakai run berikutnya (tanpa restart). Lokasi:
        <code>work/web_data/provider_tokens.json</code> (mode 0600). Nilai key tidak pernah dikirim balik ke browser.</div>
    </div>`;
  bindTokenActions();
}

function bindTokenActions() {
  document.querySelectorAll('[data-token-new]').forEach((b) => b.addEventListener('click', () => {
    tokenFormProvider = ((settingsData.tokens || []).find((t) => !t.key_set) || {}).id || '';
    tokenFormOpen = true;
    renderTokens();
  }));
  document.querySelectorAll('[data-token-edit]').forEach((b) => b.addEventListener('click', () => {
    tokenFormProvider = b.dataset.tokenEdit;
    tokenFormOpen = true;
    renderTokens();
  }));
  document.querySelectorAll('[data-token-cancel]').forEach((b) => b.addEventListener('click', () => {
    tokenFormOpen = false;
    renderTokens();
  }));
  const provider = $('token-provider');
  if (provider) provider.addEventListener('change', () => {
    tokenFormProvider = provider.value;
    renderTokens();
    const keyInput = $('token-value');
    if (keyInput) keyInput.focus();
  });
  const modelSelect = $('token-model');
  if (modelSelect) modelSelect.addEventListener('change', syncTokenModelRow);
  document.querySelectorAll('[data-token-save]').forEach((b) => b.addEventListener('click', saveToken));
  document.querySelectorAll('[data-token-load]').forEach((b) => b.addEventListener('click', loadTokenModels));
  const input = $('token-value');
  const customInput = $('token-model-custom');
  [input, customInput].forEach((field) => {
    if (!field) return;
    field.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveToken(); });
  });
  if (input) input.focus();
  document.querySelectorAll('[data-token-test]').forEach((b) => b.addEventListener('click', async () => {
    const id = b.dataset.tokenTest;
    b.disabled = true;
    try {
      const res = await fetch(`/api/settings/tokens/${encodeURIComponent(id)}/test`, { method: 'POST' });
      const data = await res.json();
      alert(`${id}: ${data.ok ? 'token valid' : 'token gagal'} — ${data.detail || ''}`);
    } finally { b.disabled = false; }
  }));
  document.querySelectorAll('[data-token-del]').forEach((b) => b.addEventListener('click', async () => {
    const id = b.dataset.tokenDel;
    if (!confirm(`Hapus token ${id}?`)) return;
    const res = await fetch(`/api/settings/tokens/${encodeURIComponent(id)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) { alert(data.error || 'gagal menghapus'); return; }
    settingsData.tokens = data.tokens;
    renderTokens();
    loadCodeModels(true);
  }));
}

async function loadTokenModels() {
  const provider = tokenFormProvider;
  const status = $('token-status');
  const button = document.querySelector('[data-token-load]');
  if (!provider || !status) return;
  if (button) button.disabled = true;
  status.className = 'set-token-status';
  status.textContent = 'memuat daftar model…';
  try {
    const res = await fetch(`/api/settings/tokens/${encodeURIComponent(provider)}/models`);
    const data = await res.json();
    if (!res.ok) {
      status.className = 'set-token-status err';
      status.textContent = data.error || 'gagal memuat model';
      return;
    }
    const select = $('token-model');
    const current = select.value === '__custom__'
      ? (($('token-model-custom') || {}).value || '').trim() : select.value;
    const models = (data.models || []).slice();
    if (!select) return;
    select.innerHTML = models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join('') +
      '<option value="__custom__">model lain (ketik sendiri)…</option>';
    if (current && models.includes(current)) {
      select.value = current;
    } else if (current) {
      select.value = '__custom__';
      if ($('token-model-custom')) $('token-model-custom').value = current;
    }
    const row = currentTokenRow();
    if (row) {
      row.models = models;
      row.catalog = Array.from(new Set([...(row.catalog || []), ...models]));
    }
    syncTokenModelRow();
    status.textContent = data.detail || '';
  } catch (err) {
    status.className = 'set-token-status err';
    status.textContent = 'gagal memuat model';
  } finally {
    if (button) button.disabled = false;
  }
}

async function saveToken() {
  const provider = ($('token-provider') || {}).value || tokenFormProvider;
  const token = (($('token-value') || {}).value || '').trim();
  const selected = $('token-model');
  let model = selected ? selected.value : '';
  if (model === '__custom__') model = (($('token-model-custom') || {}).value || '').trim();
  const status = $('token-status');
  if (!token && !currentTokenRow().key_set) {
    if (status) status.textContent = 'token masih kosong';
    return;
  }
  const res = await fetch('/api/settings/tokens', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, token, model }),
  });
  const data = await res.json();
  if (!res.ok) {
    if (status) { status.className = 'set-token-status err'; status.textContent = data.error || 'gagal menyimpan'; }
    return;
  }
  settingsData.tokens = data.tokens;
  tokenFormOpen = false;
  renderTokens();
  loadCodeModels(true);
}

async function loadVersion() {
  try {
    const v = await (await fetch('/api/version')).json();
    if (!v.version) return;
    $('brand-ver').textContent = 'v' + v.version;
    $('settings-ver').textContent = 'v' + v.version;
  } catch (e) { /* server not reachable yet */ }
}

// --------------------------------------------------------- top Dashboard ---
let dashView = 'analytics';
let dashPeriod = 'week';

document.querySelectorAll('#dash-analytics, #dash-overview').forEach(() => {});
document.querySelectorAll('[data-dash]').forEach((btn) => btn.addEventListener('click', () => {
  document.querySelectorAll('[data-dash]').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  dashView = btn.dataset.dash;
  $('dash-analytics').classList.toggle('hidden', dashView !== 'analytics');
  $('dash-overview').classList.toggle('hidden', dashView !== 'overview');
  $('dash-period-group').classList.toggle('hidden', dashView !== 'analytics');
  loadDashboard();
}));
document.querySelectorAll('[data-period]').forEach((btn) => btn.addEventListener('click', () => {
  document.querySelectorAll('[data-period]').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  dashPeriod = btn.dataset.period;
  loadDashboard();
}));

async function loadDashboard() {
  const res = await fetch('/api/analytics');
  const a = await res.json();
  if (dashView === 'overview') renderOverview(a);
  else renderFlowsActivityChart(a.daily || []);
}

function fmtTokens(n) {
  const v = Number(n) || 0;
  const trim = (x) => x.toFixed(1).replace(/\.0$/, '');
  if (v >= 1e9) return trim(v / 1e9) + 'B';
  if (v >= 1e6) return trim(v / 1e6) + 'M';
  if (v >= 1e3) return trim(v / 1e3) + 'K';
  return String(v);
}

function fmtMoney(v) {
  if (v == null || !isFinite(v)) return '-';
  const digits = v >= 1 ? 2 : v >= 0.01 ? 3 : 4;
  return '$' + v.toFixed(digits);
}

function fmtDuration(ms) {
  if (ms == null || !isFinite(ms)) return '-';
  if (ms < 1000) return Math.round(ms) + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1).replace(/\.0$/, '') + 's';
  if (ms < 3600000) {
    const m = Math.floor(ms / 60000);
    const s = Math.round((ms % 60000) / 1000);
    return s ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(ms / 3600000);
  const m = Math.round((ms % 3600000) / 60000);
  return m ? `${h}h ${m}m` : `${h}h`;
}

function renderOverview(a) {
  const tokens = (a.tokens_in || 0) + (a.tokens_out || 0);
  $('dashboard-cards').innerHTML = `
    <div class="ov-card">
      <div class="ov-head"><span class="ov-label">Total Flows</span><span class="ov-ico" data-icon="flows"></span></div>
      <div class="ov-value">${a.total_runs}</div>
      <div class="ov-sub">Tasks: ${a.hypotheses || 0} &middot; Subtasks: ${a.tool_calls_used || 0} &middot;<br>Assistants: 0</div>
    </div>
    <div class="ov-card">
      <div class="ov-head"><span class="ov-label">Tool Calls</span><span class="ov-ico" data-icon="pulse"></span></div>
      <div class="ov-value">${a.tool_calls_used || 0}</div>
      <div class="ov-sub">Total duration: ${fmtDuration((a.duration_seconds || 0) * 1000)}</div>
    </div>
    <div class="ov-card">
      <div class="ov-head"><span class="ov-label">Total Tokens</span><span class="ov-ico" data-icon="chip"></span></div>
      <div class="ov-value">${fmtTokens(tokens)}</div>
      <div class="ov-sub">Input + Output tokens<br>processed</div>
    </div>
    <div class="ov-card">
      <div class="ov-head"><span class="ov-label">Total Cost</span><span class="ov-ico" data-icon="dollar"></span></div>
      <div class="ov-value">${a.cost_known ? fmtMoney(a.total_cost) : '-'}</div>
      <div class="ov-sub">Total LLM spending across<br>all providers</div>
    </div>`;
  document.querySelectorAll('#dashboard-cards [data-icon]').forEach((el) => {
    el.innerHTML = ICONS[el.dataset.icon] || '';
  });
  renderAnaUsage($('ana-provider-body'), a.providers || [], 8);
  renderAnaUsage($('ana-model-body'), a.models || [], 8);
  renderAnaUsage($('ana-agent-body'), a.agents || [], 8);
  renderAnaTools($('ana-tool-body'), a.tools || []);
}

function renderAnaUsage(body, rows, columns) {
  if (!rows.length) {
    body.innerHTML = `<tr class="ana-empty"><td colspan="${columns}">No LLM calls recorded yet</td></tr>`;
    return;
  }
  body.innerHTML = rows.map((r) => `
    <tr>
      <td class="ana-name">${esc(r.name)}</td>
      <td>${fmtTokens(r.tokens_in)}</td>
      <td>${fmtTokens(r.tokens_out)}</td>
      <td>${fmtTokens(r.cache_in)}</td>
      <td>${fmtTokens(r.cache_out)}</td>
      <td>${r.cost_known ? fmtMoney(r.cost_in) : '-'}</td>
      <td>${r.cost_known ? fmtMoney(r.cost_out) : '-'}</td>
      <td class="ana-total">${r.cost_known ? fmtMoney(r.cost_in + r.cost_out) : '-'}</td>
    </tr>`).join('');
}

function renderAnaTools(body, rows) {
  if (!rows.length) {
    body.innerHTML = '<tr class="ana-empty"><td colspan="5">No tool calls recorded yet</td></tr>';
    return;
  }
  body.innerHTML = rows.map((r) => {
    const avg = r.duration_known && r.count ? r.total_ms / r.count : null;
    return `<tr>
      <td class="ana-name">${esc(r.name)}</td>
      <td><span class="ana-pill ${r.type === 'Agent' ? 'agent' : ''}">${esc(r.type || 'Tool')}</span></td>
      <td>${r.count}</td>
      <td>${r.duration_known ? fmtDuration(r.total_ms) : '-'}</td>
      <td>${r.duration_known ? fmtDuration(avg) : '-'}</td>
    </tr>`;
  }).join('');
}

function niceTicks(rawMax) {
  const raw = Math.max(1, rawMax);
  const step = Math.max(1, Math.ceil(raw / 5));
  const top = Math.max(step, Math.ceil((raw * 1.15) / step) * step);
  const ticks = [];
  for (let v = 0; v <= top + 1e-9; v += step) ticks.push(v);
  return ticks;
}

function localDateKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function renderFlowsActivityChart(daily) {
  const box = $('chart-flows-activity');
  const days = dashPeriod === 'week' ? 7 : dashPeriod === 'month' ? 30 : 90;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const byDate = Object.fromEntries(daily.map((d) => [d.date, d.count]));
  const points = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today); d.setDate(d.getDate() - i);
    const key = localDateKey(d);
    points.push({ label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), count: byDate[key] || 0 });
  }
  const ticks = niceTicks(Math.max(0, ...points.map((p) => p.count)));
  const top = ticks[ticks.length - 1];
  const w = 1000, h = 330;
  const padL = 52, padR = 14, padT = 12, padB = 40;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const slot = plotW / points.length;
  const barW = Math.min(22, Math.max(4, slot * 0.45));
  const yFor = (value) => padT + plotH - (value / top) * plotH;
  const baseY = yFor(0);

  const hGrid = ticks.map((t) => `<line class="chart-grid" x1="${padL}" x2="${w - padR}" y1="${yFor(t).toFixed(1)}" y2="${yFor(t).toFixed(1)}"></line>`).join('');
  const yLabels = ticks.map((t) => `<text class="chart-tick" x="${padL - 12}" y="${(yFor(t) + 4).toFixed(1)}" text-anchor="end">${esc(String(t))}</text>`).join('');

  const everyNth = points.length <= 8 ? 1 : Math.max(1, Math.ceil(points.length / 12));
  const vGrid = points.map((p, i) => (i % everyNth === 0 || i === points.length - 1)
    ? `<line class="chart-grid" x1="${(padL + slot * (i + 0.5)).toFixed(1)}" x2="${(padL + slot * (i + 0.5)).toFixed(1)}" y1="${padT}" y2="${baseY.toFixed(1)}"></line>` : '').join('');

  const bars = points.map((p, i) => {
    if (!p.count) return '';
    const cx = padL + slot * (i + 0.5);
    const y = yFor(p.count);
    return `<rect x="${(cx - barW / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${Math.max(2, baseY - y).toFixed(1)}" rx="2" fill="url(#chartBar)"></rect>`;
  }).join('');

  const labels = points.map((p, i) => (i % everyNth === 0 || i === points.length - 1)
    ? `<text class="chart-xlabel" x="${(padL + slot * (i + 0.5)).toFixed(1)}" y="${baseY + 26}" text-anchor="middle">${esc(p.label)}</text>` : '').join('');

  box.innerHTML = `<svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="Flows activity per day">
    <defs>
      <linearGradient id="chartBar" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" style="stop-color: var(--accent)"></stop>
        <stop offset="100%" style="stop-color: var(--accent)"></stop>
      </linearGradient>
    </defs>
    ${hGrid}${vGrid}
    <line class="chart-axis-line" x1="${padL}" x2="${padL}" y1="${padT}" y2="${baseY.toFixed(1)}"></line>
    <line class="chart-axis-line" x1="${padL}" x2="${w - padR}" y1="${baseY.toFixed(1)}" y2="${baseY.toFixed(1)}"></line>
    ${yLabels}${bars}${labels}
  </svg>`;
}

function renderUsageTable(body, ledger) {
  if (!ledger.length) {
    body.innerHTML = '<tr class="empty-row"><td colspan="6">No LLM calls yet this run</td></tr>';
    return;
  }
  const byModel = {};
  for (const row of ledger) {
    const m = byModel[row.model] || (byModel[row.model] = { calls: 0, in: 0, out: 0, cache: 0, failed: 0 });
    m.calls++; m.in += row.prompt_tokens; m.out += row.completion_tokens;
    if (row.cache_hit) m.cache++;
    if (row.failed) m.failed++;
  }
  body.innerHTML = Object.entries(byModel).map(([name, m]) => `
    <tr><td>${esc(name)}</td><td>${m.calls}</td><td>${m.in.toLocaleString()}</td>
    <td>${m.out.toLocaleString()}</td><td>${m.cache}</td><td>${m.failed}</td></tr>`).join('');
}

function renderUsageTableWithProvider(body, ledger) {
  if (!ledger.length) {
    body.innerHTML = '<tr class="empty-row"><td colspan="7">No LLM calls yet this run</td></tr>';
    return;
  }
  const byModel = {};
  for (const row of ledger) {
    const m = byModel[row.model] || (byModel[row.model] = { calls: 0, in: 0, out: 0, cache: 0, failed: 0 });
    m.calls++; m.in += row.prompt_tokens; m.out += row.completion_tokens;
    if (row.cache_hit) m.cache++;
    if (row.failed) m.failed++;
  }
  // LiteLLM model strings are "provider/model-name"; split what's there rather
  // than invent a provider ADAPTIX never recorded.
  body.innerHTML = Object.entries(byModel).map(([name, m]) => {
    const [provider, ...rest] = name.split('/');
    const model = rest.length ? rest.join('/') : name;
    return `<tr><td>${esc(model)}</td><td>${esc(rest.length ? provider : '-')}</td><td>${m.calls}</td>
      <td>${m.in.toLocaleString()}</td><td>${m.out.toLocaleString()}</td><td>${m.cache}</td><td>${m.failed}</td></tr>`;
  }).join('');
}

// ------------------------------------------------------------------ flows ---
// The exact tab set and order PentAGI shows inside an open flow. ADAPTIX does
// not have every one of these features; the ones it lacks say so honestly
// instead of faking data.
const FLOW_TABS = [
  ['automation', 'Automation'], ['assistant', 'Assistant'], ['dashboard', 'Dashboard'],
  ['terminal', 'Terminal'], ['tasks', 'Tasks'], ['agents', 'Agents'],
  ['searches', 'Searches'], ['vectorstore', 'Vector Store'], ['files', 'Files'],
  ['screenshots', 'Screenshots'],
];
const FLOW_TAB_UNAVAILABLE = {
  assistant: 'ADAPTIX has no separate assistant chat. Automation is the only conversation with this flow.',
  vectorstore: 'ADAPTIX does not keep a vector memory between flows.',
};

let selectedFlow = null;
let selectedFlowTab = 'automation';
let lastFlowView = null;
let renderedFlowId = null; // which flow's tab-bar chrome is currently built in the DOM
let searchQuery = '';
let flowsFilter = '';

async function loadFlows() {
  const res = await fetch('/api/flows');
  const data = await res.json();
  const flows = data.flows || [];
  renderRecentFlows(flows);
  renderFlowsPage(flows);
  if (selectedFlow && !$('flow-fullpage').classList.contains('hidden')) refreshFlowDetail();
}

const TL_ICON = {
  bot: '<svg viewBox="0 0 24 24"><rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01"/></svg>',
  warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:100%;height:100%"><path d="M12 4 2.8 20h18.4L12 4z"/><path d="M12 10v4M12 17h.01"/></svg>',
};
// ---- Flows history: grouped by date, status priority or custom group -------
const GROUP_MODES = [['date', 'Tanggal'], ['status', 'Status prioritas'], ['custom', 'Grup kustom']];
let flowsGroupMode = 'date';
try { flowsGroupMode = localStorage.getItem('adaptix.flowsGroup') || 'date'; } catch (e) { /* storage unavailable */ }
if (!GROUP_MODES.some((m) => m[0] === flowsGroupMode)) flowsGroupMode = 'date';
const collapsedGroups = new Set();
let lastFlowsList = [];

function flowBucket(f) {
  if (flowsGroupMode === 'status') {
    const st = String(f.status || '').toLowerCase();
    if (f.live) return { order: 0, label: 'Berjalan' };
    if (/fail|error|stop|cancel/.test(st)) return { order: 1, label: 'Perlu perhatian' };
    if (st.startsWith('completed')) return { order: 2, label: 'Selesai' };
    return { order: 3, label: 'Lainnya' };
  }
  if (flowsGroupMode === 'custom') return f.group ? { order: 0, label: f.group } : { order: 1, label: 'Tanpa grup' };
  if (!f.started_at) return { order: 1e15, label: 'Tanggal tidak diketahui' };
  const d = new Date(f.started_at * 1000);
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const now = new Date();
  const diff = Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - day) / 86400000);
  const label = diff === 0 ? 'Hari ini' : diff === 1 ? 'Kemarin'
    : day.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: day.getFullYear() === now.getFullYear() ? undefined : 'numeric' });
  return { order: -day.getTime(), label };
}

function flowCardHtml(f) {
  const provider = (f.model || '').split('/')[0] || '-';
  const created = f.started_at ? new Date(f.started_at * 1000).toLocaleString() : '-';
  const st = String(f.status || '');
  const cls = f.live ? 'running' : (/fail|error/.test(st) ? 'failed' : (st.startsWith('completed') ? 'done' : ''));
  const name = f.title || (f.objective ? f.objective.slice(0, 60) : (f.target[0] || 'untitled'));
  return `<div class="tl-item ${cls === 'running' ? 'running' : (cls === 'done' ? 'done' : '')}">
    <div class="tl-card clickable" data-run="${esc(f.run_id)}">
      <div class="tl-ico">${TL_ICON.bot}</div>
      <div class="tl-main"><div class="tl-name">${f.favorite ? '★ ' : ''}${esc(name)}</div>
        <div class="tl-meta"><span>${esc(f.run_id)}</span><span>${esc(f.target[0] || '-')}</span><span>${esc(provider)}</span><span>${esc(created)}</span></div></div>
      <div class="tl-side">
        ${f.findings ? `<span class="pill">${f.findings} findings${f.verified ? ' · ' + f.verified + ' verified' : ''}</span>` : ''}
        ${flowsGroupMode === 'custom' ? `<button class="tl-btn" data-group-for="${esc(f.run_id)}">${f.group ? esc(f.group) : 'Pilih grup'} ▾</button>` : ''}
        <span class="chip ${cls}">${esc(f.live ? 'running' : st || 'idle')}</span></div>
    </div></div>`;
}

function renderFlowsPage(flows) {
  lastFlowsList = flows;
  const showTable = flows.length > 0;
  $('flows-table-view').classList.toggle('hidden', !showTable);
  $('flows-empty').classList.toggle('hidden', showTable);
  if (!showTable) return;
  const q = flowsFilter.toLowerCase();
  const rows = flows.filter((f) => !q || matchesText(q, f.run_id, f.objective, f.target[0], f.status, f.group, f.title));
  const buckets = new Map();
  rows.slice().sort((a, b) => (b.started_at || 0) - (a.started_at || 0)).forEach((f) => {
    const bk = flowBucket(f);
    if (!buckets.has(bk.label)) buckets.set(bk.label, { ...bk, items: [] });
    buckets.get(bk.label).items.push(f);
  });
  const groups = [...buckets.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label));
  $('flows-timeline').innerHTML = groups.map((g) => `<div class="tl-group ${collapsedGroups.has(flowsGroupMode + g.label) ? 'collapsed' : ''}">
    <button class="tl-group-head" data-group-head="${esc(flowsGroupMode + g.label)}">${g.label ? esc(g.label) : ''}
      <svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg><span class="n">${g.items.length}</span></button>
    <div class="tl-seq">${g.items.map(flowCardHtml).join('')}</div></div>`).join('')
    || '<div class="empty-sub">Tidak ada flow yang cocok.</div>';
}

$('flows-timeline').classList.replace('tl-list', 'tl-groups');
$('flows-timeline').addEventListener('click', (e) => {
  const head = e.target.closest('[data-group-head]');
  if (head) {
    const k = head.dataset.groupHead;
    if (collapsedGroups.has(k)) collapsedGroups.delete(k); else collapsedGroups.add(k);
    renderFlowsPage(lastFlowsList);
    return;
  }
  const gbtn = e.target.closest('[data-group-for]');
  if (gbtn) { e.stopPropagation(); openGroupPicker(gbtn); return; }
  const card = e.target.closest('.tl-card[data-run]');
  if (card) openFlow(card.dataset.run);
});

async function setFlowGroup(runId, group) {
  const f = lastFlowsList.find((x) => x.run_id === runId);
  if (f) f.group = group;
  closeGroupPicker();
  renderFlowsPage(lastFlowsList);
  try {
    await fetch('/api/flows/' + encodeURIComponent(runId) + '/group', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ group }),
    });
  } catch (e) { /* retried on next list refresh */ }
}

function closeGroupPicker() { const p = document.getElementById('group-pop'); if (p) p.remove(); }

function openGroupPicker(btn) {
  closeGroupPicker();
  const runId = btn.dataset.groupFor;
  const names = [...new Set(lastFlowsList.map((f) => f.group).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const pop = document.createElement('div');
  pop.id = 'group-pop';
  pop.className = 'group-pop';
  pop.innerHTML = names.map((n) => `<button class="menu-row" data-g="${esc(n)}">${esc(n)}</button>`).join('')
    + '<button class="menu-row" data-new="1">+ Grup baru…</button>'
    + (lastFlowsList.find((f) => f.run_id === runId && f.group) ? '<button class="menu-row" data-none="1">Keluarkan dari grup</button>' : '');
  const r = btn.getBoundingClientRect();
  pop.style.top = Math.min(r.bottom + 6, window.innerHeight - 220) + 'px';
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 230)) + 'px';
  pop.addEventListener('click', (e) => {
    const t = e.target.closest('.menu-row');
    if (!t) return;
    if (t.dataset.new) {
      const name = (window.prompt('Nama grup baru (maks. 40 karakter):') || '').trim();
      if (name) setFlowGroup(runId, name.slice(0, 40)); else closeGroupPicker();
    } else if (t.dataset.none) setFlowGroup(runId, '');
    else setFlowGroup(runId, t.dataset.g);
  });
  document.body.appendChild(pop);
}

function renderFlowsMenu() {
  const cur = GROUP_MODES.find((m) => m[0] === flowsGroupMode)[1];
  $('flows-menu').innerHTML = `<div class="menu-row" style="cursor:default"><span>Kelompokkan berdasarkan</span><span class="mv">${cur}</span></div>
    <div class="menu-sub">${GROUP_MODES.map(([k, label]) => `<button class="menu-row opt" data-mode="${k}"><span><span class="ck">${k === flowsGroupMode ? '✓' : ''}</span> ${label}</span></button>`).join('')}</div>`;
}

$('flows-menu-btn').addEventListener('click', (e) => {
  e.stopPropagation();
  renderFlowsMenu();
  $('flows-menu').classList.toggle('hidden');
});
$('flows-menu').addEventListener('click', (e) => {
  const t = e.target.closest('[data-mode]');
  if (!t) return;
  flowsGroupMode = t.dataset.mode;
  try { localStorage.setItem('adaptix.flowsGroup', flowsGroupMode); } catch (err) { /* ignore */ }
  $('flows-menu').classList.add('hidden');
  renderFlowsPage(lastFlowsList);
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('#flows-menu, #flows-menu-btn')) $('flows-menu').classList.add('hidden');
  if (!e.target.closest('#group-pop, [data-group-for]')) closeGroupPicker();
});

function matchesText(q, ...fields) {
  return fields.some((f) => String(f || '').toLowerCase().includes(q));
}

function openNewFlow() {
  activateTab('chat');
  setTimeout(() => $('instruction').focus(), 60);
}
$('new-flow-btn').addEventListener('click', openNewFlow);
$('rail-new-flow').addEventListener('click', openNewFlow);
$('flows-empty-cta').addEventListener('click', openNewFlow);
$('flows-filter').addEventListener('input', (e) => { flowsFilter = e.target.value; loadFlows(); });

function renderRecentFlows(flows) {
  const box = $('recent-flows');
  if (!flows.length) {
    box.innerHTML = '<div class="empty-small">no flows yet</div>';
    return;
  }
  box.innerHTML = flows.slice(0, 4).map((f) => {
    const title = f.title || (f.objective ? f.objective.slice(0, 40) : (f.target[0] || f.run_id));
    return `
    <div class="recent-flow" data-run="${esc(f.run_id)}" title="${esc(title)}">
      <span class="badge">${f.live ? '🟢' : esc(f.run_id.slice(-2))}</span>
      <span class="recent-flow-title">${f.favorite ? '★ ' : ''}${esc(title)}</span>
    </div>`;
  }).join('');
  box.querySelectorAll('.recent-flow').forEach((row) => {
    row.addEventListener('click', () => openFlow(row.dataset.run));
  });
}

// Opening a flow fills the content pane next to the sidebar, same as PentAGI:
// the sidebar stays, only the topbar and the active page panel are swapped out.
function openFlow(runId) {
  selectedFlow = runId;
  renderedFlowId = null; // force the tab bar to rebuild for the newly opened flow
  searchQuery = '';
  document.querySelector('.topbar').classList.add('hidden');
  document.querySelectorAll('.panel.active').forEach((p) => p.classList.add('hidden'));
  $('flow-fullpage').classList.remove('hidden');
  refreshFlowDetail();
}

$('flow-back-btn').addEventListener('click', () => { closeFlowView(); });

async function refreshFlowDetail() {
  if (!selectedFlow) return;
  const res = await fetch('/api/flows/' + encodeURIComponent(selectedFlow));
  if (!res.ok) return;
  lastFlowView = await res.json();
  renderFlowDetail(lastFlowView);
}

function setFlowTab(key) {
  selectedFlowTab = key;
  $('ff-search').value = '';
  searchQuery = '';
  if (lastFlowView) renderFlowSubPanel(lastFlowView);
}

const FLOW_SEARCH_PLACEHOLDER = {
  automation: 'Search messages...', dashboard: 'Search usage...', terminal: 'Search terminal logs...',
  tasks: 'Search tasks and subtasks...', agents: 'Search agent logs...', searches: 'Search tool logs...',
  vectorstore: 'Search vector store logs...', files: 'Search files...', screenshots: 'Search screenshots...',
};

function renderFlowDetail(view) {
  // Rebuilding the header + tab bar on every 2s poll would discard whatever
  // horizontal scroll position the operator just set. Build that chrome once
  // per opened flow, then every later call only touches the content pane.
  if (renderedFlowId !== view.run_id) {
    $('ff-tabs').innerHTML = FLOW_TABS.map(([key, label]) =>
      `<button class="flow-tab ${key === selectedFlowTab ? 'active' : ''}" data-ftab="${key}">${label}</button>`).join('');
    $('ff-tabs').querySelectorAll('.flow-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        $('ff-tabs').querySelectorAll('.flow-tab').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        setFlowTab(btn.dataset.ftab);
      });
    });
    // A vertical wheel gesture scrolls this horizontal strip too, same as a
    // trackpad shift-scroll - the row is wider than the panel on a laptop screen.
    const wrap = document.querySelector('.flow-fullpage .flow-tabs-wrap');
    wrap.onwheel = (e) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { wrap.scrollLeft += e.deltaY; e.preventDefault(); }
    };
    renderedFlowId = view.run_id;
  }
  $('ff-status-dot').className = 'status-dot' + (view.running ? ' running' : '');
  $('ff-title').textContent = view.title || view.objective || view.run_id;
  $('ff-live-pill').classList.toggle('hidden', !view.running);
  const finished = !view.running && view.iteration > 0;
  $('ff-report-btn').classList.toggle('hidden', !finished);
  $('ff-star-btn').textContent = view.favorite ? '★' : '☆';
  $('ff-finish-btn').disabled = !view.running;
  $('ff-finish-btn').style.opacity = view.running ? '1' : '.4';
  $('ff-search').placeholder = FLOW_SEARCH_PLACEHOLDER[selectedFlowTab] || 'Search...';
  renderFlowSubPanel(view);
}

$('ff-report-btn').addEventListener('click', () => {
  $('ff-tabs').querySelectorAll('.flow-tab').forEach((b) => b.classList.toggle('active', b.dataset.ftab === 'automation'));
  setFlowTab('automation');
});

$('ff-star-btn').addEventListener('click', async () => {
  if (!selectedFlow) return;
  const res = await fetch('/api/flows/' + encodeURIComponent(selectedFlow) + '/favorite', { method: 'POST' });
  const d = await res.json();
  $('ff-star-btn').textContent = d.favorite ? '★' : '☆';
});

$('ff-menu-btn').addEventListener('click', (e) => {
  e.stopPropagation();
  $('ff-menu').classList.toggle('hidden');
});
document.addEventListener('click', (e) => {
  if (!$('ff-menu').contains(e.target) && e.target !== $('ff-menu-btn')) $('ff-menu').classList.add('hidden');
});

$('ff-rename-btn').addEventListener('click', async () => {
  $('ff-menu').classList.add('hidden');
  if (!selectedFlow) return;
  const current = $('ff-title').textContent;
  const title = prompt('Rename this flow', current);
  if (title === null) return;
  await fetch('/api/flows/' + encodeURIComponent(selectedFlow) + '/title', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
  });
  refreshFlowDetail();
});

$('ff-finish-btn').addEventListener('click', async () => {
  $('ff-menu').classList.add('hidden');
  if (!lastFlowView || !lastFlowView.running) return;
  await fetch('/api/cancel', { method: 'POST' });
  refreshFlowDetail();
});

$('ff-delete-btn').addEventListener('click', async () => {
  $('ff-menu').classList.add('hidden');
  if (!selectedFlow) return;
  if (!confirm('Delete this flow and all its saved artifacts? This cannot be undone.')) return;
  const res = await fetch('/api/flows/' + encodeURIComponent(selectedFlow), { method: 'DELETE' });
  if (!res.ok) { const d = await res.json(); alert(d.error || 'could not delete'); return; }
  $('flow-back-btn').click();
  loadFlows();
});

$('ff-search').addEventListener('input', (e) => {
  searchQuery = e.target.value.trim().toLowerCase();
  if (lastFlowView) renderFlowSubPanel(lastFlowView);
});

function matches(...fields) {
  if (!searchQuery) return true;
  return fields.some((f) => String(f || '').toLowerCase().includes(searchQuery));
}

function externalState(view) {
  return (view.external && view.external.state) || {};
}

function externalCounts(view) {
  return externalState(view).counts || {};
}

function renderExternalAutomation(view) {
  const external = view.external || {};
  const state = externalState(view);
  const counts = state.counts || {};
  const insights = external.insights || [];
  const activity = (external.activity || []).slice(-40).reverse();
  const findings = external.findings || [];
  const insightHtml = insights.length ? insights.slice().reverse().slice(0, 8).map((row) => {
    const items = (row.insights || []).map((item) => `
      <div class="insight-item">
        <span class="insight-kind ${esc(item.kind)}">${esc(item.kind)}</span>
        <b>${esc(item.title)}</b>
        <div class="insight-detail">${esc(item.detail)}</div>
        ${item.next_step ? `<div class="insight-next">Next: ${esc(item.next_step)}</div>` : ''}
      </div>`).join('');
    return `<div class="insight-card">
      <div class="insight-head"><span class="insight-headline">${esc(row.headline || row.current_activity || 'Reviewer')}</span>
        <span class="pill">${esc(row.model || 'reviewer')}</span></div>
      ${items}
      ${(row.coverage_gaps || []).length ? `<div class="insight-gap">Gap: ${row.coverage_gaps.map(esc).join(' · ')}</div>` : ''}
    </div>`;
  }).join('') : '<div class="empty-sub">Reviewer insights will appear after the first commands.</div>';
  const activityHtml = activity.length ? activity.map((row) => `
    <div class="activity-row">
      <span class="activity-time">${esc((row.created_at || '').slice(11, 19))}</span>
      <span class="pill">${esc(row.tool || row.agent || 'event')}</span>
      <span class="activity-cmd" title="${esc(row.command || row.summary || '')}">${esc(row.command || row.summary || '')}</span>
      <span class="activity-exit ${row.exit_code === 0 ? 'ok' : (row.exit_code ? 'bad' : '')}">${row.exit_code == null ? '' : 'exit ' + row.exit_code}</span>
    </div>`).join('') : '<div class="empty-sub">Waiting for opencode-pentester…</div>';
  const findingHtml = findings.length ? findings.map((row) => `
    <div class="finding-card">
      <div class="finding-head"><span class="sev ${sevClass(row.severity)}">${esc(row.severity || 'info')}</span>
        <span>${esc(row.title || 'external finding')}</span><span class="pill">external</span></div>
      <div class="finding-row">${esc(row.description || '')}</div>
      ${row.evidence_file ? `<div class="finding-row">evidence&nbsp; ${esc(row.evidence_file)}</div>` : ''}
    </div>`).join('') : '<div class="empty-sub">No external findings yet.</div>';
  $('ff-content').innerHTML = `
    <div class="flow-detail-cards">
      <div class="card"><div class="label">Engine</div><div class="value" style="font-size:15px">OpenCode${view.full_offensive ? ' · full offensive' : ''}</div><div class="sub">${esc(state.state || 'starting')}</div></div>
      <div class="card"><div class="label">Commands</div><div class="value">${counts.commands || 0}</div><div class="sub">${counts.leads_open || 0} open leads</div></div>
      <div class="card"><div class="label">Findings</div><div class="value">${counts.vulns || 0}</div><div class="sub">${counts.confirmed || 0} confirmed by engine</div></div>
      <div class="card"><div class="label">Surface</div><div class="value" style="font-size:18px">${counts.hosts || 0} host · ${counts.services || 0} svc</div><div class="sub">${counts.chains || 0} chains</div></div>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">Reviewer insights</div>
      <div class="dash-card-sub">Read-only review of commands and output. It never creates findings.</div>
      <div class="insight-list">${insightHtml}</div>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">Live activity</div>
      <div class="dash-card-sub">Commands recorded by opencode-pentester in its SQLite session log.</div>
      <div class="activity-list">${activityHtml}</div>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">External findings</div>
      <div class="dash-card-sub">Produced by opencode-pentester; not independently verified by ADAPTIX.</div>
      <div class="findings-list">${findingHtml}</div>
    </div>`;
}

function renderExternalTasks(view) {
  const state = externalState(view);
  const gate = state.gate || {};
  const phases = gate.phases || {};
  const pending = gate.pending || [];
  const insights = (view.external && view.external.insights) || [];
  const phaseRows = Object.entries(phases).map(([name, row]) => {
    const done = row.total && row.satisfied === row.total;
    return `<div class="task-row"><span class="task-dot">${done ? '✔' : '▶'}</span>
      <div><div class="task-title">${esc(name)}</div>
      <div class="task-sub">${row.satisfied || 0}/${row.total || 0} mandatory items</div></div></div>`;
  }).join('') || '<div class="empty-sub">Waiting for the first gate evaluation.</div>';
  const pendingRows = pending.length ? pending.map((row) => `
    <div class="task-row"><span class="task-dot">!</span>
      <div><div class="task-title">${esc(row.item || 'pending item')}</div>
      <div class="task-sub">${esc(row.phase || '')}${row.tools ? ' · tools: ' + esc(row.tools) : ''}</div></div></div>`).join('')
    : '<div class="empty-sub">No pending mandatory items recorded yet.</div>';
  const notes = insights.slice().reverse().slice(0, 6).flatMap((row) => (row.insights || []).map((item) => `
    <div class="task-row"><span class="task-dot">✦</span>
      <div><div class="task-title">${esc(item.title)}</div>
      <div class="task-sub">${esc(item.detail || '')}${item.next_step ? ' → ' + esc(item.next_step) : ''}</div></div></div>`)).join('');
  $('ff-content').innerHTML = `
    <div class="tasks-grid">
      <div class="card"><div class="label">Engagement state</div><div class="value" style="font-size:18px">${esc(state.state || 'starting')}</div></div>
      <div class="card"><div class="label">Gate</div><div class="value">${gate.mandatory_satisfied || 0}/${gate.mandatory_total || 0}</div><div class="sub">mandatory items satisfied</div></div>
      <div class="card"><div class="label">Open leads</div><div class="value">${(state.counts || {}).leads_open || 0}</div></div>
    </div>
    <div class="dash-card-title" style="margin-top:6px">Deterministic gate</div>
    <div class="task-list">${phaseRows}</div>
    <div class="dash-card-title" style="margin-top:6px">Pending items</div>
    <div class="task-list">${pendingRows}</div>
    <div class="dash-card-title" style="margin-top:6px">Reviewer notes</div>
    <div class="task-list">${notes || '<div class="empty-sub">No reviewer notes yet.</div>'}</div>`;
}

function renderExternalDashboard(view) {
  const state = externalState(view);
  const counts = state.counts || {};
  const gate = state.gate || {};
  const severity = state.severity || {};
  const phases = Object.entries(gate.phases || {}).map(([name, row]) => `
    <tr><td>${esc(name)}</td><td>${row.satisfied || 0}/${row.total || 0}</td>
    <td>${row.total && row.satisfied === row.total ? 'pass' : 'pending'}</td></tr>`).join('');
  $('ff-content').innerHTML = `
    <div class="flow-detail-cards">
      <div class="card"><div class="label">Commands</div><div class="value">${counts.commands || 0}</div></div>
      <div class="card"><div class="label">Hosts</div><div class="value">${counts.hosts || 0}</div></div>
      <div class="card"><div class="label">Vulns</div><div class="value">${counts.vulns || 0}</div><div class="sub">${counts.confirmed || 0} confirmed</div></div>
      <div class="card"><div class="label">Leads</div><div class="value">${counts.leads_open || 0}</div><div class="sub">${counts.leads_total || 0} total</div></div>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">Severity</div>
      <div class="dash-card-sub">External findings by severity.</div>
      <table class="usage-table"><thead><tr><th>Severity</th><th>Count</th></tr></thead><tbody>
        ${Object.entries(severity).map(([name, n]) => `<tr><td>${esc(name)}</td><td>${n}</td></tr>`).join('') || '<tr class="empty-row"><td colspan="2">No findings yet</td></tr>'}
      </tbody></table>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">Gate by phase</div>
      <div class="dash-card-sub">Deterministic completion gate from opencode-pentester.</div>
      <table class="usage-table"><thead><tr><th>Phase</th><th>Items</th><th>Status</th></tr></thead><tbody>${phases || '<tr class="empty-row"><td colspan="3">Waiting for gate</td></tr>'}</tbody></table>
    </div>`;
}

function renderExternalAgents(view) {
  const activity = (view.external && view.external.activity) || [];
  const groups = {};
  for (const row of activity) {
    const name = row.agent || 'opencode';
    const group = groups[name] || (groups[name] = { count: 0, last: row, failures: 0 });
    group.count++;
    group.last = row;
    if (row.exit_code && row.exit_code !== 0) group.failures++;
  }
  const rows = Object.entries(groups).map(([name, row]) => `
    <div class="finding-card"><div class="finding-head"><span>${esc(name)}</span>
      <span class="pill">${row.count} commands</span>${row.failures ? `<span class="sev high">${row.failures} failed</span>` : ''}</div>
      <div class="finding-row">last&nbsp; ${esc(row.last.command || row.last.summary || '')}</div></div>`).join('');
  $('ff-content').innerHTML = rows ? `<div class="findings-list">${rows}</div>`
    : '<div class="empty-state"><div class="empty-icon">Σ</div><div class="empty-title">No agent activity yet</div></div>';
}


let selectedTerminal = 'commands';
let terminalSignature = '';

// Every stream the external engine writes is addressable, so "how did it run"
// is answered by reading the actual terminal, not a merged summary. The toolbar
// is rebuilt only when the terminal set changes; the log body refreshes on the
// normal flow poll.
async function renderTerminal(view) {
  const box = $('ff-content');
  const terminals = view.terminals || [];
  if (!terminals.length) {
    box.innerHTML = `<div class="empty-state"><div class="empty-icon">⌁</div>
      <div class="empty-title">No terminal logs yet</div>
      <div class="empty-sub">The engine writes its logs once the run starts.</div></div>`;
    return;
  }
  const active = terminals.some((t) => t.key === selectedTerminal) ? selectedTerminal : terminals[0].key;
  const signature = terminals.map((t) => t.key).join(',');
  if (!box.querySelector('#ff-term-select') || terminalSignature !== signature) {
    terminalSignature = signature;
    box.innerHTML = `<div class="terminal-shell">
      <div class="terminal-toolbar">
        <select id="ff-term-select">${terminals.map((t) =>
          `<option value="${esc(t.key)}">${esc(t.label)}</option>`).join('')}</select>
        <button id="ff-term-refresh" title="Reload this terminal">refresh</button>
        <span class="term-meta" id="ff-term-meta"></span>
      </div>
      <pre class="terminal-view" id="ff-term-body">Loading…</pre>
    </div>`;
    $('ff-term-select').addEventListener('change', (e) => {
      selectedTerminal = e.target.value;
      terminalSignature = '';
      if (lastFlowView) renderTerminal(lastFlowView);
    });
    $('ff-term-refresh').addEventListener('click', () => {
      terminalSignature = '';
      if (lastFlowView) renderTerminal(lastFlowView);
    });
  }
  $('ff-term-select').value = active;
  let data = { exists: false, text: '' };
  try {
    const res = await fetch(`/api/flows/${encodeURIComponent(view.run_id)}/terminal/${encodeURIComponent(active)}?lines=1000`);
    data = await res.json();
  } catch (e) { /* keep the previous content on a transient fetch failure */ }
  const body = $('ff-term-body');
  if (!body) return;
  const atBottom = body.scrollTop + body.clientHeight >= body.scrollHeight - 30;
  const lines = String(data.text || '').split('\n');
  const filtered = searchQuery ? lines.filter((l) => l.toLowerCase().includes(searchQuery)) : lines;
  body.textContent = filtered.join('\n') || 'No log lines yet.';
  const meta = $('ff-term-meta');
  if (meta) meta.textContent = data.exists
    ? `${(data.size / 1024).toFixed(1)} KB · ${lines.length} lines`
    : 'not written yet';
  if (atBottom) body.scrollTop = body.scrollHeight;
}

function renderCodeAudit(view) {
  const external = view.external || {};
  const source = external.source || {};
  const report = external.report || {};
  const progress = external.progress || {};
  const findings = view.details || [];
  const scanner = external.scanner || [];
  const excludedFiles = external.excluded_files || [];
  const elapsed = progress.elapsed_seconds || view.elapsed || 0;
  const waiting = progress.waiting_provider;
  const evaluation = external.evaluation || (external.report && external.report.evaluation) || {};
  const evalHtml = evaluation.score != null ? `
    <div class="dash-card eval-hero">
      <div class="eval-score-wrap">
        <div class="eval-score">${evaluation.score}<span>/100</span></div>
        <div>
          <div class="dash-card-title">🔒 Evaluasi Keamanan · grade ${esc(evaluation.grade || '')}</div>
          <div class="eval-grade-sub">${esc(evaluation.grade_text || '')}</div>
          <div class="dash-card-sub" style="margin-top:6px">${esc(evaluation.verdict || '')}</div>
        </div>
      </div>
      <div class="eval-grid">
        ${(evaluation.categories || []).map((c) => `
          <div class="eval-cat ${c.deduction > 12 ? 'bad' : (c.deduction > 0 ? 'warn' : 'ok')}">
            <div class="eval-cat-head"><span>${esc(c.category)}</span><span class="eval-ded">-${c.deduction}pt</span></div>
            ${(c.notes || []).map((n) => `<div class="eval-note">${esc(n)}</div>`).join('')}
            <div class="eval-rec"><b>Aksi:</b> ${esc(c.recommendation || '')}</div>
          </div>`).join('')}
      </div>
      ${(evaluation.upgrades || []).length ? `<div class="dash-card-title" style="margin-top:14px">🛠 Prioritas upgrade</div>
      <div class="eval-upgrades">${evaluation.upgrades.map((u) => `
        <div class="eval-upgrade ${esc(u.prioritas)}">
          <span class="pill ${esc(u.prioritas)}">${esc(u.prioritas)}</span>
          <div><b>${esc(u.kategori)}:</b> ${esc(u.aksi)}</div>
        </div>`).join('')}</div>` : ''}
    </div>` : '';
    <div class="dash-card">
      <div class="dash-card-title">Scanner deterministik (${scanner.length} kandidat) · verified</div>
      <div class="dash-card-sub">Hasil bandit/semgrep/gitleaks/osv atau fallback regex — bukan penilaian LLM. LLM hanya menilai konteks di bawah.</div>
      <div class="findings-list">${scanner.map((s) => `
        <div class="finding-card">
          <div class="finding-head">
            <span class="sev ${sevClass(s.severity)}">${esc(s.severity || 'info')}</span>
            <span>${esc(s.title || 'scanner finding')}</span>
            ${s.cwe ? `<span class="pill">${esc(s.cwe)}</span>` : ''}
            <span class="pill">${esc(s.scanner || 'scanner')}</span>
            <span class="pill verified">verified</span>
          </div>
          ${s.path ? `<div class="finding-row">${esc(s.path)}${s.line ? ':' + s.line : ''}</div>` : ''}
          ${s.description ? `<div class="finding-text">${esc(String(s.description).slice(0, 600))}</div>` : ''}
        </div>`).join('')}</div>
    </div>` : '';
  const scannerHtml = scanner.length ? `  const excludedHtml = excludedFiles.length ? `
    <div class="dash-card">
      <div class="dash-card-title">File dikecualikan (${excludedFiles.length}) · per alasan</div>
      <div class="dash-card-sub">Buka untuk melihat kenapa file tidak masuk bundle — oversize / ekstensi / private / binary.</div>
      <details><summary style="cursor:pointer">Tampilkan daftar</summary>
      <div class="findings-list">${excludedFiles.slice(0, 50).map((e) => `
        <div class="finding-card"><code>${esc(e.path || '(tanpa path)')}</code>
          <span class="pill">${esc(e.reason || 'unknown')}</span>
          ${e.size ? `<span class="pill">${(e.size/1000).toFixed(0)} KB${e.limit_kb ? ' > ' + e.limit_kb + ' KB' : ''}</span>` : ''}
          ${e.ext ? `<span class="pill">${esc(e.ext)}</span>` : ''}
        </div>`).join('')}${excludedFiles.length > 50 ? `<div class="empty-sub">… dan ${excludedFiles.length - 50} lainnya</div>` : ''}</div>
      </details>
    </div>` : (source.excluded ? `<div class="dash-card"><div class="dash-card-title">File dikecualikan (${source.excluded})</div><div class="empty-sub">Rincian per file tidak tersedia untuk run lama.</div></div>` : '');
  const findingHtml = (findings.length || (report && report.findings && report.findings.length)) ? ((report && report.findings) || findings).map((d) => `
    <div class="finding-card">
      <div class="finding-head">
        <span class="sev ${sevClass(d.severity)}">${esc(d.severity || 'info')}</span>
        <span>${esc(d.title || 'temuan')}</span>
        ${d.cwe ? `<span class="pill">${esc(d.cwe)}</span>` : ''}
        <span class="pill">model_assessed</span>
      </div>
      ${d.endpoint ? `<div class="finding-row">source&nbsp; ${esc(d.endpoint)}</div>` : ''}
      ${d.cause ? `<div class="finding-text"><b>temuan</b> ${esc(d.cause)}</div>` : ''}
      ${d.impact ? `<div class="finding-text"><b>dampak</b> ${esc(d.impact)}</div>` : ''}
      ${d.mitigation ? `<div class="finding-text"><b>perbaikan</b> ${esc(d.mitigation)}</div>` : ''}
    </div>`).join('') : '<div class="empty-sub">Belum ada temuan yang dapat dibuktikan.</div>';
  const execShort = (() => {
    const raw = report.executive_summary || '';
    if (!raw) return 'Model membaca source yang diunggah; kode tidak dieksekusi.';
    const lines = raw.split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('-') && !l.startsWith('Rincian'));
    return (lines.slice(0, 2).join(' ') || raw.split('\n')[0]).slice(0, 400);
  })();
  const patches = report.patches || {};
  const patchApplied = patches.applied || [];
  const patchSkipped = patches.skipped || [];
  const patchLine = (p) => p.line
    ? `baris ${p.line}${p.line_end && p.line_end !== p.line ? '-' + p.line_end : ''}`
    : 'baris tidak tercatat';
  const patchHtml = (patches.enabled !== undefined || patchApplied.length || patchSkipped.length) ? `
    <div class="dash-card">
      <div class="dash-card-title">Patch otomatis</div>
      <div class="dash-card-sub">${patches.enabled === false
        ? esc(patches.error || 'Auto-patch tidak aktif.')
        : `Diterapkan ${patches.applied_count || 0} · dilewati ${patches.skipped_count || 0}${patches.backup_root ? ` · backup ${esc(patches.backup_root)}` : ''}`}</div>
      ${patchApplied.map((p) => {
        const before = p.before !== undefined ? p.before : p.search;
        const after = p.after !== undefined ? p.after : p.replace;
        const hasDetail = before !== undefined || after !== undefined;
        const side = (label, value, emptyText) => {
          const text = value == null ? '' : String(value);
          return `<div><div class="patch-label">${label}</div>${text.trim()
            ? `<pre class="patch-code">${esc(text)}</pre>`
            : `<div class="patch-empty">${emptyText}</div>`}</div>`;
        };
        return `<div class="patch-card">
          <div class="patch-head"><span class="pill">applied</span><code>${esc(p.path)}</code><span class="pill">${patchLine(p)}</span>${after === '' ? '<span class="pill">hapus</span>' : ''}</div>
          ${p.rationale ? `<div class="finding-text"><b>alasan</b> ${esc(p.rationale)}</div>` : ''}
          ${hasDetail ? `<div class="patch-grid">
            ${side('sebelum', before, 'baris baru / tidak ada kode sebelumnya')}
            ${after !== undefined
              ? side('sesudah', after, 'baris dihapus (tidak ada pengganti)')
              : side('sesudah', undefined, 'tidak ada data pengganti (run lama)')}
          </div>` : '<div class="empty-sub">Detail baris/snippet belum tersedia untuk run lama.</div>'}
        </div>`;
      }).join('')}
      ${patchSkipped.map((p) => `<div class="patch-card">
        <div class="patch-head"><span class="pill">skipped</span><code>${esc(p.path)}</code></div>
        <div class="finding-text">${esc(p.reason || 'tidak diterapkan')}</div>
      </div>`).join('')}
    </div>` : '';
  $('ff-content').innerHTML = `
    <div class="flow-detail-cards">
      <div class="card"><div class="label">Source</div><div class="value" style="font-size:14px">${esc(source.name || view.target[0] || '-')}</div><div class="sub">${source.files || 0} file teks · ${source.excluded || 0} dikecualikan</div></div>
      <div class="card"><div class="label">Status</div><div class="value" style="font-size:14px">${esc(view.status)}${waiting ? ' ⏳' : ''}</div><div class="sub">${waiting ? 'menunggu model … ' + Math.round(elapsed || 0) + 's' : esc(progress.node || view.workflow_phase || '')}</div></div>
      <div class="card"><div class="label">Iterasi</div><div class="value">${view.iteration || 0}/${view.max_iterations || 0}</div><div class="sub">${view.stop_reason ? 'stop: ' + esc(view.stop_reason) : (progress.event ? esc(progress.event.slice(0, 80)) : 'audit statis')}</div></div>
      <div class="card"><div class="label">Temuan</div><div class="value">${findings.length}</div><div class="sub">${scanner.length} verified · model-assessed, bukan verifikasi dinamis</div></div>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">🖥 Terminal audit <span class="pill" id="audit-term-pill">${esc(view.status)}</span></div>
      <div class="dash-card-sub">Log langsung dari worker. Scroll otomatis ke bawah; ${waiting ? '⏳ menunggu model …' : 'worker selesai / idle'}.</div>
      <div class="terminal-shell" style="margin-top:8px">
        <pre class="terminal-view" id="audit-term-body" style="max-height:300px;overflow:auto">${esc((view.log || []).join('\n') || 'mengemas bundle & menjalankan scanner…')}</pre>
      </div>
    </div>
    ${waiting ? `<div class="dash-card"><div class="dash-card-title">⏳ menunggu model …</div><div class="dash-card-sub">${esc(progress.event || 'mengirim prompt ke provider')} · ${Math.round(elapsed || 0)}s · token request ${progress.tokens_request ? Number(progress.tokens_request).toLocaleString() : '-'}</div></div>` : ''}
    ${evalHtml}
    ${scannerHtml}
    ${excludedHtml}
    <div class="dash-card">
      <div class="dash-card-title">${esc(report.title || 'Audit kode')}</div>
      <div class="dash-card-sub">${esc(execShort)}</div>
      ${report.limitations ? `<div class="finding-text" style="margin-top:8px"><b>keterbatasan</b> ${esc(report.limitations)}</div>` : ''}
      ${report.next_steps ? `<div class="finding-text" style="margin-top:6px"><b>berikutnya</b> ${esc(report.next_steps)}</div>` : ''}
    </div>
    <div class="dash-card">
      <div class="dash-card-title">Findings</div>
      <div class="dash-card-sub">Setiap finding wajib mengutip observation read_source yang tercatat.</div>
      <div class="findings-list">${findingHtml}</div>
    </div>
    ${patchHtml}
    ${view.log && view.log.length ? `<div class="dash-card"><div class="dash-card-title">Worker log</div>
      <div class="log-view">${view.log.slice(-40).map((l) => `<div class="log-line">${esc(l)}</div>`).join('')}</div></div>` : ''}`;
}

// ------------------------------------------------------- agent timeline UI ---
const SEV_RANK = { critical: 0, high: 1, medium: 2, low: 3, info: 4, unrated: 5 };
const stepPanel = {};          // step key -> 'tool' | 'related' | 'patch' | null
const openDetails = new Set(); // finding keys whose Details are expanded

function fkey(d) {
  const s = [d.title, d.endpoint, d.class, d.parameter].join('|');
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0;
  return h.toString(36);
}

// The operator's own decision wins; otherwise an engine-confirmed finding counts as verified.
function findingState(view, d) {
  const mark = (view.marks || {})[fkey(d)];
  if (mark) return mark;
  return ['verified', 'confirmed'].includes(String(d.status || '').toLowerCase()) ? 'verified' : 'pending';
}

function patchesFor(view, d) {
  const applied = (((view.external || {}).report || {}).patches || {}).applied || [];
  const where = String(d.endpoint || '');
  return applied.filter((p) => p.path && where.includes(p.path));
}

function sortFindings(view, items) {
  return items.slice().sort((a, b) => {
    const va = findingState(view, a) === 'verified' ? 0 : 1;
    const vb = findingState(view, b) === 'verified' ? 0 : 1;
    return (SEV_RANK[sevClass(a.severity)] ?? 5) - (SEV_RANK[sevClass(b.severity)] ?? 5) || va - vb;
  });
}

function findingCard(view, d, state) {
  const k = fkey(d);
  const ok = state === 'verified';
  const open = openDetails.has(k);
  const desc = d.cause || d.impact || '';
  const evidence = [['target', d.url || d.endpoint], ['parameter', d.parameter], ['payload', d.payload],
    ['extracted', (d.extracted || []).join(', ')], ['assessment', d.status]]
    .filter((r) => r[1]).map((r) => r[0].padEnd(11) + r[1]).join('\n');
  const detailRows = [['impact', d.impact], ['cause', d.cause], ['payload', d.payload], ['url', d.url]]
    .filter((r) => r[1]).map((r) => `<div class="finding-text"><b>${r[0]}</b> ${esc(r[1])}</div>`).join('');
  return `<div class="vf ${ok ? '' : 'pending'}">
    <div class="vf-head">
      <span style="color:var(--high);width:18px;height:18px;flex:none;margin-top:1px">${TL_ICON.warn}</span>
      <div class="vf-title">${esc(d.title || d.class || 'unclassified finding')}</div>
      ${d.cwe ? `<span class="pill">${esc(d.cwe)}</span>` : ''}
      <span class="sev ${sevClass(d.severity)}">${esc(d.severity || 'unrated')}</span>
    </div>
    ${desc ? `<div class="vf-desc">${esc(desc)}</div>` : ''}
    <div class="vf-meta">
      <span class="vf-endpoint">${esc(d.endpoint || '-')}</span>
      <span class="vf-badge ${ok ? 'ok' : 'wait'}">${ok ? 'Verified' : 'Pending verification'}</span>
    </div>
    <div class="vf-actions">
      <button class="tl-btn" data-act="${ok ? 'reverify' : 'verify'}" data-key="${k}">${ok ? 'Reverify' : 'Verify'}</button>
      <button class="tl-btn" data-act="ignore" data-key="${k}">Ignore</button>
      <button class="tl-btn ${open ? 'on' : ''}" data-act="details" data-key="${k}">${open ? 'Hide details' : 'Details'}</button>
    </div>
    ${open ? `<div class="vf-details">${detailRows || '<div class="empty-sub">Tidak ada detail tambahan.</div>'}
      ${!ok && d.mitigation ? `<div class="finding-text"><b>remediation</b> ${esc(d.mitigation)}</div>` : ''}</div>` : ''}
    ${ok ? `<div><div class="vf-label">Reproducible evidence</div><pre class="vf-evidence">${esc(evidence || '-')}</pre></div>
      ${d.mitigation ? `<div><div class="vf-label">Remediation</div><div class="vf-fix">${esc(d.mitigation)}</div></div>` : ''}` : ''}
  </div>`;
}

function buildSteps(view) {
  const dets = (view.details || []).filter((d) => matches(d.title, d.class, d.endpoint));
  const steps = [];
  if (view.engine === 'code') {
    const ex = view.external || {};
    const src = ex.source || {};
    const rep = ex.report || {};
    steps.push({ name: 'Source Reader', desc: 'Membaca source secara read-only; kode tidak dieksekusi.',
      result: `${src.files || 0} file teks dibaca · ${src.excluded || 0} dikecualikan.`, items: [],
      output: (view.log || []).slice(0, 6) });
    steps.push({ name: 'Code Audit Agent', desc: 'Menganalisis source dan mengutip observasi read_source.',
      result: rep.executive_summary || 'Audit selesai. Hasil tersedia untuk ditinjau.', items: dets, output: [] });
    return steps;
  }
  const pages = view.searches || [];
  steps.push({ name: 'Reconnaissance Agent', desc: 'Memetakan layanan, teknologi, dan endpoint aplikasi.',
    result: `${pages.length} halaman dipetakan.`, items: [], output: pages.slice(0, 12).map((s) => s.url || s.title) });
  const cats = {};
  (view.hypotheses || []).forEach((h) => { if (h.category && !cats[h.category]) cats[h.category] = h.rationale || ''; });
  dets.forEach((d) => { const c = d.class || 'other'; if (!(c in cats)) cats[c] = ''; });
  Object.entries(cats).forEach(([c, rationale]) => {
    const label = c.replace(/_/g, ' ');
    const items = dets.filter((d) => (d.class || 'other') === c);
    steps.push({ name: label.replace(/\b\w/g, (m) => m.toUpperCase()) + ' Agent', desc: rationale || ('Memeriksa ' + label),
      result: items.length ? `${items.length} temuan untuk ditinjau.` : 'Tidak ada temuan pada langkah ini.', items, output: [] });
  });
  return steps;
}

function stepPanelHtml(view, step, kind) {
  const states = step.items.map((d) => [d, findingState(view, d)]);
  const live = states.filter(([, s]) => s !== 'ignored');
  const ignored = states.filter(([, s]) => s === 'ignored');
  if (kind === 'tool') {
    if (!step.items.length) {
      return step.output.length ? `<pre class="vf-evidence">${esc(step.output.join('\n'))}</pre>`
        : '<div class="empty-sub">Belum ada output untuk langkah ini.</div>';
    }
    const cards = sortFindings(view, live.map(([d]) => d)).map((d) => findingCard(view, d, findingState(view, d))).join('');
    const bar = ignored.length ? `<div class="ignored-bar">${ignored.length} temuan diabaikan
      <button data-act="restore" data-keys="${ignored.map(([d]) => fkey(d)).join(',')}">Pulihkan</button></div>` : '';
    return cards + bar || '<div class="empty-sub">Semua temuan diabaikan.</div>';
  }
  if (kind === 'related') {
    return live.length ? sortFindings(view, live.map(([d]) => d)).map((d) => {
      const ok = findingState(view, d) === 'verified';
      return `<div class="rel-row"><span class="sev ${sevClass(d.severity)}">${esc(d.severity || 'unrated')}</span>
        <div class="t">${esc(d.title || d.class)}<div class="e">${esc(d.endpoint || '')}</div></div>
        <span class="vf-badge ${ok ? 'ok' : 'wait'}">${ok ? 'Verified' : 'Pending'}</span></div>`;
    }).join('') : '<div class="empty-sub">Belum ada temuan terkait.</div>';
  }
  const verified = live.filter(([, s]) => s === 'verified').map(([d]) => d);
  const blocks = sortFindings(view, verified).map((d) => {
    const patches = patchesFor(view, d);
    const body = patches.length ? patches.map((p) => {
      const side = (label, v) => `<div><div class="patch-label">${label}</div>${String(v == null ? '' : v).trim()
        ? `<pre class="patch-code">${esc(v)}</pre>` : '<div class="patch-empty">tidak ada kode</div>'}</div>`;
      return `<div class="patch-head"><span class="pill">${esc(p.status || 'applied')}</span><code>${esc(p.path)}</code>
        ${p.line ? `<span class="pill">baris ${p.line}${p.line_end && p.line_end !== p.line ? '-' + p.line_end : ''}</span>` : ''}</div>
        ${p.rationale ? `<div class="finding-text"><b>alasan</b> ${esc(p.rationale)}</div>` : ''}
        <div class="patch-grid">${side('sebelum', p.before)}${side('sesudah (kode baru)', p.after)}</div>`;
    }).join('') : '<div class="empty-sub">Belum ada patch otomatis untuk temuan ini.</div>';
    return `<div class="patch-block"><div class="finding-head" style="margin:0"><span class="sev ${sevClass(d.severity)}">${esc(d.severity || 'unrated')}</span>
      <span>${esc(d.title || d.class)}</span></div>${body}</div>`;
  }).join('');
  return blocks || '<div class="empty-sub">Verifikasi sebuah temuan untuk melihat hasil patch-nya.</div>';
}

function renderAutomationTimeline(view) {
  const steps = buildSteps(view);
  const all = view.details || [];
  const verifiedCount = all.filter((d) => findingState(view, d) === 'verified').length;
  const src = ((view.external || {}).source || {}).name;
  const orchStatus = view.running ? ['running', 'Running'] : (view.status === 'failed' ? ['failed', 'Failed'] : ['done', 'Completed']);
  const target = src || (view.target || [])[0] || '-';
  const stepsHtml = steps.map((step, i) => {
    const id = view.run_id + ':' + step.name;
    const kind = stepPanel[id] || null;
    const live = view.running && i === steps.length - 1;
    const hasVerified = step.items.some((d) => findingState(view, d) === 'verified');
    const nLive = step.items.filter((d) => findingState(view, d) !== 'ignored').length;
    const b = (k, label, extra) => `<button class="tl-btn ${kind === k ? 'on' : ''}" data-act="panel" data-step="${esc(id)}" data-kind="${k}">${label}${extra || ''}</button>`;
    return `<div class="tl-item ${live ? 'running' : 'done'}"><div class="tl-step-body">
      <div class="tl-card"><div class="tl-ico">${TL_ICON.bot}</div>
        <div class="tl-main"><div class="tl-name">${esc(step.name)}</div><div class="tl-desc">${esc(step.desc)}</div></div>
        <div class="tl-side"><span class="chip ${live ? 'running' : 'done'}">${live ? 'Running' : 'Completed'}</span></div></div>
      <div class="tl-result"><div class="tl-result-text">${esc(step.result)}</div>
        <div class="tl-actions">${b('tool', '&gt;_ Tool output')}${b('related', 'Related finding', ` <span class="n">${nLive}</span>`)}${hasVerified ? b('patch', 'Patch results') : ''}</div></div>
      ${kind ? `<div class="tl-panel">
        <div class="tl-panel-title">${{ tool: 'Tool output', related: 'Related findings', patch: 'Patch results' }[kind]}</div>
        ${kind === 'patch' ? '<div class="tl-panel-sub">Kode baru hasil patch otomatis untuk menutup kerentanan yang sudah terverifikasi.</div>' : ''}
        ${stepPanelHtml(view, step, kind)}</div>` : ''}
    </div></div>`;
  }).join('');
  $('ff-content').innerHTML = `
    <div class="tl-summary">
      <div class="card"><div class="label">${src ? 'Source' : 'Target'}</div><div class="value" style="font-size:14px;word-break:break-all">${esc(target)}</div></div>
      <div class="card"><div class="label">Status</div><div class="value" style="font-size:14px">${esc(view.status)}</div><div class="sub">${view.iteration || 0}/${view.max_iterations || 0} iterasi</div></div>
      <div class="card"><div class="label">Findings</div><div class="value">${all.length}</div><div class="sub">${verifiedCount} verified · ${all.length - verifiedCount} pending</div></div>
    </div>
    <div class="tl-item tl-orch ${orchStatus[0]}" style="padding-left:0"><div class="tl-card">
      <div class="tl-ico">${TL_ICON.bot}</div>
      <div class="tl-main"><div class="tl-name">Orchestrator Agent</div>
        <div class="tl-desc">${esc(view.objective || 'Coordinates the assessment and correlates evidence.')}</div></div>
      <div class="tl-side"><span class="chip ${orchStatus[0]}">${orchStatus[1]}</span></div></div>
      <div class="tl-children">${stepsHtml}</div></div>`;
}

async function setMark(key, state) {
  if (!selectedFlow || !lastFlowView) return;
  lastFlowView.marks = { ...(lastFlowView.marks || {}), [key]: state };
  renderFlowSubPanel(lastFlowView);
  try {
    await fetch('/api/flows/' + encodeURIComponent(selectedFlow) + '/findings/mark', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key, state }),
    });
  } catch (e) { /* kept locally until the next poll */ }
}

$('ff-content').addEventListener('click', (e) => {
  const t = e.target.closest('[data-act]');
  if (!t || !lastFlowView) return;
  const act = t.dataset.act;
  const key = t.dataset.key;
  if (act === 'panel') {
    const id = t.dataset.step;
    stepPanel[id] = stepPanel[id] === t.dataset.kind ? null : t.dataset.kind;
    renderFlowSubPanel(lastFlowView);
  } else if (act === 'details') {
    if (openDetails.has(key)) openDetails.delete(key); else openDetails.add(key);
    renderFlowSubPanel(lastFlowView);
  } else if (act === 'verify') setMark(key, 'verified');
  else if (act === 'reverify') setMark(key, 'pending');
  else if (act === 'ignore') setMark(key, 'ignored');
  else if (act === 'restore') t.dataset.keys.split(',').forEach((k) => setMark(k, 'pending'));
});

function renderFlowSubPanel(view) {
  const box = $('ff-content');
  const key = selectedFlowTab;
  if (FLOW_TAB_UNAVAILABLE[key]) {
    box.innerHTML = `<div class="empty-state"><div class="empty-icon">&empty;</div>
      <div class="empty-title">Not available in ADAPTIX</div>
      <div class="empty-sub">${esc(FLOW_TAB_UNAVAILABLE[key])}</div></div>`;
    return;
  }
  if (view.engine === 'code') {
    if (key === 'terminal') { renderTerminal(view); return; }
    if (key === 'automation') { renderAutomationTimeline(view); return; }
    renderCodeAudit(view);
    return;
  }
  if (view.engine === 'opencode') {
    if (key === 'automation') { renderExternalAutomation(view); return; }
    if (key === 'tasks') { renderExternalTasks(view); return; }
    if (key === 'dashboard') { renderExternalDashboard(view); return; }
    if (key === 'agents') { renderExternalAgents(view); return; }
  }
  if (key === 'automation') { renderAutomationTimeline(view); return; }
  if (key === 'dashboard') {
    const t = view.tokens;
    box.innerHTML = `
      <div class="flow-detail-cards">
        <div class="card"><div class="label">Tasks</div><div class="value">${view.iteration}/${view.max_iterations}</div><div class="sub">Hypotheses tested: ${view.hypotheses.length}</div></div>
        <div class="card"><div class="label">Tool Calls</div><div class="value">${view.tool_calls_used}</div></div>
        <div class="card"><div class="label">Tokens</div><div class="value">${(t.charged || t.total).toLocaleString()}</div><div class="sub">Input + output tokens</div></div>
        <div class="card"><div class="label">Cost</div><div class="value" style="font-size:16px">not tracked</div><div class="sub">ADAPTIX has no per-model pricing table</div></div>
      </div>
      <div class="dash-card-title" style="margin-top:4px">Usage by Model</div>
      <div class="dash-card-sub">Derived from the model string LiteLLM used (provider/model); ADAPTIX does not price calls.</div>
      <table class="usage-table"><thead><tr><th>Model</th><th>Provider</th><th>Calls</th><th>Tokens In</th><th>Tokens Out</th>
        <th>Cache Hits</th><th>Failed</th></tr></thead><tbody id="flow-usage-body"></tbody></table>`;
    renderUsageTableWithProvider($('flow-usage-body'), view.ledger || []);
    return;
  }
  if (key === 'terminal') {
    if (view.engine === 'opencode') { renderTerminal(view); return; }
    const lines = searchQuery ? view.log.filter((l) => matches(l)) : view.log;
    box.innerHTML = `<pre class="terminal-view">${esc(lines.join('\n')) || 'No log lines yet.'}</pre>`;
    return;
  }
  if (key === 'agents') {
    const rows = view.ledger.map((row, i) => ({ row, i })).filter(({ row }) => matches(row.model));
    box.innerHTML = rows.length
      ? `<div class="findings-list">${rows.map(({ row, i }) => `
        <div class="finding-card">
          <div class="finding-head"><span>planner call ${i + 1}</span>
            <span class="pill">${esc(row.model)}</span>
            ${row.cache_hit ? '<span class="pill">cache</span>' : ''}
            ${row.failed ? '<span class="sev high">failed</span>' : ''}</div>
          <div class="finding-row">tokens&nbsp; in ${row.prompt_tokens.toLocaleString()} / out ${row.completion_tokens.toLocaleString()} / charged ${row.charged.toLocaleString()}</div>
        </div>`).join('')}</div>`
      : `<div class="empty-state"><div class="empty-icon">Σ</div><div class="empty-title">No agent calls yet</div>
         <div class="empty-sub">ADAPTIX runs one adaptive planner per flow; each row here is one of its calls.</div></div>`;
    return;
  }
  if (key === 'searches') {
    const rows = view.searches.filter((s) => matches(s.url, s.title));
    box.innerHTML = rows.length
      ? `<div class="findings-list">${rows.map((s) => `
        <div class="finding-card">
          <div class="finding-head"><span>${esc(s.title || s.url)}</span></div>
          <div class="finding-row">url&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${esc(s.url)}</div>
          <div class="finding-row">${s.api_endpoints} API endpoint(s) observed, ${s.links} link(s) found</div>
        </div>`).join('')}</div>`
      : `<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">No pages visited yet</div>
         <div class="empty-sub">ADAPTIX has no web-search tool. This lists pages its browser tool actually recons.</div></div>`;
    return;
  }
  if (key === 'files') {
    box.innerHTML = '<div class="findings-list" id="flow-files-list"><div class="empty-sub">Loading…</div></div>';
    fetch('/api/flows/' + encodeURIComponent(view.run_id) + '/files').then((r) => r.json()).then((d) => {
      const list = $('flow-files-list');
      if (!list) return;
      const files = (d.files || []).filter((f) => matches(f.name));
      list.innerHTML = files.length ? files.map((f) => `
        <div class="finding-card" style="display:flex;justify-content:space-between;align-items:center;">
          <span>${esc(f.name)}</span>
          <a href="/api/flows/${encodeURIComponent(view.run_id)}/file/${encodeURIComponent(f.name)}" target="_blank" class="pill" style="text-decoration:none">${(f.size / 1024).toFixed(1)} KB · download</a>
        </div>`).join('')
        : '<div class="empty-state"><div class="empty-icon">📁</div><div class="empty-title">No files yet</div></div>';
    });
    return;
  }
  if (key === 'screenshots') {
    const rows = view.screenshots.filter((s) => matches(s.url, s.title));
    box.innerHTML = rows.length
      ? `<div class="screenshot-grid">${rows.map((s) => `
        <div class="screenshot-card">
          <a href="/api/flows/${encodeURIComponent(view.run_id)}/file/${encodeURIComponent(s.file)}" target="_blank">
            <img src="/api/flows/${encodeURIComponent(view.run_id)}/file/${encodeURIComponent(s.file)}" loading="lazy">
          </a>
          <div class="screenshot-caption">${esc(s.title || s.url)}</div>
        </div>`).join('')}</div>`
      : `<div class="empty-state"><div class="empty-icon">📷</div><div class="empty-title">No screenshots yet</div>
         <div class="empty-sub">ADAPTIX's browser tool saves one when it checks a page for script execution.</div></div>`;
    return;
  }
  if (key === 'tasks') {
    const rows = view.hypotheses.filter((h) => matches(h.category, h.target, h.rationale));
    box.innerHTML = `
      <div class="tasks-grid">
        <div class="card"><div class="label">Pass</div><div class="value">${view.iteration}/${view.max_iterations}</div></div>
        <div class="card"><div class="label">Graph node</div><div class="value" style="font-size:16px">${esc(view.workflow_node || '-')}</div><div class="sub">${esc(view.workflow_phase || '')}</div></div>
        <div class="card"><div class="label">Status</div><div class="value" style="font-size:16px">${esc(view.status)}</div>${view.stop_reason ? `<div class="sub">stop: ${esc(view.stop_reason)}</div>` : ''}</div>
      </div>
      <div class="dash-card-title" style="margin-top:4px">Hypotheses tested</div>
      <div class="dash-card-sub">ADAPTIX plans one evidence-grounded hypothesis at a time rather than a fixed task list.</div>
      <div class="task-list">${rows.length ? rows.map((h) => `
        <div class="task-row">
          <span class="task-dot">▶</span>
          <div><div class="task-title">${esc(h.category.replace(/_/g, ' '))} on ${esc(h.target)}</div>
          <div class="task-sub">${esc(h.rationale)}</div></div>
        </div>`).join('') : '<div class="empty-sub">No hypotheses recorded yet.</div>'}</div>`;
    return;
  }
}

// ---------------------------------------------------------------- polling ---
async function refresh() {
  try {
    const res = await fetch('/api/status');
    const view = await res.json();
    $('run-title').textContent = view.objective || (view.target[0] || 'no active run');
    $('status-pill').textContent = (view.engine === 'opencode' ? 'oc · ' : '') + view.status;
    $('elapsed').textContent = Math.round(view.elapsed) + 's';
    $('status-dot').className = 'status-dot' + (view.running ? ' running' : (view.status === 'failed' ? ' failed' : ''));
    $('user-row').title = view.model ? 'Model: ' + view.model : '';
    $('start-btn').textContent = view.running ? '■' : '▶';
    $('start-btn').title = view.running ? 'Cancel' : 'Start';
    if ($('panel-dashboard').classList.contains('active')) loadDashboard();
    if ($('panel-flows').classList.contains('active')) loadFlows();
    // Flow-detail polling: Tanpa ini, halaman openFlow tidak diperbarui —
    // worker jalan tapi UI pasif. Tiap 2s ambil snapshot terbaru.
    if (selectedFlow && !$('flow-fullpage').classList.contains('hidden')) refreshFlowDetail();
  } catch (e) { /* server not reachable yet */ }
}

$('start-btn').addEventListener('click', async () => {
  if ($('start-btn').title === 'Cancel') {
    await fetch('/api/cancel', { method: 'POST' });
    return;
  }
  const engine = $('b-engine').value;
  const target = $(engineTarget()).value.trim();
  const fullOffensive = engine === 'opencode' && $('b-full-offensive').checked;
  if (engine === 'opencode') {
    if (!target) { alert('target is required'); return; }
    if (fullOffensive) {
      if (!$('b-authorized').checked) { alert('centang izin tertulis dulu'); return; }
      const host = hostOf(target);
      if ($('b-confirm-target').value.trim() !== host) {
        alert('ketik host target dengan tepat: ' + host); return;
      }
    }
  }
  if (engine === 'code') {
    const kind = codeSourceKind();
    const file = $('b-code-file').files[0];
    const sourcePath = $('b-code-path').value.trim();
    const goal = $('instruction').value.trim();
    if (kind === 'zip') {
      if (!file) { alert('pilih file ZIP source code dulu'); return; }
      if (!file.name.toLowerCase().endsWith('.zip')) { alert('hanya file .zip'); return; }
    } else if (!sourcePath) {
      alert('isi path folder source code dulu'); return;
    }
    if (!goal) { alert('tuliskan tujuan audit kode'); return; }
    const autoPatch = kind === 'folder' && $('b-code-autopatch').checked;
    if (autoPatch && !confirm('Patch otomatis akan MENGUBAH file di:\n' + sourcePath +
        '\n\nSeluruh folder yang diaudit dicadangkan lebih dulu di folder induknya, ' +
        'lalu diff disimpan di artifacts run. Lanjutkan?')) return;
    const form = new FormData();
    if (kind === 'zip') form.append('file', file);
    else form.append('source_path', sourcePath);
    if (autoPatch) form.append('auto_patch', '1');
    form.append('instruction', goal);
    form.append('model', $('b-code-model').value.trim());
    form.append('time_budget', $('b-time').value.trim() || '900');
    form.append('token_budget', $('b-tokens').value.trim() || '50000');
    form.append('max_iterations', $('b-code-iterations').value.trim() || '8');
    form.append('max_file_kb', $('b-code-file-limit').value);
    form.append('oversize', $('b-code-skip-large').checked ? 'skip' : 'fail');
    const res = await fetch('/api/audit/code', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) alert(data.error || 'could not start code audit');
    else if (data.run_id) openFlow(data.run_id);
    refresh();
    return;
  }
  const body = {
    engine,
    target,
    instruction: $('instruction').value.trim(),
    model: $('b-model').value.trim(),
    opencode_model: $('b-opencode-model').value.trim(),
    focus: $('b-focus').value.trim(),
    reviewer: $('b-reviewer').checked,
    full_offensive: fullOffensive,
    authorized: $('b-authorized').checked,
    confirm_target: $('b-confirm-target').value.trim(),
    time_budget: $('b-time').value.trim() || null,
    tool_budget: $('b-tools').value.trim() || null,
    token_budget: $('b-tokens').value.trim() || null,
    identity_resource: $('b-identity').value,
    knowledge_ids: Array.from($('b-knowledge').selectedOptions).map((o) => o.value),
  };
  const res = await fetch('/api/start', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'could not start run');
  } else if (data.run_id) {
    openFlow(data.run_id); // watch the flow you just started, same as PentAGI does
  }
  refresh();
});

// ------------------------------------------------------------- templates ---
async function loadTemplates() {
  const res = await fetch('/api/templates');
  const data = await res.json();
  renderTemplates(data.templates || []);
}

function renderTemplates(items) {
  const box = $('templates-list');
  box.innerHTML = items.length ? items.map((t) => `
    <div class="finding-card template-row" data-id="${esc(t.id)}">
      <div>
        <div style="font-weight:600;font-size:13.5px;">${esc(t.name)}</div>
        <div class="meta">${esc(t.objective.slice(0, 80))}${t.target ? ' · ' + esc(t.target) : ''}</div>
      </div>
      <div class="row-actions">
        <button class="use-tpl">Use</button>
        <button class="del-tpl">Delete</button>
      </div>
    </div>`).join('')
    : '<div class="empty-state"><div class="empty-icon">▤</div><div class="empty-title">No templates yet</div>' +
      '<div class="empty-sub">Create your first template to get started</div>' +
      '<button id="new-template-btn-2" class="btn-primary empty-cta">+ New Template</button></div>';
  if (!items.length) $('new-template-btn-2').addEventListener('click', () => $('new-template-form').classList.toggle('hidden'));
  box.querySelectorAll('.use-tpl').forEach((btn) => btn.addEventListener('click', (e) => {
    const id = e.target.closest('.template-row').dataset.id;
    const t = items.find((x) => x.id === id);
    if (!t) return;
    $('target').value = t.target || '';
    $('target-opencode').value = t.target || '';
    $('instruction').value = t.objective;
    if (t.model) $('b-model').value = t.model;
    activateTab('chat');
    $('instruction').focus();
  }));
  box.querySelectorAll('.del-tpl').forEach((btn) => btn.addEventListener('click', async (e) => {
    const id = e.target.closest('.template-row').dataset.id;
    await fetch('/api/templates/' + encodeURIComponent(id), { method: 'DELETE' });
    loadTemplates();
  }));
}

$('new-template-btn').addEventListener('click', () => $('new-template-form').classList.toggle('hidden'));
$('tpl-cancel').addEventListener('click', () => $('new-template-form').classList.add('hidden'));
$('tpl-save').addEventListener('click', async () => {
  const name = $('tpl-name').value.trim();
  const objective = $('tpl-objective').value.trim();
  if (!name || !objective) { alert('name and objective are required'); return; }
  const res = await fetch('/api/templates', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, objective, target: $('tpl-target').value.trim() }),
  });
  if (res.ok) {
    $('tpl-name').value = ''; $('tpl-target').value = ''; $('tpl-objective').value = '';
    $('new-template-form').classList.add('hidden');
    loadTemplates();
  }
});

// ------------------------------------------------------------- resources ---
async function loadResources() {
  const res = await fetch('/api/resources');
  const data = await res.json();
  renderResources(data.resources || []);
  const select = $('b-identity');
  select.innerHTML = '<option value="">(none)</option>' +
    (data.resources || []).map((r) => `<option value="${esc(r.name)}">${esc(r.name)}</option>`).join('');
}

function renderResources(items) {
  const q = ($('resources-filter').value || '').toLowerCase();
  const rows = items.filter((r) => !q || r.name.toLowerCase().includes(q));
  $('resources-list').innerHTML = rows.length ? rows.map((r) => `
    <div class="finding-card resource-row" data-name="${esc(r.name)}">
      <div>
        <div style="font-weight:600;font-size:13.5px;">${esc(r.name)}</div>
        <div class="meta">${(r.size / 1024).toFixed(1)} KB</div>
      </div>
      <div class="row-actions">
        <a href="/api/resources/${encodeURIComponent(r.name)}" target="_blank">Download</a>
        <button class="del-res">Delete</button>
      </div>
    </div>`).join('')
    : '<div class="empty-state"><div class="empty-icon">⬆</div><div class="empty-title">No resources yet</div>' +
      '<div class="empty-sub">Upload identity files so a flow can use them.</div>' +
      '<button id="upload-resource-btn-2" class="btn-primary empty-cta">⬆ Upload files</button></div>';
  if (!rows.length) $('upload-resource-btn-2').addEventListener('click', () => $('resource-file-input').click());
  $('resources-list').querySelectorAll('.del-res').forEach((btn) => btn.addEventListener('click', async (e) => {
    const name = e.target.closest('.resource-row').dataset.name;
    await fetch('/api/resources/' + encodeURIComponent(name), { method: 'DELETE' });
    loadResources();
  }));
}

$('resources-filter').addEventListener('input', loadResources);
$('upload-resource-btn').addEventListener('click', () => $('resource-file-input').click());
$('resource-file-input').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  await fetch('/api/resources', { method: 'POST', body: form });
  e.target.value = '';
  loadResources();
});

// ------------------------------------------------------------- knowledge ---
async function loadKnowledge() {
  const res = await fetch('/api/knowledge');
  const data = await res.json();
  renderKnowledge(data.knowledge || []);
  const select = $('b-knowledge');
  select.innerHTML = (data.knowledge || []).map((k) => `<option value="${esc(k.id)}">${esc(k.title)}</option>`).join('');
}

function renderKnowledge(items) {
  $('knowledge-list').innerHTML = items.length ? items.map((k) => `
    <div class="finding-card knowledge-row" data-id="${esc(k.id)}">
      <div>
        <div style="font-weight:600;font-size:13.5px;">${esc(k.title)}</div>
        <div class="meta">${esc(k.content.slice(0, 100))}</div>
      </div>
      <div class="row-actions"><button class="del-kn">Delete</button></div>
    </div>`).join('')
    : '<div class="empty-state"><div class="empty-icon">▦</div><div class="empty-title">No knowledge documents yet</div>' +
      '<div class="empty-sub">Create your first knowledge document to get started</div>' +
      '<button id="new-knowledge-btn-2" class="btn-primary empty-cta">+ New Knowledge</button></div>';
  if (!items.length) $('new-knowledge-btn-2').addEventListener('click', () => $('new-knowledge-form').classList.toggle('hidden'));
  $('knowledge-list').querySelectorAll('.del-kn').forEach((btn) => btn.addEventListener('click', async (e) => {
    const id = e.target.closest('.knowledge-row').dataset.id;
    await fetch('/api/knowledge/' + encodeURIComponent(id), { method: 'DELETE' });
    loadKnowledge();
  }));
}

$('new-knowledge-btn').addEventListener('click', () => $('new-knowledge-form').classList.toggle('hidden'));
$('kn-cancel').addEventListener('click', () => $('new-knowledge-form').classList.add('hidden'));
$('kn-save').addEventListener('click', async () => {
  const title = $('kn-title').value.trim();
  const content = $('kn-content').value.trim();
  if (!title || !content) { alert('title and content are required'); return; }
  const res = await fetch('/api/knowledge', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content }),
  });
  if (res.ok) {
    $('kn-title').value = ''; $('kn-content').value = '';
    $('new-knowledge-form').classList.add('hidden');
    loadKnowledge();
  }
});

loadDashboard();
loadFlows();
loadResources();
loadKnowledge();
loadOpencodeModels();
loadVersion();
loadSettings();
refresh();
setInterval(refresh, 2000);
if (location.hash === '#settings') showSettings();
if (location.hash === '#overview') {
  const dashTab = Array.from(tabs).find((b) => b.dataset.tab === 'dashboard');
  const overviewBtn = document.querySelector('[data-dash="overview"]');
  if (dashTab) dashTab.click();
  if (overviewBtn) overviewBtn.click();
}
