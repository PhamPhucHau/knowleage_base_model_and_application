"""
BƯỚC 4 — Định nghĩa Ops, Funcs, Rules và nạp vào Neo4j.

Script này kết nối tới Neo4j (tham khảo cấu hình trong insertdata.py) để:
    1. Tạo constraint/index cho Operator, Function, Rule.
    2. Khởi tạo tập Toán tử (Ops = O(1) ∪ O(2)).
    3. Khởi tạo tập Hàm (Funcs).
    4. Khởi tạo tập Luật (Rules) gồm RuleEquation, RuleDeduce, RuleGenerate.
    5. Tạo quan hệ Rule-Operator và Rule-Function để phục vụ suy luận.

Chạy script:
    $ python op_func.py

Hoặc override thông tin kết nối bằng biến môi trường:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

from neo4j import GraphDatabase


# =============================
# Khai báo dữ liệu miền tri thức
# =============================

OPS: List[Dict[str, Any]] = [
    {
        "name": "Addition",
        "symbol": "+",
        "arity": 2,
        "category": "O(2)",
        "description": "Cộng hai đại lượng tài chính",
        "applications": [
            "Monthly_Balance",
            "Credit_Score_Calc",
        ],
    },
    {
        "name": "Subtraction",
        "symbol": "-",
        "arity": 2,
        "category": "O(2)",
        "description": "Trừ đại lượng thứ hai khỏi đại lượng thứ nhất",
        "applications": [
            "Monthly_Balance",
        ],
    },
    {
        "name": "Multiplication",
        "symbol": "×",
        "arity": 2,
        "category": "O(2)",
        "description": "Nhân hai đại lượng để chuẩn hóa/scale chỉ số",
        "applications": [
            "Credit_Score_Calc",
        ],
    },
    {
        "name": "Division",
        "symbol": "÷",
        "arity": 2,
        "category": "O(2)",
        "description": "Chia đại lượng thứ nhất cho đại lượng thứ hai",
        "applications": [
            "DTI_Ratio",
            "Credit_Utilization_Ratio",
        ],
    },
    {
        "name": "SquareRoot",
        "symbol": "sqrt",
        "arity": 1,
        "category": "O(1)",
        "description": "Tính căn bậc hai phục vụ chuẩn hóa độ lệch",
        "applications": [
            "Credit_Score_Calc",
        ],
    },
    {
        "name": "Absolute",
        "symbol": "abs",
        "arity": 1,
        "category": "O(1)",
        "description": "Lấy trị tuyệt đối để giữ giá trị dương",
        "applications": [
            "Credit_Score_Calc",
        ],
    },
]


FUNCS: List[Dict[str, Any]] = [
    {
        "func_id": "FUNC-001",
        "name": "Age_Norm",
        "description": "Chuẩn hóa Credit_History_Age thành số tháng để phục vụ các luật Age-related.",
        "inputs": ["Credit_History_Age"],
        "output": "Credit_History_Age_Months",
        "event_type": "Fu.2-Normalization",
        "signature": "Age_Norm(Credit_History_Age:str) -> months:int",
        "logic_ref": "rules.funcs.age_norm",
        "data_source": ["datasets/Data Clean.xlsx::Credit_History_Age"],
    },
    {
        "func_id": "FUNC-002",
        "name": "Score_Classifier",
        "description": "Chuẩn hóa Credit_Score thành ontology CreditScoreCategory.",
        "inputs": ["Credit_Score"],
        "output": "CreditScoreCategory",
        "event_type": "Fu.2-Classification",
        "signature": "Score_Classifier(Credit_Score:str) -> category:str",
        "logic_ref": "rules.funcs.score_classifier",
        "data_source": ["datasets/Data Clean.xlsx::Credit_Score"],
    },
    {
        "func_id": "FUNC-003",
        "name": "Payment_Behavior_Parser",
        "description": "Tách Payment_Behaviour thành Spending_Level và Value_Level.",
        "inputs": ["Payment_Behaviour"],
        "output": "Spending_Level/Value_Level",
        "event_type": "Fu.2-Extraction",
        "signature": "Payment_Behavior_Parser(Payment_Behaviour:str) -> dict",
        "logic_ref": "rules.funcs.payment_behavior_parser",
        "data_source": ["datasets/Data Clean.xlsx::Payment_Behaviour"],
    },
    {
        "func_id": "FUNC-004",
        "name": "Credit_Score_Calc",
        "description": "Hàm tổng hợp tính Credit_Score dựa trên các tỷ lệ tài chính đã chuẩn hóa.",
        "inputs": [
            "Annual_Income",
            "Outstanding_Debt",
            "DTI_Ratio",
            "Credit_Utilization_Ratio",
            "Num_of_Delayed_Payment",
            "Spending_Level",
            "Value_Level",
            "Num_of_Loan",
        ],
        "output": "Credit_Score",
        "event_type": "Fu.2-Compute",
        "signature": "Credit_Score_Calc(financial_dict:dict) -> score:float",
        "logic_ref": "rules.funcs.credit_score_calc",
        "data_source": [
            "datasets/Data Clean.xlsx::Annual_Income",
            "datasets/Data Clean.xlsx::Outstanding_Debt",
            "Derived::DTI_Ratio",
            "Derived::Credit_Utilization_Ratio",
        ],
    },
]


RULES: List[Dict[str, Any]] = [
    {
        "name": "R_MB",
        "rule_type": "RuleEquation",
        "category": "FinancialDerivedMetric",
        "description": "Luật tính Monthly Balance từ thu nhập và chi phí định kỳ",
        "expression": "Monthly_Balance = Monthly_Inhand_Salary - Total_EMI_per_month - Amount_invested_monthly",
        "premises": [
            "I1.Monthly_Inhand_Salary known",
            "I1.Total_EMI_per_month known",
            "I1.Amount_invested_monthly known",
        ],
        "conclusion": "I1.Monthly_Balance computed",
        "uses_ops": ["Subtraction"],
    },
    {
        "name": "R_DTI",
        "rule_type": "RuleEquation",
        "category": "FinancialDerivedMetric",
        "description": "Luật tính Debt-to-Income Ratio",
        "expression": "DTI_Ratio = Outstanding_Debt / Annual_Income",
        "premises": [
            "I1.Outstanding_Debt known",
            "I1.Annual_Income known",
        ],
        "conclusion": "I1.DTI_Ratio computed",
        "uses_ops": ["Division"],
    },
    {
        "name": "R_CU",
        "rule_type": "RuleEquation",
        "category": "FinancialDerivedMetric",
        "description": "Luật tính Credit Utilization Ratio giản lược",
        "expression": "Credit_Utilization_Ratio = Outstanding_Debt / (Num_Credit_Card × Avg_Limit)",
        "premises": [
            "I1.Outstanding_Debt known",
            "I1.Num_Credit_Card known",
            "Average limit estimated",
        ],
        "conclusion": "I1.Credit_Utilization_Ratio computed",
        "uses_ops": ["Division", "Multiplication"],
    },
    {
        "name": "R_P1",
        "rule_type": "RuleDeduce",
        "category": "BehaviourInference",
        "description": "Tách hành vi chi tiêu thành Spending/Value levels",
        "premises": ["I1.Payment_Behaviour = 'High_spent_Small_value_payments'"],
        "conclusion": "I1.Spending_Level = 'High' ∧ I1.Value_Level = 'Small'",
        "uses_funcs": ["Payment_Behavior_Parser"],
    },
    {
        "name": "R_D1",
        "rule_type": "RuleDeduce",
        "category": "RiskAssessment",
        "description": "Đánh giá rủi ro trễ hạn dựa trên số lần trễ và hành vi chi tiêu",
        "premises": [
            "I1.Num_of_Delayed_Payment > 5",
            "I1.Spending_Level = 'High'",
        ],
        "conclusion": "I1.Credit_Risk = 'High'",
    },
    {
        "name": "R_CS_P",
        "rule_type": "RuleDeduce",
        "category": "CreditScorePrediction",
        "description": "Suy diễn Credit Score = Poor",
        "premises": [
            "I1.DTI_Ratio ≥ 0.4",
            "I1.Num_of_Loan > 3",
            "I1.Credit_History_Age < 5 (years)",
        ],
        "conclusion": "I1.Credit_Score = 'Poor'",
        "uses_ops": ["Division"],
        "uses_funcs": ["Age_Norm"],
    },
    {
        "name": "R_CS_G",
        "rule_type": "RuleDeduce",
        "category": "CreditScorePrediction",
        "description": "Suy diễn Credit Score = Good",
        "premises": [
            "I1.DTI_Ratio ≤ 0.1",
            "I1.Credit_Utilization_Ratio ≤ 0.1",
            "I1.Num_of_Delayed_Payment = 0",
        ],
        "conclusion": "I1.Credit_Score = 'Good'",
        "uses_ops": ["Division"],
    },
    {
        "name": "R_G1",
        "rule_type": "RuleGenerate",
        "category": "ProfileGeneration",
        "description": "Sinh đối tượng Hồ sơ tín dụng ưu tú",
        "premises": [
            "I1.Credit_Score = 'Good'",
            "I1.Occupation = 'Scientist'",
        ],
        "conclusion": "∃H: PremiumCreditProfile(H.owner = I1)",
        "creates_entity": "PremiumCreditProfile",
    },
]


# =============================
# Lớp thực thi
# =============================

@dataclass
class KnowledgeSeeder:
    uri: str
    user: str
    password: str
    driver: GraphDatabase.driver = field(init=False)

    def __post_init__(self) -> None:
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        self.driver.close()

    # ---------- public API ----------
    def run(self) -> None:
        print("Bắt đầu nạp Ops/Funcs/Rules vào Neo4j...")
        with self.driver.session() as session:
            self._create_constraints(session)
            self._seed_operators(session)
            self._seed_functions(session)
            self._seed_rules(session)
            self._link_rules(session)
        print("✓ Hoàn tất nạp tri thức bước 4.")

    # ---------- private helpers ----------
    def _create_constraints(self, session) -> None:
        statements = [
            "CREATE CONSTRAINT operator_name IF NOT EXISTS FOR (o:Operator) REQUIRE o.name IS UNIQUE",
            "CREATE CONSTRAINT function_name IF NOT EXISTS FOR (f:Function) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT rule_name IF NOT EXISTS FOR (r:Rule) REQUIRE r.name IS UNIQUE",
        ]
        for stmt in statements:
            session.execute_write(lambda tx, q=stmt: tx.run(q))

    def _seed_operators(self, session) -> None:
        query = """
        UNWIND $operators AS op
        MERGE (o:Operator {name: op.name})
        SET o.symbol = op.symbol,
            o.arity = op.arity,
            o.category = op.category,
            o.description = op.description,
            o.applications = op.applications
        """
        session.execute_write(lambda tx: tx.run(query, operators=OPS))
        print(f"  • Đã nạp {len(OPS)} Operator")

    def _seed_functions(self, session) -> None:
        query = """
        UNWIND $funcs AS func
        MERGE (f:Function {name: func.name})
        SET f.description = func.description,
            f.inputs = func.inputs,
            f.output = func.output,
            f.event_type = func.event_type,
            f.func_id = func.func_id,
            f.signature = func.signature,
            f.logic_ref = func.logic_ref,
            f.data_source = func.data_source
        """
        session.execute_write(lambda tx: tx.run(query, funcs=FUNCS))
        print(f"  • Đã nạp {len(FUNCS)} Function")

    def _seed_rules(self, session) -> None:
        query = """
        UNWIND $rules AS rule
        MERGE (r:Rule {name: rule.name})
        SET r.rule_type = rule.rule_type,
            r.category = rule.category,
            r.description = rule.description,
            r.expression = rule.expression,
            r.premises = rule.premises,
            r.conclusion = rule.conclusion,
            r.creates_entity = rule.creates_entity
        """
        session.execute_write(lambda tx: tx.run(query, rules=RULES))
        print(f"  • Đã nạp {len(RULES)} Rule")

    def _link_rules(self, session) -> None:
        def link_rule_operator(tx, rule_name: str, op_name: str) -> None:
            tx.run(
                """
                MATCH (r:Rule {name: $rule_name})
                MATCH (o:Operator {name: $op_name})
                MERGE (r)-[:USES_OPERATOR]->(o)
                """,
                rule_name=rule_name,
                op_name=op_name,
            )

        def link_rule_function(tx, rule_name: str, func_name: str) -> None:
            tx.run(
                """
                MATCH (r:Rule {name: $rule_name})
                MATCH (f:Function {name: $func_name})
                MERGE (r)-[:USES_FUNCTION]->(f)
                """,
                rule_name=rule_name,
                func_name=func_name,
            )

        for rule in RULES:
            for op_name in rule.get("uses_ops", []):
                session.execute_write(link_rule_operator, rule["name"], op_name)
            for func_name in rule.get("uses_funcs", []):
                session.execute_write(link_rule_function, rule["name"], func_name)
        print("  • Đã tạo quan hệ Rule-Operator và Rule-Function")


def main() -> None:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "12345678")

    seeder = KnowledgeSeeder(uri, user, password)
    try:
        seeder.run()
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
