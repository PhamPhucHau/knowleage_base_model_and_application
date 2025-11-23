"""
Decision-tree-based inference engine (v2) derived from Rule.txt.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from rules.funcs_v2 import LABEL_MAPPING, facts_from_row
from rules.op_func_v2 import DECISION_TREE_RULES


@dataclass
class RuleEvaluation:
    rule_name: str
    matched: bool
    label: Optional[str]
    missing_fields: List[str]


class DecisionRuleEngine:
    def __init__(self, rules: List[Dict[str, Any]]):
        self.rules = rules

    def evaluate(self, facts: Dict[str, float]) -> RuleEvaluation:
        for rule in self.rules:
            missing: List[str] = []
            satisfied = True
            for field, op, threshold in rule["conditions"]:
                value = facts.get(field)
                if value is None:
                    missing.append(field)
                    satisfied = False
                    break
                if op == "<=" and not value <= threshold:
                    satisfied = False
                    break
                if op == ">" and not value > threshold:
                    satisfied = False
                    break
            if satisfied:
                label_name = LABEL_MAPPING.get(rule["label"], str(rule["label"]))
                return RuleEvaluation(rule_name=rule["name"], matched=True, label=label_name, missing_fields=[])
        return RuleEvaluation(rule_name="None", matched=False, label=None, missing_fields=[])


def run_engine_on_row(row: Dict[str, Any], engine: DecisionRuleEngine) -> Dict[str, Any]:
    facts = facts_from_row(row)
    evaluation = engine.evaluate(facts)
    return {
        "facts": facts,
        "evaluation": evaluation,
    }


def load_dataset(limit: Optional[int] = None) -> pd.DataFrame:
    candidates = [
        Path("datasets/Data Processed.xlsx"),
        Path("datasets/Data Clean.xlsx"),
    ]
    for candidate in candidates:
        if candidate.exists():
            df = pd.read_excel(candidate)
            return df.head(limit) if limit else df
    raise FileNotFoundError("Không tìm thấy file dữ liệu Data Processed.xlsx hoặc Data Clean.xlsx")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Decision Tree Inference Engine v2")
    parser.add_argument("--row", type=int, default=0, help="Index bản ghi trong dataset để chạy inference")
    parser.add_argument("--limit", type=int, default=100, help="Số lượng bản ghi tải từ dataset")
    parser.add_argument("--facts", type=str, help="JSON string custom facts để chạy inference")
    args = parser.parse_args()

    engine = DecisionRuleEngine(DECISION_TREE_RULES)

    if args.facts:
        facts = json.loads(args.facts)
        evaluation = engine.evaluate(facts)
        print(f"Rule: {evaluation.rule_name}, label={evaluation.label}, matched={evaluation.matched}")
        return

    df = load_dataset(args.limit)
    row = df.iloc[args.row].to_dict()
    result = run_engine_on_row(row, engine)
    eval_result = result["evaluation"]
    print("=== Facts ===")
    for k, v in result["facts"].items():
        print(f"{k}: {v}")
    print("\n=== Evaluation ===")
    print(f"Matched rule: {eval_result.rule_name}")
    print(f"Label: {eval_result.label}")
    print(f"Matched: {eval_result.matched}")


if __name__ == "__main__":
    cli()
