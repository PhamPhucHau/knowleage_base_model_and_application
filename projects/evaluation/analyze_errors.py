"""
Phân tích chi tiết errors để tìm bug trong inference engine.

Kiểm tra:
1. Tại sao rules không match
2. Các điều kiện gần match
3. Đề xuất cải thiện rules
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ERRORS_FILE = PROJECT_ROOT.parent / "errors.json"  # errors.json ở root của CK


def load_errors() -> List[Dict]:
    """Load errors từ JSON file."""
    with open(ERRORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_rule_conditions(facts: Dict) -> Dict[str, bool]:
    """Kiểm tra điều kiện của các rules."""
    dti = facts.get("DTI_Ratio", 0)
    utilization = facts.get("Credit_Utilization_Ratio", 0)
    delayed = facts.get("Num_of_Delayed_Payment", 0)
    num_loan = facts.get("Num_of_Loan", 0)
    history_months = facts.get("Credit_History_Age_Months", 0)
    
    # R_CS_G conditions
    r_cs_g_conditions = {
        "DTI_Ratio <= 0.1": dti <= 0.1,
        "Credit_Utilization_Ratio <= 0.1": utilization <= 0.1,
        "Num_of_Delayed_Payment == 0": delayed == 0,
    }
    
    # R_CS_P conditions
    r_cs_p_conditions = {
        "DTI_Ratio >= 0.4": dti >= 0.4,
        "Num_of_Loan > 3": num_loan > 3,
        "Credit_History_Age_Months < 60": history_months < 60,
    }
    
    return {
        "R_CS_G": r_cs_g_conditions,
        "R_CS_P": r_cs_p_conditions,
        "values": {
            "DTI_Ratio": dti,
            "Credit_Utilization_Ratio": utilization,
            "Num_of_Delayed_Payment": delayed,
            "Num_of_Loan": num_loan,
            "Credit_History_Age_Months": history_months,
        }
    }


def analyze_rule_coverage(errors: List[Dict]) -> None:
    """Phân tích coverage của rules."""
    print("=" * 80)
    print("PHÂN TÍCH RULE COVERAGE")
    print("=" * 80)
    
    # Phân loại theo ground truth
    by_ground_truth = defaultdict(list)
    for err in errors:
        by_ground_truth[err["ground_truth"]].append(err)
    
    for gt, cases in by_ground_truth.items():
        print(f"\n📊 Ground Truth: {gt} ({len(cases)} cases)")
        
        # Kiểm tra điều kiện rules cho từng case
        r_cs_g_almost = []  # Gần match R_CS_G
        r_cs_p_almost = []  # Gần match R_CS_P
        no_match = []
        
        for case in cases:
            facts = case["facts"]
            conditions = check_rule_conditions(facts)
            
            # Check R_CS_G
            r_cs_g_met = sum(conditions["R_CS_G"].values())
            if r_cs_g_met == 3:
                print(f"  ✅ Case {case['index']}: Match R_CS_G hoàn toàn!")
            elif r_cs_g_met == 2:
                r_cs_g_almost.append((case, conditions))
            
            # Check R_CS_P
            r_cs_p_met = sum(conditions["R_CS_P"].values())
            if r_cs_p_met == 3:
                print(f"  ✅ Case {case['index']}: Match R_CS_P hoàn toàn!")
            elif r_cs_p_met == 2:
                r_cs_p_almost.append((case, conditions))
            
            if r_cs_g_met < 2 and r_cs_p_met < 2:
                no_match.append((case, conditions))
        
        # Phân tích các case gần match
        if r_cs_g_almost:
            print(f"\n  ⚠️  R_CS_G - Gần match (2/3 điều kiện): {len(r_cs_g_almost)} cases")
            missing_conditions = Counter()
            for case, cond in r_cs_g_almost[:5]:  # Show first 5
                missing = [k for k, v in cond["R_CS_G"].items() if not v]
                missing_conditions.update(missing)
                print(f"    Case {case['index']}: Thiếu {', '.join(missing)}")
                print(f"      Values: DTI={cond['values']['DTI_Ratio']:.3f}, "
                      f"Util={cond['values']['Credit_Utilization_Ratio']:.3f}, "
                      f"Delayed={cond['values']['Num_of_Delayed_Payment']}")
            print(f"    Missing conditions phổ biến: {missing_conditions.most_common()}")
        
        if r_cs_p_almost:
            print(f"\n  ⚠️  R_CS_P - Gần match (2/3 điều kiện): {len(r_cs_p_almost)} cases")
            for case, cond in r_cs_p_almost[:5]:
                missing = [k for k, v in cond["R_CS_P"].items() if not v]
                print(f"    Case {case['index']}: Thiếu {', '.join(missing)}")
        
        if no_match:
            print(f"\n  ❌ Không match rule nào (< 2 điều kiện): {len(no_match)} cases")
            # Thống kê giá trị trung bình
            avg_dti = sum(c[1]["values"]["DTI_Ratio"] for c in no_match) / len(no_match)
            avg_util = sum(c[1]["values"]["Credit_Utilization_Ratio"] for c in no_match) / len(no_match)
            avg_delayed = sum(c[1]["values"]["Num_of_Delayed_Payment"] for c in no_match) / len(no_match)
            print(f"    Average values: DTI={avg_dti:.3f}, Util={avg_util:.3f}, Delayed={avg_delayed:.1f}")


def analyze_specific_cases(errors: List[Dict]) -> None:
    """Phân tích chi tiết một vài case cụ thể."""
    print("\n" + "=" * 80)
    print("PHÂN TÍCH CASE CỤ THỂ")
    print("=" * 80)
    
    # Case 1: Ground Truth = Good nhưng không match
    good_cases = [e for e in errors if e["ground_truth"] == "Good"][:3]
    
    for i, case in enumerate(good_cases, 1):
        print(f"\n📋 Case {i} (Index {case['index']}):")
        print(f"  Ground Truth: {case['ground_truth']} → Prediction: {case['prediction']}")
        facts = case["facts"]
        conditions = check_rule_conditions(facts)
        
        print(f"  Facts quan trọng:")
        print(f"    - DTI_Ratio: {conditions['values']['DTI_Ratio']:.3f}")
        print(f"    - Credit_Utilization_Ratio: {conditions['values']['Credit_Utilization_Ratio']:.3f}")
        print(f"    - Num_of_Delayed_Payment: {conditions['values']['Num_of_Delayed_Payment']}")
        print(f"    - Num_of_Loan: {conditions['values']['Num_of_Loan']}")
        print(f"    - Credit_History_Age_Months: {conditions['values']['Credit_History_Age_Months']}")
        
        print(f"  R_CS_G conditions:")
        for cond, met in conditions["R_CS_G"].items():
            status = "✅" if met else "❌"
            print(f"    {status} {cond}")
        
        print(f"  R_CS_P conditions:")
        for cond, met in conditions["R_CS_P"].items():
            status = "✅" if met else "❌"
            print(f"    {status} {cond}")
        
        print(f"  Steps: {len(case['steps'])} steps")
        if case["missing_facts"]:
            print(f"  Missing: {', '.join(case['missing_facts'])}")


def suggest_improvements(errors: List[Dict]) -> None:
    """Đề xuất cải thiện rules."""
    print("\n" + "=" * 80)
    print("ĐỀ XUẤT CẢI THIỆN")
    print("=" * 80)
    
    # Phân tích các case Good không match
    good_cases = [e for e in errors if e["ground_truth"] == "Good"]
    if not good_cases:
        return
    
    print(f"\n📊 Phân tích {len(good_cases)} cases có Ground Truth = 'Good':")
    
    # Thống kê điều kiện
    dti_values = []
    util_values = []
    delayed_counts = []
    
    for case in good_cases:
        facts = case["facts"]
        dti_values.append(facts.get("DTI_Ratio", 0))
        util_values.append(facts.get("Credit_Utilization_Ratio", 0))
        delayed_counts.append(facts.get("Num_of_Delayed_Payment", 0))
    
    import statistics
    print(f"\n  DTI_Ratio:")
    print(f"    Mean: {statistics.mean(dti_values):.3f}")
    print(f"    Median: {statistics.median(dti_values):.3f}")
    print(f"    Max: {max(dti_values):.3f}")
    print(f"    Cases with DTI > 0.1: {sum(1 for d in dti_values if d > 0.1)}")
    
    print(f"\n  Credit_Utilization_Ratio:")
    print(f"    Mean: {statistics.mean(util_values):.3f}")
    print(f"    Median: {statistics.median(util_values):.3f}")
    print(f"    Max: {max(util_values):.3f}")
    print(f"    Cases with Util > 0.1: {sum(1 for u in util_values if u > 0.1)}")
    
    print(f"\n  Num_of_Delayed_Payment:")
    print(f"    Mean: {statistics.mean(delayed_counts):.1f}")
    print(f"    Median: {statistics.median(delayed_counts):.1f}")
    print(f"    Max: {max(delayed_counts)}")
    print(f"    Cases with Delayed > 0: {sum(1 for d in delayed_counts if d > 0)}")
    
    # Đề xuất
    print(f"\n💡 Đề xuất:")
    if sum(1 for u in util_values if u > 0.1) > len(good_cases) * 0.3:
        print(f"  - Nới lỏng điều kiện Credit_Utilization_Ratio từ ≤ 0.1 lên ≤ 0.2 hoặc 0.3")
    if sum(1 for d in delayed_counts if d > 0) > len(good_cases) * 0.3:
        print(f"  - Cho phép Num_of_Delayed_Payment <= 2 hoặc <= 5 thay vì == 0")
    if statistics.mean(dti_values) > 0.1:
        print(f"  - Nới lỏng điều kiện DTI_Ratio từ ≤ 0.1 lên ≤ 0.15 hoặc 0.2")


def main():
    errors = load_errors()
    print(f"Loaded {len(errors)} error cases")
    
    analyze_rule_coverage(errors)
    analyze_specific_cases(errors)
    suggest_improvements(errors)


if __name__ == "__main__":
    main()

