# KBO 우승확률 MCP — Python 단독 (KBO 데이터는 stdlib urllib로 직접 조회, node 불필요)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulate.py kbo_data.py render.py comments.py server.py ./
COPY data/ ./data/

ENV PORT=8000
EXPOSE 8000
CMD ["python", "server.py"]
