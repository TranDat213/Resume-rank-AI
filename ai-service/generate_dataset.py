import pandas as pd
import numpy as np

SEED = 42
np.random.seed(SEED)
N = 500

def simulate_experience_diff():
    """
    Mô phỏng chênh lệch năm kinh nghiệm (cv_years - jd_required_years).
    Phân bố thực tế: nhiều người đúng hoặc dư 1-2 năm,
    ít người thiếu nhiều hoặc dư quá nhiều.
    """
    return np.clip(np.random.normal(loc=0.5, scale=2.5), -5, 10)


def simulate_cosine_similarity(skill_match_ratio):
    """
    Cosine similarity tương quan thuận với skill match,
    nhưng có nhiễu (CV viết tốt dù thiếu skill, hoặc ngược lại).
    """
    base = 0.3 + skill_match_ratio * 0.55
    noise = np.random.normal(0, 0.08)
    return float(np.clip(base + noise, 0.05, 0.98))


def compute_target_score(skill_match_ratio, experience_diff, cosine_similarity, education_match):
    """
    Công thức chấm điểm có trọng số + penalty/bonus thực tế:

    - Thiếu skill nhiều (< 0.3) bị penalty nặng
    - Dư kinh nghiệm nhiều (> 5 năm) không cộng thêm nhiều (over-qualified)
    - Thiếu kinh nghiệm (< -2 năm) bị penalty
    - education_match = 0 bị trừ điểm đáng kể
    """
    # Base score theo trọng số
    exp_norm = np.clip((experience_diff + 5) / 15, 0, 1)   # normalize [-5,10] → [0,1]
    score = (
        skill_match_ratio  * 50 +
        cosine_similarity  * 25 +
        exp_norm           * 15 +
        education_match    * 10
    )

    # Penalty: thiếu skill nghiêm trọng
    if skill_match_ratio < 0.3:
        score *= 0.75

    # Penalty: thiếu kinh nghiệm nhiều
    if experience_diff < -2:
        score -= abs(experience_diff + 2) * 2

    # Penalty: over-qualified (dư > 7 năm, thường không phù hợp vai trò)
    if experience_diff > 7:
        score -= (experience_diff - 7) * 1.5

    # Penalty: học vấn không đáp ứng
    if education_match == 0:
        score -= 8

    # Bonus: skill + cosine đều cao → CV viết rất khớp JD
    if skill_match_ratio > 0.8 and cosine_similarity > 0.75:
        score += 5

    # Thêm nhiễu nhỏ (human scoring không hoàn hảo)
    score += np.random.normal(0, 2.5)

    return float(np.clip(score, 0, 100))


def generate():
    rows = []

    for _ in range(N):
        # skill_match_ratio: phân bố beta để có nhiều giá trị trung bình (0.3–0.8)
        skill_match_ratio = float(np.random.beta(a=2.5, b=2.0))

        experience_diff   = simulate_experience_diff()
        cosine_similarity = simulate_cosine_similarity(skill_match_ratio)

        # education_match: 65% ứng viên đáp ứng yêu cầu học vấn
        education_match   = int(np.random.random() < 0.65)

        target_score = compute_target_score(
            skill_match_ratio,
            experience_diff,
            cosine_similarity,
            education_match,
        )

        rows.append({
            "skill_match_ratio" : round(skill_match_ratio, 4),
            "experience_diff"   : round(experience_diff,   2),
            "cosine_similarity" : round(cosine_similarity, 4),
            "education_match"   : education_match,
            "target_score"      : round(target_score,      2),
        })

    df = pd.DataFrame(rows)

    # Sanity check: in thống kê cơ bản
    print("=== Thống kê dataset ===")
    print(df.describe().round(2).to_string())
    print(f"\nTổng số rows: {len(df)}")
    print(f"Score trung bình : {df['target_score'].mean():.1f}")
    print(f"Score thấp nhất  : {df['target_score'].min():.1f}")
    print(f"Score cao nhất   : {df['target_score'].max():.1f}")
    print(f"education_match=1: {df['education_match'].sum()} / {N} ({df['education_match'].mean()*100:.0f}%)")

    out_path = "sample_dataset.csv"
    df.to_csv(out_path, index=False)
    print(f"\n✅ Đã lưu {N} rows vào {out_path}")
    return df


if __name__ == "__main__":
    generate()