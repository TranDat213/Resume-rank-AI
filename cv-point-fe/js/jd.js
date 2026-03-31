// js/jd.js
// Live analysis của JD textarea: detect skills, hiển thị pills

const JD_SKILLS = [
  'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'c++', 'c#',
  'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'fastapi', 'spring', 'nestjs',
  'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'linux',
  'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
  'sql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
  'html', 'css', 'rest', 'graphql', 'ci/cd', 'agile', 'scrum',
];

// ── Khởi tạo event listener (gọi sau DOMContentLoaded) ───────────────────────
function initJD() {
  document.getElementById('jd').addEventListener('input', () => {
    updateHint();
    analyseJD();
  });
}

// ── Parse JD và hiện skill pills ─────────────────────────────────────────────
function analyseJD() {
  const text = document.getElementById('jd').value.toLowerCase();
  const meta = document.getElementById('jdMeta');

  const found = JD_SKILLS.filter(s =>
    new RegExp('\\b' + s.replace(/[+#.]/g, '\\$&') + '\\b').test(text)
  );

  const yearsMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)/);

  if (!found.length && !yearsMatch) {
    meta.innerHTML = '';
    return;
  }

  meta.innerHTML = `
    <div class="jd-pills">
      ${yearsMatch ? `<span class="jd-pill jd-pill-years">⏱ ${yearsMatch[1]}+ yrs</span>` : ''}
      ${found.slice(0, 8).map(s => `<span class="jd-pill">${s}</span>`).join('')}
      ${found.length > 8 ? `<span class="jd-pill jd-pill-more">+${found.length - 8} more</span>` : ''}
    </div>`;
}

// ── Hint text bên phải nút Rank ───────────────────────────────────────────────
function updateHint() {
  const jd  = document.getElementById('jd').value.trim();
  const cnt = selectedFiles.length;
  const el  = document.getElementById('hintText');

  if (!jd && cnt === 0)  el.textContent = 'Add a JD and at least one CV to start';
  else if (!jd)          el.textContent = 'Paste a job description to continue';
  else if (cnt === 0)    el.textContent = 'Upload at least one CV to continue';
  else if (!getToken())  el.textContent = `Ready — sign in to rank ${cnt} CV${cnt > 1 ? 's' : ''}`;
  else                   el.textContent = `Ready — ${cnt} CV${cnt > 1 ? 's' : ''} queued`;
}