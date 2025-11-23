"""
Seed sample Problems (O, F -> G) into Neo4j from YAML definitions.

Usage:
    $ python projects/problems/seed_problems.py

Environment overrides:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml
from neo4j import GraphDatabase


PROBLEM_FILE = Path(__file__).with_name("problems.yaml")


def load_problems() -> List[Dict[str, Any]]:
    if not PROBLEM_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file {PROBLEM_FILE}")
    data = yaml.safe_load(PROBLEM_FILE.read_text(encoding="utf-8"))
    return data.get("problems", [])


@dataclass
class ProblemSeeder:
    uri: str
    user: str
    password: str
    driver: GraphDatabase.driver = field(init=False)

    def __post_init__(self) -> None:
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        self.driver.close()

    def run(self) -> None:
        problems = load_problems()
        if not problems:
            print("Không có problem nào để seed.")
            return

        with self.driver.session() as session:
            for problem in problems:
                print(f"→ Seeding problem {problem['id']}")
                session.execute_write(self._delete_problem, problem["id"])
                session.execute_write(self._create_problem_graph, problem)
        print("✓ Hoàn tất seed Problems.")

    @staticmethod
    def _delete_problem(tx, problem_id: str) -> None:
        tx.run(
            """
            MATCH (p:Problem {problem_id: $problem_id})
            OPTIONAL MATCH (p)-[r]-()
            WITH p, collect(r) AS rels
            FOREACH (rel IN rels | DELETE rel)
            DETACH DELETE p
            """,
            problem_id=problem_id,
        )

    @staticmethod
    def _create_problem_graph(tx, problem: Dict[str, Any]) -> None:
        tx.run(
            """
            MERGE (p:Problem {problem_id: $problem_id})
            SET p.title = $title,
                p.description = $description,
                p.source_record = $source_record
            """,
            problem_id=problem["id"],
            title=problem.get("title"),
            description=problem.get("description"),
            source_record=problem.get("source_record"),
        )

        for obj in problem.get("objects", []):
            properties = obj.get("properties") or {}
            tx.run(
                """
                MATCH (p:Problem {problem_id: $problem_id})
                MERGE (o:ProblemObject {problem_id: $problem_id, object_id: $object_id})
                SET o.label = $label,
                    o += $properties
                MERGE (p)-[:HAS_OBJECT]->(o)
                """,
                problem_id=problem["id"],
                object_id=obj["object_id"],
                label=obj.get("label"),
                properties=properties,
            )

        for fact in problem.get("facts", []):
            tx.run(
                """
                MATCH (p:Problem {problem_id: $problem_id})
                MERGE (f:ProblemFact {problem_id: $problem_id, fact_id: $fact_id})
                SET f.statement = $statement,
                    f.value = $value,
                    f.derived_by = $derived_by,
                    f.uses = $uses
                MERGE (p)-[:HAS_FACT]->(f)
                """,
                problem_id=problem["id"],
                fact_id=fact["fact_id"],
                statement=fact.get("statement"),
                value=fact.get("value"),
                derived_by=fact.get("derived_by"),
                uses=fact.get("uses"),
            )

        for func in problem.get("func_results", []):
            output = func.get("output")
            if isinstance(output, (str, int, float, bool)) or output is None:
                primitive_output = output
                output_json = None
            else:
                primitive_output = None
                output_json = json.dumps(output, ensure_ascii=False)
            tx.run(
                """
                MATCH (p:Problem {problem_id: $problem_id})
                MERGE (fr:ProblemFuncResult {problem_id: $problem_id, func_id: $func_id})
                SET fr.name = $name,
                    fr.output = $output,
                    fr.output_json = $output_json
                MERGE (p)-[:USES_FUNC_RESULT]->(fr)
                """,
                problem_id=problem["id"],
                func_id=func.get("func_id"),
                name=func.get("name"),
                output=primitive_output,
                output_json=output_json,
            )

        goal = problem.get("goal")
        if goal:
            tx.run(
                """
                MATCH (p:Problem {problem_id: $problem_id})
                MERGE (g:ProblemGoal {problem_id: $problem_id, target: $target})
                SET g.type = $type,
                    g.expected_score = $expected_score,
                    g.expected_category = $expected_category
                MERGE (p)-[:HAS_GOAL]->(g)
                """,
                problem_id=problem["id"],
                target=goal.get("target"),
                type=goal.get("type"),
                expected_score=goal.get("expected_score"),
                expected_category=goal.get("expected_category"),
            )


def main() -> None:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "12345678")

    seeder = ProblemSeeder(uri, user, password)
    try:
        seeder.run()
    finally:
        seeder.close()


if __name__ == "__main__":
    main()

