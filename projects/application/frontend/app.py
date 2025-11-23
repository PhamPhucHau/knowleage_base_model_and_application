"""
Simple Streamlit UI for credit-score inference demo.

Run with:
    streamlit run projects/application/frontend/app.py
"""

from __future__ import annotations

import os
import csv
from pathlib import Path
import requests
import streamlit as st

API_URL = os.getenv("CREDIT_API_URL", "http://localhost:8000/api/v1/predict/manual")

# Đường dẫn đến các file CSV
FRONTEND_DIR = Path(__file__).parent
OCCUPATION_CSV = FRONTEND_DIR / "Occupation.csv"
PAYMENT_BEHAVIOUR_CSV = FRONTEND_DIR / "Payment_Behaviour.csv"


def load_csv_options(csv_path: Path) -> list[str]:
    """Load options từ file CSV (bỏ qua header)."""
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # Bỏ qua header
        return [row[0] for row in reader if row]


def generate_credit_history_options() -> list[str]:
    """Tạo danh sách các giá trị Credit History Age hợp lệ."""
    options = []
    # Từ 1 năm đến 40 năm
    for years in range(1, 41):
        for months in [0, 1, 3, 6, 9]:
            if months == 0:
                if years == 1:
                    options.append(f"{years} Year and {months} Months")
                else:
                    options.append(f"{years} Years and {months} Months")
            else:
                if years == 1:
                    options.append(f"{years} Year and {months} Months")
                else:
                    options.append(f"{years} Years and {months} Months")
    return options


def display_credit_score_result(score: str, score_vn: str) -> None:
    """Hiển thị kết quả Credit Score với màu phù hợp."""
    # Định nghĩa màu sắc cho từng loại
    colors = {
        "Good": {
            "bg": "#28a745",  # Màu xanh lá
            "text": "#ffffff",
            "icon": "✅",
            "border": "#1e7e34"
        },
        "Poor": {
            "bg": "#dc3545",  # Màu đỏ
            "text": "#ffffff",
            "icon": "❌",
            "border": "#c82333"
        },
        "Standard": {
            "bg": "#ff8c00",  # Màu vàng cam
            "text": "#ffffff",
            "icon": "⚠️",
            "border": "#e67e00"
        }
    }
    
    color_config = colors.get(score, {
        "bg": "#6c757d",
        "text": "#ffffff",
        "icon": "ℹ️",
        "border": "#5a6268"
    })
    
    # Tạo HTML với màu tùy chỉnh
    html = f"""
    <div style="
        background-color: {color_config['bg']};
        color: {color_config['text']};
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid {color_config['border']};
        margin: 1rem 0;
        font-size: 1.2rem;
        font-weight: bold;
    ">
        {color_config['icon']} Credit Score: {score_vn} ({score})
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Credit Score Demo", layout="centered")
    st.title("Demo dự báo Điểm Tín dụng")
    st.caption("Nhập thông tin tài chính, bấm Dự báo để xem kết quả và giải thích.")

    # Load options từ CSV
    occupation_options = load_csv_options(OCCUPATION_CSV)
    payment_behaviour_options = load_csv_options(PAYMENT_BEHAVIOUR_CSV)
    credit_history_options = generate_credit_history_options()

    with st.form("credit_form"):
        mode = st.selectbox(
            "Chế độ suy luận",
            options=["ontology", "decision_tree"],
            index=0,
            help="Chọn phương pháp suy luận: Ontology (rule-based) hoặc Decision Tree"
        )
        
        col1, col2 = st.columns(2)
        
        # Occupation selectbox
        occupation = st.selectbox(
            "Nghề nghiệp",
            options=[""] + occupation_options,
            index=0,
            help="Chọn nghề nghiệp của khách hàng"
        )
        
        person_id = st.text_input(
            "Mã khách hàng",
            value="demo_user",
            help="Mã định danh khách hàng (có thể để trống)"
        )
        
        # Financial inputs với giới hạn miền dữ liệu
        annual_income = col1.number_input(
            "Thu nhập hàng năm (USD)",
            min_value=1000.0,
            max_value=1000000.0,
            value=52000.0,
            step=1000.0,
            help="Thu nhập hàng năm từ $1,000 đến $1,000,000"
        )
        
        outstanding_debt = col2.number_input(
            "Tổng nợ hiện tại (USD)",
            min_value=0.0,
            max_value=500000.0,
            value=2600.0,
            step=100.0,
            help="Tổng số nợ hiện tại từ $0 đến $500,000"
        )
        
        num_of_loan = col1.number_input(
            "Số khoản vay mở",
            min_value=0,
            max_value=20,
            value=2,
            step=1,
            help="Số lượng khoản vay đang mở (0-20)"
        )
        
        num_of_delayed_payment = col2.number_input(
            "Số lần trả muộn",
            min_value=0,
            max_value=100,
            value=0,
            step=1,
            help="Số lần trả nợ muộn trong quá khứ (0-100)"
        )
        
        avg_credit_limit = col1.number_input(
            "Hạn mức TB mỗi thẻ (USD)",
            min_value=500.0,
            max_value=100000.0,
            value=15000.0,
            step=500.0,
            help="Hạn mức tín dụng trung bình mỗi thẻ từ $500 đến $100,000"
        )
        
        # Credit History Age selectbox
        default_credit_history = "12 Years and 6 Months"
        credit_history_index = 0
        if default_credit_history in credit_history_options:
            credit_history_index = credit_history_options.index(default_credit_history) + 1
        
        credit_history_age = st.selectbox(
            "Lịch sử tín dụng",
            options=[""] + credit_history_options,
            index=credit_history_index,
            help="Chọn thời gian có lịch sử tín dụng (từ 1 năm đến 40 năm)"
        )
        
        # Payment Behaviour selectbox
        default_payment_behaviour = "Low_spent_Small_value_payments"
        payment_behaviour_index = 0
        if default_payment_behaviour in payment_behaviour_options:
            payment_behaviour_index = payment_behaviour_options.index(default_payment_behaviour) + 1
        
        payment_behaviour = st.selectbox(
            "Payment Behaviour",
            options=[""] + payment_behaviour_options,
            index=payment_behaviour_index,
            help="Chọn hành vi thanh toán của khách hàng"
        )
        
        spending_level = st.selectbox(
            "Spending Level",
            options=["", "Low", "High"],
            index=1,
            help="Mức độ chi tiêu: Low (thấp) hoặc High (cao)"
        )
        
        value_level = st.selectbox(
            "Value Level",
            options=["", "Small", "Large"],
            index=1,
            help="Giá trị giao dịch: Small (nhỏ) hoặc Large (lớn)"
        )
        with st.expander("Thông tin bổ sung cho Decision Tree", expanded=(mode == "decision_tree")):
            interest_rate = st.number_input(
                "Interest Rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=13.5,
                step=0.1,
                help="Lãi suất từ 0% đến 50%"
            )
            payment_of_min = st.selectbox(
                "Payment of Minimum Amount",
                options=["Yes", "No"],
                index=0,
                help="Có thanh toán số tiền tối thiểu không?"
            )
            delay_from_due = st.number_input(
                "Delay from due date (days)",
                min_value=0.0,
                max_value=365.0,
                value=10.0,
                step=1.0,
                help="Số ngày trễ so với ngày đáo hạn (0-365 ngày)"
            )
            num_credit_card = st.number_input(
                "Số thẻ tín dụng",
                min_value=0.0,
                max_value=20.0,
                value=3.0,
                step=1.0,
                help="Số lượng thẻ tín dụng đang sở hữu (0-20)"
            )
            monthly_balance = st.number_input(
                "Số dư hàng tháng (USD)",
                min_value=0.0,
                max_value=100000.0,
                value=500.0,
                step=100.0,
                help="Số dư tài khoản trung bình hàng tháng ($0-$100,000)"
            )
            total_emi_per_month = st.number_input(
                "Total EMI per month (USD)",
                min_value=0.0,
                max_value=10000.0,
                value=100.0,
                step=50.0,
                help="Tổng số tiền trả góp hàng tháng ($0-$10,000)"
            )
            amount_invested_monthly = st.number_input(
                "Amount invested monthly (USD)",
                min_value=0.0,
                max_value=50000.0,
                value=100.0,
                step=100.0,
                help="Số tiền đầu tư hàng tháng ($0-$50,000)"
            )
            monthly_inhand_salary = st.number_input(
                "Monthly in-hand salary (USD)",
                min_value=0.0,
                max_value=50000.0,
                value=4000.0,
                step=500.0,
                help="Lương thực nhận hàng tháng ($0-$50,000)"
            )
            age = st.number_input(
                "Age",
                min_value=18.0,
                max_value=100.0,
                value=35.0,
                step=1.0,
                help="Tuổi của khách hàng (18-100 tuổi)"
            )

        submitted = st.form_submit_button("Dự báo")

    if submitted:
        # Sử dụng occupation làm person_id nếu person_id trống
        final_person_id = person_id if person_id.strip() else (occupation if occupation else "demo_user")
        
        # Validation: Kiểm tra các trường bắt buộc
        if not credit_history_age:
            st.error("⚠️ Vui lòng chọn Lịch sử tín dụng")
            return
        if not payment_behaviour:
            st.error("⚠️ Vui lòng chọn Payment Behaviour")
            return
        
        payload = {
            "person_id": final_person_id,
            "occupation": occupation if occupation else None,
            "annual_income": annual_income,
            "outstanding_debt": outstanding_debt,
            "num_of_loan": num_of_loan,
            "credit_history_age": credit_history_age,
            "num_of_delayed_payment": num_of_delayed_payment,
            "payment_behaviour": payment_behaviour or None,
            "spending_level": spending_level or None,
            "value_level": value_level or None,
            "avg_credit_limit": avg_credit_limit,
            "interest_rate": interest_rate if mode == "decision_tree" else None,
            "payment_of_min_amount": payment_of_min if mode == "decision_tree" else None,
            "delay_from_due_date": delay_from_due if mode == "decision_tree" else None,
            "num_credit_card": num_credit_card if mode == "decision_tree" else None,
            "monthly_balance": monthly_balance if mode == "decision_tree" else None,
            "total_emi_per_month": total_emi_per_month if mode == "decision_tree" else None,
            "amount_invested_monthly": amount_invested_monthly if mode == "decision_tree" else None,
            "monthly_inhand_salary": monthly_inhand_salary if mode == "decision_tree" else None,
            "age": age if mode == "decision_tree" else None,
            "mode": mode,
        }
        try:
            response = requests.post(API_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Lỗi gọi API: {exc}")
            return

        st.subheader("Kết quả dự báo")
        if data.get("success"):
            score = data.get('credit_score')
            score_vn = {"Good": "Tốt", "Poor": "Kém", "Standard": "Trung bình"}.get(str(score), str(score))
            
            # Hiển thị với màu tùy chỉnh
            display_credit_score_result(str(score), score_vn)
        else:
            st.warning("Không suy diễn được Credit Score.")

        # Hiển thị giải thích từ LLM nếu có
        if data.get("llm_explanation"):
            st.subheader("💡 Giải thích tự nhiên (AI)")
            with st.expander("Xem giải thích chi tiết", expanded=True):
                st.markdown(data["llm_explanation"])
        else:
            st.info("💡 Gợi ý: Khởi động Ollama với model llama3 để xem giải thích tự nhiên từ AI.")

        st.subheader("🔍 Chi tiết từng bước suy luận")
        for idx, step in enumerate(data.get("steps", []), start=1):
            st.write(f"{idx}. {step}")

        if data.get("matched_rule"):
            st.info(f"✅ Luật được áp dụng: {data['matched_rule']}")

        if data.get("missing_facts"):
            st.warning(f"⚠️ Thiếu facts: {', '.join(data['missing_facts'])}")


if __name__ == "__main__":
    main()

