"""카카오톡 ━블록 렌더 — 우승확률 출력.

표시 규칙: ━로 감싼 블록을 그대로 노출. 0/100% 근접은 '확정/탈락' 상태문구(네비 R11).
"""
from simulate import TEAMS

_BAR = "━" * 18
_PERIOD_LABEL = {"올해": "올해 성적", "2년": "최근 2년 가중", "3년": "최근 3년 가중"}


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


def render_team(team, results, ctx):
    """특정 팀 우승확률. results={period: sim결과}. 첫 period가 주(主)."""
    st = ctx["standings"][team]
    rank = current_rank(ctx["standings"])
    pos = rank.index(team) + 1
    main_p = list(results.keys())[0]
    r0 = results[main_p]
    po = r0["po"][team]
    champ = r0["champ"][team]
    lines = [_BAR, f"⚾ {team} 우승확률"]
    rec = f"{st['w']}승 {st['l']}패" + (f" {st['t']}무" if st['t'] else "")
    lines.append(f"({ctx['year']} 현재 {pos}위 · {rec})")
    lines.append("")
    state = _po_state(po)
    if state:
        lines.append(f"📊 가을야구 진출  {state}")
    else:
        lines.append(f"📊 가을야구 진출  {po*100:.0f}%")
    # 우승% (기간별)
    if len(results) > 1:
        lines.append("🏆 우승:")
        for per, r in results.items():
            lines.append(f"   {r['champ'][team]*100:.1f}%  ({_PERIOD_LABEL.get(per, per)})")
    else:
        lines.append(f"🏆 우승  {champ*100:.1f}%  ({_PERIOD_LABEL.get(main_p, main_p)})")
    # 현재 1순위
    top = max(TEAMS, key=lambda t: r0["champ"][t])
    if top != team:
        lines.append("")
        lines.append(f"🥇 현재 1순위: {top} ({r0['champ'][top]*100:.0f}%)")
    lines.append(_BAR)
    return "\n".join(lines)


def render_all(result, period, ctx):
    """전체 팀 우승확률 순위표."""
    rank = sorted(TEAMS, key=lambda t: result["champ"][t], reverse=True)
    lines = [_BAR, f"🏆 {ctx['year']} 우승확률 ({_PERIOD_LABEL.get(period, period)})", ""]
    for i, t in enumerate(rank, 1):
        c = result["champ"][t] * 100
        po = result["po"][t]
        tag = ""
        if po >= 0.999:
            tag = " 🔒"
        elif po <= 0.001:
            tag = " ❌"
        c_str = f"{c:4.1f}%" if c >= 0.05 else "  ~0%"
        lines.append(f"{i:2}. {t:<4} {c_str}{tag}")
    lines.append("")
    lines.append("🔒확정임박 ❌사실상탈락 · MC 2만회")
    lines.append(_BAR)
    return "\n".join(lines)
