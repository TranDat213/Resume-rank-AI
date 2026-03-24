from flask import Flask, request, jsonify
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
import spacy
import re
import os
import joblib
import numpy as np

app = Flask(__name__)

try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

print("Loading NLP models (this may take a moment)...")

# ── Spacy ──────────────────────────────────────────────────────────────────────
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("WARNING: Spacy model not found. Run 'python -m spacy download en_core_web_sm'")
    nlp = None

# ── Sentence Embedder ──────────────────────────────────────────────────────────
if SentenceTransformer is not None:
    try:
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        print(f"WARNING: Failed to load sentence-transformers: {e}")
        embedder = None
else:
    embedder = None

# ── Load trained RandomForest model (.pkl) ─────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'cv_scoring_model.pkl')
scoring_model = None
if os.path.exists(MODEL_PATH):
    try:
        scoring_model = joblib.load(MODEL_PATH)
        print(f"✅ Loaded AI scoring model from {MODEL_PATH}")
    except Exception as e:
        print(f"WARNING: Could not load scoring model: {e}")
else:
    print(f"WARNING: Model file not found at {MODEL_PATH}. Falling back to ratio scoring.")

# ── Skill dictionary ───────────────────────────────────────────────────────────
COMMON_TECH_SKILLS = [
    "python", "java", "c++", "c#", "c", "javascript", "typescript", "ruby",
    "php", "go", "rust", "swift", "kotlin", "dart", "scala", "r", "matlab",
    "perl", "haskell",
    "react", "angular", "vue", "node.js", "django", "flask", "spring",
    "express", "next.js", "nestjs", "laravel", "ruby on rails", "asp.net", "fastapi",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "sqlite", "redis",
    "elasticsearch", "cassandra", "oracle", "mariadb",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux", "jenkins",
    "gitlab ci", "github actions", "terraform", "ansible", "nginx", "apache",
    "machine learning", "deep learning", "ai", "artificial intelligence",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "keras",
    "opencv", "nlp", "computer vision", "data science",
    "html", "css", "rest", "graphql", "ci/cd", "agile", "scrum", "jira", "figma",
]

EDUCATION_KEYWORDS = {
    "phd": 4, "doctorate": 4,
    "master": 3, "msc": 3, "m.s": 3, "mba": 3,
    "bachelor": 2, "bsc": 2, "b.s": 2, "b.e": 2, "undergraduate": 2,
    "associate": 1, "diploma": 1, "certificate": 1,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_text(file) -> str:
    filename = file.filename.lower()
    text = ""

    if filename.endswith('.pdf'):
        try:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            print(f"Error reading PDF {filename}: {e}")

    elif filename.endswith(('.png', '.jpg', '.jpeg')):
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(file)
            text = pytesseract.image_to_string(img)
        except ImportError:
            print("WARNING: Pillow/pytesseract not installed.")
        except Exception as e:
            print(f"WARNING: Tesseract error for {filename}: {e}")

    else:
        try:
            text = file.read().decode('utf-8')
        except Exception:
            pass

    file.seek(0)
    return text


def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found = set()
    for skill in COMMON_TECH_SKILLS:
        if skill in ['c', 'c++', 'c#']:
            pattern = r'(?<!\w)' + re.escape(skill) + r'(?!\w)'
        else:
            pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)
    return list(found)


def extract_years(text: str) -> int:
    """Return the maximum years-of-experience number found in text."""
    matches = re.findall(
        r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?',
        text, re.IGNORECASE
    )
    if not matches:
        return 0
    return max(int(y) for y in matches)


def extract_education_level(text: str) -> int:
    """
    Return a numeric education level (0–4) from text.
    4 = PhD, 3 = Master, 2 = Bachelor, 1 = Diploma/Certificate, 0 = unknown
    """
    text_lower = text.lower()
    best = 0
    for kw, level in EDUCATION_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw), text_lower):
            best = max(best, level)
    return best


def extract_companies(text: str) -> list[str]:
    companies = []
    if nlp:
        doc = nlp(text[:100_000])
        for ent in doc.ents:
            if ent.label_ == "ORG" and len(ent.text) > 2:
                companies.append(ent.text)
    return list(set(companies))


def document_cosine_similarity(text_a: str, text_b: str) -> float:
    """
    Compute semantic similarity between two full documents.
    Falls back to TF-IDF-style Jaccard if embedder unavailable.
    """
    if embedder:
        try:
            emb_a = embedder.encode([text_a[:512]])   # truncate to keep it fast
            emb_b = embedder.encode([text_b[:512]])
            sim = cosine_similarity(emb_a, emb_b)[0][0]
            return float(np.clip(sim, 0.0, 1.0))
        except Exception:
            pass

    # Fallback: word-overlap Jaccard
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def skill_match_with_embeddings(jd_skills: list, cv_skills: list) -> tuple[list, list]:
    """
    Returns (matched_skills, missing_skills).
    Uses sentence-transformer cosine similarity when available,
    otherwise falls back to exact string matching.
    """
    matched, missing = [], []

    if embedder and jd_skills and cv_skills:
        jd_emb = embedder.encode(jd_skills)
        cv_emb = embedder.encode(cv_skills)
        sim_matrix = cosine_similarity(jd_emb, cv_emb)

        for i, jd_skill in enumerate(jd_skills):
            if sim_matrix[i].max() > 0.6:
                matched.append(jd_skill)
            else:
                missing.append(jd_skill)
    else:
        cv_set = set(cv_skills)
        for js in jd_skills:
            (matched if js in cv_set else missing).append(js)

    return matched, missing


def predict_score(
    skill_match_ratio: float,
    experience_diff: float,
    cos_sim: float,
    education_match: int,
) -> float:
    """
    Use the trained RandomForest model to predict a 0–100 score.
    Falls back to a weighted formula if the model isn't loaded.
    """
    if scoring_model is not None:
        features = np.array([[skill_match_ratio, experience_diff, cos_sim, education_match]])
        raw = scoring_model.predict(features)[0]
        # Model was trained on 0–100 scale; normalise just in case
        return float(np.clip(raw, 0, 100)) / 100.0
    else:
        # Weighted fallback (no model)
        score = (
            skill_match_ratio * 0.50 +
            cos_sim            * 0.30 +
            min(max(experience_diff + 3, 0) / 6, 1) * 0.10 +
            (education_match / 4)  * 0.10
        )
        return float(np.clip(score, 0.0, 1.0))


def build_feedback(
    missing_skills: list,
    jd_skills: list,
    cv_skills: list,
    years_experience: int,
    education_level: int,
) -> list[str]:
    feedback = []

    if missing_skills:
        feedback.append(
            f"Bạn thiếu các kỹ năng: {', '.join(missing_skills)} → nên học thêm."
        )

    ai_skills = {'machine learning', 'ai', 'deep learning', 'tensorflow', 'pytorch'}
    if any(s in jd_skills for s in ai_skills) and not any(s in cv_skills for s in ai_skills):
        feedback.append("CV chưa có project AI/ML → nên bổ sung dự án thực tế.")

    if years_experience == 0:
        feedback.append("CV chưa làm rõ số năm kinh nghiệm → nên ghi rõ.")

    if education_level == 0:
        feedback.append("CV chưa đề cập trình độ học vấn → nên bổ sung.")

    return feedback


# ── Route ──────────────────────────────────────────────────────────────────────

@app.route('/rank', methods=['POST'])
def rank():
    jd        = request.form.get('jd', '').strip()
    files     = request.files.getlist('cvs')

    if not jd:
        return jsonify({"error": "Job description is required."}), 400
    if not files:
        return jsonify({"error": "At least one CV file is required."}), 400

    # ── Extract JD info ──
    jd_skills       = extract_skills(jd)
    jd_years        = extract_years(jd)          # required years from JD
    jd_edu_level    = extract_education_level(jd)

    if not jd_skills:
        jd_skills = [jd]   # use raw JD as single "skill" for similarity

    results = []

    for file in files:
        cv_text = extract_text(file)
        if not cv_text.strip():
            results.append({
                "filename": file.filename,
                "score": 0.0,
                "error": "Could not extract text from file.",
            })
            continue

        # ── Extract CV info ──
        cv_skills       = extract_skills(cv_text)
        cv_years        = extract_years(cv_text)
        cv_edu_level    = extract_education_level(cv_text)
        companies       = extract_companies(cv_text)

        # ── Feature 1: skill_match_ratio ──
        matched_skills, missing_skills = skill_match_with_embeddings(jd_skills, cv_skills)
        skill_match_ratio = len(matched_skills) / len(jd_skills) if jd_skills else 0.0

        # ── Feature 2: experience_diff ──
        # Positive = candidate has more years than required
        experience_diff = float(cv_years - jd_years)

        # ── Feature 3: document cosine similarity ──
        cos_sim = document_cosine_similarity(jd, cv_text)

        # ── Feature 4: education_match ──
        # 1 if candidate meets or exceeds JD education requirement
        education_match = int(cv_edu_level >= jd_edu_level) if jd_edu_level > 0 else 1

        # ── AI model prediction ──
        final_score = predict_score(
            skill_match_ratio,
            experience_diff,
            cos_sim,
            education_match,
        )

        # ── Feedback ──
        feedback = build_feedback(
            missing_skills, jd_skills, cv_skills,
            cv_years, cv_edu_level,
        )

        results.append({
            "filename":     file.filename,
            "score":        round(final_score, 4),
            "matched_skills":  matched_skills,
            "missing_skills":  missing_skills,
            "feedback":        feedback,
            "extracted_info": {
                "skills":           cv_skills,
                "companies":        companies,
                "years_experience": cv_years,
                "education_level":  cv_edu_level,
            },
            # expose features for transparency / debugging
            "features": {
                "skill_match_ratio": round(skill_match_ratio, 4),
                "experience_diff":   experience_diff,
                "cosine_similarity": round(cos_sim, 4),
                "education_match":   education_match,
            },
        })

    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return jsonify(results)


if __name__ == '__main__':
    app.run(port=5000, host="0.0.0.0", debug=False)