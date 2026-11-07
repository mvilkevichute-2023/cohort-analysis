-- Эффект программы лояльности (запущена 01.10.2025):
-- сравниваем удержание когорт «до» (апрель–сентябрь 2025) и «после» (октябрь 2025 – март 2026)
-- в 1-й, 2-й и 3-й месяц. Окна по 6 когорт одинаковой «зрелости».
WITH activity AS (
    SELECT DISTINCT
           c.customer_id,
           DATE_TRUNC('month', c.first_order_date) AS cohort_month,
           (EXTRACT(YEAR FROM o.order_date) - EXTRACT(YEAR FROM c.first_order_date)) * 12
         + (EXTRACT(MONTH FROM o.order_date) - EXTRACT(MONTH FROM c.first_order_date)) AS month_number
    FROM customers c
    JOIN orders o USING (customer_id)
),
labeled AS (
    SELECT *,
           CASE WHEN cohort_month BETWEEN DATE '2025-04-01' AND DATE '2025-09-01' THEN 'До программы'
                WHEN cohort_month BETWEEN DATE '2025-10-01' AND DATE '2026-03-01' THEN 'После запуска'
           END AS period
    FROM activity
)
SELECT period,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(COUNT(DISTINCT CASE WHEN month_number = 1 THEN customer_id END) * 100.0 / COUNT(DISTINCT customer_id), 1) AS m1_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number = 2 THEN customer_id END) * 100.0 / COUNT(DISTINCT customer_id), 1) AS m2_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number = 3 THEN customer_id END) * 100.0 / COUNT(DISTINCT customer_id), 1) AS m3_pct
FROM labeled
WHERE period IS NOT NULL
GROUP BY period
ORDER BY period;
