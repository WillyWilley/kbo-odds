"""과거 KBO 시즌 → 정규시즌 경기 JSON DB로 굳히기 (1회/주기 실행).

kbo-game(npm)을 node로 호출해 시즌별 경기를 받아, 정규시즌만 필터해
data/seasons.json 으로 저장한다. 과거 시즌은 안 바뀌므로 런타임엔 이 파일만 읽음.

정규시즌 필터: 10개 구단 경기 + 4~9월 (시범경기 3월·포스트시즌 10월~·올스타 제외).
사용: python build_db.py 2022 2023 2024 2025   (인자 없으면 기본 4시즌)
"""
import json
import subprocess
import sys
from pathlib import Path

TEAMS = ["LG", "KT", "삼성", "KIA", "두산", "한화", "롯데", "NC", "SSG", "키움"]
DATA = Path(__file__).parent / "data"
REG_MONTHS = {"04", "05", "06", "07", "08", "09"}

# node 인라인: 한 시즌(3/15~11/15) 완료경기 수집 → stdout JSON
_NODE = r"""
import path from "node:path";import { pathToFileURL } from "node:url";
const entry = pathToFileURL(path.join(process.env.GLOBAL_NPM_ROOT, "kbo-game", "dist", "index.js")).href;
const { getGame } = await import(entry);
function* D(s,e){for(let d=new Date(s);d<=new Date(e);d.setDate(d.getDate()+1))yield new Date(d);}
const Y=process.argv[1];
const ds=[...D(`${Y}-03-15T00:00:00+09:00`,`${Y}-11-15T00:00:00+09:00`)];
const all=[];
for(let i=0;i<ds.length;i+=24){const r=await Promise.all(ds.slice(i,i+24).map(d=>getGame(d).catch(()=>[])));for(const g of r)if(Array.isArray(g))all.push(...g);}
const out=all.filter(g=>g&&g.homeTeam&&g.awayTeam&&g.score&&g.status==="FINISHED")
  .map(g=>({d:(typeof g.date==="string"?g.date:new Date(g.date).toISOString()).slice(0,10),h:g.homeTeam,a:g.awayTeam,hs:g.score.home,as:g.score.away}));
process.stdout.write(JSON.stringify(out));
"""


def fetch_season(year: int):
    npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, shell=True).stdout.strip()
    env = {"GLOBAL_NPM_ROOT": npm_root}
    import os
    full_env = {**os.environ, **env}
    r = subprocess.run(["node", "--input-type=module", "-e", _NODE, str(year)],
                       capture_output=True, text=True, env=full_env, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"{year} fetch 실패: {r.stderr[:300]}")
    games = json.loads(r.stdout)
    # 정규시즌만
    reg = [g for g in games if g["h"] in TEAMS and g["a"] in TEAMS
           and g["d"][5:7] in REG_MONTHS]
    return reg


def main():
    years = [int(y) for y in sys.argv[1:]] or [2022, 2023, 2024, 2025]
    DATA.mkdir(exist_ok=True)
    db = {}
    for y in years:
        reg = fetch_season(y)
        db[str(y)] = reg
        print(f"{y}: 정규시즌 {len(reg)}경기 저장")
    out = DATA / "seasons.json"
    out.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
    print(f"→ {out} ({sum(len(v) for v in db.values())}경기)")


if __name__ == "__main__":
    main()
