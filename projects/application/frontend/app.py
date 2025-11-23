"""
Simple Streamlit UI for credit-score inference demo.

Run with:
    streamlit run projects/application/frontend/app.py
"""

from __future__ import annotations

import os
import requests
import streamlit as st

API_URL = os.getenv("CREDIT_API_URL", "http://localhost:8000/api/v1/predict/manual")


def main() -> None:
    st.set_page_config(page_title="Credit Score Demo", layout="centered")
    st.title("Demo dự báo Điểm Tín dụng")
    st.caption("Nhập thông tin tài chính, bấm Dự báo để xem kết quả và giải thích.")

    with st.form("credit_form"):
        mode = st.selectbox("Chế độ suy luận", options=["ontology", "decision_tree"], index=0)
        col1, col2 = st.columns(2)
        person_id = st.text_input("Mã khách hàng", value="demo_user")
        annual_income = col1.number_input("Thu nhập hàng năm (USD)", min_value=1000.0, value=52000.0)
        outstanding_debt = col2.number_input("Tổng nợ hiện tại (USD)", min_value=0.0, value=2600.0)
        num_of_loan = col1.number_input("Số khoản vay mở", min_value=0, value=2)
        num_of_delayed_payment = col2.number_input("Số lần trả muộn", min_value=0, value=0)
        avg_credit_limit = col1.number_input("Hạn mức TB mỗi thẻ", min_value=500.0, value=15000.0)
        credit_history_age = st.text_input("Lịch sử tín dụng", value="12 Years and 6 Months")
        payment_behaviour = st.text_input("Payment Behaviour", value="Low_spent_Small_value_payments")
        spending_level = st.selectbox("Spending Level", options=["", "Low", "High"], index=1)
        value_level = st.selectbox("Value Level", options=["", "Small", "Large"], index=1)
        with st.expander("Thông tin bổ sung cho Decision Tree", expanded=(mode == "decision_tree")):
            interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, value=13.5)
            payment_of_min = st.selectbox("Payment of Minimum Amount", options=["Yes", "No"], index=0)
            delay_from_due = st.number_input("Delay from due date (days)", min_value=0.0, value=10.0)
            num_credit_card = st.number_input("Số thẻ tín dụng", min_value=0.0, value=3.0)
            monthly_balance = st.number_input("Số dư hàng tháng", min_value=0.0, value=500.0)
            total_emi_per_month = st.number_input("Total EMI per month", min_value=0.0, value=100.0)
            amount_invested_monthly = st.number_input("Amount invested monthly", min_value=0.0, value=100.0)
            monthly_inhand_salary = st.number_input("Monthly in-hand salary", min_value=0.0, value=4000.0)
            age = st.number_input("Age", min_value=18.0, value=35.0)

        submitted = st.form_submit_button("Dự báo")

    if submitted:
        payload = {
            "person_id": person_id,
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
            st.success(f"Credit Score: {data.get('credit_score')}")
        else:
            st.warning("Không suy diễn được Credit Score.")

        st.subheader("Giải thích từng bước")
        for idx, step in enumerate(data.get("steps", []), start=1):
            st.write(f"{idx}. {step}")

        if data.get("missing_facts"):
            st.info(f"Thiếu facts: {', '.join(data['missing_facts'])}")


if __name__ == "__main__":
    main()

