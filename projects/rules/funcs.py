"""
Thư viện Funcs — triển khai các hàm được khai báo trong `op_func.py`.

Các hàm này được tách ra từ bước chuẩn hóa dữ liệu (process.py) để:
    • Tái sử dụng trong inference engine.
    • Gắn với metadata Funcs trong Neo4j (logic_ref).

Mỗi hàm đều có chữ ký rõ ràng, trả về None nếu không tính được.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Các hàm tiện ích dùng chung
# ---------------------------------------------------------------------------

def normalize_decimal(value: Any) -> Any:
    """Thay dấu phẩy bằng dấu chấm cho biểu diễn số thập phân."""
    if pd.isna(value):
        return value
    if isinstance(value, str):
        return value.replace(",", ".")
    return value


def convert_to_numeric(series: pd.Series) -> pd.Series:
    """Chuyển Series ký tự sang numeric, bỏ khoảng trắng và chuẩn hóa dấu."""
    series_cleaned = (
        series.astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(series_cleaned, errors="coerce")


def parse_time_to_months(time_str: Any) -> Optional[int]:
    """Chuẩn hóa chuỗi '22 Years and 1 Months' → 265 (tháng)."""
    if pd.isna(time_str) or not isinstance(time_str, str):
        return None

    years_match = re.search(r"(\d+)\s*Years?", time_str, re.IGNORECASE)
    months_match = re.search(r"(\d+)\s*Months?", time_str, re.IGNORECASE)

    years = int(years_match.group(1)) if years_match else 0
    months = int(months_match.group(1)) if months_match else 0
    return years * 12 + months


def normalize_payment_behavior(payment_str: Any) -> Dict[str, Optional[str]]:
    """Trả về Spending_Level và Value_Level từ chuỗi Payment_Behaviour."""
    if pd.isna(payment_str) or not isinstance(payment_str, str):
        return {"Spending_Level": None, "Value_Level": None}

    payment_lower = payment_str.lower()
    if "high" in payment_lower or "spent" in payment_lower:
        spending_level = "High"
    elif "low" in payment_lower:
        spending_level = "Low"
    else:
        spending_level = None

    if "large" in payment_lower or "value" in payment_lower:
        value_level = "Large"
    elif "small" in payment_lower:
        value_level = "Small"
    else:
        value_level = None

    return {"Spending_Level": spending_level, "Value_Level": value_level}


def normalize_credit_score(score: Any) -> Optional[str]:
    """Chuẩn hóa credit score dạng chuỗi thành ontology Category."""
    if pd.isna(score):
        return None
    if isinstance(score, str):
        score = score.strip()
    return f"Category: {score}"


# ---------------------------------------------------------------------------
# Các hàm Funcs chính (dùng trong inference engine)
# ---------------------------------------------------------------------------

def age_norm(credit_history_age: Any) -> Optional[int]:
    """Age_Norm(Credit_History_Age:str) -> months:int."""
    return parse_time_to_months(credit_history_age)


def score_classifier(credit_score_label: Any) -> Optional[str]:
    """Score_Classifier(Credit_Score:str) -> CreditScoreCategory:str."""
    return normalize_credit_score(credit_score_label)


def payment_behavior_parser(payment_behaviour: Any) -> Dict[str, Optional[str]]:
    """Payment_Behavior_Parser(Payment_Behaviour:str) -> dict."""
    return normalize_payment_behavior(payment_behaviour)


def credit_score_calc(inputs: Dict[str, Any]) -> Optional[float]:
    """
    Credit_Score_Calc(dict) -> float.

    inputs yêu cầu tối thiểu các khóa:
        - DTI_Ratio (0-1)
        - Credit_Utilization_Ratio (0-1)
        - Num_of_Delayed_Payment
        - Annual_Income (USD)
    Các khóa bổ sung (Spending_Level, Value_Level, Num_of_Loan) giúp điều chỉnh.
    Công thức heuristic dựa theo cấu trúc FICO (range 300-850).
    """

    required = ["DTI_Ratio", "Credit_Utilization_Ratio", "Num_of_Delayed_Payment", "Annual_Income"]
    if any(key not in inputs or inputs[key] is None for key in required):
        return None

    dti = float(inputs["DTI_Ratio"])
    utilization = float(inputs["Credit_Utilization_Ratio"])
    delayed = float(inputs["Num_of_Delayed_Payment"])
    income = float(inputs["Annual_Income"])

    score = 850.0
    score -= min(dti * 100, 100) * 1.5
    score -= min(utilization * 100, 100) * 1.2
    score -= min(delayed * 5, 200)
    score += math.log(max(income, 1), 10) * 8

    num_loan = float(inputs.get("Num_of_Loan") or 0)
    score -= num_loan * 2

    spending = (inputs.get("Spending_Level") or "").lower()
    value_level = (inputs.get("Value_Level") or "").lower()
    if spending == "high":
        score -= 10
    elif spending == "low":
        score += 5
    if value_level == "large":
        score -= 5
    elif value_level == "small":
        score += 5

    score = max(300.0, min(850.0, score))
    return round(score, 2)


FUNC_REGISTRY = {
    "Age_Norm": age_norm,
    "Score_Classifier": score_classifier,
    "Payment_Behavior_Parser": payment_behavior_parser,
    "Credit_Score_Calc": credit_score_calc,
}


