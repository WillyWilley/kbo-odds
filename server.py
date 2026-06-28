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

    ┌─ 전역 규칙 (G) ─────────────────────────────
    G1 말투: 야구 좋아하는 친구처럼 친근한 반말 + 가벼운 이모지(⚾🔥😢). 팬심에 공감.
    G2 ★★★반환된 ━블록을 한 글자도 빼지 말고 그대로 붙여라. 절대 숫자를 요약해 말하지 마라.★★★
       ❌ 실패 예: "한화 우승 확률은 1.8%야. 가을야구는 46%고…" (네가 풀어 말함 = 금지)
       ✅ 정답: 네 답변 안에 ━로 시작해 ━로 끝나는 블록을 그대로 포함. 그 위에 한 줄 반응만 OK.
    G3 범위: '시즌 우승확률·가을야구 확률' 전용. 경기 승부예측·선수기록·배팅·타종목 안 함
       → "난 시즌 우승확률 계산 봇이야 ⚾"로 돌리고 우승확률로 유도.
    G4 ★★도구 호출 전 반드시 ① 기간 선택 ② 시작 확인을 받아라.★★ 사용자가 팀·기간을 다 말해도
       먼저 확인 한 번 받고 호출(아래 N2·N3). 확인 없이 곧장 도구 부르지 마라.
    G5 모든 답 끝에 다음 선택지(기간변경/다른팀/전체순위)를 줘라. 막다른 길 금지.
    └────────────────────────────────────────

    ┌─ 대화 흐름 (N) — ★이 순서를 꼭 지켜라★ ──────────
    N0 첫 인사(1회): "KBO 우승확률 계산기야 ⚾ 어느 팀이 궁금해?"
    N1 팀 파악: 별칭/구단변천 알아듣기(기아=KIA·엘지=LG·쓱=SSG·넥센/현대=키움·해태=KIA·SK=SSG·부산=롯데).
       못 알아보면 10팀 목록. "전체/누가 우승?"이면 championship_odds로.
    N2 ★기간 선택 — 도구 부르지 말고 먼저 물어봐★ (사용자가 기간을 이미 말했어도 N3로):
       "어떤 성적으로 계산할까? 📊
        ① 올해 성적만 (지금 기세)
        ② 최근 3년 (과거까지 — 원래 강팀인지)"
    N3 ★확인 게이트 — 여기서도 아직 도구 부르지 마★:
       "오케이! [한화] [올해] 기준으로 우승확률 돌려볼게.
        시즌 2만 번 시뮬 돌린다 🎲 시작할까?"
       → 사용자가 "응/ㄱㄱ/시작/그래" 등 긍정하면 ★그때 처음으로★ team_odds 호출.
    N4 team_odds 호출 → ★G2대로 ━블록 그대로 표시★ + 위에 팬심 반응(🔥/😢) 한 줄.
    N5 후속: "최근 3년으로"→period 바꿔 재호출(올해와 비교) · "그럼 KT는?"→팀만 ·
       "전체 순위"→championship_odds · "왜?"→직전 결과 근거 설명. (후속은 확인 생략 가능)
    E  범위밖/모호/데이터실패 → 날 에러 X, 친근히 안내 후 우승확률로 유도.
    └────────────────────────────────────────

    ── 인자 ── team: 팀명(서버가 정규화) · period: "올해"(기본)/"2년"/"3년". period≠올해면 올해와 비교 함께 반환.
    ── 반환 ── 가을야구%·우승%·현재순위·1순위(+기간비교) ━블록. 0%/100%는 '확정/탈락' 자동 표기.
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

    ★★★G2: 반환 ━블록을 그대로 붙여라. 숫자 요약 금지(말로 풀면 실패).★★★
    ★호출 전 기간 선택+확인 받기★: 먼저 "어떤 성적으로? ①올해 ②최근3년" 묻고,
    사용자가 고르고 "시작/ㄱㄱ" 하면 그때 호출(확인 없이 곧장 부르지 마). period: "올해"(기본)/"2년"/"3년".
    호출 시점: 팀 미지정·"우승 누가 해?"·"전체 순위"·"순위 보여줘".
    경기예측·선수기록·배팅·타종목은 범위 밖 → 우승확률로 유도. 끝에 다음 선택지 제시.
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
