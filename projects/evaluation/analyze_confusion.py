#!/usr/bin/env python3
"""
Phân tích chi tiết các confusion patterns để tìm nguyên nhân.
"""
import json
from collections import Counter
from typing import List, Dict, Any

ERRORS_FILE = "/Users/hauphamphuc/Documents/Learning/HK5/Tri Thuc/CK/errors.json"


def load_errors() -> List[Dict]:
    with open(ERRORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_rule_match(facts: Dict) -> Dict[str, Any]:
    """Kiểm tra xem facts có match rule nào không."""
    dti = facts.get("DTI_Ratio", 0)
    utilization = facts.get("Credit_Utilization_Ratio", 0)
    delayed = facts.get("Num_of_Delayed_Payment", 0)
    num_loan = facts.get("Num_of_Loan", 0)
    history_months = facts.get("Credit_History_Age_Months", 0)
    
    # R_CS_G conditions (theo logic hiện tại)
    if dti <= 0.05:
        r_cs_g_match = delayed <= 10 and utilization <= 0.7
    else:
        r_cs_g_match = dti <= 0.1 and delayed <= 5 and utilization <= 0.7
    
    # R_CS_S conditions (theo logic hiện tại)
    case1 = (
        dti <= 0.1 and
        not (dti <= 0.05 and delayed <= 10) and
        (delayed > 5 or utilization > 0.2) and
        delayed <= 17
    )
    case2 = (
        5 < delayed <= 17 and
        dti < 0.4 and
        not (dti <= 0.05 and delayed <= 10) and
        not (dti >= 0.15 and delayed > 15)
    )
    case3 = (
        0.1 < dti <= 0.3 and
        delayed <= 17 and
        not (dti >= 0.15 and delayed > 15)
    )
    case4 = (
        utilization > 0.5 and
        dti <= 0.1 and
        delayed <= 5 and
        not (dti <= 0.05 and delayed <= 10)
    )
    r_cs_s_match = (case1 or case2 or case3 or case4) and dti < 0.4 and delayed <= 17
    
    # R_CS_P conditions (theo logic hiện tại)
    case1_p = delayed > 17 and (dti >= 0.15 or utilization > 0.3)
    case1b_p = delayed > 15 and dti >= 0.15 and delayed <= 17
    case2_p = dti >= 0.3 and (num_loan > 3 or history_months < 60)
    case3_p = delayed > 15 and (num_loan > 3 or history_months < 60)
    case4_p = utilization > 0.5 and (num_loan > 3 or history_months < 60)
    case5_p = delayed > 20
    r_cs_p_match = case1_p or case1b_p or case2_p or case3_p or case4_p or case5_p
    
    return {
        "R_CS_G": r_cs_g_match,
        "R_CS_S": r_cs_s_match,
        "R_CS_P": r_cs_p_match,
        "values": {
            "DTI_Ratio": dti,
            "Credit_Utilization_Ratio": utilization,
            "Num_of_Delayed_Payment": delayed,
            "Num_of_Loan": num_loan,
            "Credit_History_Age_Months": history_months,
        }
    }


def analyze_pattern(errors: List[Dict], pattern: str) -> None:
    """Phân tích một confusion pattern cụ thể."""
    gt, pred = pattern.split(" → ")
    cases = [e for e in errors if e["ground_truth"] == gt and e["prediction"] == pred]
    
    if not cases:
        return
    
    print(f"\n{'='*80}")
    print(f"PHÂN TÍCH: {pattern} ({len(cases)} cases)")
    print(f"{'='*80}")
    
    # Thống kê giá trị
    dti_values = [e["facts"].get("DTI_Ratio", 0) for e in cases]
    util_values = [e["facts"].get("Credit_Utilization_Ratio", 0) for e in cases]
    delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in cases]
    
    print(f"\n📊 Thống kê giá trị:")
    print(f"  DTI: min={min(dti_values):.3f}, max={max(dti_values):.3f}, "
          f"mean={sum(dti_values)/len(dti_values):.3f}, median={sorted(dti_values)[len(dti_values)//2]:.3f}")
    print(f"  Util: min={min(util_values):.3f}, max={max(util_values):.3f}, "
          f"mean={sum(util_values)/len(util_values):.3f}, median={sorted(util_values)[len(util_values)//2]:.3f}")
    print(f"  Delayed: min={min(delayed_values)}, max={max(delayed_values)}, "
          f"mean={sum(delayed_values)/len(delayed_values):.1f}, median={sorted(delayed_values)[len(delayed_values)//2]}")
    
    # Phân tích rule matching
    print(f"\n🔍 Phân tích rule matching:")
    rule_matches = {"R_CS_G": 0, "R_CS_S": 0, "R_CS_P": 0, "no_match": 0}
    
    for case in cases:
        facts = case["facts"]
        analysis = check_rule_match(facts)
        if analysis["R_CS_G"]:
            rule_matches["R_CS_G"] += 1
        elif analysis["R_CS_S"]:
            rule_matches["R_CS_S"] += 1
        elif analysis["R_CS_P"]:
            rule_matches["R_CS_P"] += 1
        else:
            rule_matches["no_match"] += 1
    
    for rule, count in rule_matches.items():
        if count > 0:
            print(f"  - {rule}: {count}/{len(cases)} ({count/len(cases):.1%})")
    
    # Phân tích tại sao không match rule đúng
    if gt == "Good" and pred == "Standard":
        print(f"\n❌ Tại sao R_CS_G không match:")
        r_cs_g_failures = {
            "DTI > 0.05 và Delayed > 5": sum(1 for i, d in enumerate(dti_values) 
                                              if d > 0.05 and delayed_values[i] > 5),
            "DTI > 0.1": sum(1 for d in dti_values if d > 0.1),
            "Delayed > 10 (DTI <= 0.05)": sum(1 for i, d in enumerate(dti_values) 
                                               if d <= 0.05 and delayed_values[i] > 10),
            "Util > 0.7": sum(1 for u in util_values if u > 0.7),
        }
        for cond, count in r_cs_g_failures.items():
            if count > 0:
                print(f"    - {cond}: {count}/{len(cases)} ({count/len(cases):.1%})")
    
    if gt == "Standard" and pred == "Unknown":
        print(f"\n❌ Tại sao R_CS_S không match:")
        r_cs_s_failures = {
            "DTI <= 0.05 và Delayed <= 10 (match Good)": sum(1 for i, d in enumerate(dti_values) 
                                                               if d <= 0.05 and delayed_values[i] <= 10),
            "DTI >= 0.15 và Delayed > 15 (match Poor)": sum(1 for i, d in enumerate(dti_values) 
                                                             if d >= 0.15 and delayed_values[i] > 15),
            "Delayed > 17": sum(1 for d in delayed_values if d > 17),
            "DTI >= 0.4": sum(1 for d in dti_values if d >= 0.4),
        }
        for cond, count in r_cs_s_failures.items():
            if count > 0:
                print(f"    - {cond}: {count}/{len(cases)} ({count/len(cases):.1%})")
    
    if gt == "Poor" and pred == "Standard":
        print(f"\n❌ Tại sao R_CS_P không match:")
        r_cs_p_failures = {
            "Delayed <= 17": sum(1 for d in delayed_values if d <= 17),
            "Delayed <= 15": sum(1 for d in delayed_values if d <= 15),
            "DTI < 0.15": sum(1 for d in dti_values if d < 0.15),
            "Util <= 0.3": sum(1 for u in util_values if u <= 0.3),
        }
        for cond, count in r_cs_p_failures.items():
            if count > 0:
                print(f"    - {cond}: {count}/{len(cases)} ({count/len(cases):.1%})")
    
    # Sample cases
    print(f"\n📋 Sample cases (first 5):")
    for i, case in enumerate(cases[:5], 1):
        facts = case["facts"]
        analysis = check_rule_match(facts)
        print(f"  Case {i} (Index {case['index']}):")
        print(f"    DTI={analysis['values']['DTI_Ratio']:.3f}, "
              f"Util={analysis['values']['Credit_Utilization_Ratio']:.3f}, "
              f"Delayed={analysis['values']['Num_of_Delayed_Payment']}")
        print(f"    Match: R_CS_G={analysis['R_CS_G']}, "
              f"R_CS_S={analysis['R_CS_S']}, "
              f"R_CS_P={analysis['R_CS_P']}")


def main():
    errors = load_errors()
    
    print("="*80)
    print("PHÂN TÍCH CHI TIẾT CONFUSION PATTERNS")
    print("="*80)
    
    # Phân tích từng pattern
    patterns = [
        "Good → Standard",
        "Standard → Unknown",
        "Poor → Standard",
        "Standard → Poor",
        "Standard → Good",
        "Good → Unknown",
    ]
    
    for pattern in patterns:
        analyze_pattern(errors, pattern)
    
    print("\n" + "="*80)
    print("ĐỀ XUẤT SỬA RULES")
    print("="*80)
    
    good_to_standard = [e for e in errors if e["ground_truth"] == "Good" and e["prediction"] == "Standard"]
    if good_to_standard:
        dti_values = [e["facts"].get("DTI_Ratio", 0) for e in good_to_standard]
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in good_to_standard]
        max_dti = max(dti_values)
        max_delayed = max(delayed_values)
        
        print(f"\n1. R_CS_G: Nới lỏng để cover Good → Standard ({len(good_to_standard)} cases):")
        print(f"   - Max DTI: {max_dti:.3f}, Max Delayed: {max_delayed}")
        if max_dti > 0.05:
            print(f"   - Đề xuất: Nới lỏng DTI từ <= 0.05 lên <= {max_dti:.3f} để cho phép Delayed <= 10")
        if max_delayed > 10:
            print(f"   - Đề xuất: Nới lỏng Delayed từ <= 10 lên <= {max_delayed} khi DTI <= 0.05")
        elif max_delayed > 5:
            print(f"   - Đề xuất: Nới lỏng Delayed từ <= 5 lên <= {max_delayed} khi DTI > 0.05 và <= 0.1")


if __name__ == "__main__":
    main()

