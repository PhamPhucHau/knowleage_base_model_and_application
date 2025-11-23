"""
Decision tree solver service wrapping engine_v2 for API usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict

from inference.engine_v2 import DecisionRuleEngine
from rules.funcs_v2 import LABEL_MAPPING, facts_from_row
from rules.op_func_v2 import DECISION_TREE_RULES


@lru_cache
def get_decision_engine() -> DecisionRuleEngine:
    return DecisionRuleEngine(DECISION_TREE_RULES)


@dataclass
class DecisionInferenceResult:
    success: bool
    credit_score: str | None
    steps: list[str]
    facts: Dict[str, Any]
    matched_rule: str | None


def run_decision_inference(payload: Dict[str, Any]) -> DecisionInferenceResult:
    engine = get_decision_engine()
    facts = facts_from_row(payload)
    evaluation = engine.evaluate(facts)
    credit_score = evaluation.label
    steps = []
    if evaluation.matched:
        steps.append(f"{evaluation.rule_name} ⇒ Credit_Score = {credit_score}")
    else:
        steps.append("Không luật nào khớp.")
    return DecisionInferenceResult(
        success=evaluation.matched,
        credit_score=credit_score,
        steps=steps,
        facts=facts,
        matched_rule=evaluation.rule_name if evaluation.matched else None,
    )

