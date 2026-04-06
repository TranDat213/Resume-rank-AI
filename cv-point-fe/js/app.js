// js/app.js
// Entry point: khởi động app sau khi DOM sẵn sàng

window.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  restoreSession();
  initFileUpload();
  initJD();
  updateHint();
});

// ── Health check: hiển thị trạng thái backend trên header ─────────────────────
async function checkHealth() {
  const pill = document.getElementById('statusPill');
  const txt = document.getElementById('statusText');

  try {
    const res = await fetch(ENDPOINTS.health, {
      signal: AbortSignal.timeout(3000),
    });

    if (res.ok) {
      const data = await res.json();

      if (data.aiService !== 'connected') {
        txt.textContent = 'AI SERVICE OFFLINE';
        pill.className = 'status-pill offline';
        return;
      }

      txt.textContent = data.aiDetails?.model_loaded
        ? 'AI APP READY'
        : 'NO MODEL';

      pill.className = data.aiDetails?.model_loaded
        ? 'status-pill ready'
        : 'status-pill warn';
    } else {
      throw new Error();
    }
  } catch {
    txt.textContent = 'APP OFFLINE';
    pill.className = 'status-pill offline';
  }
}

// ── Clear toàn bộ form và kết quả ─────────────────────────────────────────────
function clearAll() {
  selectedFiles = [];
  renderFileList();

  document.getElementById('jd').value = '';
  document.getElementById('jdMeta').innerHTML = '';
  document.getElementById('results').innerHTML = '';
  clearError();
  updateHint();
}