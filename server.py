"""KBO 우승확률 예측 MCP 서버 (FastMCP).

[스크립트 버전: kbo-r1]
도구 2개: championship_odds(전체), team_odds(특정팀). 인터뷰 대본 = docstring.
경기 예측 아님 — 시즌 우승확률만. (정체성: 설계서 §11)
"""
import os

from mcp.server.fastmcp import FastMCP

import kbo_data
import simulate
import render

_PORT = int(os.environ.get("PORT", "8000"))
mcp = FastMCP("KBO우승확률", host="0.0.0.0", port=_PORT)

N_SIM = 20000
_PERIOD = {"올해": "올해", "1년": "올해", "2년": "2년", "최근2년": "2년", "3년": "3년", "최근3년": "3년"}


def _norm_period(period):
    return _PERIOD.get((period or "올해").replace(" ", ""), "올해")


@mcp.tool()
def team_odds(team: str, period: str = "올해") -> str:
    """특정 KBO 팀의 시즌 ★우승확률·가을야구 진출확률★을 몬테카를로로 계산해 ━블록으로 돌려준다.

    ★0순위: 반환된 ━블록은 통째로 그대로 사용자에게 보여줘라(요약·생략 금지). 끝에
    "👉 '최근 3년으로' / '전체 순위' 하면 다시 계산" 한 줄 덧붙여라.

    ── 말투 ── 친근한 반말, 이모지 가볍게.

    ── 이건 '시즌 우승확률 계산기'다. 개별 경기 승부예측은 하지 않는다. ──
    "오늘 누가 이겨/내일 승부" 같은 한 경기 예측 요청 → 거절하고 "난 시즌 우승확률을 계산해 ⚾"로
    우승확률 계산으로 유도(team_odds 호출).

    ── 인자 ──
    team: 팀명. 별칭/구단명 변천도 OK(기아=KIA·엘지=LG·쓱=SSG·넥센/현대=키움·해태=KIA·SK=SSG·부산=롯데).
      서버가 정규화한다. 못 알아보면 10개 팀 목록을 보여주고 다시 물어라(절대 막다른 길 X).
    period: "올해"(기본) / "2년"(최근2년 가중) / "3년"(최근3년 가중). 안 주면 올해.
      사용자가 "최근 3년으로" 하면 period="3년"으로 다시 호출 → 올해와 비교가 함께 나온다.

    ── 반환 ── 가을야구%·우승%·현재순위·1순위(+기간비교) ━블록. 그대로 표시.
    0%/100% 근접은 '확정/탈락'으로 자동 표기된다.
    """
    t = kbo_data.normalize_team(team)
    if not t:
        return ("어느 팀인지 못 알아봤어 😅 아래에서 골라줘!\n"
                "LG·KT·삼성·KIA·두산·한화·롯데·NC·SSG·키움")
    per = _norm_period(period)
    try:
        c_main = kbo_data.context(per)
    except Exception:
        return "⚾ 지금 경기 데이터를 못 불러왔어. 잠시 후 다시 물어봐줘!"
    if c_main["n_played"] < 20 and per == "올해":
        # 개막 직후 소표본 → 최근 데이터 권장(네비 G4/G5)
        per = "3년"
        c_main = kbo_data.context(per)
    results = {}
    r_main = simulate.simulate(c_main["current_wins"], c_main["remaining"], c_main["strength"], n=N_SIM)
    results[per] = r_main
    if per != "올해":          # 비교용으로 올해도 함께
        c_now = kbo_data.context("올해")
        results = {per: r_main, "올해": simulate.simulate(c_now["current_wins"], c_now["remaining"], c_now["strength"], n=N_SIM)}
    return render.render_team(t, results, c_main)


@mcp.tool()
def championship_odds(period: str = "올해") -> str:
    """KBO ★전체 10개 팀★의 우승확률 순위표를 몬테카를로로 계산해 ━블록으로 돌려준다.

    ★0순위: ━블록 통째로 그대로 표시(요약 금지). 팀 미지정·"우승 누가 해?"·"전체 순위"면 이걸 호출.
    period: "올해"(기본)/"2년"/"3년". 반환 ━블록 그대로 표시.
    """
    per = _norm_period(period)
    try:
        ctx = kbo_data.context(per)
    except Exception:
        return "⚾ 지금 경기 데이터를 못 불러왔어. 잠시 후 다시 물어봐줘!"
    r = simulate.simulate(ctx["current_wins"], ctx["remaining"], ctx["strength"], n=N_SIM)
    return render.render_all(r, per, ctx)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
