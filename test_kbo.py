"""핵심 로직 테스트 (네트워크 불필요 — 합성 데이터)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import simulate as S
import render as R
from kbo_data import normalize_team
from simulate import TEAMS


def test_series_closed_form():
    assert abs(S.series_prob(0.5, 4) - 0.5) < 1e-9
    assert abs(S.series_prob(0.6, 2, 1) - (1 - 0.4**2)) < 1e-9   # 와일드카드
    assert abs(S.series_prob(0.6, 4) - 0.7102) < 1e-3            # BO7 p=.6


def test_log5_canonical():
    assert abs(S.log5(0.6, 0.4) - 0.692307) < 1e-5
    assert abs(S.log5(0.5, 0.5) - 0.5) < 1e-9


def test_regression_shrinkage():
    # 소표본 8승2패 → 평균회귀로 .5 쪽 (생짜 .8보다 훨씬 낮아야)
    T = {n: {"w": 0, "l": 0, "t": 0, "rs": 0, "ra": 0, "g": 0} for n in TEAMS}
    T["LG"] = {"w": 8, "l": 2, "t": 0, "rs": 60, "ra": 30, "g": 10}
    p = S.strength(T)
    assert p["LG"] < 0.7, f"소표본 과신 미방지: {p['LG']}"


def _synthetic():
    T = {n: {"w": 35+i, "l": 35-i, "t": 0, "rs": 400+i*10, "ra": 400-i*5, "g": 70}
         for i, n in enumerate(TEAMS)}
    p = S.strength(T)
    cur = {n: T[n]["w"] for n in TEAMS}
    rem = [{"h": TEAMS[i], "a": TEAMS[(i+1) % 10]} for i in range(10)] * 7
    return T, p, cur, rem


def test_prob_sums():
    T, p, cur, rem = _synthetic()
    r = S.simulate(cur, rem, p, n=5000, seed=1)
    assert abs(sum(r["champ"].values()) - 1.0) < 0.001, "우승확률 합 != 100%"
    assert abs(sum(r["po"].values()) - 5.0) < 0.02, "가을야구확률 합 != 5"


def test_reproducible():
    T, p, cur, rem = _synthetic()
    a = S.simulate(cur, rem, p, n=3000, seed=7)
    b = S.simulate(cur, rem, p, n=3000, seed=7)
    assert a["champ"] == b["champ"]


def test_normalize():
    assert normalize_team("기아") == "KIA"
    assert normalize_team("쓱") == "SSG"
    assert normalize_team("넥센") == "키움"
    assert normalize_team("부산") == "롯데"
    assert normalize_team("없는팀") is None


def test_render_frame():
    T, p, cur, rem = _synthetic()
    r = S.simulate(cur, rem, p, n=3000, seed=1)
    ctx = {"standings": T, "year": 2026, "period": "올해"}
    txt = R.render_team("LG", {"올해": r}, ctx)
    assert txt.startswith("━") and txt.endswith("━") and "우승" in txt
    txt2 = R.render_all(r, "올해", ctx)
    assert txt2.startswith("━") and "우승" in txt2


if __name__ == "__main__":
    for k, fn in list(globals().items()):
        if k.startswith("test_"):
            fn(); print(f"  ✓ {k}")
    print("전부 통과 ✅")
