// js/ranking.js
// Gọi API rank, render kết quả, build card HTML

// ── Entry point: check auth trước khi rank ────────────────────────────────────
async function rankCVs() {
  const jd = document.getElementById('jd').value.trim();

  if (!jd)                   { showError('Please enter a job description.'); return; }
  if (!selectedFiles.length) { showError('Please upload at least one CV.'); return; }

  // Chưa đăng nhập → mở modal, đặt cờ pending
  if (!getToken()) {
    pendingRank = true;
    openModal('login');
    return;
  }

  await doRank();
}

// ── Gọi API thực sự ───────────────────────────────────────────────────────────
async function doRank() {
  const jd      = document.getElementById('jd').value.trim();
  const rankBtn = document.getElementById('rankBtn');
  const loadingBar = document.getElementById('loadingBar');

  rankBtn.disabled = true;
  loadingBar.classList.add('active');
  document.getElementById('loadingLabel').textContent =
    `Analysing ${selectedFiles.length} CV${selectedFiles.length > 1 ? 's' : ''}…`;
  document.getElementById('results').innerHTML = '';
  clearError();

  const form = new FormData();
  form.append('jd', jd);
  selectedFiles.forEach(f => form.append('cvs', f, f.name));

  try {
    const res = await fetch(ENDPOINTS.rank, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: form,
    });

    // Token hết hạn
    if (res.status === 401) {
      clearAuth();
      showLoggedOut();
      showError('Session expired. Please sign in again.');
      pendingRank = true;
      openModal('login');
      return;
    }

    if (!res.ok) throw new Error(`Server responded ${res.status}: ${res.statusText}`);

    const data = await res.json();
    
    // Show JD info briefly on the UI if possible
    if (data.jd_info) {
      const { required_skills, required_years, required_education_level } = data.jd_info;
      const eduStr = ['Unknown', 'Diploma/Cert', 'Bachelor', 'Master', 'PhD'][required_education_level] || '–';
      document.getElementById('jdMeta').innerHTML = `
        <strong>Meta:</strong> 
        Skills: ${required_skills.length ? required_skills.join(', ') : 'None'} | 
        Exp: ${required_years} yr(s) | 
        Edu: ${eduStr}
      `;
    }

    renderResults(data.results);

  } catch (err) {
    showError(`
      Failed to connect to backend: <strong>${escHtml(err.message)}</strong>
      <br/><small>Make sure NestJS is running on port 3000 and Flask on port 5000.</small>
    `);
  } finally {
    rankBtn.disabled = false;
    loadingBar.classList.remove('active');
  }
}

// ── Render toàn bộ danh sách kết quả ─────────────────────────────────────────
function renderResults(data) {
  if (!data || !data.length) {
    document.getElementById('results').innerHTML =
      `<div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        No results returned from the server.
      </div>`;
    return;
  }

  document.getElementById('results').innerHTML = `
    <div class="results-header">
      <div class="results-title">Rankings</div>
      <div class="results-meta">
        <span class="results-count">${data.length} candidate${data.length > 1 ? 's' : ''}</span>
        <span class="results-hint">Click a card to expand</span>
      </div>
    </div>
    <div class="result-cards">
      ${data.map((r, i) => buildCard(r, i)).join('')}
    </div>`;

  // Animate score bars sau khi DOM render xong
  requestAnimationFrame(() => {
    document.querySelectorAll('.score-bar-fill').forEach(el => {
      const w = el.dataset.w;
      el.style.width = '0%';
      requestAnimationFrame(() => { el.style.width = w; });
    });
  });
}

// ── Build HTML cho 1 result card ──────────────────────────────────────────────
function buildCard(r, i) {
  const score    = r.score ?? 0;
  const pct      = Math.round(score);
  const info     = r.extracted_info || {};
  const features = r.features || {};
  const matched  = r.matched_skills  || [];
  const missing  = r.missing_skills  || [];
  const feedback = r.feedback || [];

  const skillsPreview = matched.slice(0, 4).join(', ') || 'No matching skills';
  const eduLabel = ['Unknown', 'Diploma/Cert', 'Bachelor', 'Master', 'PhD'][info.education_level] || '–';
  const suggestions = buildSuggestions(missing, feedback, features, info);

  return `
  <div class="result-card ${rankClass(i)}" style="animation-delay:${i * 0.06}s">

    <!-- Top row -->
    <div class="result-top" onclick="toggleDetail(this)">
      <div class="rank-badge">#${i + 1}</div>
      <div class="result-meta">
        <div class="result-filename" title="${escHtml(r.filename)}">${escHtml(r.filename)}</div>
        <div class="result-skills-preview">
          ${matched.length
            ? `✓ ${escHtml(skillsPreview)}`
            : '<span style="color:var(--danger)">No skills matched</span>'}
        </div>
      </div>
      <div class="score-block">
        <div class="score-num ${scoreClass(score)}">${pct}</div>
        <div class="score-label">/ 100</div>
      </div>
      <div class="chevron">▾</div>
    </div>

    <!-- Score bar -->
    <div class="score-bar-wrap">
      <div class="score-bar-fill ${fillClass(score)}" data-w="${pct}%" style="width:0%"></div>
    </div>

    <!-- Detail panel (expandable) -->
    <div class="result-detail">
      ${buildTabBar(suggestions.length)}
      ${buildSkillsTab(matched, missing, info)}
      ${buildAnalysisTab(pct, features, eduLabel, score)}
      ${buildSuggestionsTab(suggestions)}
    </div>

  </div>`;
}

// ── Tab bar ───────────────────────────────────────────────────────────────────
function buildTabBar(suggCount) {
  return `
    <div class="tab-bar">
      <button class="tab active" onclick="switchTab(this,'skills')">Skills</button>
      <button class="tab" onclick="switchTab(this,'analysis')">AI Analysis</button>
      <button class="tab" onclick="switchTab(this,'suggestions')">
        Suggestions
        ${suggCount ? `<span class="tab-badge">${suggCount}</span>` : ''}
      </button>
    </div>`;
}

// ── Tab: Skills ───────────────────────────────────────────────────────────────
function buildSkillsTab(matched, missing, info) {
  return `
    <div class="tab-panel" data-tab="skills">
      <div class="detail-grid">
        <div class="detail-section">
          <div class="detail-section-title">Matched skills (${matched.length})</div>
          <div class="skill-tags">
            ${matched.length
              ? matched.map(s => `<span class="skill-tag tag-match">${escHtml(s)}</span>`).join('')
              : '<span class="no-data">None matched</span>'}
          </div>
        </div>
        <div class="detail-section">
          <div class="detail-section-title">Missing skills (${missing.length})</div>
          <div class="skill-tags">
            ${missing.length
              ? missing.map(s => `<span class="skill-tag tag-miss">${escHtml(s)}</span>`).join('')
              : '<span class="no-data ok">All required skills present ✓</span>'}
          </div>
        </div>
      </div>
      ${info.companies && info.companies.length ? `
      <div class="detail-section" style="margin-top:12px">
        <div class="detail-section-title">Detected companies / orgs</div>
        <div class="info-pills">
          ${info.companies.slice(0, 8).map(c => `<div class="info-pill">${escHtml(c)}</div>`).join('')}
        </div>
      </div>` : ''}
    </div>`;
}

// ── Tab: AI Analysis ──────────────────────────────────────────────────────────
function buildAnalysisTab(pct, features, eduLabel, score) {
  return `
    <div class="tab-panel hidden" data-tab="analysis">
      <div class="feature-grid">
        ${featureCard('Skill match',     pct + '%',
            features.skill_match_ratio != null ? Math.round(features.skill_match_ratio * 100) : null, 'skill')}
        ${featureCard('Experience',      expLabel(features.experience_diff), null, 'exp')}
        ${featureCard('Text similarity', pct2(features.cosine_similarity),
            features.cosine_similarity != null ? Math.round(features.cosine_similarity * 100) : null, 'cos')}
        ${featureCard('Education',       eduLabel, features.education_match, 'edu')}
      </div>
      <div class="gauge-row">
        <div class="gauge-label">AI Score</div>
        <div class="gauge-track">
          <div class="gauge-fill ${fillClass(score)}" style="width:${pct}%"></div>
        </div>
        <div class="gauge-val ${scoreClass(score)}">${pct}<span style="font-size:12px;opacity:0.6">/100</span></div>
      </div>
      <div class="model-note">
        Scored by Gradient Boosting · 4 features · trained on 500 samples
      </div>
    </div>`;
}

// ── Tab: Suggestions ──────────────────────────────────────────────────────────
function buildSuggestionsTab(suggestions) {
  return `
    <div class="tab-panel hidden" data-tab="suggestions">
      ${suggestions.length
        ? `<div class="suggestion-list">${suggestions.map(buildSuggestionItem).join('')}</div>`
        : `<div class="no-data ok" style="padding:16px 0">✓ No issues detected — strong candidate profile.</div>`}
    </div>`;
}

// ── Feature card helper ───────────────────────────────────────────────────────
function featureCard(label, value, barPct, key) {
  const colorMap = {
    skill: barPct >= 70 ? 'fill-high' : barPct >= 40 ? 'fill-mid' : 'fill-low',
    cos:   barPct >= 70 ? 'fill-high' : barPct >= 40 ? 'fill-mid' : 'fill-low',
    exp:   'fill-mid',
    edu:   value === 'Unknown' ? 'fill-low' : 'fill-high',
  };
  return `
    <div class="feature-card">
      <div class="feature-label">${label}</div>
      <div class="feature-value">${value}</div>
      ${barPct != null ? `
      <div class="feature-bar-track">
        <div class="feature-bar-fill ${colorMap[key]}" style="width:${barPct}%"></div>
      </div>` : ''}
    </div>`;
}

function expLabel(d) {
  if (d == null) return '–';
  if (d > 0)     return `+${d}y`;
  if (d < 0)     return `${d}y`;
  return 'exact';
}

function pct2(v) {
  return v != null ? Math.round(v * 100) + '%' : '–';
}

// ── Tab switching & card expand ───────────────────────────────────────────────
function switchTab(btn, tabName) {
  const detail = btn.closest('.result-detail');
  detail.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  detail.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
  btn.classList.add('active');
  detail.querySelector(`[data-tab="${tabName}"]`).classList.remove('hidden');
}

function toggleDetail(el) {
  el.classList.toggle('expanded');
  el.parentElement.querySelector('.result-detail').classList.toggle('open');
}