import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os

def train_model():
    print("1. Đang tải dữ liệu mô phỏng từ sample_dataset.csv...")
    dataset_path = 'sample_dataset.csv'
    
    if not os.path.exists(dataset_path):
        print(f"Lỗi: Không tìm thấy file {dataset_path}")
        return
        
    df = pd.read_csv(dataset_path)
    
    # 2. Chuẩn bị đặc trưng (Features) và Nhãn (Label/Target)
    # Features (X): Tỷ lệ khớp skill, chênh lệch năm kinh nghiệm, độ tương đồng văn bản, học vấn...
    X = df[['skill_match_ratio', 'experience_diff', 'cosine_similarity', 'education_match']]
    # Target (y): Điểm số thực tế do con người đánh giá (0-100)
    y = df['target_score']
    
    # 3. Chia tập dữ liệu thành Train (để học) và Test (để kiểm tra)
    # 80% để train, 20% để test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("2. Bắt đầu huấn luyện mô hình Random Forest...")
    # Sử dụng RandomForestRegressor vì đây là bài toán dự đoán một con số (điểm)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    print("3. Đánh giá mô hình trên tập Test...")
    y_pred = model.predict(X_test)
    
    # Trích xuất độ sai số (MAE) và độ chính xác (R2)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f" - Sai số trung bình tuyệt đối (MAE): {mae:.2f} điểm (Càng nhỏ càng tốt)")
    print(f" - Hệ số xác định (R2 Score): {r2:.2f} (Càng gần 1.0 càng tốt)")
    
    # 4. Lưu mô hình lại thành file .pkl để app.py có thể dùng
    model_filename = 'cv_scoring_model.pkl'
    joblib.dump(model, model_filename)
    print(f"4. Đã lưu mô hình thành công vào file: {model_filename}")
    print("\n--- TEST THỬ MÔ HÌNH ---")
    
    # Giả sử có 1 CV mới: Khớp 70% skill, dư 1 năm kinh nghiệm, tương đồng text 0.75, học vấn khớp
    new_cv_features = [[0.70, 1.0, 0.75, 1]]
    predicted_score = model.predict(new_cv_features)[0]
    print(f"Đầu vào CV mới: {new_cv_features}")
    print(f"Mô hình AI dự đoán CV này được: {predicted_score:.2f} / 100 điểm")

if __name__ == '__main__':
    train_model()
