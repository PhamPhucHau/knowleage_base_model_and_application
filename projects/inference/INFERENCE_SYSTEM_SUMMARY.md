# Hệ Thống Suy Diễn Điểm Tín Dụng - Tổng Quan

## 1. Tổng Quan Hệ Thống

Hệ thống suy diễn điểm tín dụng là một **hệ thống tri thức tích hợp** sử dụng phương pháp **forward-chaining** để suy diễn điểm tín dụng cá nhân dựa trên các thông tin tài chính đầu vào.

### 1.1. Kiến Trúc Tổng Thể

```
┌─────────────────┐
│   Input Data    │  (Thông tin tài chính cá nhân)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Working Memory  │  (Lưu trữ facts và inference steps)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Functions      │  (Chuẩn hóa và tính toán)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Rules       │  (Logic suy diễn)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Credit Score    │  (Kết quả: Good/Standard/Poor)
└─────────────────┘
```

### 1.2. Các Thành Phần Chính

1. **Working Memory**: Lưu trữ các facts (sự kiện) và inference steps (các bước suy diễn)
2. **Functions (Funcs)**: Các hàm chuẩn hóa và tính toán
3. **Rules**: Các luật suy diễn để đưa ra kết luận
4. **Knowledge Base (Neo4j)**: Lưu trữ ontology, problems, và metadata

---

## 2. Quy Trình Suy Diễn (Forward Chaining)

### 2.1. Các Bước Thực Hiện

```
Bước 1: Khởi tạo Working Memory
  ├─ Nạp facts ban đầu từ input
  └─ Khởi tạo danh sách inference steps

Bước 2: Áp dụng Functions
  ├─ Age_Norm: Chuẩn hóa Credit_History_Age → tháng
  └─ Payment_Behavior_Parser: Parse Payment_Behaviour → Spending_Level, Value_Level

Bước 3: Áp dụng Rules (Equality Rules)
  ├─ R_DTI: Tính DTI_Ratio = Outstanding_Debt / Annual_Income
  └─ R_CU: Tính Credit_Utilization_Ratio = Outstanding_Debt / (Num_of_Loan × Avg_Credit_Limit)

Bước 4: Áp dụng Rules (Deductive Rules)
  ├─ R_P1: Parse Payment_Behaviour
  ├─ R_CS_G: Suy diễn Credit_Score = Good
  ├─ R_CS_S: Suy diễn Credit_Score = Standard
  └─ R_CS_P: Suy diễn Credit_Score = Poor

Bước 5: Kiểm tra Goal
  └─ Nếu Credit_Score đã được suy diễn → SUCCESS
     Nếu không → FAILED (Unknown)
```

### 2.2. Forward Chaining Algorithm

```python
def solve(problem):
    # 1. Khởi tạo Working Memory
    memory = WorkingMemory()
    memory.facts = initial_facts
    
    # 2. Áp dụng Functions
    for func in functions:
        func(memory)
    
    # 3. Forward chaining với Rules
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if rule.can_fire(memory):
                rule.fire(memory)
                changed = True
    
    # 4. Kiểm tra goal
    if goal_key in memory.facts:
        return SUCCESS
    else:
        return FAILED
```

---

## 3. Functions (Funcs)

### 3.1. Age_Norm
- **Mục đích**: Chuẩn hóa Credit_History_Age từ chuỗi (ví dụ: "22 Years and 1 Months") thành số tháng
- **Input**: `Credit_History_Age` (string)
- **Output**: `Credit_History_Age_Months` (int)
- **Ví dụ**: "22 Years and 1 Months" → 265 tháng

### 3.2. Payment_Behavior_Parser
- **Mục đích**: Parse Payment_Behaviour thành Spending_Level và Value_Level
- **Input**: `Payment_Behaviour` (string, ví dụ: "High_spent_Small_value_payments")
- **Output**: `Spending_Level`, `Value_Level`
- **Ví dụ**: "High_spent_Small_value_payments" → Spending_Level="High", Value_Level="Small"

### 3.3. Score_Classifier
- **Mục đích**: Phân loại Credit_Score thành category
- **Input**: `Credit_Score` (numeric)
- **Output**: Category (Good/Standard/Poor)

### 3.4. Credit_Score_Calc
- **Mục đích**: Tính toán Credit_Score dựa trên các chỉ số tài chính
- **Input**: DTI_Ratio, Credit_Utilization_Ratio, Num_of_Delayed_Payment, Annual_Income
- **Output**: Credit_Score (numeric)

---

## 4. Rules (Luật Suy Diễn)

### 4.1. Equality Rules (Luật Đẳng Thức)

#### R_DTI: Tính DTI Ratio
```
DTI_Ratio = Outstanding_Debt / Annual_Income
```
- **Mục đích**: Tính tỷ lệ nợ trên thu nhập
- **Điều kiện**: Cần có `Outstanding_Debt` và `Annual_Income`

#### R_CU: Tính Credit Utilization Ratio
```
Credit_Utilization_Ratio = Outstanding_Debt / (Num_of_Loan × Avg_Credit_Limit)
```
- **Mục đích**: Tính tỷ lệ sử dụng tín dụng
- **Điều kiện**: Cần có `Outstanding_Debt`, `Num_of_Loan`, `Avg_Credit_Limit`

### 4.2. Deductive Rules (Luật Dẫn)

#### R_P1: Parse Payment Behaviour
```
IF Payment_Behaviour = "High_spent_Small_value_payments"
THEN Spending_Level = "High" AND Value_Level = "Small"
```
- **Mục đích**: Trích xuất Spending_Level và Value_Level từ Payment_Behaviour

#### R_CS_G: Suy Diễn Credit Score = Good

**Điều kiện:**
- **Nếu DTI ≤ 0.05**: 
  - `Num_of_Delayed_Payment ≤ 10`
  - `Credit_Utilization_Ratio ≤ 0.7`
- **Nếu 0.05 < DTI ≤ 0.1**:
  - `Num_of_Delayed_Payment ≤ 8`
  - `Credit_Utilization_Ratio ≤ 0.7`

**Logic:**
```python
if dti <= 0.05:
    conditions = [delayed <= 10, utilization <= 0.7]
elif dti <= 0.1:
    conditions = [delayed <= 8, utilization <= 0.7]
else:
    return False  # Không match Good
```

**Ý nghĩa**: Điểm tín dụng tốt khi DTI thấp, số lần trễ thanh toán ít, và tỷ lệ sử dụng tín dụng hợp lý.

#### R_CS_S: Suy Diễn Credit Score = Standard

**Các trường hợp:**

1. **Case 1**: DTI ≤ 0.1 nhưng có vấn đề
   - `DTI ≤ 0.1` AND `(Delayed > 5 OR Utilization > 0.2)` AND `Delayed ≤ 17`
   - KHÔNG match nếu có thể match Good (DTI ≤ 0.05 và Delayed ≤ 10, HOẶC DTI ≤ 0.1 và Delayed ≤ 8)

2. **Case 2**: Delayed trong range Standard
   - `5 < Delayed ≤ 17` AND `DTI < 0.4`
   - KHÔNG match Good hoặc Poor cases

3. **Case 3**: DTI trong range Standard
   - `0.1 < DTI ≤ 0.3` AND `Delayed ≤ 17`
   - KHÔNG match Poor cases

4. **Case 4**: Utilization cao nhưng DTI thấp
   - `Utilization > 0.5` AND `DTI ≤ 0.1` AND `Delayed ≤ 5`
   - KHÔNG match Good cases

5. **Case 5**: DTI thấp, Delayed thấp, Util thấp
   - `DTI ≤ 0.1` AND `Delayed ≤ 5` AND `Utilization ≤ 0.2`
   - KHÔNG match Good cases

6. **Case 6**: Delayed cao nhưng DTI thấp
   - `Delayed > 17` AND `Delayed ≤ 20` AND `DTI < 0.15`

**Điều kiện chung**: `DTI < 0.4` AND `Delayed ≤ 20`

**Ý nghĩa**: Điểm tín dụng trung bình khi có một số vấn đề nhưng không quá nghiêm trọng.

#### R_CS_P: Suy Diễn Credit Score = Poor

**Các trường hợp:**

1. **Case 1**: Delayed quá cao + điều kiện bổ sung
   - `Delayed > 17` AND `(DTI ≥ 0.15 OR Utilization > 0.3)`

2. **Case 1b**: Delayed cao + DTI cao
   - `Delayed > 15` AND `Delayed ≤ 17` AND `DTI ≥ 0.15`

3. **Case 2**: DTI cao + additional risk
   - `DTI ≥ 0.3` AND `(Num_of_Loan > 3 OR Credit_History_Age_Months < 60)`

4. **Case 3**: Delayed cao + additional risk
   - `Delayed > 15` AND `(Num_of_Loan > 3 OR Credit_History_Age_Months < 60)`

5. **Case 4**: Utilization cao + additional risk
   - `Utilization > 0.5` AND `(Num_of_Loan > 3 OR Credit_History_Age_Months < 60)`

6. **Case 5**: Delayed rất cao
   - `Delayed > 20` (không cần điều kiện khác)

**Ý nghĩa**: Điểm tín dụng kém khi có nhiều vấn đề nghiêm trọng về nợ, trễ thanh toán, hoặc sử dụng tín dụng quá mức.

---

## 5. Thứ Tự Ưu Tiên Rules

Rules được áp dụng theo thứ tự sau để tránh conflict:

1. **R_DTI** (Equality Rule)
2. **R_CU** (Equality Rule)
3. **R_P1** (Deductive Rule)
4. **R_CS_G** (Credit Score = Good) - **Ưu tiên cao nhất**
5. **R_CS_S** (Credit Score = Standard) - **Ưu tiên trung bình**
6. **R_CS_P** (Credit Score = Poor) - **Ưu tiên thấp nhất**

**Lý do**: 
- Good được check trước để tránh Standard/Poor match các cases tốt
- Standard được check trước Poor để tránh Poor match các cases trung bình
- Mỗi rule có điều kiện loại trừ để tránh match cases của rule khác

---

## 6. Ví Dụ Suy Diễn

### 6.1. Case: Good Credit Score

**Input:**
```json
{
  "Annual_Income": 50000,
  "Outstanding_Debt": 2000,
  "Num_of_Loan": 2,
  "Num_of_Delayed_Payment": 2,
  "Credit_History_Age": "10 Years and 0 Months",
  "Avg_Credit_Limit": 15000,
  "Payment_Behaviour": "Low_spent_Small_value_payments"
}
```

**Quy trình suy diễn:**
```
Bước 1: Observation
  → Annual_Income = 50000
  → Outstanding_Debt = 2000
  → Num_of_Delayed_Payment = 2
  → ...

Bước 2: Age_Norm
  → Credit_History_Age_Months = 120

Bước 3: R_DTI
  → DTI_Ratio = 2000 / 50000 = 0.04

Bước 4: R_CU
  → Credit_Utilization_Ratio = 2000 / (2 × 15000) = 0.0667

Bước 5: R_P1
  → Spending_Level = "Low"
  → Value_Level = "Small"

Bước 6: R_CS_G
  → DTI = 0.04 ≤ 0.05 ✓
  → Delayed = 2 ≤ 10 ✓
  → Utilization = 0.0667 ≤ 0.7 ✓
  → Credit_Score = "Good" ✓

Kết quả: SUCCESS, Credit_Score = "Good"
```

### 6.2. Case: Standard Credit Score

**Input:**
```json
{
  "Annual_Income": 30000,
  "Outstanding_Debt": 1500,
  "Num_of_Delayed_Payment": 12,
  "DTI_Ratio": 0.05,
  "Credit_Utilization_Ratio": 0.15
}
```

**Quy trình suy diễn:**
```
Bước 1-4: (tương tự như trên)
  → DTI_Ratio = 0.05
  → Credit_Utilization_Ratio = 0.15
  → Num_of_Delayed_Payment = 12

Bước 5: R_CS_G
  → DTI = 0.05 ≤ 0.05 ✓
  → Delayed = 12 > 10 ✗
  → Không match Good

Bước 6: R_CS_S (Case 2)
  → 5 < Delayed = 12 ≤ 17 ✓
  → DTI = 0.05 < 0.4 ✓
  → Credit_Score = "Standard" ✓

Kết quả: SUCCESS, Credit_Score = "Standard"
```

### 6.3. Case: Poor Credit Score

**Input:**
```json
{
  "Annual_Income": 20000,
  "Outstanding_Debt": 8000,
  "Num_of_Delayed_Payment": 22,
  "DTI_Ratio": 0.4,
  "Credit_Utilization_Ratio": 0.6
}
```

**Quy trình suy diễn:**
```
Bước 1-4: (tương tự như trên)
  → DTI_Ratio = 0.4
  → Credit_Utilization_Ratio = 0.6
  → Num_of_Delayed_Payment = 22

Bước 5: R_CS_G
  → DTI = 0.4 > 0.1 ✗
  → Không match Good

Bước 6: R_CS_S
  → Delayed = 22 > 20 ✗
  → Không match Standard

Bước 7: R_CS_P (Case 5)
  → Delayed = 22 > 20 ✓
  → Credit_Score = "Poor" ✓

Kết quả: SUCCESS, Credit_Score = "Poor"
```

---

## 7. Đánh Giá Hệ Thống

### 7.1. Độ Chính Xác (Accuracy)

- **Accuracy hiện tại**: ~52.5-56.5% (trên 200 samples)
- **Per-class metrics**:
  - **Good**: Precision ~0.54, Recall ~0.17, F1 ~0.26
  - **Standard**: Precision ~0.64, Recall ~0.68, F1 ~0.66
  - **Poor**: Precision ~0.59, Recall ~0.42, F1 ~0.49

### 7.2. Các Vấn Đề Hiện Tại

1. **Good → Standard (32 cases)**: 
   - Nguyên nhân: R_CS_G quá strict với Delayed khi DTI > 0.05
   - Giải pháp: Đã nới lỏng Delayed ≤ 8 khi DTI ≤ 0.1

2. **Standard → Unknown (21 cases)**:
   - Nguyên nhân: R_CS_S không cover một số edge cases
   - Giải pháp: Đã thêm Case 5 và Case 6

3. **Poor → Standard (14 cases)**:
   - Nguyên nhân: R_CS_P không match các cases có Delayed ≤ 17
   - Giải pháp: Đã thêm Case 1b

4. **Standard → Poor (11 cases)**:
   - Nguyên nhân: R_CS_P match quá nhiều Standard cases
   - Giải pháp: Đã thêm điều kiện DTI ≥ 0.15 hoặc Utilization > 0.3

### 7.3. Hướng Cải Thiện

1. **Tinh chỉnh ngưỡng**: Dựa trên phân tích errors để điều chỉnh các ngưỡng DTI, Delayed, Utilization
2. **Thêm rules**: Có thể thêm rules cho các edge cases đặc biệt
3. **Feature engineering**: Thêm các features mới như Monthly_Balance, Payment_Ratio
4. **Ensemble**: Kết hợp với decision tree model (v2) để cải thiện accuracy

---

## 8. So Sánh với Decision Tree Model (V2)

| Tiêu chí | Ontology Model (V1) | Decision Tree Model (V2) |
|----------|---------------------|--------------------------|
| **Phương pháp** | Rule-based forward chaining | Decision tree rules |
| **Interpretability** | Cao (có inference steps) | Trung bình (có rule path) |
| **Accuracy** | ~52-56% | ~70-80% (ước tính) |
| **Flexibility** | Cao (dễ thêm/sửa rules) | Thấp (cần retrain tree) |
| **Coverage** | Tốt (cover nhiều cases) | Tốt (cover toàn bộ cases) |
| **Maintenance** | Dễ (sửa rules) | Khó (cần retrain) |

**Khuyến nghị**: 
- Sử dụng **Ontology Model** khi cần giải thích chi tiết và dễ maintain
- Sử dụng **Decision Tree Model** khi cần accuracy cao hơn

---

## 9. Kết Luận

Hệ thống suy diễn điểm tín dụng sử dụng phương pháp **forward-chaining** với các rules được định nghĩa rõ ràng. Hệ thống có khả năng:

✅ **Suy diễn tự động** điểm tín dụng từ thông tin tài chính đầu vào
✅ **Giải thích từng bước** quá trình suy diễn
✅ **Dễ maintain** và mở rộng với rules mới
✅ **Interpretable** - người dùng có thể hiểu tại sao đưa ra kết luận

**Độ chính xác hiện tại**: ~52-56%, có thể cải thiện thêm bằng cách:
- Tinh chỉnh các ngưỡng trong rules
- Thêm rules cho các edge cases
- Kết hợp với decision tree model

---

## 10. Tài Liệu Tham Khảo

- **File chính**: `projects/inference/engine.py`
- **Functions**: `projects/rules/funcs.py`
- **Rules metadata**: `projects/rules/op_func.py`
- **Evaluation**: `projects/evaluation/evaluation.py`
- **Problems**: `projects/problems/problems.yaml`

---

*Tài liệu này được tạo tự động dựa trên code và phân tích evaluation results.*

