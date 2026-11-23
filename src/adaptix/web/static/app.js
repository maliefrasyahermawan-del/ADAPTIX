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
};
document.querySelectorAll('[data-icon]').forEach((el) => {
  el.innerHTML = ICONS[el.dataset.icon] || '';
});

// ---------------------------------------------------------------- top nav ---
const tabs = document.querySelectorAll('.nav-item');
const panels = document.querySelectorAll('.panel');
tabs.forEach((btn) => btn.addEventListener('click', () => {
  tabs.forEach((b) => b.classList.remove('active'));
  panels.forEach((p) => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
  if (btn.dataset.tab === 'dashboard') loadDashboard();
  if (btn.dataset.tab === 'flows') loadFlows();
  if (btn.dataset.tab === 'templates') loadTemplates();
  if (btn.dataset.tab === 'resources') loadResources();
  if (btn.dataset.tab === 'knowledges') loadKnowledge();
}));
if (location.hash && location.hash !== '#settings') {
  const initial = Array.from(tabs).find((b) => b.dataset.tab === location.hash.slice(1));
  if (initial) initial.click();
}

$('budget-toggle').addEventListener('click', () => {
  $('budget-panel').classList.toggle('hidden');
});

function hostOf(target) {
  try {
    return new URL(target.includes('://') ? target : 'http://' + target).hostname;
  } catch (e) {
    return '';
  }
}

function syncEngine() {
  const engine = $('b-engine').value;
  const opencode = engine === 'opencode';
  const code = engine === 'code';
  $('opencode-options').classList.toggle('hidden', !opencode);
  $('code-options').classList.toggle('hidden', !code);
  $('full-offensive-panel').classList.toggle('hidden', !opencode || !$('b-full-offensive').checked);
  $('target').placeholder = code
    ? 'Target tidak diperlukan untuk audit kode (pilih ZIP atau folder di bawah)'
    : 'Target, e.g. http://127.0.0.1:3000';
  if (opencode && !$('b-opencode-model').dataset.loaded) loadOpencodeModels();
  if (code && !$('b-code-model').dataset.loaded) loadCodeModels();
  if (code) syncCodeSource();
}

function codeSourceKind() {
  return $('b-code-source-folder').checked ? 'folder' : 'zip';
}

function syncCodeSource() {
  const folder = codeSourceKind() === 'folder';
  $('b-code-zip-row').classList.toggle('hidden', folder);
  $('b-code-folder-row').classList.toggle('hidden', !folder);
  $('b-code-patch-row').classList.toggle('hidden', !folder);
}

$('b-engine').addEventListener('change', syncEngine);
$('b-full-offensive').addEventListener('change', syncEngine);
$('b-code-source-zip').addEventListener('change', syncCodeSource);
$('b-code-source-folder').addEventListener('change', syncCodeSource);
syncEngine();

async function loadCodeModels() {
  const select = $('b-code-model');
  if (!select) return;
  try {
    const res = await fetch('/api/audit/models');
    const data = await res.json();
    const models = data.models || [];
    select.innerHTML = '<option value="">(dari .env)</option>' +
      models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    if (data.default) select.value = data.default;
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
    <div class="set-hint">Edit <code>.env</code> and restart <code>adaptix-web</code> to change these values.</div>`;
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

function renderTokens() {
  $('settings-content').innerHTML = `
    <div class="set-card">
      <div class="set-card-head">
        <div>
          <div class="set-card-title">API tokens</div>
          <div class="set-card-sub">Tokens for automating ADAPTIX over HTTP.</div>
        </div>
        <button class="set-btn" disabled>+ New Token</button>
      </div>
      <div class="set-empty">
        <div class="set-empty-title">No API tokens</div>
        <div class="set-empty-sub">The local web API listens on 127.0.0.1 and is unauthenticated by design, so there are no tokens to issue or revoke.</div>
      </div>
    </div>`;
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
        <stop offset="0%" stop-color="#3b82f6"></stop>
        <stop offset="100%" stop-color="#1a5cbe"></stop>
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
let showingNewFlowForm = false; // "+ New Flow" was clicked explicitly
let flowsFilter = '';

async function loadFlows() {
  const res = await fetch('/api/flows');
  const data = await res.json();
  const flows = data.flows || [];
  renderRecentFlows(flows);
  renderFlowsPage(flows);
  if (selectedFlow && !$('flow-fullpage').classList.contains('hidden')) refreshFlowDetail();
}

function renderFlowsPage(flows) {
  const showTable = flows.length > 0 && !showingNewFlowForm;
  $('flows-table-view').classList.toggle('hidden', !showTable);
  $('new-flow-view').classList.toggle('hidden', showTable);
  $('new-flow-close').classList.toggle('hidden', flows.length === 0);
  if (!showTable) return;
  const q = flowsFilter.toLowerCase();
  const rows = flows.filter((f) => !q || matchesText(q, f.run_id, f.objective, f.target[0], f.status));
  $('flows-table-body').innerHTML = rows.map((f) => {
    const provider = (f.model || '').split('/')[0] || '-';
    const created = f.started_at ? new Date(f.started_at * 1000).toLocaleString() : '-';
    return `<tr data-run="${esc(f.run_id)}">
      <td class="mono">${f.live ? '🟢 ' : ''}${esc(f.run_id)}</td>
      <td>${f.favorite ? '★ ' : ''}${esc(f.title || (f.objective ? f.objective.slice(0, 50) : (f.target[0] || 'untitled')))}</td>
      <td>${esc(f.status)}</td>
      <td>${esc(provider)}</td>
      <td class="mono">${esc(f.target[0] || '-')}</td>
      <td>${esc(created)}</td>
    </tr>`;
  }).join('');
  $('flows-table-body').querySelectorAll('tr').forEach((row) => {
    row.addEventListener('click', () => openFlow(row.dataset.run));
  });
}

function matchesText(q, ...fields) {
  return fields.some((f) => String(f || '').toLowerCase().includes(q));
}

function openNewFlow() {
  const flowsTab = Array.from(document.querySelectorAll('.nav-item')).find((b) => b.dataset.tab === 'flows');
  if (flowsTab) flowsTab.click();
  showingNewFlowForm = true;
  loadFlows();
}
$('new-flow-btn').addEventListener('click', openNewFlow);
$('rail-new-flow').addEventListener('click', openNewFlow);
$('new-flow-close').addEventListener('click', () => { showingNewFlowForm = false; loadFlows(); });
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

$('flow-back-btn').addEventListener('click', () => {
  $('flow-fullpage').classList.add('hidden');
  document.querySelector('.topbar').classList.remove('hidden');
  document.querySelectorAll('.panel.active').forEach((p) => p.classList.remove('hidden'));
});

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
  const findingHtml = findings.length ? findings.map((d) => `
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
      <div class="card"><div class="label">Status</div><div class="value" style="font-size:14px">${esc(view.status)}</div><div class="sub">${esc(progress.node || view.workflow_phase || '')}</div></div>
      <div class="card"><div class="label">Iterasi</div><div class="value">${view.iteration || 0}/${view.max_iterations || 0}</div><div class="sub">${view.stop_reason ? 'stop: ' + esc(view.stop_reason) : 'audit statis'}</div></div>
      <div class="card"><div class="label">Temuan</div><div class="value">${findings.length}</div><div class="sub">model-assessed, bukan verifikasi dinamis</div></div>
    </div>
    <div class="dash-card">
      <div class="dash-card-title">${esc(report.title || 'Audit kode')}</div>
      <div class="dash-card-sub">${esc(report.executive_summary || 'Model membaca source yang diunggah; kode tidak dieksekusi.')}</div>
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
    renderCodeAudit(view);
    return;
  }
  if (view.engine === 'opencode') {
    if (key === 'automation') { renderExternalAutomation(view); return; }
    if (key === 'tasks') { renderExternalTasks(view); return; }
    if (key === 'dashboard') { renderExternalDashboard(view); return; }
    if (key === 'agents') { renderExternalAgents(view); return; }
  }
  if (key === 'automation') {
    const hasLog = view.objective || view.log.length;
    box.innerHTML = `
      <div class="flow-detail-cards">
        <div class="card"><div class="label">Target</div><div class="value" style="font-size:14px">${esc(view.target[0] || '-')}</div></div>
        <div class="card"><div class="label">Status</div><div class="value" style="font-size:14px">${esc(view.status)}</div></div>
        <div class="card"><div class="label">Findings</div><div class="value">${view.details.length}</div></div>
      </div>
      <div class="log-view">${hasLog
        ? (view.objective && matches(view.objective) ? `<div class="log-line objective">${esc(view.objective)}</div>` : '') +
          view.log.filter((l) => matches(l)).map((l) => `<div class="log-line">${esc(l)}</div>`).join('')
        : '<div class="empty-state"><div class="empty-icon">⌁</div><div class="empty-title">No activity yet</div></div>'}
      </div>
      <div class="findings-list">${view.details.filter((d) => matches(d.title, d.class, d.endpoint)).map((d) => `
        <div class="finding-card">
          <div class="finding-head">
            <span class="sev ${sevClass(d.severity)}">${esc(d.severity || 'unrated')}</span>
            <span>${esc(d.title || d.class || 'unclassified finding')}</span>
            ${d.cwe ? `<span class="pill">${esc(d.cwe)}</span>` : ''}
          </div>
          <div class="finding-row">endpoint&nbsp; ${esc(d.endpoint || '')}</div>
          ${d.payload ? `<div class="finding-row">payload&nbsp; ${esc(d.payload)}</div>` : ''}
          ${d.cause ? `<div class="finding-text"><b>cause</b> ${esc(d.cause)}</div>` : ''}
          ${d.mitigation ? `<div class="finding-text"><b>fix</b> ${esc(d.mitigation)}</div>` : ''}
        </div>`).join('')}</div>`;
    return;
  }
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
  } catch (e) { /* server not reachable yet */ }
}

$('start-btn').addEventListener('click', async () => {
  if ($('start-btn').title === 'Cancel') {
    await fetch('/api/cancel', { method: 'POST' });
    return;
  }
  const engine = $('b-engine').value;
  const target = $('target').value.trim();
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
    const res = await fetch('/api/audit/code', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) alert(data.error || 'could not start code audit');
    else if (data.run_id) { showingNewFlowForm = false; openFlow(data.run_id); }
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
    showingNewFlowForm = false; // the Flows page goes back to its table next time
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
    $('instruction').value = t.objective;
    if (t.model) $('b-model').value = t.model;
    tabs.forEach((b) => b.classList.toggle('active', b.dataset.tab === 'flows'));
    panels.forEach((p) => p.classList.toggle('active', p.id === 'panel-flows'));
    showingNewFlowForm = true;
    loadFlows();
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
