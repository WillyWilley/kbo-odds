"""데이터 레이어 — 과거 DB(내장) + 올해 경기(API 캐시) + 팀명 정규화 + 다년 가중.

런타임 원칙: 과거는 data/seasons.json 만 읽고, 올해만 kbo-game API를 TTL 캐시로 가볍게.
"""
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from simulate import TEAMS, aggregate, strength

DATA = Path(__file__).parent / "data"
TTL = 6 * 3600          # 올해 데이터 캐시 6시간
REG_MONTHS = {"04", "05", "06", "07", "08", "09", "10"}

# 팀명 정규화 (별칭·구단명 변천·해체팀)
_ALIAS = {
    "엘지": "LG", "엘쥐": "LG", "lg": "LG",
    "케이티": "KT", "kt": "KT", "위즈": "KT",
    "기아": "KIA", "기아타이거즈": "KIA", "kia": "KIA", "해태": "KIA", "타이거즈": "KIA",
    "쓱": "SSG", "ssg": "SSG", "랜더스": "SSG", "sk": "SSG", "에스케이": "SSG",
    "엔씨": "NC", "nc": "NC", "다이노스": "NC",
    "넥센": "키움", "히어로즈": "키움", "키움히어로즈": "키움", "현대": "키움",
    "두산베어스": "두산", "베어스": "두산",
    "삼성라이온즈": "삼성", "라이온즈": "삼성",
    "롯데자이언츠": "롯데", "자이언츠": "롯데", "부산": "롯데",
    "한화이글스": "한화", "이글스": "한화",
}

_cache = {"t": 0, "data": None}


def normalize_team(name):
    """입력 팀명 → 정규 팀명(10개) 또는 None."""
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


_NODE = r"""
import path from "node:path";import { pathToFileURL } from "node:url";
const entry = pathToFileURL(path.join(process.env.GLOBAL_NPM_ROOT, "kbo-game", "dist", "index.js")).href;
const { getGame } = await import(entry);
function* D(s,e){for(let d=new Date(s);d<=new Date(e);d.setDate(d.getDate()+1))yield new Date(d);}
const Y=process.argv[1];
const ds=[...D(`${Y}-03-15T00:00:00+09:00`,`${Y}-10-15T00:00:00+09:00`)];
const all=[];
for(let i=0;i<ds.length;i+=24){const r=await Promise.all(ds.slice(i,i+24).map(d=>getGame(d).catch(()=>[])));for(const g of r)if(Array.isArray(g))all.push(...g);}
const norm=g=>(typeof g.date==="string"?g.date:new Date(g.date).toISOString()).slice(0,10);
const out=all.filter(g=>g&&g.homeTeam&&g.awayTeam).map(g=>({d:norm(g),h:g.homeTeam,a:g.awayTeam,
  fin:g.status==="FINISHED"&&g.score?1:0, hs:g.score?g.score.home:null, as:g.score?g.score.away:null}));
process.stdout.write(JSON.stringify(out));
"""


def _fetch_current(year):
    npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, shell=True).stdout.strip()
    env = {**os.environ, "GLOBAL_NPM_ROOT": npm_root}
    r = subprocess.run(["node", "--input-type=module", "-e", _NODE, str(year)],
                       capture_output=True, text=True, env=env, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"current fetch 실패: {r.stderr[:200]}")
    games = json.loads(r.stdout)
    reg = [g for g in games if g["h"] in TEAMS and g["a"] in TEAMS and g["d"][5:7] in REG_MONTHS]
    return reg


def current_season(year=None):
    """올해 경기 (TTL 캐시). {played:[...], remaining:[{h,a}], year, n_played}."""
    if year is None:
        year = datetime.now().year
    if _cache["data"] and time.time() - _cache["t"] < TTL:
        return _cache["data"]
    games = _fetch_current(year)
    played = [g for g in games if g["fin"]]
    remaining = [{"h": g["h"], "a": g["a"]} for g in games if not g["fin"]]
    data = {"played": played, "remaining": remaining, "year": year, "n_played": len(played)}
    _cache.update(t=time.time(), data=data)
    return data


def load_past():
    f = DATA / "seasons.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _combine(weighted):
    """[(T, w)] → 가중 합산 T (rs/ra/g에 가중치)."""
    C = {n: {"w": 0, "l": 0, "t": 0, "rs": 0.0, "ra": 0.0, "g": 0.0} for n in TEAMS}
    for T, w in weighted:
        for n in TEAMS:
            for k in ("rs", "ra", "g"):
                C[n][k] += T[n][k] * w
    return C


def context(period="올해", year=None):
    """period(올해/2년/3년)에 따른 시뮬 입력 묶음.
    반환: {current_wins, remaining, strength, n_played, year, period}
    """
    cur = current_season(year)
    y = cur["year"]
    curT = aggregate(cur["played"])
    current_wins = {n: curT[n]["w"] for n in TEAMS}

    past = load_past()
    # 가중치: 올해 1.0, 작년 0.5, 재작년 0.25 ...
    weights = {"올해": [(curT, 1.0)],
               "2년": [(curT, 1.0), (aggregate(past.get(str(y - 1), [])), 0.5)],
               "3년": [(curT, 1.0), (aggregate(past.get(str(y - 1), [])), 0.5),
                       (aggregate(past.get(str(y - 2), [])), 0.25)]}
    combo = _combine(weights.get(period, weights["올해"]))
    p = strength(combo)
    return {"current_wins": current_wins, "remaining": cur["remaining"],
            "strength": p, "n_played": cur["n_played"], "year": y, "period": period,
            "standings": curT}


if __name__ == "__main__":
    print("팀명 정규화:", normalize_team("기아"), normalize_team("쓱"), normalize_team("넥센"), normalize_team("부산"))
    ctx = context("올해")
    print(f"올해({ctx['year']}) 완료 {ctx['n_played']}경기 · 남은 {len(ctx['remaining'])}")
    top = sorted(TEAMS, key=lambda t: ctx["strength"][t], reverse=True)[:3]
    print("실력 상위3:", [(t, round(ctx["strength"][t], 3)) for t in top])
