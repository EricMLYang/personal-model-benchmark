"""產生 X03 的合成門市看板資料（4 個 CSV）。

python generators/x03_csv.py  →  tasks/X03_csv_analysis/inputs/data/*.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tasks" / "X03_csv_analysis" / "inputs" / "data"
TYPES = ["住宅型", "辦公型", "交通型", "學區型"]
REGIONS = ["北區", "中區", "南區"]
SLOTS = ["早餐", "午餐", "下午", "晚餐", "宵夜"]
CATS = ["咖啡", "便當", "甜點", "飲料", "鮮食"]
PACKS = [
    ("P01", "上班族早餐", "咖啡", "早餐"),
    ("P02", "午餐便當", "便當", "午餐|晚餐"),
    ("P03", "午後甜點", "甜點", "下午"),
    ("P04", "通勤飲料", "飲料", "早餐|晚餐"),
    ("P05", "宵夜鮮食", "鮮食", "宵夜"),
]
SLOT_W = {"早餐": 1.2, "午餐": 1.5, "下午": 0.8, "晚餐": 1.3, "宵夜": 0.6}
TYPE_SLOT = {"辦公型": {"早餐": 1.4, "午餐": 1.8, "宵夜": 0.4}, "交通型": {"早餐": 1.6, "晚餐": 1.4},
             "學區型": {"下午": 1.7, "午餐": 1.3}, "住宅型": {"晚餐": 1.5, "宵夜": 1.3}}


def main() -> None:
    rnd = random.Random(42)
    OUT.mkdir(parents=True, exist_ok=True)
    stores = []
    for i in range(1, 41):
        stores.append({"store_id": f"S{i:03d}", "store_type": TYPES[i % 4], "region": REGIONS[(i * 7) % 3],
                       "status": "closed" if i in (7, 22, 35) else "open",
                       "opened": (dt.date(2019, 1, 1) + dt.timedelta(days=rnd.randint(0, 2000))).isoformat()})
    days = [dt.date(2026, 9, 1) + dt.timedelta(days=k) for k in range(14)]

    plays, sales = [], []
    for s in stores:
        for d in days:
            for slot in SLOTS:
                n_packs = rnd.choice([1, 1, 2])
                for p in rnd.sample(PACKS, n_packs):
                    imp = int(rnd.gauss(300, 60) * SLOT_W[slot])
                    plays.append([d.isoformat(), s["store_id"], slot, p[0], max(imp, 20)])
                for c in CATS:
                    base = 900 * SLOT_W[slot] * TYPE_SLOT.get(s["store_type"], {}).get(slot, 1.0)
                    if (c, slot) in {("咖啡", "早餐"), ("便當", "午餐"), ("甜點", "下午"), ("鮮食", "宵夜")}:
                        base *= 1.5 if c == "咖啡" else 1.8
                    if c == "咖啡" and d >= dt.date(2026, 9, 8):
                        base *= 1.12
                    tx = max(1, int(rnd.gauss(base / 85, base / 400)))
                    rev = round(tx * rnd.uniform(70, 110))
                    sales.append([d.isoformat(), s["store_id"], slot, c, rev, tx])
    # 重複上傳的播放紀錄
    for row in rnd.sample(plays, 37):
        plays.append(list(row))
    rnd.shuffle(plays)
    # POS 回傳失敗：營收空白
    for idx in rnd.sample(range(len(sales)), 58):
        sales[idx][4] = ""

    def write(name, header, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    write("stores.csv", ["store_id", "store_type", "region", "status", "opened"],
          [[s[k] for k in ("store_id", "store_type", "region", "status", "opened")] for s in stores])
    write("plays.csv", ["date", "store_id", "slot", "pack", "impressions"], plays)
    write("sales.csv", ["date", "store_id", "slot", "category", "revenue", "transactions"], sales)
    write("packs.csv", ["pack", "name", "target_category", "target_slots"], [list(p) for p in PACKS])
    print("ok")


if __name__ == "__main__":
    main()
