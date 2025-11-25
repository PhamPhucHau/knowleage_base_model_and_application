"""
Manual inference helpers to run credit-score reasoning without Neo4j Problems.

This module reuses WorkingMemory + rule executors from inference.engine to
produce an explanation trace for ad-hoc user inputs (CLI/UI forms).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from inference.engine import RULE_EXECUTORS, WorkingMemory
from rules.funcs import FUNC_REGISTRY


@dataclass
class ManualInferenceRequest:
    person_id: str
    annual_income: float
    outstanding_debt: float
    num_of_loan: int
    credit_history_age: str
    num_of_delayed_payment: int = 0
    payment_behaviour: Optional[str] = None
    spending_level: Optional[str] = None
    value_level: Optional[str] = None
    avg_credit_limit: Optional[float] = None
    occupation: Optional[str] = None


@dataclass
class ManualInferenceResult:
    success: bool
    credit_score: Optional[Any]
    steps: List[str]
    facts: Dict[str, Any]
    missing_facts: List[str]


def _seed_observation(memory: WorkingMemory, key: str, value: Any) -> None:
    if value is not None:
        memory.upsert_fact(key, value, "Observation")


def _apply_funcs(memory: WorkingMemory) -> None:
    age_raw = memory.facts.get("Credit_History_Age")
    if age_raw and "Credit_History_Age_Months" not in memory.facts:
        val = FUNC_REGISTRY["Age_Norm"](age_raw)
        if val is not None:
            memory.upsert_fact("Credit_History_Age_Months", val, "Age_Norm")

    if "Payment_Behaviour" in memory.facts:
        result = FUNC_REGISTRY["Payment_Behavior_Parser"](memory.facts["Payment_Behaviour"])
        for key, value in result.items():
            if value:
                memory.upsert_fact(key, value, "Payment_Behavior_Parser")


def _forward_chain(memory: WorkingMemory, goal_key: str) -> bool:
    max_iterations = 20
    for _ in range(max_iterations):
        if goal_key in memory.facts:
            return True
        progress = False
        for executor in RULE_EXECUTORS.values():
            updated, _ = executor(memory)
            if updated:
                progress = True
        if not progress:
            break
    return goal_key in memory.facts


def run_manual_inference(request: ManualInferenceRequest) -> ManualInferenceResult:
    memory = WorkingMemory()

    # Seed observations
    _seed_observation(memory, "Person_ID", request.person_id)
    if request.occupation:
        _seed_observation(memory, "Occupation", request.occupation)
    _seed_observation(memory, "Annual_Income", request.annual_income)
    _seed_observation(memory, "Outstanding_Debt", request.outstanding_debt)
    _seed_observation(memory, "Num_of_Loan", request.num_of_loan)
    _seed_observation(memory, "Num_of_Delayed_Payment", request.num_of_delayed_payment)
    _seed_observation(memory, "Credit_History_Age", request.credit_history_age)

    avg_limit = request.avg_credit_limit or 1000.0
    _seed_observation(memory, "Avg_Credit_Limit", avg_limit)

    if request.payment_behaviour:
        _seed_observation(memory, "Payment_Behaviour", request.payment_behaviour)
    if request.spending_level:
        _seed_observation(memory, "Spending_Level", request.spending_level)
    if request.value_level:
        _seed_observation(memory, "Value_Level", request.value_level)

    # Derived metrics from inputs
    if request.annual_income:
        dti = request.outstanding_debt / request.annual_income
        _seed_observation(memory, "DTI_Ratio", round(dti, 5))

    if avg_limit:
        effective_loans = request.num_of_loan if request.num_of_loan and request.num_of_loan > 0 else 1
        cu = request.outstanding_debt / (effective_loans * avg_limit)
        _seed_observation(memory, "Credit_Utilization_Ratio", round(cu, 5))

    _apply_funcs(memory)

    occ_executor = RULE_EXECUTORS.get("R_OCC_PROFILE")
    if occ_executor:
        occ_executor(memory)

    success = _forward_chain(memory, goal_key="Credit_Score")
    missing = [] if success else ["Credit_Score"]
    return ManualInferenceResult(
        success=success,
        credit_score=memory.facts.get("Credit_Score"),
        steps=memory.steps,
        facts=memory.facts,
        missing_facts=missing,
    )

