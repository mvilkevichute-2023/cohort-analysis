"""Проверяем SQL-запросы на маленьком наборе, где правильный ответ известен заранее."""
import pandas as pd
import pytest

from cohorts.data import connect, query


@pytest.fixture
def con(tmp_path):
    customers = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4],
            "first_order_date": ["2025-01-10", "2025-01-25", "2025-01-31", "2025-02-05"],
            "channel": ["Соцсети", "Соцсети", "Поиск (SEO)", "Поиск (SEO)"],
            "city": ["Москва"] * 4,
        }
    )
    orders = pd.DataFrame(
        {
            "order_id": range(1, 10),
            "customer_id": [1, 1, 1, 2, 3, 3, 4, 4, 4],
            "order_date": [
                "2025-01-10", "2025-02-03", "2025-02-20",  # клиент 1: месяц 0 и дважды в месяц 1
                "2025-01-25",                              # клиент 2: только первая покупка
                "2025-01-31", "2025-03-01",                # клиент 3: месяц 0 и месяц 2
                "2025-02-05", "2025-03-10", "2025-04-02",  # клиент 4: месяцы 0, 1, 2
            ],
            "amount": [1000, 500, 500, 2000, 1500, 1500, 800, 800, 800],
        }
    )
    marketing = pd.DataFrame({"month": ["2025-01-01"], "channel": ["Соцсети"], "spend": [1000]})
    customers.to_csv(tmp_path / "customers.csv", index=False)
    orders.to_csv(tmp_path / "orders.csv", index=False)
    marketing.to_csv(tmp_path / "marketing.csv", index=False)
    return connect(tmp_path)


def test_retention_counts_calendar_months_and_unique_customers(con):
    r = query(con, "01_cohort_retention.sql")
    jan = r[r.cohort_month == pd.Timestamp("2025-01-01")].set_index("month_number")
    assert jan.loc[0, "cohort_size"] == 3
    # в 1-м месяце купил только клиент 1 — два заказа, но один клиент
    assert jan.loc[1, "active_customers"] == 1
    assert jan.loc[1, "retention_pct"] == pytest.approx(33.3)
    # клиент 3 купил 31.01 и 01.03 — это 2-й календарный месяц, хотя прошёл всего месяц
    assert jan.loc[2, "active_customers"] == 1
    feb = r[r.cohort_month == pd.Timestamp("2025-02-01")].set_index("month_number")
    assert feb.loc[1, "retention_pct"] == 100.0
    assert feb.loc[2, "retention_pct"] == 100.0


def test_rfm_frequency_uses_thresholds_not_ntile(con):
    rfm = query(con, "04_rfm.sql").set_index("customer_id")
    assert rfm.loc[2, "f"] == 1          # одна покупка
    assert rfm.loc[3, "f"] == 2          # две покупки
    assert rfm.loc[1, "f"] == 3          # три покупки
    assert rfm.loc[2, "segment"] == "Ушедшие"  # одна покупка давно


def test_monthly_revenue_splits_new_and_repeat(con):
    m = query(con, "06_monthly_revenue.sql").set_index("month")
    jan = m.loc[pd.Timestamp("2025-01-01")]
    assert jan.new_revenue == 4500       # первые покупки клиентов 1, 2, 3
    assert jan.repeat_revenue == 0
    feb = m.loc[pd.Timestamp("2025-02-01")]
    assert feb.new_revenue == 800        # первая покупка клиента 4
    assert feb.repeat_revenue == 1000    # два повторных заказа клиента 1
    assert feb.mom_growth_pct == pytest.approx((1800 - 4500) / 4500 * 100, abs=0.1)
