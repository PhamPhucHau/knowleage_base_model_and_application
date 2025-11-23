"""
Version 2 Ops/Funcs/Rules derived from decision tree (Rule.txt).

This script can seed the metadata into Neo4j to keep consistency with
the integrated knowledge model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from neo4j import GraphDatabase

from rules.funcs_v2 import LABEL_MAPPING


OPS_V2: List[Dict[str, Any]] = [
    {
        "name": "LessOrEqual",
        "symbol": "<=",
        "arity": 2,
        "category": "Comparator",
        "description": "Checks if feature value is less than or equal to a threshold.",
    },
    {
        "name": "GreaterThan",
        "symbol": ">",
        "arity": 2,
        "category": "Comparator",
        "description": "Checks if feature value is greater than a threshold.",
    },
]

FUNCS_V2: List[Dict[str, Any]] = [
    {
        "func_id": "FUNC-V2-001",
        "name": "Payment_Min_Flag",
        "description": "Convert Payment_of_Min_Amount (Yes/No) into binary flag.",
        "inputs": ["Payment_of_Min_Amount"],
        "output": "Payment_of_Min_Amount_Yes",
        "logic_ref": "rules.funcs_v2.yes_no_flag",
    },
    {
        "func_id": "FUNC-V2-002",
        "name": "Occupation_Developer_Flag",
        "description": "Binary flag to indicate applicant is a Developer.",
        "inputs": ["Occupation"],
        "output": "Occupation_Developer",
        "logic_ref": "rules.funcs_v2.occupation_developer_flag",
    },
    {
        "func_id": "FUNC-V2-003",
        "name": "Credit_History_Months",
        "description": "Normalize Credit_History_Age string into total months.",
        "inputs": ["Credit_History_Age"],
        "output": "Credit_History_Months",
        "logic_ref": "rules.funcs_v2.months_from_history",
    },
]


DECISION_TREE_RULES: List[Dict[str, Any]] = [
    {
        "name": "DT_RULE_1",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", "<=", 0.5),
            ("Interest_Rate", "<=", 12.5),
            ("Num_Credit_Card", "<=", 2.5),
        ],
        "label": 0,
    },
    {
        "name": "DT_RULE_2",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", "<=", 0.5),
            ("Interest_Rate", "<=", 12.5),
            ("Num_Credit_Card", ">", 2.5),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_3",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", "<=", 0.5),
            ("Interest_Rate", ">", 12.5),
            ("Total_EMI_per_month", "<=", 280.51),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_4",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", "<=", 0.5),
            ("Interest_Rate", ">", 12.5),
            ("Total_EMI_per_month", ">", 280.51),
            ("Num_of_Loan", "<=", 1.5),
        ],
        "label": 0,
    },
    {
        "name": "DT_RULE_5",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", ">", 0.5),
            ("Interest_Rate", "<=", 20.5),
            ("Num_Credit_Card", "<=", 7.5),
            ("Delay_from_due_date", "<=", 34.5),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_6",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", ">", 0.5),
            ("Interest_Rate", "<=", 20.5),
            ("Num_Credit_Card", "<=", 7.5),
            ("Delay_from_due_date", ">", 34.5),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_7",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", ">", 0.5),
            ("Interest_Rate", "<=", 20.5),
            ("Num_Credit_Card", ">", 7.5),
            ("Num_Credit_Card", "<=", 15.5),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_8",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", ">", 0.5),
            ("Interest_Rate", ">", 20.5),
            ("Total_EMI_per_month", "<=", 21.02),
            ("Monthly_Balance", "<=", 257.71),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_9",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", ">", 0.5),
            ("Interest_Rate", ">", 20.5),
            ("Total_EMI_per_month", "<=", 21.02),
            ("Monthly_Balance", ">", 257.71),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_10",
        "conditions": [
            ("Outstanding_Debt", "<=", 1500.01),
            ("Payment_of_Min_Amount_Yes", ">", 0.5),
            ("Interest_Rate", ">", 20.5),
            ("Total_EMI_per_month", ">", 21.02),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_11",
        "conditions": [
            ("Outstanding_Debt", ">", 1500.01),
            ("Outstanding_Debt", "<=", 2696.55),
            ("Interest_Rate", "<=", 14.5),
            ("Outstanding_Debt", "<=", 1645.58),
            ("Age", "<=", 39.5),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_12",
        "conditions": [
            ("Outstanding_Debt", ">", 1500.01),
            ("Outstanding_Debt", "<=", 2696.55),
            ("Interest_Rate", "<=", 14.5),
            ("Outstanding_Debt", "<=", 1645.58),
            ("Age", ">", 39.5),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_13",
        "conditions": [
            ("Outstanding_Debt", ">", 1500.01),
            ("Outstanding_Debt", "<=", 2696.55),
            ("Interest_Rate", ">", 14.5),
            ("Credit_History_Months", "<=", 52.5),
            ("Monthly_Inhand_Salary", "<=", 4347.7),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_14",
        "conditions": [
            ("Outstanding_Debt", ">", 1500.01),
            ("Outstanding_Debt", "<=", 2696.55),
            ("Interest_Rate", ">", 14.5),
            ("Credit_History_Months", ">", 52.5),
            ("Interest_Rate", "<=", 19.5),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_15",
        "conditions": [
            ("Outstanding_Debt", ">", 2696.55),
            ("Num_Credit_Card", "<=", 9.5),
            ("Interest_Rate", "<=", 27.5),
            ("Outstanding_Debt", "<=", 2962.53),
        ],
        "label": 2,
    },
    {
        "name": "DT_RULE_16",
        "conditions": [
            ("Outstanding_Debt", ">", 2696.55),
            ("Num_Credit_Card", "<=", 9.5),
            ("Interest_Rate", "<=", 27.5),
            ("Outstanding_Debt", ">", 2962.53),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_17",
        "conditions": [
            ("Outstanding_Debt", ">", 2696.55),
            ("Num_Credit_Card", ">", 9.5),
            ("Outstanding_Debt", "<=", 2739.29),
            ("Amount_invested_monthly", "<=", 99.11),
        ],
        "label": 1,
    },
    {
        "name": "DT_RULE_18",
        "conditions": [
            ("Outstanding_Debt", ">", 2696.55),
            ("Num_Credit_Card", ">", 9.5),
            ("Outstanding_Debt", "<=", 2739.29),
            ("Amount_invested_monthly", ">", 99.11),
        ],
        "label": 1,
    },
]


@dataclass
class DecisionKnowledgeSeeder:
    uri: str
    user: str
    password: str
    driver: GraphDatabase.driver = field(init=False)

    def __post_init__(self) -> None:
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        self.driver.close()

    def run(self) -> None:
        print("Seeding v2 Ops/Funcs/Rules...")
        with self.driver.session() as session:
            self._create_constraints(session)
            self._seed_ops(session)
            self._seed_funcs(session)
            self._seed_rules(session)
        print("✓ Completed seeding v2 knowledge.")

    @staticmethod
    def _create_constraints(session) -> None:
        statements = [
            "CREATE CONSTRAINT operator_name_v2 IF NOT EXISTS FOR (o:OperatorV2) REQUIRE o.name IS UNIQUE",
            "CREATE CONSTRAINT function_name_v2 IF NOT EXISTS FOR (f:FunctionV2) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT rule_name_v2 IF NOT EXISTS FOR (r:DecisionRule) REQUIRE r.name IS UNIQUE",
        ]
        for query in statements:
            session.run(query)

    def _seed_ops(self, session) -> None:
        session.run(
            """
            UNWIND $ops AS op
            MERGE (o:OperatorV2 {name: op.name})
            SET o.symbol = op.symbol,
                o.arity = op.arity,
                o.category = op.category,
                o.description = op.description
            """,
            ops=OPS_V2,
        )

    def _seed_funcs(self, session) -> None:
        session.run(
            """
            UNWIND $funcs AS func
            MERGE (f:FunctionV2 {name: func.name})
            SET f.func_id = func.func_id,
                f.description = func.description,
                f.logic_ref = func.logic_ref,
                f.inputs = func.inputs,
                f.output = func.output
            """,
            funcs=FUNCS_V2,
        )

    def _seed_rules(self, session) -> None:
        session.run(
            """
            UNWIND $rules AS rule
            MERGE (r:DecisionRule {name: rule.name})
            SET r.conditions = rule.conditions,
                r.label = rule.label,
                r.label_name = $label_map[rule.label]
            """,
            rules=DECISION_TREE_RULES,
            label_map=LABEL_MAPPING,
        )


def main() -> None:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "12345678")
    seeder = DecisionKnowledgeSeeder(uri, user, password)
    try:
        seeder.run()
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
