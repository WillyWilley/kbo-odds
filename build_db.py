"""과거 KBO 시즌 → 정규시즌 경기 JSON DB로 굳히기 (1회/주기 실행, Python 전용).

kbo_data.fetch_season(KBO asmx 직접조회)로 시즌별 완료경기를 받아 data/seasons.json 저장.
과거 시즌은 안 바뀌므로 런타임엔 이 파일만 읽음.
사용: python build_db.py 2022 2023 2024 2025
"""
import json
import sys
from pathlib import Path

from kbo_data import fetch_season

DATA = Path(__file__).parent / "data"


def main():
    years = [int(y) for y in sys.argv[1:]] or [2022, 2023, 2024, 2025]
    DATA.mkdir(exist_ok=True)
    db = {}
    for y in years:
        games = [{"d": g["d"], "h": g["h"], "a": g["a"], "hs": g["hs"], "as": g["as"]}
                 for g in fetch_season(y) if g["fin"]]
        db[str(y)] = games
        print(f"{y}: 정규시즌 {len(games)}경기")
    out = DATA / "seasons.json"
    out.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
    print(f"→ {out} ({sum(len(v) for v in db.values())}경기)")


if __name__ == "__main__":
    main()
