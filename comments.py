"""한줄평 — 수치 기반 조립(결정론적). 우승%·가을%로 절을 골라 합친다.

원칙: 하드코딩 풀이 아니라 수치→문구 매핑이라 품질이 구조적으로 보장된다.
- 틀린 단정(확정 남발) 금지: '사실상'·'유력' 등 확률적 표현만.
- 배팅 조장 금지(정체성 §11). 응원/정보 톤만.
실제 숫자(%)를 문장에 박아 '수치적 코멘트'를 강제한다.
"""


def _head(c):
    """우승 절 — c = 우승확률(%)."""
    if c >= 35:
        return f"우승 확률 {c:.1f}% — 압도적 선두야 🔥"
    if c >= 20:
        return f"우승 확률 {c:.1f}% — 강력한 우승 후보"
    if c >= 10:
        return f"우승 확률 {c:.1f}% — 충분히 노려볼 만해"
    if c >= 3:
        return f"우승 확률 {c:.1f}% — 다크호스로 살아있어"
    if c >= 1:
        return f"우승은 {c:.1f}%, 쉽진 않은 길이야"
    return None  # 1% 미만이면 우승 언급 생략, 가을 절만


def _tail(p):
    """가을 절 — p = 가을야구확률(%)."""
    if p >= 99.5:
        return "가을야구는 사실상 확정 🔒"
    if p >= 80:
        return "가을야구 진출이 거의 유력해"
    if p >= 55:
        return "가을야구는 유리한 고지에 있어"
    if p >= 45:
        return "가을야구는 딱 반반, 한 경기가 크다"
    if p >= 20:
        return "가을야구는 험난한 싸움이야"
    if p >= 3:
        return "가을야구 가려면 기적이 필요해"
    return "올핸 가을야구가 어려워 보여 ⚾"


def team_line(champ, po):
    """우승확률·가을야구확률(0~1) → '💬 ...' 한 줄."""
    c, p = champ * 100, po * 100
    head, tail = _head(c), _tail(p)
    body = f"{head}, {tail}" if head else tail
    return f"💬 {body}"


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    cases = [("삼성", .395, 1.0), ("LG", .376, 1.0), ("KIA", .156, .98),
             ("KT", .044, .87), ("한화", .020, .56), ("두산", .009, .51),
             ("NC", .001, .08), ("롯데", .0003, .01), ("SSG", .0001, .002),
             ("키움", .0, .0)]
    for t, c, p in cases:
        print(f"{t:4} 우승{c*100:4.1f}% 가을{p*100:3.0f}%  →  {team_line(c, p)}")
