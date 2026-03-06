// ── Theme toggle ────────────────────────────────────────────────────────
const html = document.documentElement;
const themeBtn = document.getElementById('theme-toggle');
const saved = localStorage.getItem('fltk-theme') || 'dark';
html.setAttribute('data-theme', saved);
themeBtn.textContent = saved === 'dark' ? '☀️' : '🌙';

themeBtn.addEventListener('click', () => {
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('fltk-theme', next);
  themeBtn.textContent = next === 'dark' ? '☀️' : '🌙';
});

// ── Hamburger mobile nav ────────────────────────────────────────────────
const ham = document.getElementById('hamburger');
const nav = document.getElementById('main-nav');
ham.addEventListener('click', () => {
  nav.classList.toggle('open');
  ham.classList.toggle('open');
});

// ── Workflow dropdown (click on mobile, hover on desktop) ───────────────
const wftGroup = document.getElementById('wft-nav-group');
const wftLabel = document.getElementById('wft-label');
const wftDrop  = document.getElementById('wft-dropdown');
wftLabel.addEventListener('click', () => {
  wftDrop.classList.toggle('open');
});
document.addEventListener('click', (e) => {
  if (!wftGroup.contains(e.target)) wftDrop.classList.remove('open');
});

// ── Toast notifications ─────────────────────────────────────────────────
function showToast(category, message) {
  const tc = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${category}`;
  toast.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()">✕</button>`;
  tc.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 350); }, 4500);
}

if (window.__flashes) {
  window.__flashes.forEach(([cat, msg]) => showToast(cat, msg));
}
