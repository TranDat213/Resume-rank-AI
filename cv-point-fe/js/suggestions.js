// js/suggestions.js
// Tạo gợi ý cải thiện CV từ kết quả AI (missing skills, features, feedback)

const SKILL_CATEGORIES = {
  'Languages':  ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 'c++', 'c#'],
  'Frameworks': ['react', 'angular', 'vue', 'node.js', 'django', 'flask', 'fastapi', 'spring', 'nestjs'],
  'Databases':  ['sql', 'postgresql', 'mysql', 'mongodb', 'redis'],
  'DevOps':     ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'linux'],
  'AI/ML':      ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp', 'data science'],
};

const LEARN_LINKS = {
  'AI/ML':      { label: 'Kaggle Learn',  url: 'https://www.kaggle.com/learn' },
  'DevOps':     { label: 'Docker Docs',   url: 'https://docs.docker.com/get-started/' },
  'Databases':  { label: 'SQLZoo',        url: 'https://sqlzoo.net' },
  'Languages':  { label: 'Exercism',      url: 'https://exercism.org' },
  'Frameworks': { label: 'MDN Web Docs',  url: 'https://developer.mozilla.org' },
};

// ── Phân loại missing skills theo nhóm ───────────────────────────────────────
function categorizeMissing(skills) {
  const cats = {};
  skills.forEach(s => {
    let placed = false;
    for (const [cat, list] of Object.entries(SKILL_CATEGORIES)) {
      if (list.includes(s)) {
        (cats[cat] = cats[cat] || []).push(s);
        placed = true;
        break;
      }
    }
    if (!placed) (cats['Other'] = cats['Other'] || []).push(s);
  });
  return cats;
}

function learnLink(cat, skills) {
  return LEARN_LINKS[cat] || {
    label: 'Search Coursera',
    url: `https://www.coursera.org/search?query=${encodeURIComponent(skills[0])}`,
  };
}

// ── Build danh sách gợi ý ─────────────────────────────────────────────────────
function buildSuggestions(missing, feedback, features, info) {
  const items = [];

  // 1. Missing skills → nhóm theo category
  if (missing.length) {
    const cats = categorizeMissing(missing);
    Object.entries(cats).forEach(([cat, skills]) => {
      items.push({
        level:  'high',
        title:  `Learn missing ${cat} skills`,
        body:   `CV is missing: <strong>${skills.join(', ')}</strong>. These are required by the JD.`,
        action: learnLink(cat, skills),
      });
    });
  }

  // 2. Skill match thấp
  if (features.skill_match_ratio != null && features.skill_match_ratio < 0.5) {
    items.push({
      level:  'high',
      title:  'Skill match below 50%',
      body:   `Only ${Math.round(features.skill_match_ratio * 100)}% of required skills appear in this CV. Add specific technical keywords that mirror the JD.`,
      action: null,
    });
  }

  // 3. Text similarity thấp
  if (features.cosine_similarity != null && features.cosine_similarity < 0.4) {
    items.push({
      level:  'mid',
      title:  "CV wording doesn't match JD",
      body:   'Text similarity is low. Rewrite the summary and experience sections using vocabulary from the job description.',
      action: null,
    });
  }

  // 4. Thiếu kinh nghiệm
  if (features.experience_diff != null && features.experience_diff < -1) {
    items.push({
      level: 'mid',
      title: `Experience gap: ${Math.abs(Math.round(features.experience_diff))} year(s) short`,
      body:  'Consider highlighting relevant projects, internships, or freelance work to compensate.',
      action: null,
    });
  }

  // 5. Không detect được học vấn
  if (info.education_level === 0) {
    items.push({
      level:  'low',
      title:  'Education level not detected',
      body:   'Add degree information (e.g. "Bachelor of Science in Computer Science") to improve the score.',
      action: null,
    });
  }

  // 6. Số năm kinh nghiệm không rõ
  if (info.years_experience === 0) {
    items.push({
      level:  'low',
      title:  'Years of experience unclear',
      body:   'Mention total years explicitly, e.g. "3+ years of experience in backend development".',
      action: null,
    });
  }

  // 7. JD yêu cầu AI/ML nhưng CV không có
  feedback.forEach(fb => {
    if (fb.includes('AI/ML') && !items.find(x => x.title.includes('AI/ML'))) {
      items.push({
        level:  'mid',
        title:  'No AI/ML projects in CV',
        body:   'JD requires AI/ML experience. Add at least one project using scikit-learn, TensorFlow, or PyTorch.',
        action: { label: 'Browse ML project ideas', url: 'https://www.kaggle.com/competitions' },
      });
    }
  });

  return items;
}

// ── Render 1 suggestion item ──────────────────────────────────────────────────
function buildSuggestionItem(s) {
  const colorMap = { high: 'sug-high', mid: 'sug-mid', low: 'sug-low' };
  const iconMap  = { high: '🔴',       mid: '🟡',      low: '🔵' };

  return `
    <div class="suggestion-item ${colorMap[s.level]}">
      <div class="sug-icon">${iconMap[s.level]}</div>
      <div class="sug-body">
        <div class="sug-title">${escHtml(s.title)}</div>
        <div class="sug-text">${s.body}</div>
        ${s.action
          ? `<a class="sug-link" href="${s.action.url}" target="_blank" rel="noopener">${escHtml(s.action.label)} →</a>`
          : ''}
      </div>
    </div>`;
}