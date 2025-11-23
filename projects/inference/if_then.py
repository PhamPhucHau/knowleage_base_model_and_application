from __future__ import annotations
from typing import Dict, List, Any, Tuple

# Mapping nhãn kết quả
LABEL_MAPPING = {0: "Good", 1: "Poor", 2: "Standard"}

class CreditDecisionTree:
    def __init__(self):
        self.explanation: List[str] = []

    def predict_with_explain(self, features: Dict[str, float]) -> Tuple[int, str, List[str]]:
        """
        Dự đoán lớp tín dụng và trả về giải thích chi tiết
        Args:
            features: dict chứa các trường cần thiết (có thể thiếu 1 số trường → sẽ báo lỗi)
        Returns:
            (class_id, class_name, explanation_steps)
        """
        self.explanation = []
        self._log("Bắt đầu suy luận cây quyết định tín dụng")

        # Root
        Outstanding_Debt = features.get("Outstanding_Debt")
        if Outstanding_Debt is None:
            raise ValueError("Thiếu trường Outstanding_Debt")

        if Outstanding_Debt <= 1500.01:
            self._log("Outstanding_Debt <= 1500.01 → Nhánh trái")
            return self._branch_low_debt(features)
        else:
            self._log("Outstanding_Debt > 1500.01 → Nhánh phải")
            return self._branch_high_debt(features)

    # ===================================================================
    # Nhánh Outstanding_Debt <= 1500.01
    # ===================================================================
    def _branch_low_debt(self, f: Dict[str, float]) -> Tuple[int, str, List[str]]:
        Payment_of_Min_Amount_Yes = f.get("Payment_of_Min_Amount_Yes", 0)

        if Payment_of_Min_Amount_Yes <= 0.50:
            self._log("  Payment_of_Min_Amount_Yes <= 0.50")
            Interest_Rate = f.get("Interest_Rate")

            if Interest_Rate <= 12.50:
                self._log("    Interest_Rate <= 12.50")
                Num_Credit_Card = f.get("Num_Credit_Card")

                if Num_Credit_Card <= 2.50:
                    self._log("      Num_Credit_Card <= 2.50")
                    Monthly_Balance = f.get("Monthly_Balance")
                    if Monthly_Balance <= 796.59:
                        return self._leaf(0, "Monthly_Balance <= 796.59")
                    else:
                        return self._leaf(0, "Monthly_Balance > 796.59")
                else:
                    self._log("      Num_Credit_Card > 2.50")
                    Delay_from_due_date = f.get("Delay_from_due_date")
                    if Delay_from_due_date <= 15.50:
                        return self._leaf(2, "Delay_from_due_date <= 15.50")
                    else:
                        return self._leaf(2, "Delay_from_due_date > 15.50")

            else:  # Interest_Rate > 12.50
                self._log("    Interest_Rate > 12.50")
                Total_EMI_per_month = f.get("Total_EMI_per_month")

                if Total_EMI_per_month <= 280.51:
                    self._log("      Total_EMI_per_month <= 280.51")
                    Occupation_Developer = f.get("Occupation_Developer", 0)
                    return self._leaf(2, f"Occupation_Developer = {Occupation_Developer}")

                else:  # Total_EMI_per_month > 280.51
                    self._log("      Total_EMI_per_month > 280.51")
                    Num_of_Loan = f.get("Num_of_Loan")
                    if Num_of_Loan <= 1.50:
                        return self._leaf(0, "Num_of_Loan <= 1.50")
                    else:
                        return self._leaf(2, "Num_of_Loan > 1.50")

        else:  # Payment_of_Min_Amount_Yes > 0.50
            self._log("  Payment_of_Min_Amount_Yes > 0.50")
            Interest_Rate = f.get("Interest_Rate")

            if Interest_Rate <= 20.50:
                self._log("    Interest_Rate <= 20.50")
                Num_Credit_Card = f.get("Num_Credit_Card")

                if Num_Credit_Card <= 7.50:
                    Delay_from_due_date = f.get("Delay_from_due_date")
                    if Delay_from_due_date <= 34.50:
                        return self._leaf(2, "Num_Credit_Card <= 7.50 & Delay <= 34.50")
                    else:
                        return self._leaf(1, "Num_Credit_Card <= 7.50 & Delay > 34.50")
                else:
                    if Num_Credit_Card <= 15.50:
                        return self._leaf(1, "7.50 < Num_Credit_Card <= 15.50")
                    else:
                        return self._leaf(2, "Num_Credit_Card > 15.50")

            else:  # Interest_Rate > 20.50
                self._log("    Interest_Rate > 20.50")
                Total_EMI_per_month = f.get("Total_EMI_per_month")

                if Total_EMI_per_month <= 21.02:
                    Monthly_Balance = f.get("Monthly_Balance")
                    if Monthly_Balance <= 257.71:
                        return self._leaf(2, "Total_EMI <= 21.02 & Monthly_Balance <= 257.71")
                    else:
                        return self._leaf(1, "Total_EMI <= 21.02 & Monthly_Balance > 257.71")
                else:
                    if Total_EMI_per_month <= 292.59:
                        return self._leaf(1, "21.02 < Total_EMI_per_month <= 292.59")
                    else:
                        return self._leaf(1, "Total_EMI_per_month > 292.59")

    # ===================================================================
    # Nhánh Outstanding_Debt > 1500.01
    # ===================================================================
    def _branch_high_debt(self, f: Dict[str, float]) -> Tuple[int, str, List[str]]:
        Outstanding_Debt = f["Outstanding_Debt"]

        if Outstanding_Debt <= 2696.55:
            self._log("  Outstanding_Debt <= 2696.55")
            Interest_Rate = f.get("Interest_Rate")

            if Interest_Rate <= 14.50:
                self._log("    Interest_Rate <= 14.50")
                if Outstanding_Debt <= 1645.58:
                    Age = f.get("Age")
                    if Age <= 39.50:
                        return self._leaf(1, "Age <= 39.50")
                    else:
                        return self._leaf(2, "Age > 39.50")
                else:
                    Credit_History_Months = f.get("Credit_History_Months")
                    return self._leaf(2, f"Credit_History_Months = {Credit_History_Months}")
            else:
                self._log("    Interest_Rate > 14.50")
                Credit_History_Months = f.get("Credit_History_Months")

                if Credit_History_Months <= 52.50:
                    Monthly_Inhand_Salary = f.get("Monthly_Inhand_Salary")
                    if Monthly_Inhand_Salary <= 4347.70:
                        return self._leaf(2, "Salary <= 4347.70")
                    else:
                        return self._leaf(1, "Salary > 4347.70")
                else:
                    if Interest_Rate <= 19.50:
                        return self._leaf(1, "Interest_Rate <= 19.50")
                    else:
                        return self._leaf(1, "Interest_Rate > 19.50")
        else:
            self._log("  Outstanding_Debt > 2696.55")
            Num_Credit_Card = f.get("Num_Credit_Card")

            if Num_Credit_Card <= 9.50:
                Interest_Rate = f.get("Interest_Rate")
                if Interest_Rate <= 27.50:
                    if Outstanding_Debt <= 2962.53:
                        return self._leaf(2, "Outstanding_Debt <= 2962.53")
                    else:
                        return self._leaf(1, "Outstanding_Debt > 2962.53")
                else:
                    Delay_from_due_date = f.get("Delay_from_due_date")
                    return self._leaf(2, f"Delay_from_due_date = {Delay_from_due_date}")
            else:
                if Outstanding_Debt <= 2739.29:
                    Amount_invested_monthly = f.get("Amount_invested_monthly")
                    return self._leaf(1, f"Amount_invested_monthly = {Amount_invested_monthly}")
                else:
                    if Outstanding_Debt <= 2901.38:
                        return self._leaf(2, "Outstanding_Debt <= 2901.38")
                    else:
                        return self._leaf(2, "Outstanding_Debt > 2901.38")

    # ===================================================================
    # Helper
    # ===================================================================
    def _log(self, msg: str):
        self.explanation.append(msg)

    def _leaf(self, class_id: int, reason: str) -> Tuple[int, str, List[str]]:
        self._log(f"    → Kết luận: class = {class_id} ({LABEL_MAPPING[class_id]}) | Lý do: {reason}")
        return class_id, LABEL_MAPPING[class_id], self.explanation.copy()


# ====================== CHẠY THỬ ======================
if __name__ == "__main__":
    engine = CreditDecisionTree()

    # Ví dụ dữ liệu khách hàng
    sample = {
        "Outstanding_Debt": 1200.0,
        "Payment_of_Min_Amount_Yes": 0.0,
        "Interest_Rate": 10.0,
        "Num_Credit_Card": 2,
        "Monthly_Balance": 800.0,
        # các trường khác có thể bỏ qua nếu không dùng ở nhánh này
    }

    try:
        class_id, class_name, steps = engine.predict_with_explain(sample)
        print("\n" + "="*60)
        print(f"KẾT QUẢ DỰ ĐOÁN: {class_id} → {class_name}")
        print("="*60)
        for i, step in enumerate(steps, 1):
            print(f"Bước {i:2d}: {step}")
        print("="*60)
    except Exception as e:
        print("Lỗi:", e)