# Database local hoặc online
Cài đặt docker Neo4j 
docker pull neo4j:5.26.17-ubi9
# Start Docker 
docker run \
    --publish=7474:7474 --publish=7687:7687 \
    --volume=$HOME/neo4j/data:/data \
    neo4j
# 
# Backend
uvicorn application.api.server:app --reload

# Frontend
streamlit run projects/application/frontend/app.py