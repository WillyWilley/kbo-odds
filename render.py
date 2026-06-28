"""카카오톡 ━블록 렌더 — 우승확률 출력.

표시 규칙: ━로 감싼 블록을 그대로 노출. 0/100% 근접은 '확정/탈락' 상태문구(네비 R11).
"""
from simulate import TEAMS

_BAR = "━" * 18
_PERIOD_LABEL = {"올해": "이번 시즌", "2년": "최근 2시즌", "3년": "최근 3시즌"}
_PERIOD_SHORT = {"올해": "이번시즌", "2년": "2시즌", "3년": "3시즌"}


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


def render_team(team, results, ctx):
    """특정 팀 우승확률(상세). results={period: sim결과}. 첫 period가 주(主)."""
    st = ctx["standings"][team]
    main_p = list(results.keys())[0]
    r0 = results[main_p]
    po, champ = r0["po"][team], r0["champ"][team]
    rk = r0["rank"][team]
    gb, pos = _gb_from_5th(ctx["standings"], team)
    games_left = sum(1 for g in ctx.get("remaining", []) if team in (g["h"], g["a"]))
    rec = f"{st['w']}승 {st['l']}패" + (f" {st['t']}무" if st['t'] else "")

    # ★압축 유지(DMM F25: 긴 블록은 드롭). 핵심만 ~12줄.★
    state = _po_state(po)
    po_str = state if state else f"{po*100:.0f}%"
    rng = f"{rk['mode']}위" if rk["lo"] == rk["hi"] else f"{rk['mode']}위 ({rk['lo']}~{rk['hi']}위권)"
    top3 = sorted(TEAMS, key=lambda t: r0["champ"][t], reverse=True)[:3]

    lines = [_BAR, f"⚾ {team} — 우승확률 ({_PERIOD_LABEL.get(main_p, main_p)})"]
    lines.append(f"📍 현재성적 {pos}위 · {rec}")
    if len(results) > 1:   # 기간 비교
        lines.append("🏆 우승  " + " · ".join(
            f"{r['champ'][team]*100:.1f}%({_PERIOD_SHORT.get(per,per)})" for per, r in results.items()))
    else:
        lines.append(f"🏆 우승      {champ*100:.1f}%")
    lines.append(f"📊 가을야구   {po_str}")
    lines.append(f"📈 예상순위   {rng}")
    lines.append('💬 결과가 안 보이면 "다시 보여줘"라고 해줘')
    lines.append(_BAR)
    return "\n".join(lines)


def render_all(result, period, ctx):
    """전체 팀 우승확률 + 가을야구확률 순위표 (둘 다 항상 표시)."""
    rank = sorted(TEAMS, key=lambda t: result["champ"][t], reverse=True)
    lines = [_BAR, f"🏆 {ctx['year']} 우승·가을야구 ({_PERIOD_LABEL.get(period, period)})",
             "  팀    우승 / 가을"]
    for i, t in enumerate(rank, 1):
        c = result["champ"][t] * 100
        po = result["po"][t] * 100
        c_str = f"{c:4.1f}%" if c >= 0.05 else " ~0%"
        po_str = f"{po:3.0f}%" if 0.5 <= po <= 99.5 else ("100%" if po > 99.5 else "~0%")
        lines.append(f"{i:2} {t:<4}{c_str} / {po_str}")
    lines.append('💬 결과가 안 보이면 "다시 보여줘"라고 해줘')
    lines.append(_BAR)
    return "\n".join(lines)
