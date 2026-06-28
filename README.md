# KBO 우승확률 예측 MCP

카카오 PlayMCP 출품작. "한화 우승확률?" 한마디에 몬테카를로 시즌 시뮬로 각 팀 우승·가을야구 확률을 계산.
기획: [../KBO우승확률예측_설계.md](../KBO우승확률예측_설계.md)

## 구조
```
kbo_mcp/
├── data/seasons.json   과거 4시즌(2022~2025) 정규시즌 DB (불변, build_db로 생성)
├── build_db.py         kbo-game → 과거 시즌 JSON 굳히기 (수동/주기)
├── kbo_data.py         DB 로드 + 올해 API 캐시(TTL 6h) + 팀명 정규화 + 다년 가중
├── simulate.py         Pythagenpat + 평균회귀 + Log5 + MC + 이항분포 시리즈
├── render.py           카카오톡 ━블록
├── server.py           FastMCP — team_odds / championship_odds
└── test_kbo.py         테스트
```

## 모델 (설계서 §10)
- 팀 실력: **Pythagenpat** + **평균회귀**(소표본 과신 방지)
- 경기 승률: **Log5** (+홈 0.035)
- 시즌: **몬테카를로 2만회** → 순위 → **스텝래더 PO**(이항분포 닫힌해 시리즈)
- 구현 정확성: 닫힌해·교과서값 대조 검증 완료

## 실행
```bash
python -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt
python build_db.py 2022 2023 2024 2025      # 과거 DB 1회 생성 (Node+kbo-game 필요)
python test_kbo.py                          # 테스트
GLOBAL_NPM_ROOT="$(npm root -g)" python server.py   # http://127.0.0.1:8000/mcp
```

## 도구
- **team_odds(team, period)** — 특정 팀 우승·가을야구 확률 (period: 올해/2년/3년). 팀명 별칭·구단변천 정규화. period≠올해면 올해와 비교.
- **championship_odds(period)** — 전체 10팀 우승확률 순위표.

## 정체성
**경기 예측기 아님 — 시즌 우승확률 계산기.** 개별 경기 승부예측 안 함(설계서 §11).

## 상태
- ✅ 엔진·데이터·서버·테스트·Dockerfile (Python+Node)
- ⬜ #3 실력 불확실성 draw (v2) · Elo 블렌딩(확장) · 매직넘버(v2)
- ⬜ GitHub(형 계정) → KC 배포 → PlayMCP 등록
