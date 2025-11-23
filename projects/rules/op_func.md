## Báo cáo Ops / Funcs / Rules (`op_func.py`)

### Mục tiêu của script
- Kết nối Neo4j và khởi tạo tập Toán tử (Ops), Hàm (Funcs) và Luật (Rules) phục vụ mô hình tri thức dự báo điểm tín dụng cá nhân.
- Tạo ràng buộc duy nhất cho `Operator`, `Function`, `Rule`.
- Seed dữ liệu miền vào đồ thị và nối các quan hệ `USES_OPERATOR`, `USES_FUNCTION`.

Chạy bằng `python projects/rules/op_func.py` (các biến môi trường `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` override cấu hình mặc định).

---

### 1. Tập Toán tử (Ops)

| Tên | Ký hiệu | Bậc | Category | Vai trò chính |
| --- | --- | --- | --- | --- |
| Addition | `+` | 2 | O(2) | Cộng các đại lượng tài chính, dùng trong `Monthly_Balance`, `Credit_Score_Calc`. |
| Subtraction | `-` | 2 | O(2) | Trừ chi phí khỏi thu nhập khi tính `Monthly_Balance`. |
| Multiplication | `×` | 2 | O(2) | Nhân để scale/tham chiếu khi tính `Credit_Score_Calc` hoặc ước lượng hạn mức. |
| Division | `÷` | 2 | O(2) | Tạo ratio: `DTI_Ratio`, `Credit_Utilization_Ratio`. |
| SquareRoot | `sqrt` | 1 | O(1) | Chuẩn hóa độ lệch/variance trong tính điểm. |
| Absolute | `abs` | 1 | O(1) | Giữ giá trị dương cho các chỉ số rủi ro. |

---

### 2. Tập Hàm (Funcs)

Mỗi hàm đã được triển khai thành mã thực thi trong `rules/funcs.py`, đồng thời lưu metadata (ID, chữ ký, logic_ref) khi seed vào Neo4j.

| Hàm | Func ID | Signature | Logic ref | Event type | Nguồn dữ liệu chính |
| --- | --- | --- | --- | --- | --- |
| `Age_Norm` | `FUNC-001` | `Age_Norm(Credit_History_Age:str) -> months:int` | `rules.funcs.age_norm` | Fu.2-Normalization | `Credit_History_Age` (dataset) |
| `Score_Classifier` | `FUNC-002` | `Score_Classifier(Credit_Score:str) -> category:str` | `rules.funcs.score_classifier` | Fu.2-Classification | `Credit_Score` |
| `Payment_Behavior_Parser` | `FUNC-003` | `Payment_Behavior_Parser(Payment_Behaviour:str) -> dict` | `rules.funcs.payment_behavior_parser` | Fu.2-Extraction | `Payment_Behaviour` |
| `Credit_Score_Calc` | `FUNC-004` | `Credit_Score_Calc(financial_dict:dict) -> score:float` | `rules.funcs.credit_score_calc` | Fu.2-Compute | Annual_Income, Outstanding_Debt, DTI_Ratio, Credit_Utilization_Ratio, Num_of_Delayed_Payment (+ derived) |

---

### 3. Tập Luật (Rules)

#### 3.1 RuleEquation (g = h)
- **R_MB**: `Monthly_Balance = Monthly_Inhand_Salary - Total_EMI_per_month - Amount_invested_monthly` (dùng `Subtraction`).
- **R_DTI**: `DTI_Ratio = Outstanding_Debt / Annual_Income` (dùng `Division`).
- **R_CU**: `Credit_Utilization_Ratio = Outstanding_Debt / (Num_Credit_Card × Avg_Limit)` (dùng `Division`, `Multiplication`).

#### 3.2 RuleDeduce (IF–THEN)
- **R_P1**: Payment behaviour “High_spent_Small_value_payments” ⇒ `Spending_Level = High ∧ Value_Level = Small` (sử dụng `Payment_Behavior_Parser`).
- **R_D1**: `Num_of_Delayed_Payment > 5 ∧ Spending_Level = High` ⇒ `Credit_Risk = High`.
- **R_CS_P**: `DTI_Ratio ≥ 0.4 ∧ Num_of_Loan > 3 ∧ Credit_History_Age < 5` ⇒ `Credit_Score = Poor` (dùng `Division`, `Age_Norm`).
- **R_CS_G**: `DTI_Ratio ≤ 0.1 ∧ Credit_Utilization_Ratio ≤ 0.1 ∧ Num_of_Delayed_Payment = 0` ⇒ `Credit_Score = Good`.

#### 3.3 RuleGenerate (tạo đối tượng mới)
- **R_G1**: `Credit_Score = Good ∧ Occupation = Scientist` ⇒ sinh `PremiumCreditProfile` gắn với `Person`.

---

### 4. Pipeline kỹ thuật
1. Tạo constraint cho `Operator`, `Function`, `Rule`.
2. `UNWIND` seed dữ liệu Ops, Funcs, Rules (có mô tả, inputs, outputs, premises, conclusions).
3. Tạo quan hệ:
   - `(:Rule)-[:USES_OPERATOR]->(:Operator)` theo trường `uses_ops`.
   - `(:Rule)-[:USES_FUNCTION]->(:Function)` theo trường `uses_funcs`.
4. Log tiến trình (`print`) để dễ theo dõi khi chạy thủ công hoặc automation.

---

### 5. Ghi chú triển khai
- Script idempotent nhờ `MERGE`, có thể chạy lại khi cập nhật ontology.
- Cần cài `neo4j` driver (đã cập nhật trong `projects/data processing/requirements.txt`).
- Các hàm/luật tương ứng với bước chuẩn hóa trước đó (`process.py`), đảm bảo chuỗi chuyển hóa dữ liệu → concept → quan hệ → tri thức suy luận liền mạch.


