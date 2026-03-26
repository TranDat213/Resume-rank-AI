import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from sklearn.ensemble         import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model     import LinearRegression
from sklearn.model_selection  import KFold, cross_val_score
from sklearn.metrics          import mean_absolute_error, r2_score, mean_squared_error, root_mean_squared_error
from sklearn.preprocessing    import StandardScaler
from sklearn.pipeline         import Pipeline

FEATURES     = ["skill_match_ratio", "experience_diff", "cosine_similarity", "education_match"]
TARGET       = "target_score"
DATASET_PATH = "sample_dataset.csv"
MODEL_PATH   = "cv_scoring_model.pkl"
CHART_PATH   = "model_evaluation.png"
N_FOLDS      = 5
SEED         = 42


# ── 1. Load data ───────────────────────────────────────────────────────────────

def load_data():
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Không tìm thấy {DATASET_PATH}. Hãy chạy generate_dataset.py trước.")
        raise FileNotFoundError(DATASET_PATH)

    df = pd.read_csv(DATASET_PATH)
    print(f"✅ Loaded {len(df)} rows từ {DATASET_PATH}")

    X = df[FEATURES].values
    y = df[TARGET].values
    return X, y


# ── 2. Định nghĩa các model cần so sánh ───────────────────────────────────────

def get_models():
    return {
        "Random Forest": RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=4,
            random_state=SEED,
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            min_samples_leaf=4,
            random_state=SEED,
        ),
        "Linear Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model",  LinearRegression()),
        ]),
    }


# ── 3. Cross-validation ────────────────────────────────────────────────────────

def cross_validate_all(models, X, y):
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    results = {}

    print(f"\n=== {N_FOLDS}-Fold Cross Validation ===")
    print(f"{'Model':<22} {'MAE mean':>10} {'MAE std':>9} {'R2 mean':>9} {'R2 std':>8}")
    print("-" * 62)

    for name, model in models.items():
        mae_scores = -cross_val_score(model, X, y, cv=kf, scoring="neg_mean_absolute_error")
        r2_scores  =  cross_val_score(model, X, y, cv=kf, scoring="r2")

        results[name] = {
            "mae_mean": mae_scores.mean(),
            "mae_std" : mae_scores.std(),
            "r2_mean" : r2_scores.mean(),
            "r2_std"  : r2_scores.std(),
            "mae_scores": mae_scores,
            "r2_scores" : r2_scores,
        }

        print(
            f"{name:<22} "
            f"{mae_scores.mean():>10.3f} "
            f"±{mae_scores.std():>7.3f} "
            f"{r2_scores.mean():>9.3f} "
            f"±{r2_scores.std():>6.3f}"
        )

    return results


# ── 4. Chọn model tốt nhất và train toàn bộ data ──────────────────────────────

def train_best_model(models, cv_results, X, y):
    # Chọn theo R2 cao nhất
    best_name = max(cv_results, key=lambda n: cv_results[n]["r2_mean"])
    best_model = models[best_name]

    print(f"\n🏆 Model tốt nhất: {best_name}")
    print(f"   R2  = {cv_results[best_name]['r2_mean']:.4f} ± {cv_results[best_name]['r2_std']:.4f}")
    print(f"   MAE = {cv_results[best_name]['mae_mean']:.4f} ± {cv_results[best_name]['mae_std']:.4f}")

    print(f"\nTraining {best_name} trên toàn bộ {len(X)} samples...")
    best_model.fit(X, y)

    # Đánh giá trên toàn bộ tập (train score — chỉ để tham khảo)
    y_pred = best_model.predict(X)
    print(f"Train MAE : {mean_absolute_error(y, y_pred):.3f}")
    print(f"Train RMSE: {root_mean_squared_error(y, y_pred):.3f}")
    print(f"Train R2  : {r2_score(y, y_pred):.4f}")

    return best_name, best_model


# ── 5. Vẽ biểu đồ đánh giá ────────────────────────────────────────────────────

def plot_evaluation(cv_results, best_name, best_model, X, y):
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("CV Scoring Model — Evaluation Report", fontsize=15, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.35)

    model_names = list(cv_results.keys())
    colors      = ["#5B6EE8", "#E8825B", "#5BE8A8"]
    best_color  = "#E8825B" if best_name == "Gradient Boosting" else (
                  "#5BE8A8" if best_name == "Linear Regression" else "#5B6EE8")

    # ── Panel 1: MAE so sánh (bar + error bar) ──
    ax1 = fig.add_subplot(gs[0, 0])
    mae_means = [cv_results[n]["mae_mean"] for n in model_names]
    mae_stds  = [cv_results[n]["mae_std"]  for n in model_names]
    bars = ax1.bar(model_names, mae_means, yerr=mae_stds, color=colors,
                   capsize=5, edgecolor="white", linewidth=0.8, alpha=0.88)
    ax1.set_title("MAE (thấp hơn = tốt hơn)", fontsize=11)
    ax1.set_ylabel("MAE (điểm)")
    ax1.set_xticks(range(len(model_names)))
    ax1.set_xticklabels([n.replace(" ", "\n") for n in model_names], fontsize=9)
    for bar, val in zip(bars, mae_means):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=9)

    # ── Panel 2: R2 so sánh ──
    ax2 = fig.add_subplot(gs[0, 1])
    r2_means = [cv_results[n]["r2_mean"] for n in model_names]
    r2_stds  = [cv_results[n]["r2_std"]  for n in model_names]
    bars2 = ax2.bar(model_names, r2_means, yerr=r2_stds, color=colors,
                    capsize=5, edgecolor="white", linewidth=0.8, alpha=0.88)
    ax2.set_title("R² Score (cao hơn = tốt hơn)", fontsize=11)
    ax2.set_ylabel("R²")
    ax2.set_ylim(0, 1.05)
    ax2.set_xticks(range(len(model_names)))
    ax2.set_xticklabels([n.replace(" ", "\n") for n in model_names], fontsize=9)
    for bar, val in zip(bars2, r2_means):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                 f"{val:.3f}", ha="center", va="bottom", fontsize=9)

    # ── Panel 3: Cross-val scores phân bố (boxplot) ──
    ax3 = fig.add_subplot(gs[0, 2])
    r2_data = [cv_results[n]["r2_scores"] for n in model_names]
    bp = ax3.boxplot(r2_data, patch_artist=True, notch=False,
                     medianprops=dict(color="white", linewidth=2))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ax3.set_title(f"Phân bố R² ({N_FOLDS}-fold)", fontsize=11)
    ax3.set_ylabel("R²")
    ax3.set_xticklabels([n.replace(" ", "\n") for n in model_names], fontsize=9)
    ax3.set_ylim(0, 1.05)

    # ── Panel 4: Feature importance (best model) ──
    ax4 = fig.add_subplot(gs[1, 0])
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
    elif hasattr(best_model, "named_steps"):
        # Linear Regression pipeline → dùng abs(coef) normalize
        coefs = np.abs(best_model.named_steps["model"].coef_)
        importances = coefs / coefs.sum()
    else:
        importances = np.ones(len(FEATURES)) / len(FEATURES)

    feat_labels = ["Skill match", "Exp. diff", "Cosine sim", "Education"]
    sorted_idx  = np.argsort(importances)
    ax4.barh([feat_labels[i] for i in sorted_idx],
             [importances[i] for i in sorted_idx],
             color=best_color, alpha=0.85, edgecolor="white")
    ax4.set_title(f"Feature Importance\n({best_name})", fontsize=11)
    ax4.set_xlabel("Importance")
    for i, (idx, val) in enumerate(zip(sorted_idx, sorted(importances))):
        ax4.text(val + 0.005, i, f"{val:.3f}", va="center", fontsize=9)

    # ── Panel 5: Predicted vs Actual (best model) ──
    ax5 = fig.add_subplot(gs[1, 1])
    y_pred = best_model.predict(X)
    ax5.scatter(y, y_pred, alpha=0.35, s=18, color=best_color, edgecolors="none")
    lims = [min(y.min(), y_pred.min()) - 2, max(y.max(), y_pred.max()) + 2]
    ax5.plot(lims, lims, "k--", linewidth=1, alpha=0.5, label="Perfect fit")
    ax5.set_xlim(lims); ax5.set_ylim(lims)
    ax5.set_xlabel("Actual score"); ax5.set_ylabel("Predicted score")
    ax5.set_title(f"Predicted vs Actual\n({best_name})", fontsize=11)
    ax5.legend(fontsize=9)
    r2_full = r2_score(y, y_pred)
    mae_full = mean_absolute_error(y, y_pred)
    ax5.text(0.04, 0.93, f"R²={r2_full:.3f}  MAE={mae_full:.2f}",
             transform=ax5.transAxes, fontsize=9,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))

    # ── Panel 6: Residuals ──
    ax6 = fig.add_subplot(gs[1, 2])
    residuals = y - y_pred
    ax6.scatter(y_pred, residuals, alpha=0.35, s=18, color=best_color, edgecolors="none")
    ax6.axhline(0, color="k", linewidth=1, linestyle="--", alpha=0.5)
    ax6.set_xlabel("Predicted score"); ax6.set_ylabel("Residual (actual − predicted)")
    ax6.set_title(f"Residual Plot\n({best_name})", fontsize=11)
    rmse = root_mean_squared_error(y, y_pred)
    ax6.text(0.04, 0.93, f"RMSE={rmse:.2f}", transform=ax6.transAxes, fontsize=9,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))

    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"\n📊 Đã lưu biểu đồ đánh giá vào {CHART_PATH}")
    plt.close()


# ── 6. Lưu model ──────────────────────────────────────────────────────────────

def save_model(model, name):
    joblib.dump(model, MODEL_PATH)
    print(f"💾 Đã lưu model ({name}) vào {MODEL_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def train():
    print("=" * 62)
    print("  CV Scoring Model — Training Pipeline")
    print("=" * 62)

    X, y = load_data()

    models     = get_models()
    cv_results = cross_validate_all(models, X, y)

    best_name, best_model = train_best_model(models, cv_results, X, y)

    plot_evaluation(cv_results, best_name, best_model, X, y)
    save_model(best_model, best_name)

    print("\n✅ Hoàn tất! Chạy app.py để sử dụng model.")
    print("=" * 62)

    # Demo predict 1 CV mẫu
    print("\n--- Demo predict ---")
    sample = np.array([[0.75, 1.0, 0.78, 1]])
    score  = best_model.predict(sample)[0]
    print(f"Input : skill_match=0.75, exp_diff=+1yr, cosine=0.78, edu_match=1")
    print(f"Output: {score:.1f} / 100 điểm")


if __name__ == "__main__":
    train()