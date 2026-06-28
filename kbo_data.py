"""데이터 레이어 — 과거 DB(내장) + 올해 경기(KBO API 직접조회, Python stdlib) + 정규화 + 다년가중.

★node 의존 제거: koreabaseball.com asmx를 urllib로 직접 POST (kbo-game과 동일 소스).
런타임: 과거는 data/seasons.json, 올해만 TTL 캐시로 가볍게.
"""
import json
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date as _date, timedelta
from pathlib import Path

from simulate import TEAMS, aggregate, strength

DATA = Path(__file__).parent / "data"
TTL = 6 * 3600
REG_MONTHS = {"04", "05", "06", "07", "08", "09", "10"}
_URL = "https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList"
_HDRS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.koreabaseball.com",
    "Referer": "https://www.koreabaseball.com/",
    "User-Agent": "Mozilla/5.0 (kbo-odds-mcp)",
}

_ALIAS = {
    "엘지": "LG", "엘쥐": "LG", "lg": "LG",
    "케이티": "KT", "kt": "KT", "위즈": "KT",
    "기아": "KIA", "기아타이거즈": "KIA", "kia": "KIA", "해태": "KIA", "타이거즈": "KIA",
    "쓱": "SSG", "ssg": "SSG", "랜더스": "SSG", "sk": "SSG", "에스케이": "SSG",
    "엔씨": "NC", "nc": "NC", "다이노스": "NC",
    "넥센": "키움", "히어로즈": "키움", "키움히어로즈": "키움", "현대": "키움",
    "두산베어스": "두산", "베어스": "두산", "삼성라이온즈": "삼성", "라이온즈": "삼성",
    "롯데자이언츠": "롯데", "자이언츠": "롯데", "부산": "롯데",
    "한화이글스": "한화", "이글스": "한화",
}
_cache = {"t": 0, "data": None}


def normalize_team(name):
    if not name:
        return None
    s = name.strip()
    if s in TEAMS:
        return s
    low = s.lower().replace(" ", "")
    if low in _ALIAS:
        return _ALIAS[low]
    for n in TEAMS:
        if n in s or s in n:
            return n
    return None


def _fetch_date(ymd):
    """하루치 경기 조회 → 정규화 [{d,h,a,fin,hs,as}]. 실패 시 []"""
    body = urllib.parse.urlencode({"leId": 1, "srId": "0,1,3,4,5,6,7,8,9", "date": ymd}).encode()
    try:
        req = urllib.request.Request(_URL, data=body, headers=_HDRS)
        with urllib.request.urlopen(req, timeout=10) as r:
            games = json.load(r).get("game") or []
    except Exception:
        return []
    out = []
    for g in games:
        if g.get("CANCEL_SC_ID") != "0":          # 취소경기 제외
            continue
        h, a = g.get("HOME_NM"), g.get("AWAY_NM")
        if h not in TEAMS or a not in TEAMS:       # 올스타·시범 등 제외
            continue
        d = g["G_DT"]
        fin = g.get("GAME_STATE_SC") == "3"
        rec = {"d": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "h": h, "a": a, "fin": fin}
        if fin:
            try:
                rec["hs"] = int(g["B_SCORE_CN"]); rec["as"] = int(g["T_SCORE_CN"])
            except (TypeError, ValueError, KeyError):
                continue
        out.append(rec)
    return out


def fetch_season(year, start="03-15", end="10-31"):
    """시즌 전체 경기 병렬 조회 (정규시즌 월만)."""
    d0 = _date(year, int(start[:2]), int(start[3:]))
    d1 = _date(year, int(end[:2]), int(end[3:]))
    days = [(d0 + timedelta(n)).strftime("%Y%m%d") for n in range((d1 - d0).days + 1)]
    games = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for res in ex.map(_fetch_date, days):
            games.extend(res)
    return [g for g in games if g["d"][5:7] in REG_MONTHS]


def current_season(year=None):
    if year is None:
        year = datetime.now().year
    if _cache["data"] and time.time() - _cache["t"] < TTL:
        return _cache["data"]
    games = fetch_season(year)
    played = [g for g in games if g["fin"]]
    remaining = [{"h": g["h"], "a": g["a"]} for g in games if not g["fin"]]
    data = {"played": played, "remaining": remaining, "year": year, "n_played": len(played)}
    if played:                       # 빈 응답이면 캐시하지 않음(다음 호출 재시도)
        _cache.update(t=time.time(), data=data)
    return data


def load_past():
    f = DATA / "seasons.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _combine(weighted):
    C = {n: {"w": 0, "l": 0, "t": 0, "rs": 0.0, "ra": 0.0, "g": 0.0} for n in TEAMS}
    for T, w in weighted:
        for n in TEAMS:
            for k in ("rs", "ra", "g"):
                C[n][k] += T[n][k] * w
    return C


def context(period="올해", year=None):
    cur = current_season(year)
    y = cur["year"]
    curT = aggregate(cur["played"])
    current_wins = {n: curT[n]["w"] for n in TEAMS}
    past = load_past()
    weights = {"올해": [(curT, 1.0)],
               "2년": [(curT, 1.0), (aggregate(past.get(str(y - 1), [])), 0.5)],
               "3년": [(curT, 1.0), (aggregate(past.get(str(y - 1), [])), 0.5),
                       (aggregate(past.get(str(y - 2), [])), 0.25)]}
    p = strength(_combine(weights.get(period, weights["올해"])))
    return {"current_wins": current_wins, "remaining": cur["remaining"], "strength": p,
            "n_played": cur["n_played"], "year": y, "period": period, "standings": curT}


if __name__ == "__main__":
    print("정규화:", normalize_team("기아"), normalize_team("쓱"), normalize_team("넥센"))
    ctx = context("올해")
    print(f"올해({ctx['year']}) 완료 {ctx['n_played']} · 남은 {len(ctx['remaining'])}")
    print("상위3:", sorted(TEAMS, key=lambda t: ctx['strength'][t], reverse=True)[:3])
