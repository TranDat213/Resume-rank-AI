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
    print("WARNING: Spacy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

# ── Sentence Embedder ──────────────────────────────────────────────────────────
if SentenceTransformer is not None:
    try:
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Loaded sentence-transformer: all-MiniLM-L6-v2")
    except Exception as e:
        print(f"WARNING: Failed to load sentence-transformers: {e}")
        embedder = None
else:
    embedder = None

# ── Load Gradient Boosting model (.pkl) ────────────────────────────────────────
# Model được train bởi train_scoring_model.py, predict score trên thang 0–100
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'cv_scoring_model.pkl')
scoring_model = None
if os.path.exists(MODEL_PATH):
    try:
        scoring_model = joblib.load(MODEL_PATH)
        print(f"✅ Loaded scoring model from {MODEL_PATH}")
    except Exception as e:
        print(f"WARNING: Could not load scoring model: {e}")
else:
    print(f"WARNING: {MODEL_PATH} not found.")
    print("         Run: python generate_dataset.py && python train_scoring_model.py")

# ── Constants ──────────────────────────────────────────────────────────────────
# Phải giống hệt thứ tự FEATURES trong train_scoring_model.py
FEATURE_ORDER = ["skill_match_ratio", "experience_diff", "cosine_similarity", "education_match"]

COMMON_TECH_SKILLS = [
    # Languages
    "python", "java", "c++", "c#", "c", "javascript", "typescript", "ruby",
    "php", "go", "rust", "swift", "kotlin", "dart", "scala", "r", "matlab",
    "perl", "haskell",
    # Frameworks
    "react", "angular", "vue", "node.js", "django", "flask", "spring",
    "express", "next.js", "nestjs", "laravel", "ruby on rails", "asp.net", "fastapi",
    # Databases
    "sql", "nosql", "mongodb", "postgresql", "mysql", "sqlite", "redis",
    "elasticsearch", "cassandra", "oracle", "mariadb",
    # Infrastructure & DevOps
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux", "jenkins",
    "gitlab ci", "github actions", "terraform", "ansible", "nginx", "apache",
    # AI & ML
    "machine learning", "deep learning", "ai", "artificial intelligence",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "keras",
    "opencv", "nlp", "computer vision", "data science",
    # General
    "html", "css", "rest", "graphql", "ci/cd", "agile", "scrum", "jira", "figma",
]

# Phải nhất quán với compute_target_score() trong generate_dataset.py
EDUCATION_KEYWORDS = {
    "phd": 4, "doctorate": 4,
    "master": 3, "msc": 3, "m.s": 3, "mba": 3,
    "bachelor": 2, "bsc": 2, "b.s": 2, "b.e": 2, "undergraduate": 2,
    "associate": 1, "diploma": 1, "certificate": 1,
}

# Skills liên quan AI/ML — dùng trong build_feedback
AI_SKILLS = {
    "machine learning", "ai", "deep learning", "tensorflow", "pytorch",
    "scikit-learn", "keras", "computer vision", "nlp", "data science",
}

# Từ hay bị Spacy nhận nhầm là ORG
INVALID_ORG_KEYWORDS = {
    "frontend", "backend", "skills", "education", "experience", "role",
    "responsibilities", "certificates", "projects", "summary", "profile",
    "database", "framework", "library", "vscode", "visual studio", "postman",
    "wamp", "crud", "rest api", "uml", "club", "git", "docker", "prisma",
    "bootstrap", "visual", "sql server", "objective", "tools", "languages",
    "technologies", "frameworks", "libraries", "mysql", "api",
}


# ── Text extraction ────────────────────────────────────────────────────────────

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


# ── Feature extractors ─────────────────────────────────────────────────────────

def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found = set()
    for skill in COMMON_TECH_SKILLS:
        if skill in ('c', 'c++', 'c#'):
            pattern = r'(?<!\w)' + re.escape(skill) + r'(?!\w)'
        else:
            pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)
    return list(found)


def extract_years(text: str) -> int:
    """Trả về số năm kinh nghiệm lớn nhất tìm được trong text."""
    matches = re.findall(
        r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?',
        text, re.IGNORECASE
    )
    return max((int(y) for y in matches), default=0)


def extract_education_level(text: str) -> int:
    """
    Trả về mức học vấn dạng số (0–4).
    Nhất quán với EDUCATION_KEYWORDS trong generate_dataset.py.
    """
    text_lower = text.lower()
    best = 0
    for kw, level in EDUCATION_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw), text_lower):
            best = max(best, level)
    return best


def extract_companies(text: str) -> list[str]:
    """Dùng Spacy NER tìm tên công ty, lọc bỏ từ kỹ thuật hay bị nhận nhầm."""
    if not nlp:
        return []

    companies = []
    doc = nlp(text[:100_000])

    for ent in doc.ents:
        if ent.label_ != "ORG":
            continue

        ent_text  = re.sub(r'\s+', ' ', ent.text.strip())
        lower_txt = ent_text.lower()

        if len(ent_text) <= 2:
            continue
        if lower_txt in COMMON_TECH_SKILLS or lower_txt in INVALID_ORG_KEYWORDS:
            continue
        if any(x in lower_txt for x in ["role", "responsibilit", "skill", "education",
                                         "backend", "frontend", "certificat", "summary"]):
            continue

        words = set(w.strip() for w in re.split(r'[\s\-,&/|]+', lower_txt) if w.strip())
        if words and all(w in COMMON_TECH_SKILLS or w in INVALID_ORG_KEYWORDS for w in words):
            continue

        # Bỏ nếu xuất hiện quá sớm — thường là tên người
        idx = text.lower().find(lower_txt)
        if 0 <= idx < 150:
            if not any(cw in lower_txt for cw in ["university", "college", "school",
                                                    "inc", "ltd", "corp", "company"]):
                continue

        companies.append(ent_text)

    return list(set(companies))


# ── Similarity & matching ──────────────────────────────────────────────────────

def document_cosine_similarity(text_a: str, text_b: str) -> float:
    """
    Tính semantic similarity giữa 2 văn bản.
    Nhất quán với feature cosine_similarity trong generate_dataset.py.
    """
    if embedder:
        try:
            emb_a = embedder.encode([text_a[:512]])
            emb_b = embedder.encode([text_b[:512]])
            sim = cosine_similarity(emb_a, emb_b)[0][0]
            return float(np.clip(sim, 0.0, 1.0))
        except Exception:
            pass

    # Fallback: Jaccard
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def skill_match_with_embeddings(jd_skills: list, cv_skills: list) -> tuple[list, list]:
    """
    So khớp skill JD vs CV.
    Dùng cosine > 0.6 để bắt synonym (vd: "ml" ≈ "machine learning").
    Trả về (matched_skills, missing_skills).
    """
    if not jd_skills:
        return [], []

    if embedder and cv_skills:
        jd_emb     = embedder.encode(jd_skills)
        cv_emb     = embedder.encode(cv_skills)
        sim_matrix = cosine_similarity(jd_emb, cv_emb)
        matched = [jd_skills[i] for i in range(len(jd_skills)) if sim_matrix[i].max() > 0.6]
        missing = [jd_skills[i] for i in range(len(jd_skills)) if sim_matrix[i].max() <= 0.6]
    else:
        cv_set  = set(cv_skills)
        matched = [s for s in jd_skills if s in cv_set]
        missing = [s for s in jd_skills if s not in cv_set]

    return matched, missing


# ── AI scoring ─────────────────────────────────────────────────────────────────

def predict_score(
    skill_match_ratio: float,
    experience_diff:   float,
    cos_sim:           float,
    education_match:   int,
) -> float:
    """
    Trả về score 0–100.

    Model (Gradient Boosting) output đã là thang 0–100 → KHÔNG chia thêm.
    Fallback dùng công thức giống compute_target_score() trong generate_dataset.py
    để kết quả nhất quán khi model chưa được train.
    """
    # Feature vector phải đúng thứ tự FEATURE_ORDER
    features = np.array([[skill_match_ratio, experience_diff, cos_sim, education_match]])

    if scoring_model is not None:
        raw = scoring_model.predict(features)[0]
        return float(np.clip(raw, 0.0, 100.0))

    # ── Weighted fallback ──
    exp_norm = float(np.clip((experience_diff + 5) / 15, 0, 1))
    score = (
        skill_match_ratio * 50 +
        cos_sim           * 25 +
        exp_norm          * 15 +
        education_match   * 10
    )
    if skill_match_ratio < 0.3:
        score *= 0.75
    if experience_diff < -2:
        score -= abs(experience_diff + 2) * 2
    if education_match == 0:
        score -= 8
    return float(np.clip(score, 0.0, 100.0))


# ── Feedback ───────────────────────────────────────────────────────────────────

def build_feedback(
    missing_skills:   list,
    jd_skills:        list,
    cv_skills:        list,
    years_experience: int,
    education_level:  int,
) -> list[str]:
    feedback = []

    if missing_skills:
        feedback.append(f"Thiếu kỹ năng: {', '.join(missing_skills)} → nên học thêm.")

    if any(s in jd_skills for s in AI_SKILLS) and not any(s in cv_skills for s in AI_SKILLS):
        feedback.append("JD yêu cầu AI/ML nhưng CV chưa có dự án liên quan → nên bổ sung.")

    if years_experience == 0:
        feedback.append("CV chưa ghi rõ số năm kinh nghiệm → nên bổ sung.")

    if education_level == 0:
        feedback.append("CV chưa đề cập trình độ học vấn → nên bổ sung.")

    return feedback


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """Kiểm tra service và trạng thái các model."""
    return jsonify({
        "status":          "ok",
        "model_loaded":    scoring_model is not None,
        "embedder_loaded": embedder is not None,
        "spacy_loaded":    nlp is not None,
    })


@app.route('/rank', methods=['POST'])
def rank():
    jd    = request.form.get('jd', '').strip()
    files = request.files.getlist('cvs')

    if not jd:
        return jsonify({"error": "Job description is required."}), 400
    if not files:
        return jsonify({"error": "At least one CV file is required."}), 400

    # ── Extract JD info ──
    jd_skills    = extract_skills(jd)
    jd_years     = extract_years(jd)
    jd_edu_level = extract_education_level(jd)

    if not jd_skills:
        jd_skills = [jd]   # dùng raw text nếu không tìm được skill cụ thể

    results = []

    for file in files:
        cv_text = extract_text(file)

        if not cv_text.strip():
            results.append({
                "filename": file.filename,
                "score":    0.0,
                "error":    "Could not extract text from file.",
            })
            continue

        # ── Extract CV info ──
        cv_skills    = extract_skills(cv_text)
        cv_years     = extract_years(cv_text)
        cv_edu_level = extract_education_level(cv_text)
        companies    = extract_companies(cv_text)

        # ── Feature 1: skill_match_ratio ──
        matched_skills, missing_skills = skill_match_with_embeddings(jd_skills, cv_skills)
        skill_match_ratio = len(matched_skills) / len(jd_skills) if jd_skills else 0.0

        # ── Feature 2: experience_diff ──
        # Clip về đúng phạm vi train [-5, 10] (xem simulate_experience_diff trong generate_dataset.py)
        experience_diff = float(np.clip(cv_years - jd_years, -5, 10))

        # ── Feature 3: cosine_similarity ──
        cos_sim = document_cosine_similarity(jd, cv_text)

        # ── Feature 4: education_match ──
        # Nếu JD không đề cập học vấn (level=0) → mặc định match=1
        education_match = int(cv_edu_level >= jd_edu_level) if jd_edu_level > 0 else 1

        # ── Predict (0–100) ──
        score = predict_score(skill_match_ratio, experience_diff, cos_sim, education_match)

        # ── Feedback ──
        feedback = build_feedback(
            missing_skills, jd_skills, cv_skills,
            cv_years, cv_edu_level,
        )

        results.append({
            "filename":       file.filename,
            "score":          round(score, 2),   # 0–100, ví dụ: 73.45
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "feedback":       feedback,
            "extracted_info": {
                "skills":           cv_skills,
                "companies":        companies,
                "years_experience": cv_years,
                "education_level":  cv_edu_level,
            },
            "features": {                         # debug / transparency
                "skill_match_ratio": round(skill_match_ratio, 4),
                "experience_diff":   round(experience_diff, 2),
                "cosine_similarity": round(cos_sim, 4),
                "education_match":   education_match,
            },
        })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return jsonify(results)


if __name__ == '__main__':
    app.run(port=5000, host="0.0.0.0", debug=False)