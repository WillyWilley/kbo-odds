"""KBO 우승확률 시뮬레이션 엔진 (순수 함수 — 검증 완료 모델).

모델: Pythagenpat(실력) + 평균회귀(#1) + Log5(경기) + 몬테카를로(시즌) + 이항분포 시리즈(#2).
구현 정확성은 닫힌해·교과서값 대조로 검증됨(설계서 §10.2).
"""
import math
import random

TEAMS = ["LG", "KT", "삼성", "KIA", "두산", "한화", "롯데", "NC", "SSG", "키움"]
HOME = 0.035        # 홈 어드밴티지(승률 가산, KBO 홈승률 ~53%)
PRIOR_G = 40        # 평균회귀 강도: .500 가상 PRIOR_G경기를 섞음(소표본 과신 방지, #1)


def aggregate(games):
    """경기 리스트 → 팀별 {w,l,t,rs,ra,g}."""
    T = {n: {"w": 0, "l": 0, "t": 0, "rs": 0, "ra": 0, "g": 0} for n in TEAMS}
    for x in games:
        h, a = x["h"], x["a"]
        if h not in T or a not in T:
            continue
        hs, as_ = x["hs"], x["as"]
        T[h]["rs"] += hs; T[h]["ra"] += as_; T[h]["g"] += 1
        T[a]["rs"] += as_; T[a]["ra"] += hs; T[a]["g"] += 1
        if hs > as_:
            T[h]["w"] += 1; T[a]["l"] += 1
        elif as_ > hs:
            T[a]["w"] += 1; T[h]["l"] += 1
        else:
            T[h]["t"] += 1; T[a]["t"] += 1
    return T


def strength(T):
    """팀별 실력 win%(0~1) — Pythagenpat + 평균회귀(.500 shrinkage)."""
    p = {}
    for n in TEAMS:
        s = T[n]
        g = s["g"]
        if g < 1:
            p[n] = 0.5
            continue
        x = ((s["rs"] + s["ra"]) / g) ** 0.287
        pyth = s["rs"] ** x / (s["rs"] ** x + s["ra"] ** x)
        # #1 평균회귀: 표본(g)이 작을수록 .500으로 끌어당김
        p[n] = (pyth * g + 0.5 * PRIOR_G) / (g + PRIOR_G)
    return p


def log5(a, b):
    """두 팀 실력(a,b)에서 a가 이길 확률 (Bradley-Terry)."""
    d = a + b - 2 * a * b
    return 0.5 if d == 0 else (a - a * b) / d


def _comb(n, k):
    r = 1
    for i in range(k):
        r = r * (n - i) // (i + 1)
    return r


def series_prob(p, need, pre=0):
    """#2 이항분포 닫힌 해: 매경기 승률 p인 팀이 시리즈 이길 확률.
    need=목표 승수(BO3=2/BO5=3/BO7=4), pre=이미 따낸 승수(와일드카드 4위 1선승).
    """
    a = need - pre          # 더 따야 할 승수
    b = need                # 상대가 따야 할 승수
    P = 0.0
    for k in range(b):      # 상대가 k승 하는 동안 내가 a승 먼저
        P += _comb(a - 1 + k, k) * p ** a * (1 - p) ** k
    return P


def simulate(current_wins, remaining, p, n=20000, seed=42):
    """몬테카를로 시즌 시뮬 → {champ:{팀:확률}, po:{팀:확률}}.
    current_wins: {팀:현재승수} · remaining: [{h,a}] 남은경기 · p: strength()
    """
    rng = random.Random(seed)
    champ = {t: 0 for t in TEAMS}
    po = {t: 0 for t in TEAMS}
    wsum = {t: 0 for t in TEAMS}              # 예상 최종 승수 누적(평균용)
    pos_cnt = {t: [0] * 10 for t in TEAMS}   # 최종 순위(1~10위) 분포
    for _ in range(n):
        w = dict(current_wins)
        for g in remaining:
            ph = log5(p.get(g["h"], .5), p.get(g["a"], .5)) + HOME
            if rng.random() < ph:
                w[g["h"]] += 1
            else:
                w[g["a"]] += 1
        for t in TEAMS:
            wsum[t] += w[t]
        # 순위(승수 → 동률시 실력)
        rank = sorted(TEAMS, key=lambda t: (w[t], p[t]), reverse=True)
        for i, t in enumerate(rank):
            pos_cnt[t][i] += 1
        s1, s2, s3, s4, s5 = rank[:5]
        for t in rank[:5]:
            po[t] += 1

        def adv(hi, lo, need, pre=0):
            ph = log5(p[hi], p[lo]) + HOME
            return hi if rng.random() < series_prob(ph, need, pre) else lo
        win = adv(s4, s5, 2, 1)   # 와일드카드(4위 1선승, BO3)
        win = adv(s3, win, 3)     # 준PO (BO5)
        win = adv(s2, win, 3)     # PO (BO5)
        win = adv(s1, win, 4)     # 한국시리즈 (BO7)
        champ[win] += 1

    def _rank_stats(t):
        c = pos_cnt[t]
        mode = c.index(max(c)) + 1                       # 가장 가능성 높은 순위
        # 10~90% 구간(누적)
        lo = hi = None
        acc = 0
        for i, v in enumerate(c):
            acc += v
            if lo is None and acc >= 0.1 * n:
                lo = i + 1
            if hi is None and acc >= 0.9 * n:
                hi = i + 1
        return {"mode": mode, "lo": lo or mode, "hi": hi or mode}

    return {"champ": {t: champ[t] / n for t in TEAMS},
            "po": {t: po[t] / n for t in TEAMS},
            "exp_wins": {t: wsum[t] / n for t in TEAMS},   # 예상 최종 승수
            "rank": {t: _rank_stats(t) for t in TEAMS}}


if __name__ == "__main__":
    # 닫힌 해 자기검증
    assert abs(series_prob(0.5, 4) - 0.5) < 1e-9, "BO7 p=.5 should be .5"
    assert abs(series_prob(0.6, 2, 1) - (1 - 0.4 ** 2)) < 1e-9, "와일드카드 공식"
    assert abs(log5(0.6, 0.4) - 0.692307) < 1e-5
    print("simulate.py 자기검증 통과 ✅ (series_prob/log5 닫힌해 일치)")
