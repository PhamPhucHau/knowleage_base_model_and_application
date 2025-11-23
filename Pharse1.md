## Phase 1 — Hệ thống hiện tại làm được gì?

### 1. Nền tảng tri thức đã hiện thực
- **Chuẩn hóa dữ liệu (Bước 1)**: `process.py` đọc Excel, chuẩn hóa số, thời gian, Payment Behaviour, Credit Score, sinh thêm chỉ số (DTI, Credit Utilization, Credit_Score_Computed).
- **Ontology & Neo4j import (Bước 2–3)**: `cypher_import.cypher` + script tạo đầy đủ `Person`, `Income`, `Loan`, `PaymentBehaviour`, `CreditHistory`, `DebtProfile`, `CreditScoreCategory`, quan hệ tương ứng.
- **Tri thức Ops/Funcs/Rules (Bước 4)**: `op_func.py`, `funcs.py` seed vào Neo4j; mỗi Func có ID, signature, logic reference; Rules bao gồm RuleEquation (R_MB, R_DTI, R_CU), RuleDeduce (R_P1, R_D1, R_CS_P, R_CS_G) và RuleGenerate (R_G1).
- **Problems mẫu (O,F→G)**: `projects/problems/problems.yaml` + `seed_problems.py` tạo các Problem graph (PROB-001..004) làm bộ test cho inference.
- **Bộ máy suy luận**: `inference/engine.py` nạp Problem/Rules từ Neo4j, quản lý Working Memory, thực thi Funcs/Rules theo forward-chaining, log `solution_steps`, phát hiện goal đạt/chưa đạt.

### 2. Những yêu cầu đã đáp ứng
- Có thể **demo Workflow CLI**: seed dữ liệu → `python inference/engine.py --problem PROB-004` cho kết quả `Credit_Score = Good` với trace rõ ràng.
- Hệ thống **giải thích được các bước suy luận** (Bước 1…).
- Cơ sở tri thức modul hóa, có thể mở rộng với luật/func/bài toán mới.

## Phase 1 — Những thiếu hụt so với yêu cầu

### A. Bài toán & Thuật giải mở rộng
- Chưa có **phân loại vấn đề** đa dạng; mới tập trung vào dự báo điểm tín dụng. Chưa liệt kê thuật giải thay thế (ví dụ heuristic khác, tối ưu, mô phỏng kịch bản).
- **Bayesian inference** chưa được tích hợp: không có mô-đun xác suất, không ước lượng phân phối hay cập nhật niềm tin từ bằng chứng.
- Chưa có cơ chế chọn thuật giải tùy bài toán (chỉ có forward-chaining deterministic).

### B. LLM giải thích yếu tố ảnh hưởng
- Hiện chỉ có trace dựa trên luật. Chưa tích hợp LLM để diễn giải bằng ngôn ngữ tự nhiên các yếu tố ảnh hưởng đến Credit Score.
- Thiếu prompt/agent nhận facts và sinh narrative “vì sao điểm cao/thấp”.

### C. Yêu cầu sản phẩm
| Yêu cầu | Tình trạng hiện tại | Khoảng thiếu |
| --- | --- | --- |
| **Demo nhập thông tin cá nhân → dự báo điểm tín dụng** | Có pipeline CLI dựa trên Problems mẫu | Chưa có UI/endpoint cho người dùng nhập tay; chưa kết nối inference engine với form thực tế |
| **Hiển thị biểu đồ nhân quả** | Chưa có | Cần định nghĩa causal graph (ví dụ DAG) và render (Plotly, Neo4j Bloom, hoặc D3). |
| **Báo cáo đánh giá mô hình** | Chưa có | Cần metrics (accuracy so với nhãn dataset), phân tích lỗi, so sánh với baseline (ví dụ logistic regression), mô tả dữ liệu train/test. |

## Phase 1 — Đề xuất bước tiếp theo

1. **Mở rộng Problems & Rule coverage**
   - Thêm case cho luật `R_CS_P`, `R_D1`.
   - Bổ sung facts cần thiết từ dataset thực nhằm tăng tỷ lệ goal đạt.
2. **Bayesian inference / Probabilistic reasoning**
   - Thiết kế DAG đơn giản: biến ẩn `Credit_Risk`, `LatePayment`, `DTI`, `Utilization`.
   - Dùng thư viện `pgmpy` hoặc `pyro` để cập nhật xác suất; tích hợp kết quả vào Working Memory (ví dụ fact `P(Credit_Score=Poor)=0.72`).
3. **LLM Explanation**
   - Tạo module `explanations/llm.py`: nhận Working Memory, trace, metadata; prompt LLM (OpenAI API hoặc local) tạo đoạn phân tích.
   - Lưu output vào Neo4j (node `Explanation`) để truy vết.
4. **User-facing Demo**
   - Xây dựng FastAPI/Streamlit form: người dùng nhập Income, Debt, Payment behaviour → gọi inference engine.
   - Cho phép lưu lại instance thành Problem tạm trong Neo4j.
5. **Causal visualization**
   - Định nghĩa causal graph trong Neo4j (label `CausalNode`, `CAUSES`).
   - Hiển thị bằng Streamlit (pyvis/plotly) hoặc xuất GraphML để viewer (Neo4j Bloom).
6. **Model Evaluation Report**
   - Dùng dataset `Data Clean.xlsx` làm ground truth → so inference output vs `Credit_Score` cột gốc.
   - Báo cáo metrics (accuracy, precision per class), phân tích các trường hợp sai.
   - Viết markdown/báo cáo PDF mô tả quy trình, dữ liệu, kiến trúc.

Với các bổ sung trên, hệ thống sẽ đáp ứng đầy đủ yêu cầu Phase 1: có nhiều thuật giải (deterministic + Bayesian), có LLM giải thích, có demo nhập liệu và biểu đồ nhân quả, đồng thời có báo cáo đánh giá. 

