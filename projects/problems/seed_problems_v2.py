"""
Generate Problems v2 from dataset for decision-tree inference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from rules.funcs_v2 import LABEL_MAPPING, facts_from_row

OUTPUT_FILE = Path("problems/problems_v2.json")


def load_dataset(limit: int = 500) -> pd.DataFrame:
    candidates = [
        Path("datasets/Data Processed.xlsx"),
        Path("datasets/Data Clean.xlsx"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return pd.read_excel(candidate).head(limit)
    raise FileNotFoundError("Không tìm thấy dữ liệu nguồn.")


def select_examples(df: pd.DataFrame) -> List[Dict[str, any]]:
    examples = []
    for label in LABEL_MAPPING.values():
        subset = df[df["Credit_Score"] == label]
        if subset.empty:
            continue
        row = subset.iloc[0].to_dict()
        facts = facts_from_row(row)
        examples.append(
            {
                "problem_id": f"PROB-V2-{label.upper()}",
                "label": label,
                "facts": facts,
                "raw": {
                    "Outstanding_Debt": row.get("Outstanding_Debt"),
                    "Payment_of_Min_Amount": row.get("Payment_of_Min_Amount"),
                    "Interest_Rate": row.get("Interest_Rate"),
                    "Num_Credit_Card": row.get("Num_Credit_Card"),
                    "Monthly_Balance": row.get("Monthly_Balance"),
                    "Total_EMI_per_month": row.get("Total_EMI_per_month"),
                    "Num_of_Loan": row.get("Num_of_Loan"),
                    "Delay_from_due_date": row.get("Delay_from_due_date"),
                    "Age": row.get("Age"),
                },
            }
        )
    return examples


def main() -> None:
    df = load_dataset()
    problems = select_examples(df)
    OUTPUT_FILE.write_text(json.dumps({"problems": problems}, indent=2, ensure_ascii=False))
    print(f"Đã lưu {len(problems)} problem v2 tại {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
