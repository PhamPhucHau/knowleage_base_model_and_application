"""
LLM-based explainer for inference traces using local Ollama (llama3).

Sử dụng kỹ thuật prompt engineering để tạo giải thích tự nhiên bằng tiếng Việt
cho quá trình suy luận điểm tín dụng.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from application.llm.llm import CreditLLM


@dataclass
class LLMExplainer:
    """Wrapper cho CreditLLM với prompt engineering tối ưu cho inference traces."""
    
    def __init__(self, base_url: str = "http://localhost:11434/api/generate", model: str = "llama3"):
        self.llm = CreditLLM()
        self.llm.base_url = base_url
        self.llm.model = model
        self.llm.temperature = 0.2  # Thấp hơn để ổn định hơn
        self.llm.max_tokens = 800  # Tăng để có giải thích đầy đủ hơn
    
    def _parse_steps(self, steps: List[str]) -> Dict[str, Any]:
        """Parse inference steps để trích xuất thông tin quan trọng."""
        parsed = {
            "observations": [],
            "calculations": [],
            "rules_applied": [],
            "final_score": None,
        }
        
        for step in steps:
            # Pattern: "Source ⇒ Key = Value"
            match = re.match(r"(.+?)\s*⇒\s*(.+?)\s*=\s*(.+)", step)
            if not match:
                continue
            
            source, key, value = match.groups()
            
            # Phân loại theo source
            if source == "Observation":
                parsed["observations"].append({"key": key, "value": value})
            elif source.startswith("R_"):
                parsed["rules_applied"].append({"rule": source, "key": key, "value": value})
                if key == "Credit_Score":
                    parsed["final_score"] = value
            elif source.endswith("_Norm") or source.endswith("_Parser") or source.endswith("_Classifier"):
                parsed["calculations"].append({"function": source, "key": key, "value": value})
        
        return parsed
    
    def _build_structured_prompt(self, steps: List[str], credit_score: Optional[str] = None) -> str:
        """Xây dựng prompt có cấu trúc với kỹ thuật prompt engineering."""
        
        parsed = self._parse_steps(steps)
        
        # Map key names to Vietnamese
        key_map = {
            "Person_ID": "Mã khách hàng",
            "Annual_Income": "Thu nhập hàng năm",
            "Outstanding_Debt": "Tổng nợ hiện tại",
            "Num_of_Loan": "Số khoản vay",
            "Num_of_Delayed_Payment": "Số lần trả muộn",
            "Credit_History_Age": "Lịch sử tín dụng",
            "Credit_History_Age_Months": "Lịch sử tín dụng (tháng)",
            "DTI_Ratio": "Tỷ lệ nợ trên thu nhập (DTI)",
            "Credit_Utilization_Ratio": "Tỷ lệ sử dụng tín dụng",
            "Payment_Behaviour": "Hành vi thanh toán",
            "Spending_Level": "Mức độ chi tiêu",
            "Value_Level": "Mức giá trị giao dịch",
            "Credit_Score": "Điểm tín dụng",
        }
        
        # Map rule names to Vietnamese
        rule_map = {
            "R_DTI": "Luật tính tỷ lệ nợ trên thu nhập",
            "R_CU": "Luật tính tỷ lệ sử dụng tín dụng",
            "R_P1": "Luật phân tích hành vi chi tiêu",
            "R_CS_G": "Luật suy diễn điểm tín dụng tốt",
            "R_CS_P": "Luật suy diễn điểm tín dụng kém",
            "R_D1": "Luật đánh giá rủi ro trễ hạn",
        }
        
        # Xây dựng prompt theo cấu trúc
        prompt_parts = [
            "## BẠN LÀ CHUYÊN GIA PHÂN TÍCH TÀI CHÍNH",
            "",
            "Nhiệm vụ: Giải thích quá trình suy luận điểm tín dụng bằng tiếng Việt một cách rõ ràng, dễ hiểu.",
            "",
            "### THÔNG TIN ĐẦU VÀO:",
        ]
        
        # Thông tin quan sát
        if parsed["observations"]:
            prompt_parts.append("\n**Dữ liệu đầu vào:**")
            for obs in parsed["observations"]:
                key_vn = key_map.get(obs["key"], obs["key"])
                value = obs["value"]
                # Format số
                try:
                    num_val = float(value)
                    if num_val >= 1000:
                        value = f"{num_val:,.0f}"
                    elif 0 < num_val < 1:
                        value = f"{num_val:.2%}" if "Ratio" in obs["key"] or "Utilization" in obs["key"] else f"{num_val:.5f}"
                except (ValueError, TypeError):
                    pass
                prompt_parts.append(f"- {key_vn}: {value}")
        
        # Các phép tính
        if parsed["calculations"]:
            prompt_parts.append("\n**Các phép tính chuẩn hóa:**")
            for calc in parsed["calculations"]:
                key_vn = key_map.get(calc["key"], calc["key"])
                prompt_parts.append(f"- {calc['function']} → {key_vn} = {calc['value']}")
        
        # Các luật được áp dụng
        if parsed["rules_applied"]:
            prompt_parts.append("\n**Các luật suy luận được áp dụng:**")
            for rule_info in parsed["rules_applied"]:
                rule_vn = rule_map.get(rule_info["rule"], rule_info["rule"])
                key_vn = key_map.get(rule_info["key"], rule_info["key"])
                prompt_parts.append(f"- {rule_vn} → {key_vn} = {rule_info['value']}")
        
        # Kết quả cuối cùng
        final_score = credit_score or parsed["final_score"]
        if final_score:
            score_vn = {"Good": "Tốt", "Poor": "Kém", "Standard": "Trung bình"}.get(str(final_score), str(final_score))
            prompt_parts.append(f"\n**KẾT QUẢ:** Điểm tín dụng = {score_vn}")
        
        # Hướng dẫn output
        prompt_parts.extend([
            "",
            "### YÊU CẦU GIẢI THÍCH:",
            "",
            "Hãy viết một đoạn giải thích tự nhiên bằng tiếng Việt với cấu trúc sau:",
            "",
            "1. **Tóm tắt tình hình tài chính:** Mô tả ngắn gọn về hồ sơ (thu nhập, nợ, lịch sử).",
            "",
            "2. **Phân tích các chỉ số quan trọng:**",
            "   - Tỷ lệ nợ trên thu nhập (DTI): Giải thích ý nghĩa và đánh giá (tốt/xấu).",
            "   - Tỷ lệ sử dụng tín dụng: Giải thích và đánh giá.",
            "   - Lịch sử thanh toán: Số lần trả muộn và ý nghĩa.",
            "",
            "3. **Quá trình suy luận:** Giải thích từng bước logic mà hệ thống đã thực hiện.",
            "",
            "4. **Kết luận:** Tóm tắt lý do tại sao điểm tín dụng là [Good/Poor/Standard] và các yếu tố chính ảnh hưởng.",
            "",
            "Lưu ý:",
            "- Sử dụng ngôn ngữ tự nhiên, dễ hiểu cho người không chuyên.",
            "- Nhấn mạnh các yếu tố tích cực và tiêu cực.",
            "- Giải thích rõ ràng mối quan hệ nhân quả giữa các chỉ số và kết quả.",
            "- Độ dài khoảng 200-300 từ.",
        ])
        
        return "\n".join(prompt_parts)
    
    def explain_inference_trace(
        self, 
        steps: List[str], 
        credit_score: Optional[str] = None,
        person_id: Optional[str] = None
    ) -> str:
        """
        Giải thích inference trace bằng tiếng Việt sử dụng LLM.
        
        Args:
            steps: Danh sách các bước suy luận
            credit_score: Điểm tín dụng cuối cùng (nếu có)
            person_id: Mã khách hàng (nếu có)
        
        Returns:
            Giải thích tự nhiên bằng tiếng Việt
        """
        # Xây dựng prompt có cấu trúc
        prompt = self._build_structured_prompt(steps, credit_score)
        
        # Gọi LLM với system prompt tối ưu
        self.llm.system_prompt = (
            "Bạn là một chuyên gia phân tích tài chính và tín dụng có kinh nghiệm. "
            "Nhiệm vụ của bạn là giải thích quá trình đánh giá điểm tín dụng một cách "
            "rõ ràng, chính xác và dễ hiểu bằng tiếng Việt. Bạn cần phân tích các chỉ số "
            "tài chính, giải thích logic suy luận, và đưa ra kết luận có căn cứ."
        )
        
        try:
            explanation = self.llm._call_llm(prompt)
            return explanation.strip()
        except Exception as e:
            # Fallback nếu LLM không khả dụng
            return (
                f"⚠️ Không thể kết nối với LLM để tạo giải thích tự nhiên. "
                f"Lỗi: {str(e)}\n\n"
                f"Xem chi tiết các bước suy luận ở phần dưới."
            )
