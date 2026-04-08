// js/auth.js
// Quản lý toàn bộ xác thực: modal login/register, JWT localStorage, header UI

let authMode    = 'login'; // 'login' | 'register'
let pendingRank = false;   // true khi user bấm Rank trước khi đăng nhập

// ── LocalStorage helpers ───────────────────────────────────────────────────────
function getToken() { return localStorage.getItem('cvrank_token'); }
function getUser()  { return JSON.parse(localStorage.getItem('cvrank_user') || 'null'); }

function saveAuth(token, user) {
  localStorage.setItem('cvrank_token', token);
  localStorage.setItem('cvrank_user', JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem('cvrank_token');
  localStorage.removeItem('cvrank_user');
}

// ── Session restore (gọi khi DOMContentLoaded) ────────────────────────────────
function restoreSession() {
  const user  = getUser();
  const token = getToken();
  if (user && token) showLoggedIn(user);
  else               showLoggedOut();
}

// ── Header UI ─────────────────────────────────────────────────────────────────
function showLoggedIn(user) {
  document.getElementById('userChip').classList.remove('hidden');
  document.getElementById('btnSignIn').style.display = 'none';
  document.getElementById('userEmail').textContent   = user.email || user.username || 'User';
  document.getElementById('userAvatar').textContent  =
    (user.email || user.username || 'U')[0].toUpperCase();
}

function showLoggedOut() {
  document.getElementById('userChip').classList.add('hidden');
  document.getElementById('btnSignIn').style.display = '';
}

function logout() {
  clearAuth();
  showLoggedOut();
  document.getElementById('results').innerHTML = '';
  clearError();
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal(mode = 'login') {
  setAuthMode(mode);
  clearAuthError();
  document.getElementById('authModal').classList.add('open');
  setTimeout(() => document.getElementById('authEmail').focus(), 100);
}

function closeModal() {
  document.getElementById('authModal').classList.remove('open');
  pendingRank = false;
}

function handleBackdropClick(e) {
  if (e.target === document.getElementById('authModal')) closeModal();
}

// ── Mode toggle: Login ↔ Register ─────────────────────────────────────────────
function setAuthMode(mode) {
  authMode = mode;
  clearAuthError();

  const isLogin = mode === 'login';
  document.getElementById('tabLogin').classList.toggle('active', isLogin);
  document.getElementById('tabRegister').classList.toggle('active', !isLogin);
  document.getElementById('nameGroup').style.display        = isLogin ? 'none' : '';
  document.getElementById('btnAuthLabel').textContent       = isLogin ? 'Sign in' : 'Create account';
  document.getElementById('modalTitle').textContent         = isLogin ? 'Sign in to continue' : 'Create account';
  document.getElementById('modalSub').textContent           = isLogin
    ? 'Enter your credentials to rank CVs'
    : 'Register to start using CVRank';
  document.getElementById('authPassword').autocomplete      = isLogin ? 'current-password' : 'new-password';
}

// ── Submit ─────────────────────────────────────────────────────────────────────
async function submitAuth() {
  const email    = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value;
  const name     = document.getElementById('authName').value.trim();

  if (!email || !password)             { showAuthError('Please fill in all fields.'); return; }
  if (authMode === 'register' && !name){ showAuthError('Please enter your full name.'); return; }

  setAuthLoading(true);
  clearAuthError();

  try {
    const url  = authMode === 'login' ? ENDPOINTS.login : ENDPOINTS.register;
    const body = authMode === 'login' ? { email, password } : { email, password, name };

    const res  = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      const msg = data.message || data.error || 'Authentication failed.';
      showAuthError(Array.isArray(msg) ? msg.join(' · ') : msg);
      return;
    }

    // NestJS JWT thường trả { access_token, user } hoặc { token, user }
    const token = data.access_token || data.token;
    const user  = data.user || { email };

    if (!token && authMode === 'register') {
  // Đăng ký thành công → chuyển sang login
  setAuthMode('login');
  showAuthError('Register success! Please login.');
  return;
}

    saveAuth(token, user);
    showLoggedIn(user);
    closeModal();

    // Nếu đang pending rank → tự động rank luôn
    if (pendingRank) {
      pendingRank = false;
      doRank();
    }

  } catch (err) {
    showAuthError('Network error: ' + err.message);
  } finally {
    setAuthLoading(false);
  }
}

// ── Auth UI helpers ───────────────────────────────────────────────────────────
function showAuthError(msg) {
  const el = document.getElementById('authError');
  el.textContent  = msg;
  el.style.display = 'block';
  el.classList.add('shake');
  setTimeout(() => el.classList.remove('shake'), 400);
}

function clearAuthError() {
  const el = document.getElementById('authError');
  el.style.display = 'none';
  el.textContent   = '';
}

function setAuthLoading(on) {
  document.getElementById('btnAuth').disabled           = on;
  document.getElementById('btnAuthLabel').style.opacity = on ? '0' : '1';
  document.getElementById('authSpinner').classList.toggle('hidden', !on);
}

function togglePw() {
  const inp = document.getElementById('authPassword');
  inp.type  = inp.type === 'password' ? 'text' : 'password';
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  const modal = document.getElementById('authModal');
  if (e.key === 'Escape' && modal.classList.contains('open')) closeModal();
  if (e.key === 'Enter'  && modal.classList.contains('open')) submitAuth();
});