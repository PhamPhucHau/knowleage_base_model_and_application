"""
Model evaluation for credit knowledge inference with detailed error analysis.

Steps:
    1. Load processed dataset (Data Processed.xlsx if exists, else Data Clean.xlsx).
    2. For each record, build ManualInferenceRequest and run inference.
    3. Compare predicted Credit_Score with dataset label.
    4. Output metrics: accuracy, precision/recall per class.
    5. Analyze errors: show misclassified cases, missing facts, rule coverage.

Usage:
    python projects/evaluation/evaluation.py --limit 200 --show-errors
    python projects/evaluation/evaluation.py --limit 200 --analyze-errors
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from application.services.manual_solver import (  # noqa: E402
    ManualInferenceRequest,
    run_manual_inference,
)

@dataclass
class ErrorCase:
    """Chi tiết một trường hợp dự đoán sai."""
    index: int
    person_id: str
    ground_truth: str
    prediction: str
    success: bool
    missing_facts: List[str]
    steps: List[str]
    facts: Dict[str, Any]
    input_data: Dict[str, Any]


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


def evaluate_dataset(
    df: pd.DataFrame, 
    track_errors: bool = False
) -> Tuple[Dict[str, Any], Dict[str, Counter], List[ErrorCase]]:
    total = len(df)
    correct = 0
    class_stats: Dict[str, Counter] = defaultdict(Counter)
    errors: List[ErrorCase] = []
    failed_inferences = 0

    for idx, (_, row) in enumerate(df.iterrows()):
        ground_truth = str(row.get("Credit_Score", "Unknown"))
        request = build_request(row)
        result = run_manual_inference(request)
        prediction = str(result.credit_score) if result.success else "Unknown"
        
        if not result.success:
            failed_inferences += 1

        if prediction == ground_truth:
            correct += 1
            class_stats[ground_truth]["tp"] += 1
        else:
            class_stats[ground_truth]["fn"] += 1
            if prediction != "Unknown":
                class_stats[prediction]["fp"] += 1
            
            if track_errors:
                dti = request.outstanding_debt / request.annual_income if request.annual_income else 0
                errors.append(ErrorCase(
                    index=idx,
                    person_id=request.person_id,
                    ground_truth=ground_truth,
                    prediction=prediction,
                    success=result.success,
                    missing_facts=result.missing_facts,
                    steps=result.steps,
                    facts=result.facts,
                    input_data={
                        "annual_income": request.annual_income,
                        "outstanding_debt": request.outstanding_debt,
                        "num_of_loan": request.num_of_loan,
                        "num_of_delayed_payment": request.num_of_delayed_payment,
                        "credit_history_age": request.credit_history_age,
                        "dti_ratio": dti,
                        "payment_behaviour": request.payment_behaviour,
                    }
                ))

    metrics = {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0,
        "failed_inferences": failed_inferences,
        "failed_rate": failed_inferences / total if total else 0,
    }
    return metrics, class_stats, errors


def print_metrics(
    metrics: Dict[str, Any], 
    class_stats: Dict[str, Counter], 
    errors: Optional[List[ErrorCase]] = None
) -> None:
    print("=== Overall Metrics ===")
    print(f"Total Samples: {metrics['total']}")
    print(f"Correct Predictions: {metrics['correct']}")
    print(f"Accuracy: {metrics['accuracy']:.3f}")
    print(f"Failed Inferences: {metrics['failed_inferences']} ({metrics['failed_rate']:.1%})")
    
    print("\n=== Per-Class Precision/Recall ===")
    for label, stats in class_stats.items():
        tp = stats["tp"]
        fp = stats["fp"]
        fn = stats["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0
        print(f"{label}: precision={precision:.3f}, recall={recall:.3f}, f1={f1:.3f} (tp={tp}, fp={fp}, fn={fn})")
    
    if errors:
        print(f"\n=== Error Analysis ({len(errors)} errors) ===")
        analyze_errors(errors)


def analyze_errors(errors: List[ErrorCase]) -> None:
    """Phân tích chi tiết các lỗi."""
    if not errors:
        return
    
    # 1. Phân tích missing facts
    missing_facts_counter = Counter()
    for err in errors:
        missing_facts_counter.update(err.missing_facts)
    
    if missing_facts_counter:
        print("\n📊 Missing Facts Analysis:")
        for fact, count in missing_facts_counter.most_common(10):
            print(f"  - {fact}: {count} cases ({count/len(errors):.1%})")
    
    # 2. Phân tích confusion matrix
    confusion = Counter()
    for err in errors:
        confusion[(err.ground_truth, err.prediction)] += 1
    
    print("\n📊 Confusion Patterns (Ground Truth → Prediction):")
    for (gt, pred), count in confusion.most_common(10):
        print(f"  - {gt} → {pred}: {count} cases")
    
    # 3. Phân tích các trường hợp không suy luận được
    failed = [e for e in errors if not e.success]
    if failed:
        print(f"\n⚠️  Failed Inferences: {len(failed)} cases")
        print("   Common missing facts in failed cases:")
        failed_missing = Counter()
        for err in failed:
            failed_missing.update(err.missing_facts)
        for fact, count in failed_missing.most_common(5):
            print(f"     - {fact}: {count} cases")
    
    # 4. Phân tích DTI ratio của các trường hợp sai
    dti_values = [e.input_data.get("dti_ratio", 0) for e in errors if e.input_data.get("dti_ratio")]
    if dti_values:
        import statistics
        print(f"\n📊 DTI Ratio Statistics (Error Cases):")
        print(f"  - Mean: {statistics.mean(dti_values):.3f}")
        print(f"  - Median: {statistics.median(dti_values):.3f}")
        print(f"  - Min: {min(dti_values):.3f}, Max: {max(dti_values):.3f}")
    
    # 5. Hiển thị một vài ví dụ lỗi
    print("\n📋 Sample Error Cases (first 5):")
    for i, err in enumerate(errors[:5], 1):
        print(f"\n  Case {i}:")
        print(f"    Person: {err.person_id}")
        print(f"    Ground Truth: {err.ground_truth} → Prediction: {err.prediction}")
        print(f"    Success: {err.success}")
        if err.missing_facts:
            print(f"    Missing Facts: {', '.join(err.missing_facts)}")
        if err.input_data.get("dti_ratio"):
            print(f"    DTI Ratio: {err.input_data['dti_ratio']:.3f}")


def export_errors(errors: List[ErrorCase], output_path: Path) -> None:
    """Export errors ra file JSON để phân tích sau."""
    errors_dict = [asdict(err) for err in errors]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(errors_dict, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n💾 Exported {len(errors)} errors to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate credit inference model.")
    parser.add_argument("--limit", type=int, default=100, help="Số lượng bản ghi tối đa.")
    parser.add_argument("--show-errors", action="store_true", help="Hiển thị phân tích lỗi chi tiết.")
    parser.add_argument("--analyze-errors", action="store_true", help="Phân tích và export lỗi ra file.")
    parser.add_argument("--export", type=str, help="Đường dẫn file để export errors (JSON).")
    args = parser.parse_args()

    df = load_dataset(args.limit)
    track_errors = args.show_errors or args.analyze_errors or args.export
    metrics, class_stats, errors = evaluate_dataset(df, track_errors=track_errors)
    print_metrics(metrics, class_stats, errors if track_errors else None)
    
    if args.export or args.analyze_errors:
        export_path = Path(args.export) if args.export else PROJECT_ROOT / "evaluation_errors.json"
        export_errors(errors, export_path)


if __name__ == "__main__":
    main()
