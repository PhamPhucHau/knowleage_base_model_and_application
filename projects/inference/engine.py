"""
Inference Engine for Credit Score Knowledge Model.

Chức năng chính:
    • Nạp Problem (objects, facts, goal) từ Neo4j.
    • Khởi tạo Working Memory với facts ban đầu.
    • Áp dụng Funcs/Rules để suy diễn theo forward-chaining.
    • Trả về chuỗi giải thích dạng từng bước.

Chạy thử:
    $ python projects/inference/engine.py --problem PROB-001
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from rules.funcs import FUNC_REGISTRY  # noqa: E402

OCCUPATION_CREDIT_STATS: Dict[str, Dict[str, float]] = {
    "Teacher": {"Good": 19.924295, "Poor": 28.114246, "Standard": 51.961459},
    "Musician": {"Good": 19.247009, "Poor": 26.988037, "Standard": 53.764954},
    "Architect": {"Good": 19.229469, "Poor": 25.718148, "Standard": 55.052383},
    "Media_Manager": {"Good": 18.793343, "Poor": 24.82663, "Standard": 56.380028},
    "Accountant": {"Good": 18.707483, "Poor": 28.027211, "Standard": 53.265306},
    "Scientist": {"Good": 18.677573, "Poor": 27.743695, "Standard": 53.578732},
    "Journalist": {"Good": 18.675722, "Poor": 28.998302, "Standard": 52.325976},
    "Engineer": {"Good": 18.53875, "Poor": 29.156709, "Standard": 52.304541},
    "Manager": {"Good": 18.457102, "Poor": 27.757751, "Standard": 53.785148},
    "Developer": {"Good": 18.06694, "Poor": 28.312842, "Standard": 53.620219},
    "Doctor": {"Good": 17.669045, "Poor": 26.843357, "Standard": 55.487598},
    "Entrepreneur": {"Good": 17.537827, "Poor": 29.57359, "Standard": 52.888583},
    "Lawyer": {"Good": 17.380273, "Poor": 25.91183, "Standard": 56.707897},
    "Mechanic": {"Good": 17.254112, "Poor": 28.667338, "Standard": 54.07855},
    "Writer": {"Good": 13.212894, "Poor": 30.605739, "Standard": 56.181367},
}


def _get_occupation(memory: WorkingMemory) -> Optional[str]:
    occupation = memory.facts.get("occupation") or memory.facts.get("Occupation")
    if occupation:
        return str(occupation)
    return None


def _compute_occupation_risk(stats: Dict[str, float]) -> str:
    standard_ratio = stats["Standard"]
    diff_poor_good = stats["Poor"] - stats["Good"]
    if standard_ratio >= 55.0:
        return "Stable"
    if diff_poor_good >= 12.0:
        return "High"
    if diff_poor_good <= 4.0:
        return "Low"
    return "Medium"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class WorkingMemory:
    facts: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)

    def upsert_fact(self, key: str, value: Any, provenance: str) -> bool:
        """Insert fact if not exists. Return True if new fact added."""
        if key in self.facts:
            return False
        self.facts[key] = value
        self.steps.append(f"{provenance} ⇒ {key} = {value}")
        return True


@dataclass
class InferenceResult:
    success: bool
    goal: str
    value: Optional[Any]
    steps: List[str]
    missing_facts: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Knowledge base client
# ---------------------------------------------------------------------------


class KnowledgeBaseClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def fetch_problem(self, problem_id: str) -> Dict[str, Any]:
        with self.driver.session() as session:
            problem = session.execute_read(self._get_problem, problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} không tồn tại trong Neo4j.")
        return problem

    @staticmethod
    def _get_problem(tx, problem_id: str) -> Dict[str, Any]:
        base = tx.run(
            """
            MATCH (p:Problem {problem_id: $problem_id})
            OPTIONAL MATCH (p)-[:HAS_GOAL]->(g:ProblemGoal)
            RETURN p AS problem, g AS goal
            """,
            problem_id=problem_id,
        ).single()
        if not base:
            return {}

        def collect_nodes(query: str) -> List[Dict[str, Any]]:
            result = tx.run(query, problem_id=problem_id)
            return [record.data() for record in result]

        objects = collect_nodes(
            """
            MATCH (p:Problem {problem_id: $problem_id})-[:HAS_OBJECT]->(o:ProblemObject)
            RETURN o.object_id AS object_id, o.label AS label, properties(o) AS props
            """
        )
        facts = collect_nodes(
            """
            MATCH (p:Problem {problem_id: $problem_id})-[:HAS_FACT]->(f:ProblemFact)
            RETURN f.fact_id AS fact_id, f.statement AS statement,
                   f.value AS value, f.derived_by AS derived_by, f.uses AS uses
            """
        )
        func_results = collect_nodes(
            """
            MATCH (p:Problem {problem_id: $problem_id})-[:USES_FUNC_RESULT]->(fr:ProblemFuncResult)
            RETURN fr.func_id AS func_id, fr.name AS name,
                   fr.output AS output, fr.output_json AS output_json
            """
        )

        return {
            "problem": dict(base["problem"]),
            "goal": dict(base["goal"]) if base["goal"] else {},
            "objects": objects,
            "facts": facts,
            "func_results": func_results,
        }

    def fetch_rules(self) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (r:Rule)
                OPTIONAL MATCH (r)-[:USES_FUNCTION]->(f:Function)
                OPTIONAL MATCH (r)-[:USES_OPERATOR]->(o:Operator)
                RETURN r.name AS name, r.rule_type AS rule_type, r.description AS description,
                       r.expression AS expression, r.premises AS premises,
                       r.conclusion AS conclusion, collect(DISTINCT f.name) AS functions,
                       collect(DISTINCT o.name) AS operators
                """
            )
            return [record.data() for record in records]


# ---------------------------------------------------------------------------
# Rule executor implementations
# ---------------------------------------------------------------------------


def rule_dti_ratio(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    if {"Outstanding_Debt", "Annual_Income"}.issubset(memory.facts):
        debt = memory.facts["Outstanding_Debt"]
        income = memory.facts["Annual_Income"]
        if income:
            value = debt / income
            return memory.upsert_fact("DTI_Ratio", round(value, 5), "R_DTI"), "R_DTI"
    return False, None


def rule_credit_utilization(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    if {"Outstanding_Debt", "Num_of_Loan"}.issubset(memory.facts):
        debt = memory.facts["Outstanding_Debt"]
        num_loans = memory.facts["Num_of_Loan"]
        if num_loans:
            avg_limit = memory.facts.get("Avg_Credit_Limit", 1000)
            value = debt / (num_loans * avg_limit)
            return memory.upsert_fact("Credit_Utilization_Ratio", round(value, 6), "R_CU"), "R_CU"
    return False, None


def rule_payment_parser(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    raw = memory.facts.get("Payment_Behaviour")
    if raw and "Spending_Level" not in memory.facts:
        result = FUNC_REGISTRY["Payment_Behavior_Parser"](raw)
        updated = False
        for key, value in result.items():
            if value:
                updated |= memory.upsert_fact(key, value, "R_P1")
        return updated, "R_P1" if updated else (False, None)
    return False, None


def rule_occupation_profile(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    """
    R_OCC_PROFILE: Ghi nhận tỷ lệ Good/Poor/Standard và mức rủi ro theo nghề nghiệp.
    """
    occupation = _get_occupation(memory)
    if not occupation:
        return False, None
    stats = OCCUPATION_CREDIT_STATS.get(occupation)
    if not stats:
        return False, None

    updated_any = False
    for key, value in stats.items():
        updated_any |= memory.upsert_fact(f"Occupation_{key}_Ratio", value, "R_OCC_PROFILE")

    risk = _compute_occupation_risk(stats)
    updated_any |= memory.upsert_fact("Occupation_Risk_Level", risk, "R_OCC_PROFILE")
    return updated_any, "R_OCC_PROFILE" if updated_any else (False, None)


def rule_credit_score_good(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    """
    R_CS_G: Suy diễn Credit Score = Good
    
    Điều kiện (đã điều chỉnh dựa trên phân tích Good → Standard và Good → Unknown):
    - DTI_Ratio <= 0.05: Cho phép Delayed <= 10 và Utilization <= 0.7
    - DTI_Ratio > 0.05 và <= 0.1: Cho phép Delayed <= 8 và Utilization <= 0.7
    - Nghề nghiệp rủi ro thấp chỉ nới nhẹ (+1 lần trễ, +0.02 utilization)
    - Nghề nghiệp rủi ro cao siết nhẹ (-1 lần trễ, -0.02 utilization)
    
    Lý do: 
    - Good → Standard (24 cases): DTI=0.042, Delayed=7-8 → cần nới lỏng Delayed nếu DTI rất thấp
    - Good → Unknown (11 cases): DTI=0.017, Util=0.605, Delayed=1 → nên match nhưng bị R_CS_S match trước
    """
    # Nếu đã có Credit_Score thì không chạy
    if "Credit_Score" in memory.facts:
        return False, None
    
    dti = memory.facts.get("DTI_Ratio", 1)
    utilization = memory.facts.get("Credit_Utilization_Ratio")
    if utilization is None:
        utilization = 0.4 if dti <= 0.1 else 1
    delayed = memory.facts.get("Num_of_Delayed_Payment", 999)

    risk = memory.facts.get("Occupation_Risk_Level")
    delay_bonus = 0
    util_bonus = 0.0
    if risk in {"Stable", "Low"}:
        delay_bonus = 1
        util_bonus = 0.02
    elif risk == "High":
        delay_bonus = -1
        util_bonus = -0.02

    if dti <= 0.05:
        delay_cap = 10 + delay_bonus
    elif dti <= 0.1:
        delay_cap = 8 + delay_bonus
    else:
        return False, None

    delay_cap = max(4, min(12, delay_cap))
    util_cap = min(0.85, max(0.6, 0.7 + util_bonus))

    if dti <= 0.03 and delayed <= 2:
        util_cap = min(0.95, util_cap + 0.15)
    if dti <= 0.02 and delayed <= 1:
        util_cap = 0.98

    if delayed <= delay_cap and utilization <= util_cap:
        updated = memory.upsert_fact("Credit_Score", "Good", "R_CS_G")
        return updated, "R_CS_G" if updated else (False, None)
    return False, None


def rule_credit_score_standard(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    """
    R_CS_S: Suy diễn Credit Score = Standard
    
    Điều kiện (đã điều chỉnh dựa trên phân tích Unknown cases):
    - Nếu đã có Credit_Score thì không chạy
    - Mở rộng để cover nhiều trường hợp hơn:
      * DTI <= 0.1 nhưng có Delayed > 5 HOẶC Utilization > 0.2
      * Delayed > 15 và <= 20 (nhiều Standard cases có Delayed 17-19)
      * Utilization > 0.5 nhưng DTI thấp và Delayed thấp
      * DTI > 0.1 và <= 0.3
    - Nghề nghiệp Stable chỉ được ưu tiên nhẹ khi các chỉ số đều tốt
    - Và không quá xấu (DTI < 0.4, Delayed <= 20)
    """
    # Nếu đã có Credit_Score thì không chạy
    if "Credit_Score" in memory.facts:
        return False, None
    
    dti = memory.facts.get("DTI_Ratio", 0)
    utilization = memory.facts.get("Credit_Utilization_Ratio")
    util_value = utilization if utilization is not None else 0.0
    delayed = memory.facts.get("Num_of_Delayed_Payment", 0)
    risk = memory.facts.get("Occupation_Risk_Level")
    
    util_good_threshold = 0.75
    good_primary = dti <= 0.05 and delayed <= 10 and (utilization is None or util_value <= util_good_threshold)
    good_secondary = dti <= 0.1 and delayed <= 8 and (utilization is None or util_value <= util_good_threshold)

    # Điều kiện Standard (mở rộng nhưng tránh match Good cases)
    # Case 1: DTI thấp nhưng có vấn đề về Delayed hoặc Utilization
    # KHÔNG match nếu có thể match Good (DTI <= 0.05 và Delayed <= 10, HOẶC DTI <= 0.1 và Delayed <= 8)
    case1 = (
        dti <= 0.1
        and not good_primary
        and not good_secondary
        and (delayed > 5 or util_value > 0.2)
        and delayed <= 17
    )
    
    # Case 2: Delayed trong range Standard (5-17)
    # KHÔNG match nếu có thể match Good hoặc Poor
    case2 = (
        5 < delayed <= 17 and
        dti < 0.4 and
        not good_primary and  # Tránh match Good cases
        not good_secondary and  # Tránh match Good cases
        not (dti >= 0.15 and delayed > 15)  # Tránh match Poor cases
    )
    
    # Case 3: DTI trong range Standard
    # KHÔNG match nếu Delayed > 15 và DTI >= 0.15 (có thể là Poor)
    case3 = (
        0.1 < dti <= 0.3 and
        delayed <= 17 and
        not (dti >= 0.15 and delayed > 15)  # Tránh match Poor cases
    )
    
    # Case 4: Utilization cao nhưng DTI thấp và Delayed thấp
    # KHÔNG match nếu có thể match Good
    case4 = (
        utilization is not None and util_value > 0.5 and
        dti <= 0.1 and
        delayed <= 5 and
        not good_primary and
        not good_secondary
    )
    
    # Case 5: DTI thấp (<= 0.1) nhưng Delayed = 0-5 và Util thấp (có thể là Standard)
    case5 = (
        dti <= 0.1 and
        delayed <= 5 and
        util_value <= 0.2 and
        not good_primary and
        not good_secondary
    )
    
    # Case 6: Delayed > 17 nhưng DTI thấp (< 0.15) và không match Poor
    case6 = (
        delayed > 17 and
        dti < 0.15 and
        delayed <= 20  # Cho phép Delayed cao hơn một chút
    )

    # Case 7: Nghề nghiệp ổn định (Stable) + chỉ số ở mức trung tính
    case7 = (
        risk == "Stable" and
        dti <= 0.12 and
        delayed <= 10 and
        (utilization is None or util_value <= 0.5) and
        not good_primary and
        not good_secondary
    )

    # Case 8: Good candidate nhưng util cao → hạ xuống Standard
    case8 = (
        dti <= 0.05 and
        delayed <= 6 and
        utilization is not None and
        util_value > util_good_threshold and
        util_value <= 0.95
    )
    
    is_standard = (case1 or case2 or case3 or case4 or case5 or case6 or case7 or case8) and (
        dti < 0.4 and  # Không quá xấu
        delayed <= 20  # Mở rộng từ 17 lên 20 để cover nhiều cases hơn
    )
    
    if is_standard:
        updated = memory.upsert_fact("Credit_Score", "Standard", "R_CS_S")
        return updated, "R_CS_S" if updated else (False, None)
    return False, None


def rule_credit_score_poor(memory: WorkingMemory) -> Tuple[bool, Optional[str]]:
    """
    R_CS_P: Suy diễn Credit Score = Poor
    
    Điều kiện (đã điều chỉnh dựa trên phân tích Unknown cases):
    - Nếu đã có Credit_Score thì không chạy
    - Case 1: Delayed > 17 + (DTI >= 0.15 HOẶC Utilization > 0.3)
    - Case 1b: Delayed > 15 và <= 17 + DTI >= 0.15
    - Case 2: DTI >= 0.3 + additional_risk
    - Case 3: Delayed > 15 + additional_risk
    - Case 4: Utilization > 0.5 + additional_risk
    - Case 5: Delayed > 20 (không cần điều kiện khác)
    - Case 6: DTI >= 0.4 (không cần additional_risk) - MỚI
    - Case 7: Utilization > 0.7 (không cần additional_risk)
    - Case 8: Nghề nghiệp rủi ro cao (High) + chỉ số xấu vừa phải (DTI ≥ 0.3 & Delayed ≥ 12, hoặc Util ≥ 0.7 & Delayed ≥ 10)
    
    Lý do: 
    - Tất cả 24 Poor Unknown cases có Delayed > 15 (mean=21.2, min=18, max=24)
    - Một số cases có DTI hoặc Utilization rất cao nhưng không có additional_risk
    - Case 6 và 7 cover các trường hợp DTI/Utilization cực cao (rõ ràng là Poor)
    """
    # Nếu đã có Credit_Score thì không chạy
    if "Credit_Score" in memory.facts:
        return False, None
    
    dti = memory.facts.get("DTI_Ratio", 0)
    utilization = memory.facts.get("Credit_Utilization_Ratio", 0)
    delayed = memory.facts.get("Num_of_Delayed_Payment", 0)
    num_loan = memory.facts.get("Num_of_Loan", 0)
    history_months = memory.facts.get("Credit_History_Age_Months", math.inf)
    risk = memory.facts.get("Occupation_Risk_Level")
    
    # Điều kiện Poor (nới lỏng nhưng tránh match Standard cases)
    # Case 1: Delayed quá cao (> 17) + (DTI >= 0.15 HOẶC Utilization > 0.3)
    # Thêm điều kiện để tránh match Standard cases có Delayed cao nhưng DTI thấp
    case1 = (
        delayed > 17 and
        (dti >= 0.15 or utilization > 0.3)  # Thêm điều kiện để tránh match Standard
    )
    
    # Case 1b: Delayed > 15 và DTI >= 0.15 (cover Poor → Standard cases)
    case1b = (
        delayed > 15 and
        dti >= 0.15 and
        delayed <= 17  # Trong range Standard nhưng có DTI cao
    )
    
    # Case 2: DTI cao (>= 0.3, nới lỏng từ 0.4) + additional_risk
    case2 = (
        dti >= 0.3 and
        (num_loan > 3 or history_months < 60)
    )
    
    # Case 3: Delayed > 15 + additional_risk
    case3 = (
        delayed > 15 and
        (num_loan > 3 or history_months < 60)
    )
    
    # Case 4: Utilization cao + additional_risk
    case4 = (
        utilization > 0.5 and
        (num_loan > 3 or history_months < 60)
    )
    
    # Case 5: Delayed rất cao (> 20) là đủ để là Poor (không cần điều kiện khác)
    case5 = delayed > 20
    
    # Case 6: DTI rất cao (>= 0.4) là đủ để là Poor (không cần additional_risk)
    case6 = dti >= 0.4
    
    # Case 7: Utilization rất cao (> 0.7) là đủ để là Poor (không cần additional_risk)
    # Ngưỡng 0.7 để cover các cases có Utilization cao nhưng không có additional_risk
    case7 = utilization > 0.7

    # Case 8: Nghề nghiệp rủi ro cao + chỉ số trung bình nhưng đáng lo
    case8 = (
        risk == "High" and
        (
            (dti >= 0.3 and delayed >= 12) or
            (utilization >= 0.7 and delayed >= 10)
        )
    )
    
    if case1 or case1b or case2 or case3 or case4 or case5 or case6 or case7 or case8:
        updated = memory.upsert_fact("Credit_Score", "Poor", "R_CS_P")
        return updated, "R_CS_P" if updated else (False, None)
    return False, None


RULE_EXECUTORS = {
    "R_DTI": rule_dti_ratio,
    "R_CU": rule_credit_utilization,
    "R_P1": rule_payment_parser,
    "R_OCC_PROFILE": rule_occupation_profile,
    "R_CS_G": rule_credit_score_good,
    "R_CS_S": rule_credit_score_standard,  # Thêm rule cho Standard
    "R_CS_P": rule_credit_score_poor,
}


# ---------------------------------------------------------------------------
# Inference Engine
# ---------------------------------------------------------------------------


class InferenceEngine:
    def __init__(self, kb_client: KnowledgeBaseClient):
        self.kb = kb_client

    def solve(self, problem_id: str) -> InferenceResult:
        problem = self.kb.fetch_problem(problem_id)
        rules = self.kb.fetch_rules() or []
        existing = {rule["name"] for rule in rules} if rules else set()
        for name in RULE_EXECUTORS:
            if name not in existing:
                rules.append({"name": name})
        memory = WorkingMemory()

        self._initialize_memory(problem, memory)
        self._derive_func_results(problem, memory)

        goal_key = problem["goal"].get("target", "Credit_Score")
        if goal_key in memory.facts:
            return InferenceResult(True, goal_key, memory.facts[goal_key], memory.steps)

        success = self._forward_chain(memory, rules, goal_key)
        if success:
            return InferenceResult(True, goal_key, memory.facts.get(goal_key), memory.steps)

        missing = [goal_key] if goal_key not in memory.facts else []
        return InferenceResult(False, goal_key, None, memory.steps, missing)

    @staticmethod
    def _initialize_memory(problem: Dict[str, Any], memory: WorkingMemory) -> None:
        for obj in problem["objects"]:
            props = obj.get("props", {})
            for key, value in props.items():
                memory.facts.setdefault(key, value)

        for fact in problem["facts"]:
            memory.upsert_fact(fact["statement"], fact["value"], fact.get("derived_by", "Fact"))
            # Cũng đưa vào alias nếu statement có dạng KEY = ...
            if "=" in fact["statement"]:
                key = fact["statement"].split("=")[0].strip()
                memory.facts.setdefault(key, fact["value"])

    @staticmethod
    def _derive_func_results(problem: Dict[str, Any], memory: WorkingMemory) -> None:
        for func in problem["func_results"]:
            output = func.get("output")
            if output is None and func.get("output_json"):
                output = func["output_json"]
            memory.upsert_fact(func["name"], output, func["name"])

        # Nếu thiếu các kết quả chuẩn hóa, tự gọi hàm từ FUNC_REGISTRY
        age_raw = memory.facts.get("Credit_History_Age")
        if age_raw and "Credit_History_Age_Months" not in memory.facts:
            value = FUNC_REGISTRY["Age_Norm"](age_raw)
            if value is not None:
                memory.upsert_fact("Credit_History_Age_Months", value, "Age_Norm")

        if "Payment_Behaviour" in memory.facts:
            rule_payment_parser(memory)

        # Tiền xử lý thông tin nghề nghiệp để các rule khác sử dụng
        rule_occupation_profile(memory)

    def _forward_chain(self, memory: WorkingMemory, rules: List[Dict[str, Any]], goal_key: str) -> bool:
        max_iterations = 20
        for _ in range(max_iterations):
            if goal_key in memory.facts:
                return True
            progress = False
            for rule in rules:
                executor = RULE_EXECUTORS.get(rule["name"])
                if not executor:
                    continue
                updated, _ = executor(memory)
                if updated:
                    progress = True
            if not progress:
                break
        return goal_key in memory.facts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run inference engine for a Problem ID.")
    parser.add_argument("--problem", required=True, help="Problem ID (e.g., PROB-001)")
    args = parser.parse_args()

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "12345678")

    kb_client = KnowledgeBaseClient(uri, user, password)
    engine = InferenceEngine(kb_client)

    try:
        result = engine.solve(args.problem)
        print(f"Goal: {result.goal}")
        print(f"Success: {result.success}")
        if result.value:
            print(f"Value: {result.value}")
        if result.missing_facts:
            print(f"Missing facts: {result.missing_facts}")
        print("\nSolution steps:")
        for idx, step in enumerate(result.steps, start=1):
            print(f"  Bước {idx}: {step}")
    finally:
        kb_client.close()


if __name__ == "__main__":
    main()

