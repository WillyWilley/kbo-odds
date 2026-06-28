"""카카오톡 ━블록 렌더 — 우승확률 출력.

표시 규칙: ━로 감싼 블록을 그대로 노출. 0/100% 근접은 '확정/탈락' 상태문구(네비 R11).
"""
import unicodedata

import comments
from simulate import TEAMS

_BAR = "━" * 18


def _dw(s):
    """표시폭(한글·전각=2, 영문·숫자=1) — 고정폭 정렬용."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(s, width):
    """표시폭 기준 좌측정렬 패딩(오른쪽 공백)."""
    return s + " " * max(0, width - _dw(s))


def _winpct(s):
    d = s["w"] + s["l"]
    return s["w"] / d if d else 0.0


def current_rank(standings):
    return sorted(TEAMS, key=lambda t: _winpct(standings[t]), reverse=True)


def _po_state(po):
    if po >= 0.999:
        return "🔒 사실상 확정"
    if po <= 0.001:
        return "❌ 사실상 탈락"
    return None


def _gb_from_5th(standings, team):
    """5위(가을야구 막차)와의 게임차. 양수=뒤처짐, 0이하=가을권."""
    rank = current_rank(standings)
    fifth = standings[rank[4]]
    s = standings[team]
    return ((fifth["w"] - s["w"]) + (s["l"] - fifth["l"])) / 2, rank.index(team) + 1


def render_team(team, results, ctx, note=None):
    """특정 팀 우승확률(상세). results={period: sim결과}. 첫 period가 주(主).
    note: 표본부족 자동대체 등 블록 안에 넣을 안내 한 줄(있으면 헤더 밑에)."""
    st = ctx["standings"][team]
    main_p = list(results.keys())[0]
    r0 = results[main_p]
    po, champ = r0["po"][team], r0["champ"][team]
    pos = r0["rank"][team]["mode"]                 # 예상 최종 순위
    # 예상 최종 성적: 시뮬 평균 승수 + (현재 무승부 유지) → 나머지는 패
    games_left = sum(1 for g in ctx.get("remaining", []) if team in (g["h"], g["a"]))
    total_g = st["w"] + st["l"] + st["t"] + games_left
    w_fin = round(r0["exp_wins"][team])
    t_fin = st["t"]
    l_fin = total_g - w_fin - t_fin
    rec = f"{w_fin}승 {l_fin}패" + (f" {t_fin}무" if t_fin else "")

    # 가을야구 거의 확정/탈락이면 숫자 대신 상태문구(네비 R11)
    state = _po_state(po)
    po_str = state if state else f"{po*100:.0f}%"

    lines = [_BAR, f"⚾ {ctx['year']} KBO {team} 시뮬레이션"]
    if note:
        lines.append(note)
    lines.append(f"📍 최종성적  {pos}위 {rec}")
    lines.append(f"🏆 우승확률      {champ*100:.1f}%")
    lines.append(f"📊 가을야구확률  {po_str}")
    lines.append(comments.team_line(champ, po))
    lines.append(_BAR)
    return "\n".join(lines)


def render_all(result, period, ctx, note=None):
    """전체 팀 우승확률 + 가을야구확률 순위표 (둘 다 항상 표시)."""
    rank = sorted(TEAMS, key=lambda t: result["champ"][t], reverse=True)
    lines = [_BAR, f"🏆 {ctx['year']} KBO 시뮬레이션"]
    if note:
        lines.append(note)
    lines.append(" #  팀    우승 / 가을야구")
    for i, t in enumerate(rank, 1):
        c = result["champ"][t] * 100
        po = result["po"][t] * 100
        c_str = (f"{c:.1f}%" if c >= 0.05 else "~0%").rjust(5)
        po_str = (f"{po:.0f}%" if 0.5 <= po <= 99.5 else ("100%" if po > 99.5 else "~0%")).rjust(4)
        lines.append(f"{i:2}  {_pad(t, 4)}  {c_str} / {po_str}")
    lines.append(_BAR)
    return "\n".join(lines)
