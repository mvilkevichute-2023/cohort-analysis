"""Прогон всех SQL-запросов, вывод ключевых цифр и построение графиков.

Запуск:  python -m cohorts.report
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

from cohorts.data import connect, query

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "images"

CHANNEL_COLORS = {  # порядок фиксирован, палитра проверена на различимость при дальтонизме
    "Соцсети": "#C8327A",
    "Контекстная реклама": "#2a78d6",
    "Поиск (SEO)": "#eda100",
    "Рекомендации друзей": "#1baf7a",
}
INK, MUTED, GRID = "#2B2B2B", "#6B6B6B", "#E6E6E6"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "axes.axisbelow": True,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    }
)


def title(ax, text: str) -> None:
    ax.set_title(text, loc="left", color=INK, fontsize=13, fontweight="bold")


def plot_heatmap(ret: pd.DataFrame, path: Path) -> None:
    mat = ret.pivot(index="cohort_month", columns="month_number", values="retention_pct")
    mat = mat.drop(columns=0)
    mat.index = [d.strftime("%m.%Y") for d in pd.to_datetime(mat.index)]
    fig, ax = plt.subplots(figsize=(10, 6.4))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("pink", ["#FCEAF2", "#C8327A", "#6E1440"])
    im = ax.imshow(mat.values, cmap=cmap, vmin=0, vmax=40, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if v > 22 else INK)
    ax.set_xticks(range(mat.shape[1]), mat.columns)
    ax.set_yticks(range(mat.shape[0]), mat.index)
    ax.set_xlabel("Месяц после первой покупки")
    ax.grid(False)
    ax.axhline(8.5, color=INK, linewidth=1.5, linestyle="--")
    ax.text(mat.shape[1] - 0.6, 8.35, "запуск программы лояльности ↓", ha="right", va="bottom", fontsize=9, color=INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.025)
    cb.set_label("% клиентов когорты, купивших снова", color=MUTED)
    title(ax, "Удержание по когортам: после октября 2025 клиенты возвращаются чаще")
    fig.savefig(path)
    plt.close(fig)


def plot_channel_curves(con, path: Path) -> None:
    df = con.execute(
        """
        WITH activity AS (
            SELECT DISTINCT c.customer_id, c.channel,
                   (EXTRACT(YEAR FROM o.order_date) - EXTRACT(YEAR FROM c.first_order_date)) * 12
                 + (EXTRACT(MONTH FROM o.order_date) - EXTRACT(MONTH FROM c.first_order_date)) AS month_number
            FROM customers c JOIN orders o USING (customer_id)
            WHERE c.first_order_date < DATE '2026-01-01'
        )
        SELECT channel, month_number,
               COUNT(DISTINCT customer_id) * 100.0
               / MAX(COUNT(DISTINCT customer_id)) OVER (PARTITION BY channel) AS retention_pct
        FROM activity
        WHERE month_number BETWEEN 1 AND 6
           OR month_number = 0
        GROUP BY channel, month_number
        ORDER BY channel, month_number
        """
    ).df()
    df = df[df.month_number > 0]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    for ch, color in CHANNEL_COLORS.items():
        d = df[df.channel == ch]
        ax.plot(d.month_number, d.retention_pct / 100, color=color, linewidth=2, marker="o", markersize=5)
        last = d.iloc[-1]
        ax.text(6.15, last.retention_pct / 100, f"{ch} · {last.retention_pct:.0f}%", va="center", color=INK, fontsize=10)
    ax.set_xlim(0.8, 8.2)
    ax.set_xticks(range(1, 7))
    ax.set_xlabel("Месяц после первой покупки")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    title(ax, "Удержание по каналам: клиенты из соцсетей почти не возвращаются")
    fig.savefig(path)
    plt.close(fig)


def plot_ltv_cac(ltv: pd.DataFrame, path: Path) -> None:
    ltv = ltv.set_index("channel").loc[list(CHANNEL_COLORS)[::-1]]
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    y = np.arange(len(ltv))
    # цвет показывает статус окупаемости, а не канал: розовый — убыток, светлый — в ноль, серый — окупается
    colors = ["#C8327A" if r < 1 else ("#E7A9C7" if r < 1.5 else "#8C8C8C") for r in ltv.ltv_to_cac]
    ax.barh(y, ltv.ltv_to_cac, color=colors, height=0.55)
    ax.axvline(1, color=INK, linewidth=1.2, linestyle="--")
    ax.text(1.05, 2.5, "окупаемость (LTV = CAC)", color=MUTED, fontsize=9, va="center")
    for yi, (ch, r) in zip(y, ltv.iterrows()):
        ax.text(r.ltv_to_cac + 0.05, yi, f"{r.ltv_to_cac:.2f}".replace(".", ",")
                + f"   (LTV {r.ltv_6m:,.0f} ₽ / CAC {r.cac:,.0f} ₽)".replace(",", " "),
                va="center", color=INK, fontsize=10)
    ax.set_yticks(y, ltv.index)
    ax.set_xlim(0, ltv.ltv_to_cac.max() * 1.9)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("LTV / CAC за 6 месяцев (по валовой прибыли)")
    title(ax, "Окупаемость каналов: соцсети приносят меньше, чем стоят")
    fig.savefig(path)
    plt.close(fig)


SEGMENT_ORDER = ["Чемпионы", "Лояльные", "Нельзя потерять", "Под угрозой ухода",
                 "Требуют внимания", "Новички", "Ушедшие"]


def plot_rfm(seg: pd.DataFrame, path: Path) -> None:
    seg = seg.set_index("segment").loc[SEGMENT_ORDER[::-1]]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    y = np.arange(len(seg))
    h = 0.36
    ax.barh(y + h / 2, seg.customers_share, height=h, color="#E7A9C7", label="доля клиентов")
    ax.barh(y - h / 2, seg.revenue_share, height=h, color="#C8327A", label="доля выручки")
    for yi, (_, r) in zip(y, seg.iterrows()):
        ax.text(r.revenue_share + 0.005, yi - h / 2, f"{r.revenue_share:.0%}", va="center", fontsize=9, color=INK)
        ax.text(r.customers_share + 0.005, yi + h / 2, f"{r.customers_share:.0%}", va="center", fontsize=9, color=MUTED)
    ax.set_yticks(y, seg.index)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=2, frameon=False)
    title(ax, "RFM-сегменты: 24% клиентов дают почти половину выручки")
    fig.savefig(path)
    plt.close(fig)


def main() -> dict:
    IMG.mkdir(exist_ok=True)
    con = connect()
    ret = query(con, "01_cohort_retention.sql")
    by_channel = query(con, "02_retention_by_channel.sql")
    ltv = query(con, "03_ltv_cac.sql")
    rfm = query(con, "04_rfm.sql")
    loyalty = query(con, "05_loyalty_effect.sql")
    monthly = query(con, "06_monthly_revenue.sql")

    seg = (
        rfm.groupby("segment")
        .agg(customers=("customer_id", "count"), revenue=("monetary", "sum"),
             avg_orders=("frequency", "mean"), avg_recency=("recency_days", "mean"))
        .reset_index()
    )
    seg["customers_share"] = seg.customers / seg.customers.sum()
    seg["revenue_share"] = seg.revenue / seg.revenue.sum()

    plot_heatmap(ret, IMG / "01_retention_heatmap.png")
    plot_channel_curves(con, IMG / "02_retention_by_channel.png")
    plot_ltv_cac(ltv, IMG / "03_ltv_cac.png")
    plot_rfm(seg, IMG / "04_rfm_segments.png")

    n_customers = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    n_orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"Клиентов: {n_customers:,}, заказов: {n_orders:,}")
    print("\nУдержание по каналам (когорты до 12.2025):\n", by_channel.to_string(index=False))
    print("\nLTV/CAC за 6 месяцев:\n", ltv.to_string(index=False))
    print("\nПрограмма лояльности:\n", loyalty.to_string(index=False))
    print("\nRFM-сегменты:\n", seg.sort_values("revenue_share", ascending=False).round(3).to_string(index=False))
    print("\nВыручка по месяцам (последние 6):\n", monthly.tail(6).to_string(index=False))
    soc_share = con.execute(
        "SELECT AVG((channel = 'Соцсети')::INT) FROM customers"
    ).fetchone()[0]
    print(f"\nДоля новых клиентов из соцсетей: {soc_share:.1%}")
    return {"by_channel": by_channel, "ltv": ltv, "loyalty": loyalty, "seg": seg, "monthly": monthly}


if __name__ == "__main__":
    main()
