#!/usr/bin/env python3
"""
Phân tích các cases trả về "Unknown" để tìm pattern và đề xuất sửa rules.
"""
import json
import statistics
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
    
    # R_CS_G conditions (đã cập nhật)
    r_cs_g_match = (
        dti <= 0.1 and
        utilization <= 0.2 and
        delayed <= 5
    )
    
    # R_CS_S conditions
    r_cs_s_match = (
        (0.1 < dti <= 0.3) or
        (0.2 < utilization <= 0.5) or
        (5 < delayed <= 15)
    ) and (
        dti < 0.4 and
        delayed <= 15
    )
    
    # R_CS_P conditions
    has_high_risk = (
        dti >= 0.4 or
        delayed > 15 or
        utilization > 0.5
    )
    has_additional_risk = (
        num_loan > 3 or
        history_months < 60
    )
    r_cs_p_match = has_high_risk and has_additional_risk
    
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


def analyze_unknown_cases(errors: List[Dict]) -> None:
    """Phân tích các cases trả về Unknown."""
    unknown_cases = [e for e in errors if e["prediction"] == "Unknown"]
    print(f"\n{'='*80}")
    print(f"PHÂN TÍCH {len(unknown_cases)} CASES 'Unknown'")
    print(f"{'='*80}")
    
    if not unknown_cases:
        print("Không có case nào Unknown!")
        return
    
    # Phân loại theo ground truth
    by_gt = Counter()
    for case in unknown_cases:
        by_gt[case["ground_truth"]] += 1
    
    print(f"\n📊 Phân bố theo Ground Truth:")
    for gt, count in by_gt.most_common():
        print(f"  - {gt}: {count} cases ({count/len(unknown_cases):.1%})")
    
    # Phân tích tại sao không match rules
    print(f"\n🔍 Phân tích tại sao không match rules:")
    
    for gt in ["Good", "Standard", "Poor"]:
        cases = [c for c in unknown_cases if c["ground_truth"] == gt]
        if not cases:
            continue
        
        print(f"\n  📋 {gt} cases ({len(cases)} cases):")
        
        # Thống kê giá trị
        dti_values = []
        util_values = []
        delayed_values = []
        num_loan_values = []
        history_values = []
        
        match_analysis = {
            "R_CS_G": 0,
            "R_CS_S": 0,
            "R_CS_P": 0,
            "no_match": 0,
        }
        
        for case in cases:
            facts = case["facts"]
            analysis = check_rule_match(facts)
            
            dti_values.append(analysis["values"]["DTI_Ratio"])
            util_values.append(analysis["values"]["Credit_Utilization_Ratio"])
            delayed_values.append(analysis["values"]["Num_of_Delayed_Payment"])
            num_loan_values.append(analysis["values"]["Num_of_Loan"])
            history_values.append(analysis["values"]["Credit_History_Age_Months"])
            
            if analysis["R_CS_G"]:
                match_analysis["R_CS_G"] += 1
            elif analysis["R_CS_S"]:
                match_analysis["R_CS_S"] += 1
            elif analysis["R_CS_P"]:
                match_analysis["R_CS_P"] += 1
            else:
                match_analysis["no_match"] += 1
        
        print(f"    Rule matching (theo logic hiện tại):")
        print(f"      - R_CS_G: {match_analysis['R_CS_G']} cases")
        print(f"      - R_CS_S: {match_analysis['R_CS_S']} cases")
        print(f"      - R_CS_P: {match_analysis['R_CS_P']} cases")
        print(f"      - Không match: {match_analysis['no_match']} cases")
        
        print(f"\n    Thống kê giá trị:")
        print(f"      DTI_Ratio: mean={statistics.mean(dti_values):.3f}, "
              f"median={statistics.median(dti_values):.3f}, "
              f"min={min(dti_values):.3f}, max={max(dti_values):.3f}")
        print(f"      Credit_Utilization_Ratio: mean={statistics.mean(util_values):.3f}, "
              f"median={statistics.median(util_values):.3f}, "
              f"min={min(util_values):.3f}, max={max(util_values):.3f}")
        print(f"      Num_of_Delayed_Payment: mean={statistics.mean(delayed_values):.1f}, "
              f"median={statistics.median(delayed_values):.1f}, "
              f"min={min(delayed_values)}, max={max(delayed_values)}")
        print(f"      Num_of_Loan: mean={statistics.mean(num_loan_values):.1f}, "
              f"median={statistics.median(num_loan_values):.1f}")
        print(f"      Credit_History_Age_Months: mean={statistics.mean(history_values):.1f}, "
              f"median={statistics.median(history_values):.1f}")
        
        # Phân tích tại sao không match
        print(f"\n    🔎 Phân tích tại sao không match:")
        
        # Đếm các điều kiện không thỏa
        r_cs_g_failures = {
            "DTI > 0.1": sum(1 for d in dti_values if d > 0.1),
            "Util > 0.2": sum(1 for u in util_values if u > 0.2),
            "Delayed > 5": sum(1 for d in delayed_values if d > 5),
        }
        
        r_cs_s_failures = {
            "DTI not in (0.1, 0.3]": sum(1 for d in dti_values if not (0.1 < d <= 0.3)),
            "Util not in (0.2, 0.5]": sum(1 for u in util_values if not (0.2 < u <= 0.5)),
            "Delayed not in (5, 15]": sum(1 for d in delayed_values if not (5 < d <= 15)),
            "DTI >= 0.4": sum(1 for d in dti_values if d >= 0.4),
            "Delayed > 15": sum(1 for d in delayed_values if d > 15),
        }
        
        r_cs_p_failures = {
            "DTI < 0.4": sum(1 for d in dti_values if d < 0.4),
            "Delayed <= 15": sum(1 for d in delayed_values if d <= 15),
            "Util <= 0.5": sum(1 for u in util_values if u <= 0.5),
            "Num_Loan <= 3": sum(1 for n in num_loan_values if n <= 3),
            "History >= 60": sum(1 for h in history_values if h >= 60),
        }
        
        if gt == "Good":
            print(f"      R_CS_G failures:")
            for cond, count in r_cs_g_failures.items():
                if count > 0:
                    print(f"        - {cond}: {count} cases ({count/len(cases):.1%})")
        
        if gt == "Standard":
            print(f"      R_CS_S failures:")
            for cond, count in r_cs_s_failures.items():
                if count > 0:
                    print(f"        - {cond}: {count} cases ({count/len(cases):.1%})")
        
        if gt == "Poor":
            print(f"      R_CS_P failures:")
            for cond, count in r_cs_p_failures.items():
                if count > 0:
                    print(f"        - {cond}: {count} cases ({count/len(cases):.1%})")
        
        # Hiển thị sample cases
        print(f"\n    📋 Sample cases (first 3):")
        for i, case in enumerate(cases[:3], 1):
            facts = case["facts"]
            analysis = check_rule_match(facts)
            print(f"      Case {i} (Index {case['index']}):")
            print(f"        DTI={analysis['values']['DTI_Ratio']:.3f}, "
                  f"Util={analysis['values']['Credit_Utilization_Ratio']:.3f}, "
                  f"Delayed={analysis['values']['Num_of_Delayed_Payment']}, "
                  f"Loans={analysis['values']['Num_of_Loan']}, "
                  f"History={analysis['values']['Credit_History_Age_Months']}")
            print(f"        Match: R_CS_G={analysis['R_CS_G']}, "
                  f"R_CS_S={analysis['R_CS_S']}, "
                  f"R_CS_P={analysis['R_CS_P']}")


def suggest_fixes(errors: List[Dict]) -> None:
    """Đề xuất sửa rules."""
    unknown_cases = [e for e in errors if e["prediction"] == "Unknown"]
    
    print(f"\n{'='*80}")
    print("ĐỀ XUẤT SỬA RULES")
    print(f"{'='*80}")
    
    # Phân tích Good cases Unknown
    good_unknown = [c for c in unknown_cases if c["ground_truth"] == "Good"]
    if good_unknown:
        print(f"\n💡 Good cases Unknown ({len(good_unknown)} cases):")
        util_values = [c["facts"].get("Credit_Utilization_Ratio", 0) for c in good_unknown]
        delayed_values = [c["facts"].get("Num_of_Delayed_Payment", 0) for c in good_unknown]
        dti_values = [c["facts"].get("DTI_Ratio", 0) for c in good_unknown]
        
        util_over_02 = sum(1 for u in util_values if u > 0.2)
        util_over_05 = sum(1 for u in util_values if u > 0.5)
        delayed_over_5 = sum(1 for d in delayed_values if d > 5)
        dti_over_01 = sum(1 for d in dti_values if d > 0.1)
        
        print(f"  - Utilization > 0.2: {util_over_02}/{len(good_unknown)} ({util_over_02/len(good_unknown):.1%})")
        print(f"  - Utilization > 0.5: {util_over_05}/{len(good_unknown)} ({util_over_05/len(good_unknown):.1%})")
        print(f"  - Delayed > 5: {delayed_over_5}/{len(good_unknown)} ({delayed_over_5/len(good_unknown):.1%})")
        print(f"  - DTI > 0.1: {dti_over_01}/{len(good_unknown)} ({dti_over_01/len(good_unknown):.1%})")
        
        if util_over_05 > len(good_unknown) * 0.3:
            print(f"\n  ✅ Đề xuất: Nới lỏng R_CS_G Credit_Utilization_Ratio từ <= 0.2 lên <= 0.6")
        if delayed_over_5 > len(good_unknown) * 0.3:
            print(f"  ✅ Đề xuất: Nới lỏng R_CS_G Num_of_Delayed_Payment từ <= 5 lên <= 10")
    
    # Phân tích Poor cases Unknown
    poor_unknown = [c for c in unknown_cases if c["ground_truth"] == "Poor"]
    if poor_unknown:
        print(f"\n💡 Poor cases Unknown ({len(poor_unknown)} cases):")
        dti_values = [c["facts"].get("DTI_Ratio", 0) for c in poor_unknown]
        delayed_values = [c["facts"].get("Num_of_Delayed_Payment", 0) for c in poor_unknown]
        util_values = [c["facts"].get("Credit_Utilization_Ratio", 0) for c in poor_unknown]
        num_loan_values = [c["facts"].get("Num_of_Loan", 0) for c in poor_unknown]
        history_values = [c["facts"].get("Credit_History_Age_Months", 0) for c in poor_unknown]
        
        dti_under_04 = sum(1 for d in dti_values if d < 0.4)
        delayed_under_15 = sum(1 for d in delayed_values if d <= 15)
        util_under_05 = sum(1 for u in util_values if u <= 0.5)
        loan_under_3 = sum(1 for n in num_loan_values if n <= 3)
        history_over_60 = sum(1 for h in history_values if h >= 60)
        
        print(f"  - DTI < 0.4: {dti_under_04}/{len(poor_unknown)} ({dti_under_04/len(poor_unknown):.1%})")
        print(f"  - Delayed <= 15: {delayed_under_15}/{len(poor_unknown)} ({delayed_under_15/len(poor_unknown):.1%})")
        print(f"  - Utilization <= 0.5: {util_under_05}/{len(poor_unknown)} ({util_under_05/len(poor_unknown):.1%})")
        print(f"  - Num_Loan <= 3: {loan_under_3}/{len(poor_unknown)} ({loan_under_3/len(poor_unknown):.1%})")
        print(f"  - History >= 60: {history_over_60}/{len(poor_unknown)} ({history_over_60/len(poor_unknown):.1%})")
        
        print(f"\n  ✅ Đề xuất: Nới lỏng R_CS_P - chỉ cần 1 điều kiện high_risk + 1 điều kiện additional_risk")
        print(f"     Hoặc: Nới lỏng ngưỡng DTI từ >= 0.4 xuống >= 0.3")
        print(f"     Hoặc: Nới lỏng ngưỡng Delayed từ > 15 xuống > 10")
    
    # Phân tích Standard cases Unknown
    standard_unknown = [c for c in unknown_cases if c["ground_truth"] == "Standard"]
    if standard_unknown:
        print(f"\n💡 Standard cases Unknown ({len(standard_unknown)} cases):")
        print(f"  ✅ Đề xuất: Mở rộng R_CS_S để cover nhiều trường hợp hơn")
        print(f"     - Cho phép DTI <= 0.1 nếu Utilization hoặc Delayed trong range Standard")
        print(f"     - Cho phép Utilization > 0.5 nếu DTI và Delayed trong range Standard")


if __name__ == "__main__":
    errors = load_errors()
    analyze_unknown_cases(errors)
    suggest_fixes(errors)

