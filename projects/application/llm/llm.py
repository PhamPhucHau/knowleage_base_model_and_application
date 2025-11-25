"""
Local LLM helper module (Ollama llama3) for explaining credit score factors.

Usage example:
    from application.llm.llm import CreditLLM

    llm = CreditLLM()
    explanation = llm.explain_credit_profile(
        person_id="Scientist",
        facts={"DTI_Ratio": 0.042, "Credit_Utilization_Ratio": 0.27},
        steps=[
            "R_DTI ⇒ DTI_Ratio = 0.042",
            "R_CU ⇒ Credit_Utilization_Ratio = 0.27",
        ],
    )
    print(explanation)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import requests


def _format_facts(facts: Dict[str, float | str | int | bool]) -> str:
    lines = []
    for key, value in facts.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _format_steps(steps: Iterable[str]) -> str:
    return "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(steps))


def _build_occupation_context(facts: Dict[str, float | str | int | bool]) -> str:
    """Summarize occupation-related knowledge to human-friendly text."""
    occupation = facts.get("Occupation") or facts.get("occupation")
    if not occupation:
        return ""

    occupation = str(occupation)
    risk_level = facts.get("Occupation_Risk_Level")

    ratios = {}
    for key in ("Occupation_Good_Ratio", "Occupation_Standard_Ratio", "Occupation_Poor_Ratio"):
        if key in facts:
            label = key.replace("Occupation_", "").replace("_Ratio", "")
            ratios[label] = facts[key]

    parts: List[str] = [f"- Nghề nghiệp: {occupation}."]
    if risk_level:
        risk_map = {
            "High": "có mức rủi ro cao hơn mức trung bình",
            "Medium": "có mức rủi ro trung bình",
            "Low": "có xu hướng an toàn",
            "Stable": "rất ổn định và ít rủi ro",
        }
        risk_text = risk_map.get(str(risk_level), f"mức rủi ro {risk_level}")
        parts.append(f"- Nhóm rủi ro nghề nghiệp: {risk_text}.")

    if ratios:
        ratio_text = ", ".join(
            f"{label}: {value:.1f}%" for label, value in ratios.items() if isinstance(value, (int, float))
        )
        if ratio_text:
            parts.append(f"- Thống kê lịch sử điểm tín dụng theo nghề: {ratio_text}.")

    parts.append(
        "- Khi giải thích kết quả, hãy liên hệ các quy tắc phù hợp cho nghề này "
        "(ví dụ: nghề ổn định có thể được nới lỏng điều kiện, nghề rủi ro cao cần khắt khe hơn)."
    )
    return "\n".join(parts)


@dataclass
class CreditLLM:
    base_url: str = "http://localhost:11434/api/generate"
    model: str = "llama3"
    temperature: float = 0.1
    max_tokens: int = 512
    system_prompt: str = field(
        default=(
            "You are an expert financial analyst. "
            "Explain credit score outcomes in Vietnamese with clear steps. "
            "Highlight which facts increase or decrease risk, and mention "
            "transparent reasoning based on the given rule trace."
        )
    )

    def _call_llm(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": self.system_prompt,
            "temperature": self.temperature,
            "options": {
                "num_predict": self.max_tokens,
            },
            "stream": False,
        }
        response = requests.post(self.base_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "response" in data:
            return data["response"].strip()
        # Fallback for streaming-style concatenated JSON lines
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                return parsed.get("response", "").strip()
            except json.JSONDecodeError:
                return data.strip()
        return json.dumps(data, ensure_ascii=False)

    def explain_credit_profile(
        self,
        person_id: str,
        facts: Dict[str, float | str | int | bool],
        steps: Optional[List[str]] = None,
        expected_score: Optional[str] = None,
    ) -> str:
        """Generate natural-language explanation for credit score factors."""

        prompt_parts = [
            f"Đánh giá hồ sơ tín dụng của khách hàng: {person_id}.",
            "Các facts quan trọng:",
            _format_facts(facts),
        ]

        occupation_context = _build_occupation_context(facts)
        if occupation_context:
            prompt_parts.append("\nThông tin nghề nghiệp & tri thức bổ sung:")
            prompt_parts.append(occupation_context)

        if steps:
            prompt_parts.append("\nChuỗi suy luận từ bộ máy suy luận:")
            prompt_parts.append(_format_steps(steps))
        if expected_score:
            prompt_parts.append(f"\nĐiểm tín dụng kỳ vọng (goal): {expected_score}.")
        prompt_parts.append(
            "\nHãy tóm tắt các yếu tố làm tăng/giảm rủi ro, kết luận ngắn gọn."
        )

        prompt = "\n".join(prompt_parts)
        return self._call_llm(prompt)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run local LLM explanation.")
    parser.add_argument("--person", default="DemoUser")
    parser.add_argument("--facts", nargs="*", default=["DTI_Ratio=0.05", "Credit_Utilization=0.1"])
    parser.add_argument("--steps", nargs="*", default=[])
    parser.add_argument("--expected_score", default=None)
    args = parser.parse_args()

    facts_dict: Dict[str, str] = {}
    for item in args.facts:
        if "=" in item:
            key, value = item.split("=", 1)
            facts_dict[key] = value

    llm = CreditLLM()
    explanation = llm.explain_credit_profile(
        person_id=args.person,
        facts=facts_dict,
        steps=args.steps,
        expected_score=args.expected_score,
    )
    print(explanation)


if __name__ == "__main__":
    main()
