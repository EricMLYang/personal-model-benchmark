# BENCH-GRADER-CANARY-7f3a9c1e
"""X03 的標準解：從 CSV 算出 10 題答案，以及報告數字追溯用的「合法數值集合」。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load(data: Path):
    stores = pd.read_csv(data / "stores.csv")
    plays_raw = pd.read_csv(data / "plays.csv")
    sales_raw = pd.read_csv(data / "sales.csv")
    packs = pd.read_csv(data / "packs.csv")
    open_ids = set(stores.loc[stores.status == "open", "store_id"])
    plays = plays_raw.drop_duplicates()
    plays = plays[plays.store_id.isin(open_ids)]
    sales = sales_raw[sales_raw.revenue.notna()]
    sales = sales[sales.store_id.isin(open_ids)].merge(stores, on="store_id")
    plays = plays.merge(stores, on="store_id")
    return stores, plays_raw, sales_raw, plays, sales, packs


def pack_metrics(plays, sales, packs):
    out = {}
    for _, p in packs.iterrows():
        pp = plays[plays.pack == p.pack]
        slots = p.target_slots.split("|")
        imp = pp.impressions.sum()
        align = pp[pp.slot.isin(slots)].impressions.sum() / imp * 100
        keys = pp[["date", "store_id", "slot"]].drop_duplicates()
        rev = sales[sales.category == p.target_category].merge(keys, on=["date", "store_id", "slot"]).revenue.sum()
        out[p.pack] = {"impressions": int(imp), "align": align, "per_mille": rev / imp * 1000, "target_rev": rev}
    return out


def answers(data: Path) -> dict:
    stores, plays_raw, sales_raw, plays, sales, packs = load(data)
    pm = pack_metrics(plays, sales, packs)
    office_open = ((stores.store_type == "辦公型") & (stores.status == "open")).sum()
    q04 = sales[(sales.store_type == "辦公型") & (sales.slot == "午餐")].revenue.sum() / (office_open * 14)
    s = sales[(sales.region == "南區") & (sales.slot == "晚餐")]
    coffee = sales[sales.category == "咖啡"]
    w1 = coffee[coffee.date <= "2026-09-07"].revenue.sum()
    w2 = coffee[coffee.date >= "2026-09-08"].revenue.sum()
    best = max(pm, key=lambda k: pm[k]["per_mille"])
    return {
        "Q01": int(plays.impressions.sum()),
        "Q02": int(len(plays_raw) - len(plays_raw.drop_duplicates())),
        "Q03": sales.groupby("store_type").revenue.sum().idxmax(),
        "Q04": round(q04, 2),
        "Q05": round(pm["P03"]["align"], 2),
        "Q06": best,
        "Q07": round(pm[best]["per_mille"], 2),
        "Q08": round(s.revenue.sum() / s.transactions.sum(), 2),
        "Q09": round((w2 - w1) / w1 * 100, 2),
        "Q10": int(sales_raw.revenue.isna().sum()),
    }


def allowed_numbers(data: Path) -> set[float]:
    """報告中可出現的數值（各種常見彙總、比例、排名數值）。"""
    stores, plays_raw, sales_raw, plays, sales, packs = load(data)
    vals: list[float] = []
    total_rev = sales.revenue.sum()
    total_imp = plays.impressions.sum()
    vals += [total_rev, total_imp, sales.transactions.sum(), total_rev / sales.transactions.sum(),
             len(stores), (stores.status == "open").sum(), (stores.status == "closed").sum(), 14, 7, 5,
             len(plays_raw), len(plays_raw.drop_duplicates()), len(sales_raw), len(sales_raw) - sales_raw.revenue.isna().sum(),
             len(sales), len(plays)]
    for dim in ("store_type", "region", "slot", "category"):
        g = sales.groupby(dim)
        rev = g.revenue.sum()
        vals += list(rev) + list(rev / total_rev * 100) + list(rev / g.transactions.sum()) + list(g.transactions.sum())
        if dim in ("store_type", "region"):
            n = stores[stores.status == "open"].groupby(dim).size()
            vals += list(n) + list(rev / n) + list(rev / n / 14)
    for dim in ("slot", "pack", "store_type", "region"):
        imp = plays.groupby(dim).impressions.sum()
        vals += list(imp) + list(imp / total_imp * 100)
    for a, b in (("store_type", "slot"), ("region", "slot"), ("category", "slot")):
        g = sales.groupby([a, b])
        vals += list(g.revenue.sum()) + list(g.revenue.sum() / g.transactions.sum())
    office_open = ((stores.store_type == "辦公型") & (stores.status == "open")).sum()
    for st in stores.store_type.unique():
        n = ((stores.store_type == st) & (stores.status == "open")).sum()
        for sl in sales.slot.unique():
            vals.append(sales[(sales.store_type == st) & (sales.slot == sl)].revenue.sum() / (n * 14))
    pm = pack_metrics(plays, sales, packs)
    for m in pm.values():
        vals += [m["impressions"], m["align"], m["per_mille"], m["target_rev"], 100 - m["align"]]
    for c in sales.category.unique():
        cs = sales[sales.category == c]
        w1 = cs[cs.date <= "2026-09-07"].revenue.sum()
        w2 = cs[cs.date >= "2026-09-08"].revenue.sum()
        vals += [w1, w2, w2 - w1, (w2 - w1) / w1 * 100]
    w1 = sales[sales.date <= "2026-09-07"].revenue.sum()
    w2 = sales[sales.date >= "2026-09-08"].revenue.sum()
    vals += [w1, w2, (w2 - w1) / w1 * 100]
    vals += [v for v in answers(data).values() if isinstance(v, (int, float))]
    vals += [office_open, len(plays_raw) - len(plays_raw.drop_duplicates()), sales_raw.revenue.isna().sum()]
    out = set()
    for v in vals:
        v = float(v)
        for scale in (1, 1 / 1000, 1 / 10000, 1 / 1_000_000):  # 千、萬、百萬元的換算
            out.add(round(v * scale, 6))
    return out
