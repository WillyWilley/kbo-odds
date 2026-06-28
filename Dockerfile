# KBO 우승확률 MCP — Python(시뮬·서버) + Node(kbo-game, 올해 경기 조회)
FROM python:3.12-slim

# Node.js + kbo-game (런타임에 올해 경기 조회용)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g kbo-game \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulate.py kbo_data.py render.py server.py ./
COPY data/ ./data/

ENV PORT=8000
EXPOSE 8000
CMD ["python", "server.py"]
