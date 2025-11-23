"""
FastAPI server exposing credit score inference endpoints.

- POST /api/v1/predict/manual
    Accepts personal finance inputs and returns reasoning trace.
- GET /api/v1/health
    Liveness check.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from application.services.manual_solver import (  # noqa: E402
    ManualInferenceRequest,
    run_manual_inference,
)
from inference.engine import InferenceEngine, KnowledgeBaseClient  # noqa: E402

app = FastAPI(title="Credit Knowledge API", version="1.0")


class ManualPredictPayload(BaseModel):
    person_id: str = Field(..., description="Unique identifier for the applicant")
    annual_income: float = Field(..., gt=0)
    outstanding_debt: float = Field(..., ge=0)
    num_of_loan: int = Field(..., ge=0)
    credit_history_age: str = Field(..., description="e.g. '12 Years and 6 Months'")
    num_of_delayed_payment: int = 0
    payment_behaviour: Optional[str] = None
    spending_level: Optional[str] = Field(None, description="High/Low")
    value_level: Optional[str] = Field(None, description="Large/Small")
    avg_credit_limit: Optional[float] = None
    interest_rate: Optional[float] = None
    payment_of_min_amount: Optional[str] = None
    delay_from_due_date: Optional[float] = None
    num_credit_card: Optional[float] = None
    monthly_balance: Optional[float] = None
    total_emi_per_month: Optional[float] = None
    amount_invested_monthly: Optional[float] = None
    monthly_inhand_salary: Optional[float] = None
    age: Optional[float] = None
    mode: str = Field("ontology", description="ontology or decision_tree")

    @validator("spending_level")
    def _normalize_spending(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return value.capitalize()
        return value

    @validator("value_level")
    def _normalize_value(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return value.capitalize()
        return value


@lru_cache
def get_inference_engine() -> InferenceEngine:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "12345678")
    kb_client = KnowledgeBaseClient(uri, user, password)
    return InferenceEngine(kb_client)


@app.get("/api/v1/health")
def health_check() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/v1/predict/manual")
def predict_manual(payload: ManualPredictPayload) -> Dict[str, Any]:
    if payload.mode == "decision_tree":
        from application.services.decision_solver import run_decision_inference

        result = run_decision_inference(payload.dict())
        return {
            "person_id": payload.person_id,
            "success": result.success,
            "credit_score": result.credit_score,
            "steps": result.steps,
            "missing_facts": [] if result.success else ["Decision tree did not match"],
            "facts": result.facts,
            "matched_rule": result.matched_rule,
            "mode": "decision_tree",
        }
    request = ManualInferenceRequest(**payload.dict())
    result = run_manual_inference(request)
    return {
        "person_id": payload.person_id,
        "success": result.success,
        "credit_score": result.credit_score,
        "steps": result.steps,
        "missing_facts": result.missing_facts,
        "facts": result.facts,
        "mode": "ontology",
    }


@app.post("/api/v1/predict/problem/{problem_id}")
def predict_problem(problem_id: str) -> Dict[str, Any]:
    engine = get_inference_engine()
    try:
        inference_result = engine.solve(problem_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "problem_id": problem_id,
        "success": inference_result.success,
        "credit_score": inference_result.value,
        "steps": inference_result.steps,
        "missing_facts": inference_result.missing_facts,
    }


def main() -> None:
    import uvicorn

    uvicorn.run("application.api.server:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()

