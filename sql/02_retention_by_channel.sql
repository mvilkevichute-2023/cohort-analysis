-- Удержание по каналам привлечения: доля клиентов, купивших снова в 1-й, 3-й и 6-й месяц.
-- Берём только когорты, которые успели «прожить» 6 месяцев, чтобы сравнение было честным.
WITH activity AS (
    SELECT DISTINCT
           c.customer_id,
           c.channel,
           DATE_TRUNC('month', c.first_order_date) AS cohort_month,
           (EXTRACT(YEAR FROM o.order_date) - EXTRACT(YEAR FROM c.first_order_date)) * 12
         + (EXTRACT(MONTH FROM o.order_date) - EXTRACT(MONTH FROM c.first_order_date)) AS month_number
    FROM customers c
    JOIN orders o USING (customer_id)
),
mature AS (
    SELECT *
    FROM activity
    WHERE cohort_month <= DATE '2025-12-01'
)
SELECT channel,
       COUNT(DISTINCT customer_id)                                                        AS customers,
       ROUND(COUNT(DISTINCT CASE WHEN month_number = 1 THEN customer_id END) * 100.0
             / COUNT(DISTINCT customer_id), 1)                                            AS m1_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number = 3 THEN customer_id END) * 100.0
             / COUNT(DISTINCT customer_id), 1)                                            AS m3_pct,
       ROUND(COUNT(DISTINCT CASE WHEN month_number = 6 THEN customer_id END) * 100.0
             / COUNT(DISTINCT customer_id), 1)                                            AS m6_pct
FROM mature
GROUP BY channel
ORDER BY m3_pct DESC;
