
// STATE
let selectedFiles = [];

const cvInput   = document.getElementById('cvInput');
const dropZone  = document.getElementById('dropZone');
const fileList  = document.getElementById('fileList');
const rankBtn   = document.getElementById('rankBtn');
const hintText  = document.getElementById('hintText');
const loadingBar = document.getElementById('loadingBar');
const jdEl      = document.getElementById('jd');

// HEALTH CHECK
async function checkHealth() {
  const pill = document.getElementById('statusPill');
  const txt  = document.getElementById('statusText');
  try {
    const r = await fetch('http://localhost:3000/health');
    const d = await r.json();
    txt.textContent = d.model_loaded ? 'AI MODEL READY' : 'NO MODEL';
    pill.className  = d.model_loaded ? 'status-pill ready' : 'status-pill warn';
  } catch {
    txt.textContent = 'BACKEND OFFLINE';
    pill.className  = 'status-pill offline';
  }
}
checkHealth();

// FILE EVENTS
cvInput.addEventListener('change', () => {
  addFiles(Array.from(cvInput.files));
  cvInput.value = '';
});

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  addFiles(Array.from(e.dataTransfer.files));
});

// ADD FILES (FIX TRÙNG)
function addFiles(newFiles) {
  newFiles.forEach(f => {
    const exists = selectedFiles.some(
      x => x.name === f.name && x.size === f.size && x.lastModified === f.lastModified
    );
    if (!exists) selectedFiles.push(f);
  });
  renderFileList();
  updateHint();
}

function removeFile(idx) {
  selectedFiles.splice(idx, 1);
  renderFileList();
  updateHint();
}

function renderFileList() {
  document.getElementById('cvCount').textContent = selectedFiles.length;
  fileList.innerHTML = selectedFiles.map((f, i) => `
    <div class="file-chip">
      <span>${f.name}</span>
      <span>${fmtSize(f.size)}</span>
      <button onclick="removeFile(${i})">×</button>
    </div>
  `).join('');
}

// SUBMIT
async function rankCVs() {
  const jd = jdEl.value.trim();
  if (!jd) return alert('Nhập JD');
  if (!selectedFiles.length) return alert('Upload CV');

  rankBtn.disabled = true;
  loadingBar.classList.add('active');

  const form = new FormData();
  form.append('jd', jd);
  selectedFiles.forEach(f => form.append('cvs', f, f.name));

  try {
    const res = await fetch('http://localhost:3000/ranking/upload', {
      method: 'POST',
      body: form
    });
    const data = await res.json();
    renderResults(data);
  } catch {
    alert('Backend lỗi');
  }

  rankBtn.disabled = false;
  loadingBar.classList.remove('active');
}

// RENDER
function renderResults(data) {
  document.getElementById('results').innerHTML = data.map((r, i) => `
    <div class="result-card">
      <h3>#${i+1} - ${r.filename}</h3>
      <p>Score: ${r.score}</p>

      <div class="suggestion-list">
        ${buildSuggestions(r.feedback).map(buildSuggestionItem).join('')}
      </div>

      <div class="feedback-list">
        ${r.feedback?.map(f => `<div class="feedback-item">${f}</div>`).join('') || ''}
      </div>
    </div>
  `).join('');
}

// BUILD SUGGESTIONS TỪ BACKEND
function buildSuggestions(feedback) {
  const items = [];
  if (!feedback) return items;

  feedback.forEach(fb => {
    items.push({
      level: detectLevel(fb),
      title: extractTitle(fb),
      body: fb
    });
  });

  return items;
}

// HELPER
function detectLevel(text) {
  if (text.includes('Thiếu')) return 'high';
  if (text.includes('nên')) return 'mid';
  return 'low';
}

function extractTitle(text) {
  if (text.includes('kỹ năng')) return 'Thiếu kỹ năng';
  if (text.includes('kinh nghiệm')) return 'Thiếu kinh nghiệm';
  if (text.includes('học vấn')) return 'Thiếu học vấn';
  return 'Cải thiện CV';
}

function buildSuggestionItem(s) {
  return `
    <div class="suggestion-item sug-${s.level}">
      <div class="sug-icon">${s.level === 'high' ? '🔴' : s.level === 'mid' ? '🟡' : '🔵'}</div>
      <div>
        <div class="sug-title">${s.title}</div>
        <div class="sug-text">${s.body}</div>
      </div>
    </div>
  `;
}

function updateHint() {
  if (!jdEl.value && !selectedFiles.length) hintText.textContent = 'Add JD + CV';
  else if (!jdEl.value) hintText.textContent = 'Nhập JD';
  else if (!selectedFiles.length) hintText.textContent = 'Upload CV';
  else hintText.textContent = 'Ready';
}

function fmtSize(b) {
  if (b < 1024) return b + 'B';
  if (b < 1024*1024) return (b/1024).toFixed(1) + 'KB';
  return (b/1024/1024).toFixed(1) + 'MB';
}
