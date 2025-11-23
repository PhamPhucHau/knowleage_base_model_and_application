import os
import sys
from pathlib import Path

import pandas as pd

# Bổ sung đường dẫn để import thư viện Funcs dùng chung
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from rules.funcs import (  # noqa: E402
    convert_to_numeric,
    credit_score_calc,
    normalize_credit_score,
    normalize_decimal,
    normalize_payment_behavior,
    parse_time_to_months,
)

# ============================================
# BƯỚC 1: CHUẨN HÓA DỮ LIỆU (Data Pre-processing)
# ============================================

def preprocess_data(df):
    """Thực hiện tất cả các bước chuẩn hóa dữ liệu"""
    df_processed = df.copy()
    
    print("Bắt đầu chuẩn hóa dữ liệu...")
    
    # 1.1. Chuẩn hóa số thập phân cho tất cả các cột
    print("  → Chuẩn hóa số thập phân...")
    for col in df_processed.columns:
        df_processed[col] = df_processed[col].apply(normalize_decimal)
    
    # 1.2. Chuyển các cột số từ character → numeric
    print("  → Chuyển đổi cột số sang numeric...")
    numeric_columns = []
    for col in df_processed.columns:
        # Thử xác định cột số
        sample = df_processed[col].dropna().head(100)
        if len(sample) > 0:
            # Kiểm tra xem có phải là số không
            try:
                test_val = str(sample.iloc[0]).replace(',', '.').replace(' ', '')
                float(test_val)
                numeric_columns.append(col)
            except:
                pass
    
    for col in numeric_columns:
        if col not in ['ID', 'Customer_ID']:  # Giữ nguyên ID
            df_processed[col] = convert_to_numeric(df_processed[col])
    
    # 1.3. Chuẩn hóa chuỗi thời gian
    print("  → Chuẩn hóa chuỗi thời gian...")
    time_columns = [col for col in df_processed.columns 
                   if 'time' in col.lower() or 'month' in col.lower() or 'year' in col.lower()]
    
    for col in time_columns:
        if df_processed[col].dtype == 'object':
            df_processed[f'{col}_Months'] = df_processed[col].apply(parse_time_to_months)
    
    # 1.4. Chuẩn hóa Payment_Behaviour
    print("  → Chuẩn hóa Payment_Behaviour...")
    payment_cols = [col for col in df_processed.columns 
                   if 'payment' in col.lower() and 'behaviour' in col.lower()]
    
    for col in payment_cols:
        payment_data = df_processed[col].apply(normalize_payment_behavior)
        df_processed['Spending_Level'] = payment_data.apply(lambda x: x['Spending_Level'])
        df_processed['Value_Level'] = payment_data.apply(lambda x: x['Value_Level'])
    
    # 1.5. Chuẩn hóa Credit_Score
    print("  → Chuẩn hóa Credit_Score...")
    credit_score_cols = [col for col in df_processed.columns 
                        if 'credit' in col.lower() and 'score' in col.lower()]
    
    for col in credit_score_cols:
        df_processed[f'{col}_Category'] = df_processed[col].apply(normalize_credit_score)
    
    # Derived financial metrics for Funcs
    if 'DTI_Ratio' not in df_processed.columns and {'Outstanding_Debt', 'Annual_Income'}.issubset(df_processed.columns):
        denom = df_processed['Annual_Income'].replace({0: pd.NA})
        df_processed['DTI_Ratio'] = df_processed['Outstanding_Debt'] / denom
    
    # Tính Credit Score tham chiếu để inference engine có dữ liệu mục tiêu
    required_calc_cols = {'DTI_Ratio', 'Credit_Utilization_Ratio', 'Num_of_Delayed_Payment', 'Annual_Income'}
    optional_calc_cols = {'Spending_Level', 'Value_Level', 'Num_of_Loan'}
    if required_calc_cols.issubset(df_processed.columns):
        def _compute_credit_score(row):
            payload = {}
            for col in required_calc_cols.union(optional_calc_cols):
                if col in df_processed.columns and not pd.isna(row[col]):
                    payload[col] = row[col]
            if not required_calc_cols.issubset(payload.keys()):
                return None
            return credit_score_calc(payload)
        
        df_processed['Credit_Score_Computed'] = df_processed.apply(_compute_credit_score, axis=1)
    
    print("✓ Hoàn thành chuẩn hóa dữ liệu!\n")
    return df_processed

# ============================================
# BƯỚC 2 & 3: TẠO ONTOLOGY VÀ QUAN HỆ
# ============================================

def escape_cypher_string(value):
    """Escape string cho Cypher query"""
    if value is None:
        return None
    value_str = str(value)
    # Escape single quotes và backslashes
    value_str = value_str.replace('\\', '\\\\').replace("'", "\\'")
    return value_str

def format_cypher_property(key, value):
    """Format property cho Cypher query"""
    if pd.isna(value):
        return None
    
    key_clean = key.replace(' ', '_').replace('-', '_').replace('.', '_')
    
    if pd.api.types.is_numeric_dtype(type(value)) or isinstance(value, (int, float)):
        return f"{key_clean}: {float(value)}"
    else:
        escaped = escape_cypher_string(value)
        return f"{key_clean}: '{escaped}'"

def generate_cypher_queries(df):
    """Tạo các câu lệnh Cypher để import vào Neo4j"""
    
    cypher_queries = []
    
    # Tạo constraints và indexes
    cypher_queries.append("// ============================================")
    cypher_queries.append("// TẠO CONSTRAINTS VÀ INDEXES")
    cypher_queries.append("// ============================================")
    cypher_queries.append("CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;")
    cypher_queries.append("CREATE INDEX occupation_name IF NOT EXISTS FOR (o:Occupation) ON (o.name);")
    cypher_queries.append("CREATE INDEX credit_score_category IF NOT EXISTS FOR (c:CreditScoreCategory) ON (c.category);")
    cypher_queries.append("")
    
    # Xác định các cột và mapping
    person_id_col = None
    occupation_col = None
    income_cols = []
    loan_cols = []
    payment_behaviour_cols = []
    credit_score_col = None
    credit_history_cols = []
    debt_cols = []
    emi_cols = []
    balance_cols = []
    utilization_cols = []
    
    # Tự động phát hiện các cột
    for col in df.columns:
        col_lower = col.lower()
        
        if 'id' in col_lower and person_id_col is None:
            person_id_col = col
        elif 'occupation' in col_lower:
            occupation_col = col
        elif 'income' in col_lower:
            income_cols.append(col)
        elif 'loan' in col_lower:
            loan_cols.append(col)
        elif 'payment' in col_lower or 'spending' in col_lower or 'value' in col_lower:
            payment_behaviour_cols.append(col)
        elif 'credit' in col_lower and 'score' in col_lower:
            credit_score_col = col
        elif 'credit' in col_lower and ('history' in col_lower or 'month' in col_lower):
            credit_history_cols.append(col)
        elif 'debt' in col_lower:
            debt_cols.append(col)
        elif 'emi' in col_lower:
            emi_cols.append(col)
        elif 'balance' in col_lower:
            balance_cols.append(col)
        elif 'utilization' in col_lower:
            utilization_cols.append(col)
    
    # Nếu không tìm thấy ID, dùng index
    if person_id_col is None:
        person_id_col = df.columns[0]
    
    print(f"Sử dụng cột ID: {person_id_col}")
    print(f"Các cột phát hiện được:")
    print(f"  - Occupation: {occupation_col}")
    print(f"  - Income: {income_cols}")
    print(f"  - Loan: {loan_cols}")
    print(f"  - Payment Behaviour: {payment_behaviour_cols}")
    print(f"  - Credit Score: {credit_score_col}")
    print(f"  - Credit History: {credit_history_cols}")
    print(f"  - Debt: {debt_cols}")
    print(f"  - EMI: {emi_cols}")
    print(f"  - Balance: {balance_cols}")
    print(f"  - Utilization: {utilization_cols}\n")
    
    cypher_queries.append("// ============================================")
    cypher_queries.append("// TẠO NODES VÀ RELATIONSHIPS")
    cypher_queries.append("// ============================================")
    cypher_queries.append("")
    
    # Tạo từng bản ghi
    for idx, row in df.iterrows():
        person_id_raw = str(row[person_id_col]) if not pd.isna(row[person_id_col]) else f"person_{idx}"
        person_id = escape_cypher_string(person_id_raw)
        
        # Tạo Person node
        cypher_queries.append(f"// Person {person_id}")
        cypher_queries.append(f"MERGE (p:Person {{id: '{person_id}'}});")
        
        # Occupation
        if occupation_col and not pd.isna(row[occupation_col]):
            occupation = escape_cypher_string(row[occupation_col])
            cypher_queries.append(f"MERGE (o:Occupation {{name: '{occupation}'}});")
            cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}), (o:Occupation {{name: '{occupation}'}}) MERGE (p)-[:HAS_OCCUPATION]->(o);")
        
        # Income
        if income_cols:
            income_props = []
            for col in income_cols:
                prop = format_cypher_property(col, row[col])
                if prop:
                    income_props.append(prop)
            
            if income_props:
                props_str = ', '.join(income_props)
                cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_INCOME]->(i:Income {{{props_str}}});")
        
        # Loan
        if loan_cols:
            loan_props = []
            for col in loan_cols:
                prop = format_cypher_property(col, row[col])
                if prop:
                    loan_props.append(prop)
            
            if loan_props:
                props_str = ', '.join(loan_props)
                cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_LOAN]->(l:Loan {{{props_str}}});")
        
        # Payment Behaviour
        if payment_behaviour_cols:
            spending_level = None
            value_level = None
            
            if 'Spending_Level' in df.columns and not pd.isna(row['Spending_Level']):
                spending_level = str(row['Spending_Level'])
            if 'Value_Level' in df.columns and not pd.isna(row['Value_Level']):
                value_level = str(row['Value_Level'])
            
            if spending_level or value_level:
                pb_props = []
                if spending_level:
                    spending_escaped = escape_cypher_string(spending_level)
                    pb_props.append(f"spending_level: '{spending_escaped}'")
                if value_level:
                    value_escaped = escape_cypher_string(value_level)
                    pb_props.append(f"value_level: '{value_escaped}'")
                
                props_str = ', '.join(pb_props)
                cypher_queries.append(f"MERGE (pb:PaymentBehaviour {{{props_str}}});")
                cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}), (pb:PaymentBehaviour {{{props_str}}}) MERGE (p)-[:HAS_PAYMENT_BEHAVIOUR]->(pb);")
        
        # Credit Score Category
        if credit_score_col:
            credit_score_val = None
            if f'{credit_score_col}_Category' in df.columns and not pd.isna(row[f'{credit_score_col}_Category']):
                credit_score_val = str(row[f'{credit_score_col}_Category'])
            elif not pd.isna(row[credit_score_col]):
                credit_score_val = normalize_credit_score(row[credit_score_col])
            
            if credit_score_val:
                credit_score_escaped = escape_cypher_string(credit_score_val)
                cypher_queries.append(f"MERGE (csc:CreditScoreCategory {{category: '{credit_score_escaped}'}});")
                cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}), (csc:CreditScoreCategory {{category: '{credit_score_escaped}'}}) MERGE (p)-[:HAS_CREDIT_SCORE]->(csc);")
        
        # Credit History
        if credit_history_cols:
            history_props = []
            for col in credit_history_cols:
                prop = format_cypher_property(col, row[col])
                if prop:
                    history_props.append(prop)
            
            if history_props:
                props_str = ', '.join(history_props)
                cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_CREDIT_HISTORY]->(ch:CreditHistory {{{props_str}}});")
        
        # Debt Profile
        if debt_cols:
            debt_props = []
            for col in debt_cols:
                prop = format_cypher_property(col, row[col])
                if prop:
                    debt_props.append(prop)
            
            if debt_props:
                props_str = ', '.join(debt_props)
                cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_DEBT_PROFILE]->(dp:DebtProfile {{{props_str}}});")
        
        # EMI
        if emi_cols:
            for col in emi_cols:
                if not pd.isna(row[col]):
                    emi_value = float(row[col]) if pd.api.types.is_numeric_dtype(type(row[col])) else None
                    if emi_value is not None:
                        cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_EMI]->(emi:EMI {{value: {emi_value}}});")
        
        # Balance
        if balance_cols:
            for col in balance_cols:
                if not pd.isna(row[col]):
                    balance_value = float(row[col]) if pd.api.types.is_numeric_dtype(type(row[col])) else None
                    if balance_value is not None:
                        cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_BALANCE]->(bal:Balance {{value: {balance_value}}});")
        
        # Credit Utilization
        if utilization_cols:
            for col in utilization_cols:
                if not pd.isna(row[col]):
                    util_value = float(row[col]) if pd.api.types.is_numeric_dtype(type(row[col])) else None
                    if util_value is not None:
                        cypher_queries.append(f"MATCH (p:Person {{id: '{person_id}'}}) MERGE (p)-[:HAS_CREDIT_UTILIZATION]->(cu:CreditUtilization {{value: {util_value}}});")
        
        cypher_queries.append("")
    
    return '\n'.join(cypher_queries)

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    # Đường dẫn đến file Excel
    excel_path = os.path.join(os.path.dirname(__file__), '../../datasets/Data Clean.xlsx')
    
    print("=" * 60)
    print("XỬ LÝ DỮ LIỆU VÀ TẠO CYPHER QUERIES CHO NEO4J")
    print("=" * 60)
    print(f"\nĐang đọc file: {excel_path}\n")
    
    # Đọc file Excel
    try:
        df = pd.read_excel(excel_path)
        print(f"✓ Đã đọc thành công {len(df)} dòng dữ liệu")
        print(f"  Số cột: {len(df.columns)}")
        print(f"  Các cột: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}\n")
    except Exception as e:
        print(f"✗ Lỗi khi đọc file Excel: {e}")
        return
    
    # BƯỚC 1: Chuẩn hóa dữ liệu
    df_processed = preprocess_data(df)
    
    # Lưu file đã xử lý (tùy chọn)
    output_excel = os.path.join(os.path.dirname(__file__), '../../datasets/Data Processed.xlsx')
    df_processed.to_excel(output_excel, index=False)
    print(f"✓ Đã lưu dữ liệu đã xử lý vào: {output_excel}\n")
    
    # BƯỚC 2 & 3: Tạo Cypher queries
    print("Đang tạo Cypher queries...")
    cypher_queries = generate_cypher_queries(df_processed)
    
    # Lưu Cypher queries vào file
    cypher_output = os.path.join(os.path.dirname(__file__), '../../cypher_import.cypher')
    with open(cypher_output, 'w', encoding='utf-8') as f:
        f.write(cypher_queries)
    
    print(f"✓ Đã tạo {len(cypher_queries.split(chr(10)))} dòng Cypher queries")
    print(f"✓ Đã lưu vào file: {cypher_output}\n")
    
    print("=" * 60)
    print("HOÀN THÀNH!")
    print("=" * 60)
    print(f"\nĐể import vào Neo4j, bạn có thể:")
    print(f"1. Mở Neo4j Browser")
    print(f"2. Copy nội dung file {cypher_output}")
    print(f"3. Paste và chạy trong Neo4j Browser")
    print(f"\nHoặc sử dụng Neo4j import tool:")
    print(f"  neo4j-admin import --nodes=...")
    print(f"  (Xem file {cypher_output} để biết chi tiết)")

if __name__ == "__main__":
    main()

