-- Матрица удержания: какая доля клиентов каждой когорты покупала снова через N месяцев.
-- Когорта = месяц первой покупки. Месяц 0 — сама первая покупка (всегда 100%).
WITH orders_with_cohort AS (
    SELECT o.customer_id,
           DATE_TRUNC('month', c.first_order_date) AS cohort_month,
           DATE_TRUNC('month', o.order_date)       AS order_month
    FROM orders o
    JOIN customers c USING (customer_id)
),
activity AS (
    SELECT DISTINCT
           customer_id,
           cohort_month,
           (EXTRACT(YEAR FROM order_month) - EXTRACT(YEAR FROM cohort_month)) * 12
         + (EXTRACT(MONTH FROM order_month) - EXTRACT(MONTH FROM cohort_month)) AS month_number
    FROM orders_with_cohort
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS customers
    FROM activity
    WHERE month_number = 0
    GROUP BY cohort_month
)
SELECT a.cohort_month,
       a.month_number,
       s.customers                                              AS cohort_size,
       COUNT(DISTINCT a.customer_id)                            AS active_customers,
       ROUND(COUNT(DISTINCT a.customer_id) * 100.0 / s.customers, 1) AS retention_pct
FROM activity a
JOIN cohort_size s USING (cohort_month)
GROUP BY a.cohort_month, a.month_number, s.customers
ORDER BY a.cohort_month, a.month_number;
