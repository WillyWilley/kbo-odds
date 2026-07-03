"""KBO 우승확률 예측 MCP 서버 (FastMCP).

[스크립트 버전: kbo-r1]
도구 2개: championship_odds(전체), team_odds(특정팀). 인터뷰 대본 = docstring.
경기 예측 아님 — 시즌 우승확률만. (정체성: 설계서 §11)
"""
import os

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

import kbo_data
import simulate
import render

_PORT = int(os.environ.get("PORT", "8000"))
mcp = FastMCP("KBO우승확률", host="0.0.0.0", port=_PORT)


def _anno():
    # PlayMCP 심사 요건(F29+): annotations 필수 4종(title·readOnly·idempotent·openWorld).
    # 읽기전용·비파괴·멱등(같은 인자=같은 결과)·외부데이터 사용.
    return ToolAnnotations(title="KBO 우승확률 계산기", readOnlyHint=True,
                           destructiveHint=False, idempotentHint=True,
                           openWorldHint=True)

N_SIM = 20000
MIN_GAMES = 30      # 이번 시즌 단독 분석 최소 경기수(소표본이면 최근 3시즌으로 자동 대체)
_PERIOD = {"올해": "올해", "1년": "올해", "2년": "2년", "최근2년": "2년", "3년": "3년", "최근3년": "3년"}


def _norm_period(period):
    return _PERIOD.get((period or "올해").replace(" ", ""), "올해")


@mcp.tool(annotations=_anno())
def team_odds(team: str, period: str = "올해") -> str:
    """KBO 우승확률 계산기 — 특정 팀의 시즌 우승확률·가을야구 진출확률을 몬테카를로 시뮬레이션으로 계산한다.

    0순위: 이 도구가 돌려준 ━블록이 곧 네 답이다. 한 글자도 빼지 말고 그대로 출력하라.
    숫자를 풀어 말하거나 요약·대체하지 마라. "다시 보여줘"면 같은 인자로 재호출.
    흐름(매 요청 처음부터, N1·N2 둘 다 필수 — 사용자가 이미 말했어도 각각 한 번씩 확인): N1 → N2 → 호출. 끝나면 또 N1부터.
    N1 대상 확인(생략 금지): "OO 한 팀만 볼까? (전체 순위도 가능해!)" — 사용자가 답한 뒤에만 N2로.
       팀 정규화(기아=KIA·엘지=LG·쓱=SSG·넥센/현대=키움·해태=KIA·SK=SSG·부산=롯데).
       2팀 이상이면 "전체로 분석할게" 하고 championship_odds 사용.
    N2 "어떤 데이터로 예측해볼까? 1.이번 시즌 2.최근 2개 시즌 3.최근 3개 시즌" (1=올해/2=2년/3=3년)
    말투는 친근한 반말이되 도구 호출 후엔 블록만 출력. 경기예측·선수기록·배팅·타종목은 범위 밖.
    인자: team(서버 정규화), period 올해/2년/3년 중 택1(비교 없음).
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
    note = None
    if per == "올해" and c_main["n_played"] < MIN_GAMES:
        # 개막 직후 소표본 → 최근 3시즌으로 자동 대체 + 블록 안에 안내(네비 G4/G5)
        note = f"ⓘ 이번 시즌 표본 부족({c_main['n_played']}경기) → 최근 3시즌으로 계산했어 (이번 시즌 분석은 {MIN_GAMES}경기 이후 가능)"
        per = "3년"
        c_main = kbo_data.context(per)
    r_main = simulate.simulate(c_main["current_wins"], c_main["remaining"], c_main["strength"], n=N_SIM)
    return render.render_team(t, {per: r_main}, c_main, note=note)


@mcp.tool(annotations=_anno())
def championship_odds(period: str = "올해") -> str:
    """KBO 우승확률 계산기 — 전체 10개 팀의 우승확률·가을야구 진출확률 순위표를 몬테카를로 시뮬레이션으로 계산한다.

    0순위: 돌려준 ━블록이 곧 네 답이다. 그대로 출력하고 숫자 요약·대체 금지. "다시 보여줘"면 같은 인자로 재호출.
    전체·여러 팀·"전체 가을야구"는 모두 이 도구 한 번으로(team_odds 반복 호출 금지).
    흐름(매 요청 처음부터, N1·N2 둘 다 필수 — 사용자가 이미 말했어도 각각 한 번씩 확인): N1 → N2 → 호출. 끝나면 N1부터.
    N1 대상 확인(생략 금지): "KBO 전체 팀을 볼까? 아니면 특정 한 팀만 볼까?" — 답한 뒤에만 N2로. 특정 팀이면 team_odds.
    N2 "어떤 데이터로 예측해볼까? 1.이번 시즌 2.최근 2개 시즌 3.최근 3개 시즌" (1=올해/2=2년/3=3년)
    경기예측·선수기록·배팅·타종목은 범위 밖. 인자: period 올해/2년/3년 중 택1.
    """
    per = _norm_period(period)
    try:
        ctx = kbo_data.context(per)
    except Exception:
        return "⚾ 지금 경기 데이터를 못 불러왔어. 잠시 후 다시 물어봐줘!"
    note = None
    if per == "올해" and ctx["n_played"] < MIN_GAMES:
        note = f"ⓘ 이번 시즌 표본 부족({ctx['n_played']}경기) → 최근 3시즌으로 계산 ({MIN_GAMES}경기 이후 이번 시즌 가능)"
        per = "3년"
        ctx = kbo_data.context(per)
    r = simulate.simulate(ctx["current_wins"], ctx["remaining"], ctx["strength"], n=N_SIM)
    return render.render_all(r, per, ctx, note=note)


if __name__ == "__main__":
    try:
        kbo_data.current_season()   # 워밍업: 재시작 직후 첫 호출 타임아웃 방지
    except Exception:
        pass
    mcp.run(transport="streamable-http")
