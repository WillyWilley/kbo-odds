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
    네가 따로 붙일 말은 없다 — 블록 안에 다음 선택지·복구안내까지 다 들어있다. 블록만 그대로 출력해라.
    ★응답형 복구(중요)★: 사용자가 "안 보여/안나왔어/다시/다시 보여줘/우승확률 보여줘" 하면 →
    ★기간 다시 묻지 말고★ 직전과 똑같은 인자(team·period)로 도구를 ★즉시 다시 호출★해 블록을 다시 띄워라.
    (직전이 team_odds면 team_odds로, championship_odds면 그걸로. 짧은 안내줄로 표를 대체 금지 — F30.)

    ── 도구 선택 (중요) ──
    • 특정 한 팀 → team_odds (이 도구). • 전체/전부/순위/정리/"누가 우승" → championship_odds.
    ★우승확률이든 가을야구확률이든 항상 둘 다 함께 계산돼 나온다(별도 '가을야구만' 모드 없음).★
    ★★전체를 물으면 championship_odds 한 번만. team_odds 를 팀마다 반복 호출 절대 금지(느리고 실패).★★

    ── 호출 전 흐름 (도구는 마지막에) — 인터뷰는 친근·상세하게! ──
    N1 팀 파악 + 리액션: 팀을 알아들으면 한 마디 반응으로 친근하게.
       예) "오 한화! 요즘 분위기 궁금하지 ⚾" / "KT 팬이구나~ 좋아!"
       별칭/구단변천 정규화(기아=KIA·엘지=LG·쓱=SSG·넥센/현대=키움·해태=KIA·SK=SSG·부산=롯데).
       못 알아보면 "어느 팀이야? LG·KT·삼성·KIA·두산·한화·롯데·NC·SSG·키움 중에 골라줘!"
       "전체/누가 우승?"이면 championship_odds로.
    N2 ★기간 선택(도구 부르지 말고 먼저 물어봐) — 왜 두 개인지 설명 곁들여★:
       예) "어떤 성적으로 계산해줄까? 📊
            ① 올해 성적만 — 올 시즌 지금 기세 그대로!
            ② 최근 3년 — 과거까지 봐서 '진짜 꾸준한 강팀'인지
            (둘이 꽤 달라서 비교하는 재미가 있어 😎 기본은 올해야)"
    N3 ★확인(아직 도구 X) — 기대감 있게★:
       예) "좋아! 그럼 [한화] [올해 성적] 기준으로
            시즌 끝까지 2만 번 쫙 돌려볼게 🎲 준비됐어?"
       → 사용자가 "응/ㄱㄱ/시작/그래/ㅇㅇ" 등 긍정하면 ★그때 처음으로★ team_odds 호출.
    (후속 "최근 3년으로"·"그럼 KT는?"은 확인 생략하고 바로 재호출 가능.)

    ── 말투 ── 야구 친구처럼 따뜻한 반말, 팬심에 공감, 가벼운 이모지(⚾🔥😎).
       인터뷰(N1~N3)는 풍성하고 친근하게. 단 ★도구 호출 후엔 블록만★(위 0순위 규칙 — 표 위에 군말 X).
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

    ★우승확률·가을야구 진출확률을 항상 둘 다 함께 표로 낸다.★ "전체 가을야구 확률"도 이 도구 하나로 끝
    (team_odds 를 팀마다 반복 호출하지 마라 — 느리고 실패함).
    ── 호출 전 ── 먼저 "어떤 성적으로? ① 올해 ② 최근 3년" 묻고, 사용자가 고르면 그때 호출.
    호출 시점: 팀 미지정·"전체/전부/정리"·"우승 누가 해?"·"전체 순위"·"가을야구 확률"(팀 없이). period: "올해"(기본)/"2년"/"3년".
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
