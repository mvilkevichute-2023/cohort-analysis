"""Генерация синтетических данных интернет-магазина косметики.

Период: январь 2025 — июнь 2026. Три таблицы:
- customers  — клиент, дата первой покупки, канал привлечения, город;
- orders     — все заказы клиентов;
- marketing  — расходы на привлечение по месяцам и каналам.

В данных заложены истории, которые должен найти аналитик:
- «Соцсети» приводят больше всего клиентов, но они почти не возвращаются;
- «Рекомендации друзей» — мало клиентов, зато самые лояльные;
- с октября 2025 запущена программа лояльности — удержание новых когорт выросло.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2026-06-30")
LOYALTY_START = pd.Timestamp("2025-10-01")

CHANNELS = {
    # share — доля новых клиентов, r1 — шанс купить снова в 1-й месяц после первой покупки,
    # decay — как быстро он падает, check — медианный чек, cac — стоимость привлечения
    # (для SEO — контент и продвижение, для рекомендаций — бонус пригласившему)
    "Соцсети":              {"share": 0.40, "r1": 0.11, "decay": 0.80, "check": 1500, "cac": 1100},
    "Контекстная реклама":  {"share": 0.30, "r1": 0.22, "decay": 0.90, "check": 2100, "cac": 1500},
    "Поиск (SEO)":          {"share": 0.20, "r1": 0.26, "decay": 0.92, "check": 2200, "cac": 600},
    "Рекомендации друзей":  {"share": 0.10, "r1": 0.34, "decay": 0.95, "check": 2400, "cac": 700},
}
CITIES = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Другие"]
CITY_P = [0.32, 0.16, 0.08, 0.08, 0.06, 0.30]


def generate(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    months = pd.date_range(START, END, freq="MS")
    names = list(CHANNELS)
    shares = [CHANNELS[c]["share"] for c in names]

    customers, orders, marketing = [], [], []
    cid, oid = 1, 1
    for i, m in enumerate(months):
        n_new = int(1200 * (1 + 0.03 * i) * (1.25 if m.month in (11, 12) else 1.0))
        chans = rng.choice(names, size=n_new, p=shares)
        days_in_month = m.days_in_month
        for ch in names:
            n_ch = int((chans == ch).sum())
            spend = n_ch * CHANNELS[ch]["cac"] * rng.uniform(0.92, 1.08)
            marketing.append((m.date(), ch, round(spend, -2)))
        for ch in chans:
            cfg = CHANNELS[ch]
            first = m + pd.Timedelta(days=int(rng.integers(0, days_in_month)))
            city = rng.choice(CITIES, p=CITY_P)
            customers.append((cid, first.date(), ch, city))
            loyalty = 1.35 if first >= LOYALTY_START else 1.0
            # индивидуальная «любовь к магазину»: у кого-то выше, у кого-то ниже
            taste = rng.lognormal(0, 0.5)
            check_scale = cfg["check"] * rng.lognormal(0, 0.25)

            orders.append((oid, cid, first.date(), round(check_scale * rng.lognormal(0, 0.35), 0)))
            oid += 1
            k = 1
            while True:
                month_start = m + pd.DateOffset(months=k)  # k-й календарный месяц после когорты
                if month_start > END:
                    break
                p = min(cfg["r1"] * cfg["decay"] ** (k - 1) * loyalty * taste, 0.9)
                if rng.random() < p:
                    d = month_start + pd.Timedelta(days=int(rng.integers(0, month_start.days_in_month)))
                    if d <= END:
                        orders.append((oid, cid, d.date(), round(check_scale * rng.lognormal(0, 0.35), 0)))
                        oid += 1
                k += 1
            cid += 1

    customers = pd.DataFrame(customers, columns=["customer_id", "first_order_date", "channel", "city"])
    orders = pd.DataFrame(orders, columns=["order_id", "customer_id", "order_date", "amount"])
    marketing = pd.DataFrame(marketing, columns=["month", "channel", "spend"])
    return customers, orders, marketing


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "data"
    out.mkdir(exist_ok=True)
    customers, orders, marketing = generate()
    customers.to_csv(out / "customers.csv", index=False)
    orders.to_csv(out / "orders.csv", index=False)
    marketing.to_csv(out / "marketing.csv", index=False)
    print(f"customers: {len(customers):,}, orders: {len(orders):,}, marketing: {len(marketing)}")


if __name__ == "__main__":
    main()
