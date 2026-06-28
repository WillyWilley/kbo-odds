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
    # PlayMCP 심사 요건(F29): annotations + 서비스명. 읽기전용·비파괴, 외부데이터 사용.
    return ToolAnnotations(title="KBO 우승확률 계산기", readOnlyHint=True,
                           destructiveHint=False, openWorldHint=True)

N_SIM = 20000
_PERIOD = {"올해": "올해", "1년": "올해", "2년": "2년", "최근2년": "2년", "3년": "3년", "최근3년": "3년"}


def _norm_period(period):
    return _PERIOD.get((period or "올해").replace(" ", ""), "올해")


@mcp.tool(annotations=_anno())
def team_odds(team: str, period: str = "올해") -> str:
    """KBO 우승확률 계산기 — 특정 팀의 시즌 우승확률·가을야구 진출확률을 몬테카를로로 계산한다.

    ★★★0순위 규칙 (제일 중요) ★★★
    이 도구가 돌려준 텍스트(━로 시작해 ━로 끝나는 블록)가 곧 네 답이다.
    ★네 답변 = 그 ━블록 그 자체.★ 한 글자도 빼지 말고 그대로 붙여라.
    ❌ 절대 금지: 숫자를 네가 풀어서 말하기. ("한화 우승 1.8%야, 가을야구 46%…" = 실패)
    ❌ 절대 금지: 블록 대신 요약/반응/안내문만 내기. 블록을 다른 말로 대체하지 마라.
    네가 따로 붙일 말은 없다 — 블록 안에 다음 선택지까지 다 들어있다. 블록만 그대로 출력해라.

    ── 호출 전 흐름 (도구는 마지막에) ──
    N1 팀 파악: 별칭/구단변천 정규화(기아=KIA·엘지=LG·쓱=SSG·넥센/현대=키움·해태=KIA·SK=SSG·부산=롯데).
       못 알아보면 10팀 목록 보여주고 다시. "전체/누가 우승?"이면 championship_odds로.
    N2 ★기간 선택(도구 부르지 말고 먼저 물어봐)★:
       "어떤 성적으로 계산할까? 📊\n ① 올해 성적만 (지금 기세)\n ② 최근 3년 (원래 강팀인지)"
    N3 ★확인(아직 도구 X)★: "[한화] [올해] 기준으로 2만 번 시뮬 돌릴게 🎲 시작할까?"
       → 사용자가 "응/ㄱㄱ/시작" 등 긍정하면 ★그때 처음으로★ team_odds 호출.
    (후속 "최근 3년으로"·"그럼 KT는?"은 확인 생략하고 바로 재호출 가능.)

    ── 말투 ── 친근한 반말·가벼운 이모지(⚾). 단 호출 후엔 블록만(위 0순위 규칙).
    ── 범위 ── 시즌 우승확률 전용. 경기예측·선수기록·배팅·타종목은 "난 우승확률 봇이야"로 유도.
    ── 인자 ── team(서버 정규화) · period "올해"(기본)/"2년"/"3년". period≠올해면 올해와 비교 함께.
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


@mcp.tool(annotations=_anno())
def championship_odds(period: str = "올해") -> str:
    """KBO 우승확률 계산기 — 전체 10개 팀의 우승확률 순위표를 몬테카를로로 계산한다.

    ★★★0순위: 이 도구가 돌려준 ━블록이 곧 네 답이다. 그대로 붙여라.★★★
    ❌ 숫자 요약 금지("LG 43%·삼성 36%…" 식으로 네가 풀어 말하면 실패). 블록만 그대로 출력.
    블록 안에 다음 선택지까지 들어있으니 따로 덧붙일 말 없다.

    ── 호출 전 ── 먼저 "어떤 성적으로? ① 올해 ② 최근 3년" 묻고, 사용자가 고르면 그때 호출.
    호출 시점: 팀 미지정·"우승 누가 해?"·"전체 순위"·"순위 보여줘". period: "올해"(기본)/"2년"/"3년".
    경기예측·선수기록·배팅·타종목은 범위 밖 → 우승확률로 유도.
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
