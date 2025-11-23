"""
Model evaluation for credit knowledge inference.

Steps:
    1. Load processed dataset (Data Processed.xlsx if exists, else Data Clean.xlsx).
    2. For each record, build ManualInferenceRequest and run inference.
    3. Compare predicted Credit_Score with dataset label.
    4. Output metrics: accuracy, precision/recall per class.

Usage:
    python projects/evaluation/evaluation.py --limit 200
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from application.services.manual_solver import (  # noqa: E402
    ManualInferenceRequest,
    run_manual_inference,
)


DATA_PROCESSED = PROJECT_ROOT / "datasets" / "Data Processed.xlsx"
DATA_CLEAN = PROJECT_ROOT / "datasets" / "Data Clean.xlsx"


def load_dataset(limit: int | None = None) -> pd.DataFrame:
    source = DATA_PROCESSED if DATA_PROCESSED.exists() else DATA_CLEAN
    df = pd.read_excel(source)
    if limit:
        df = df.head(limit)
    return df


def build_request(row: pd.Series) -> ManualInferenceRequest:
    return ManualInferenceRequest(
        person_id=str(row.get("Occupation", "Person")),
        annual_income=float(row.get("Annual_Income", 0)),
        outstanding_debt=float(row.get("Outstanding_Debt", 0)),
        num_of_loan=int(row.get("Num_of_Loan", 0)),
        credit_history_age=str(row.get("Credit_History_Age", "0 Years and 0 Months")),
        num_of_delayed_payment=int(row.get("Num_of_Delayed_Payment", 0)),
        payment_behaviour=row.get("Payment_Behaviour"),
        spending_level=row.get("Spending_Level"),
        value_level=row.get("Value_Level"),
        avg_credit_limit=float(row.get("Avg_Credit_Limit", 1000)),
    )


def evaluate_dataset(df: pd.DataFrame) -> Tuple[Dict[str, int], Dict[str, Counter]]:
    total = len(df)
    correct = 0
    class_stats: Dict[str, Counter] = defaultdict(Counter)

    for _, row in df.iterrows():
        ground_truth = str(row.get("Credit_Score"))
        request = build_request(row)
        result = run_manual_inference(request)
        prediction = result.credit_score if result.success else "Unknown"

        if prediction == ground_truth:
            correct += 1
            class_stats[ground_truth]["tp"] += 1
        else:
            class_stats[ground_truth]["fn"] += 1
            class_stats[prediction]["fp"] += 1

    metrics = {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0,
    }
    return metrics, class_stats


def print_metrics(metrics: Dict[str, int], class_stats: Dict[str, Counter]) -> None:
    print("=== Overall Metrics ===")
    print(f"Total Samples: {metrics['total']}")
    print(f"Correct Predictions: {metrics['correct']}")
    print(f"Accuracy: {metrics['accuracy']:.3f}")
    print("\n=== Per-Class Precision/Recall ===")
    for label, stats in class_stats.items():
        tp = stats["tp"]
        fp = stats["fp"]
        fn = stats["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        print(f"{label}: precision={precision:.3f}, recall={recall:.3f} (tp={tp}, fp={fp}, fn={fn})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate credit inference model.")
    parser.add_argument("--limit", type=int, default=100, help="Số lượng bản ghi tối đa.")
    args = parser.parse_args()

    df = load_dataset(args.limit)
    metrics, class_stats = evaluate_dataset(df)
    print_metrics(metrics, class_stats)


if __name__ == "__main__":
    main()
