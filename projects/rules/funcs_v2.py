"""
Utility functions for decision-tree-based knowledge (version 2).

These helpers convert raw dataset fields into normalized facts used by
the v2 inference engine derived from Rule.txt.
"""

from __future__ import annotations

from typing import Any, Optional

from rules.funcs import parse_time_to_months  # reuse existing helper

LABEL_MAPPING = {0: "Good", 1: "Poor", 2: "Standard"}


def yes_no_flag(value: Any) -> float:
    if value is None:
        return 0.0
    normalized = str(value).strip().lower()
    return 1.0 if normalized in {"yes", "y", "true", "1"} else 0.0


def occupation_developer_flag(value: Any) -> float:
    if value is None:
        return 0.0
    return 1.0 if str(value).strip().lower() == "developer" else 0.0


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def months_from_history(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    months = parse_time_to_months(value)
    return float(months or 0)


def facts_from_row(row: dict) -> dict:
    """Extract the key features used by the decision tree."""
    facts = {
        "Outstanding_Debt": safe_float(row.get("Outstanding_Debt")),
        "Payment_of_Min_Amount_Yes": yes_no_flag(row.get("Payment_of_Min_Amount")),
        "Interest_Rate": safe_float(row.get("Interest_Rate")),
        "Num_Credit_Card": safe_float(row.get("Num_Credit_Card")),
        "Monthly_Balance": safe_float(row.get("Monthly_Balance")),
        "Total_EMI_per_month": safe_float(row.get("Total_EMI_per_month")),
        "Num_of_Loan": safe_float(row.get("Num_of_Loan")),
        "Delay_from_due_date": safe_float(row.get("Delay_from_due_date")),
        "Monthly_Inhand_Salary": safe_float(row.get("Monthly_Inhand_Salary")),
        "Amount_invested_monthly": safe_float(row.get("Amount_invested_monthly")),
        "Age": safe_float(row.get("Age")),
        "Credit_History_Months": months_from_history(
            row.get("Credit_History_Age") or row.get("Credit_History_Months")
        ),
        "Occupation_Developer": occupation_developer_flag(row.get("Occupation")),
    }
    return facts
