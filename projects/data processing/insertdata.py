from neo4j import GraphDatabase

# Thông tin kết nối
uri = "bolt://localhost:7687"  # hoặc địa chỉ máy chủ Neo4j
username = "neo4j"
password = "12345678"

# Tạo driver
driver = GraphDatabase.driver(uri, auth=(username, password))

# Đọc và thực thi file .cypher
with driver.session() as session:
    with open("../../cypher_import.cypher", "r", encoding="utf-8") as file:
        cypher_script = file.read()
        for query in cypher_script.strip().split(";"):
            if query.strip():  # bỏ qua dòng trống
                session.run(query)
