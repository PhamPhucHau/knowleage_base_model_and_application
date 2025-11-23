#!/usr/bin/env python3
"""
Phân tích chi tiết các error cases để tìm pattern và sửa rules.
"""
import json
from collections import Counter
from typing import List, Dict, Any

ERRORS_FILE = "/Users/hauphamphuc/Documents/Learning/HK5/Tri Thuc/CK/errors.json"


def load_errors() -> List[Dict]:
    with open(ERRORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_confusion_pattern(errors: List[Dict]) -> None:
    """Phân tích các confusion patterns."""
    print("=" * 80)
    print("PHÂN TÍCH CONFUSION PATTERNS")
    print("=" * 80)
    
    # Good → Standard
    good_to_standard = [e for e in errors if e["ground_truth"] == "Good" and e["prediction"] == "Standard"]
    if good_to_standard:
        print(f"\n📊 Good → Standard ({len(good_to_standard)} cases):")
        dti_values = [e["facts"].get("DTI_Ratio", 0) for e in good_to_standard]
        util_values = [e["facts"].get("Credit_Utilization_Ratio", 0) for e in good_to_standard]
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in good_to_standard]
        
        print(f"  DTI: min={min(dti_values):.3f}, max={max(dti_values):.3f}, mean={sum(dti_values)/len(dti_values):.3f}")
        print(f"  Util: min={min(util_values):.3f}, max={max(util_values):.3f}, mean={sum(util_values)/len(util_values):.3f}")
        print(f"  Delayed: min={min(delayed_values)}, max={max(delayed_values)}, mean={sum(delayed_values)/len(delayed_values):.1f}")
        
        # Check why R_CS_G didn't match
        r_cs_g_failures = {
            "DTI > 0.1": sum(1 for d in dti_values if d > 0.1),
            "Util > 0.7": sum(1 for u in util_values if u > 0.7),
            "Delayed > 5": sum(1 for d in delayed_values if d > 5),
        }
        print(f"  R_CS_G failures:")
        for cond, count in r_cs_g_failures.items():
            if count > 0:
                print(f"    - {cond}: {count}/{len(good_to_standard)} ({count/len(good_to_standard):.1%})")
        
        # Sample cases
        print(f"\n  Sample cases (first 5):")
        for i, case in enumerate(good_to_standard[:5], 1):
            facts = case["facts"]
            print(f"    Case {i}: DTI={facts.get('DTI_Ratio', 0):.3f}, "
                  f"Util={facts.get('Credit_Utilization_Ratio', 0):.3f}, "
                  f"Delayed={facts.get('Num_of_Delayed_Payment', 0)}")
    
    # Standard → Poor
    standard_to_poor = [e for e in errors if e["ground_truth"] == "Standard" and e["prediction"] == "Poor"]
    if standard_to_poor:
        print(f"\n📊 Standard → Poor ({len(standard_to_poor)} cases):")
        dti_values = [e["facts"].get("DTI_Ratio", 0) for e in standard_to_poor]
        util_values = [e["facts"].get("Credit_Utilization_Ratio", 0) for e in standard_to_poor]
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in standard_to_poor]
        
        print(f"  DTI: min={min(dti_values):.3f}, max={max(dti_values):.3f}, mean={sum(dti_values)/len(dti_values):.3f}")
        print(f"  Util: min={min(util_values):.3f}, max={max(util_values):.3f}, mean={sum(util_values)/len(util_values):.3f}")
        print(f"  Delayed: min={min(delayed_values)}, max={max(delayed_values)}, mean={sum(delayed_values)/len(delayed_values):.1f}")
        
        # Check why R_CS_P matched (shouldn't have)
        print(f"  R_CS_P matched because:")
        case1_count = sum(1 for d in delayed_values if d > 17)
        case2_count = sum(1 for d in dti_values if d >= 0.3)
        print(f"    - Delayed > 17: {case1_count}/{len(standard_to_poor)} ({case1_count/len(standard_to_poor):.1%})")
        print(f"    - DTI >= 0.3: {case2_count}/{len(standard_to_poor)} ({case2_count/len(standard_to_poor):.1%})")
        
        # Sample cases
        print(f"\n  Sample cases (first 5):")
        for i, case in enumerate(standard_to_poor[:5], 1):
            facts = case["facts"]
            print(f"    Case {i}: DTI={facts.get('DTI_Ratio', 0):.3f}, "
                  f"Util={facts.get('Credit_Utilization_Ratio', 0):.3f}, "
                  f"Delayed={facts.get('Num_of_Delayed_Payment', 0)}")
    
    # Poor → Standard
    poor_to_standard = [e for e in errors if e["ground_truth"] == "Poor" and e["prediction"] == "Standard"]
    if poor_to_standard:
        print(f"\n📊 Poor → Standard ({len(poor_to_standard)} cases):")
        dti_values = [e["facts"].get("DTI_Ratio", 0) for e in poor_to_standard]
        util_values = [e["facts"].get("Credit_Utilization_Ratio", 0) for e in poor_to_standard]
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in poor_to_standard]
        
        print(f"  DTI: min={min(dti_values):.3f}, max={max(dti_values):.3f}, mean={sum(dti_values)/len(dti_values):.3f}")
        print(f"  Util: min={min(util_values):.3f}, max={max(util_values):.3f}, mean={sum(util_values)/len(util_values):.3f}")
        print(f"  Delayed: min={min(delayed_values)}, max={max(delayed_values)}, mean={sum(delayed_values)/len(delayed_values):.1f}")
        
        # Check why R_CS_P didn't match
        print(f"  R_CS_P didn't match because:")
        case1_fail = sum(1 for d in delayed_values if d <= 17)
        case2_fail = sum(1 for d in dti_values if d < 0.3)
        print(f"    - Delayed <= 17: {case1_fail}/{len(poor_to_standard)} ({case1_fail/len(poor_to_standard):.1%})")
        print(f"    - DTI < 0.3: {case2_fail}/{len(poor_to_standard)} ({case2_fail/len(poor_to_standard):.1%})")
    
    # Good → Unknown
    good_to_unknown = [e for e in errors if e["ground_truth"] == "Good" and e["prediction"] == "Unknown"]
    if good_to_unknown:
        print(f"\n📊 Good → Unknown ({len(good_to_unknown)} cases):")
        dti_values = [e["facts"].get("DTI_Ratio", 0) for e in good_to_unknown]
        util_values = [e["facts"].get("Credit_Utilization_Ratio", 0) for e in good_to_unknown]
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in good_to_unknown]
        
        print(f"  DTI: min={min(dti_values):.3f}, max={max(dti_values):.3f}, mean={sum(dti_values)/len(dti_values):.3f}")
        print(f"  Util: min={min(util_values):.3f}, max={max(util_values):.3f}, mean={sum(util_values)/len(util_values):.3f}")
        print(f"  Delayed: min={min(delayed_values)}, max={max(delayed_values)}, mean={sum(delayed_values)/len(delayed_values):.1f}")
        
        # Sample cases
        print(f"\n  Sample cases (first 5):")
        for i, case in enumerate(good_to_unknown[:5], 1):
            facts = case["facts"]
            print(f"    Case {i}: DTI={facts.get('DTI_Ratio', 0):.3f}, "
                  f"Util={facts.get('Credit_Utilization_Ratio', 0):.3f}, "
                  f"Delayed={facts.get('Num_of_Delayed_Payment', 0)}")


def suggest_fixes(errors: List[Dict]) -> None:
    """Đề xuất sửa rules."""
    print("\n" + "=" * 80)
    print("ĐỀ XUẤT SỬA RULES")
    print("=" * 80)
    
    good_to_standard = [e for e in errors if e["ground_truth"] == "Good" and e["prediction"] == "Standard"]
    standard_to_poor = [e for e in errors if e["ground_truth"] == "Standard" and e["prediction"] == "Poor"]
    poor_to_standard = [e for e in errors if e["ground_truth"] == "Poor" and e["prediction"] == "Standard"]
    
    print("\n💡 Đề xuất:")
    
    if good_to_standard:
        dti_values = [e["facts"].get("DTI_Ratio", 0) for e in good_to_standard]
        util_values = [e["facts"].get("Credit_Utilization_Ratio", 0) for e in good_to_standard]
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in good_to_standard]
        
        max_dti = max(dti_values)
        max_util = max(util_values)
        max_delayed = max(delayed_values)
        
        print(f"\n1. R_CS_G: Nới lỏng thêm để cover Good → Standard ({len(good_to_standard)} cases):")
        if max_dti > 0.1:
            print(f"   - Nới lỏng DTI từ <= 0.1 lên <= {max_dti:.3f} (max trong Good→Standard)")
        if max_util > 0.7:
            print(f"   - Nới lỏng Utilization từ <= 0.7 lên <= {max_util:.3f} (max trong Good→Standard)")
        if max_delayed > 5:
            print(f"   - Nới lỏng Delayed từ <= 5 lên <= {max_delayed} (max trong Good→Standard)")
    
    if standard_to_poor:
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in standard_to_poor]
        min_delayed = min(delayed_values)
        max_delayed = max(delayed_values)
        
        print(f"\n2. R_CS_P: Điều chỉnh ranh giới với Standard ({len(standard_to_poor)} cases):")
        print(f"   - Standard cases bị predict Poor có Delayed: min={min_delayed}, max={max_delayed}")
        print(f"   - Đề xuất: Tăng ngưỡng Delayed từ > 17 lên > {max_delayed} để tránh match Standard")
        print(f"   - HOẶC: Thêm điều kiện DTI >= 0.2 cho case Delayed > 17")
    
    if poor_to_standard:
        delayed_values = [e["facts"].get("Num_of_Delayed_Payment", 0) for e in poor_to_standard]
        max_delayed = max(delayed_values)
        
        print(f"\n3. R_CS_P: Nới lỏng để cover Poor → Standard ({len(poor_to_standard)} cases):")
        print(f"   - Poor cases bị predict Standard có Delayed <= {max_delayed}")
        print(f"   - Đề xuất: Giảm ngưỡng Delayed từ > 17 xuống > {max_delayed} để match Poor cases")


if __name__ == "__main__":
    errors = load_errors()
    analyze_confusion_pattern(errors)
    suggest_fixes(errors)

