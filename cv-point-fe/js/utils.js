// js/utils.js
// Các hàm tiện ích dùng chung toàn bộ app

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function fmtSize(bytes) {
  if (bytes < 1024)        return bytes + 'B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
  return (bytes / 1024 / 1024).toFixed(1) + 'MB';
}

function showError(msg) {
  document.getElementById('errorBox').innerHTML =
    `<div class="error-box">${msg}</div>`;
}

function clearError() {
  document.getElementById('errorBox').innerHTML = '';
}

// score 0–100 → CSS class
function scoreClass(s) { return s >= 70 ? 'score-high' : s >= 40 ? 'score-mid' : 'score-low'; }
function fillClass(s)  { return s >= 70 ? 'fill-high'  : s >= 40 ? 'fill-mid'  : 'fill-low';  }
function rankClass(i)  { return ['rank-1', 'rank-2', 'rank-3'][i] || 'rank-other'; }