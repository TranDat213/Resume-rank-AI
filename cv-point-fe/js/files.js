

let selectedFiles = [];

// ── Khởi tạo event listeners (gọi sau DOMContentLoaded) ──────────────────────
function initFileUpload() {
  const cvInput  = document.getElementById('cvInput');
  const dropZone = document.getElementById('dropZone');

  cvInput.addEventListener('change', () => {
    addFiles(Array.from(cvInput.files));
    cvInput.value = '';
  });

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    addFiles(Array.from(e.dataTransfer.files));
  });
}

// ── Thêm files, bỏ qua duplicate ─────────────────────────────────────────────
function addFiles(newFiles) {
  newFiles.forEach(f => {
    const isDuplicate = selectedFiles.find(x => x.name === f.name && x.size === f.size);
    if (!isDuplicate) selectedFiles.push(f);
  });
  renderFileList();
  updateHint();
}

// ── Xóa 1 file theo index ─────────────────────────────────────────────────────
function removeFile(idx) {
  selectedFiles.splice(idx, 1);
  renderFileList();
  updateHint();
}

// ── Render danh sách file ─────────────────────────────────────────────────────
function renderFileList() {
  document.getElementById('cvCount').textContent = selectedFiles.length;

  document.getElementById('fileList').innerHTML = selectedFiles
    .map((f, i) => `
      <div class="file-chip" style="animation-delay:${i * 0.04}s">
        <span class="file-type-badge">${getExt(f.name)}</span>
        <span class="file-chip-name">${escHtml(f.name)}</span>
        <span class="file-chip-size">${fmtSize(f.size)}</span>
        <button class="file-chip-remove" onclick="removeFile(${i})" title="Remove">×</button>
      </div>`)
    .join('');
}

function getExt(filename) {
  return filename.split('.').pop().toUpperCase();
}