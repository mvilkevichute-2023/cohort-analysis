-- LTV за 6 месяцев против стоимости привлечения (CAC) по каналам.
-- LTV считаем по валовой прибыли: выручка × маржа 30%. CAC = расходы канала / новые клиенты.
-- LTV/CAC < 1 — канал не окупается за полгода.
WITH mature_customers AS (
    SELECT customer_id, channel, first_order_date
    FROM customers
    WHERE first_order_date < DATE '2026-01-01'
),
revenue_6m AS (
    SELECT m.channel,
           m.customer_id,
           SUM(CASE WHEN o.order_date < m.first_order_date + INTERVAL 6 MONTH
                    THEN o.amount ELSE 0 END) AS revenue_6m
    FROM mature_customers m
    JOIN orders o USING (customer_id)
    GROUP BY m.channel, m.customer_id
),
cac AS (
    SELECT mk.channel,
           SUM(mk.spend) * 1.0 / SUM(n.new_customers) AS cac
    FROM marketing mk
    JOIN (
        SELECT channel, DATE_TRUNC('month', first_order_date) AS month, COUNT(*) AS new_customers
        FROM customers
        GROUP BY 1, 2
    ) n ON n.channel = mk.channel AND n.month = mk.month
    WHERE mk.month < DATE '2026-01-01'
    GROUP BY mk.channel
)
SELECT r.channel,
       COUNT(*)                                   AS customers,
       ROUND(AVG(r.revenue_6m), 0)                AS revenue_6m,
       ROUND(AVG(r.revenue_6m) * 0.30, 0)         AS ltv_6m,
       ROUND(c.cac, 0)                            AS cac,
       ROUND(AVG(r.revenue_6m) * 0.30 / c.cac, 2) AS ltv_to_cac
FROM revenue_6m r
JOIN cac c USING (channel)
GROUP BY r.channel, c.cac
ORDER BY ltv_to_cac DESC;
