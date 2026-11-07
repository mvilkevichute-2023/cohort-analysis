-- Выручка по месяцам: от новых и от вернувшихся клиентов, рост к прошлому месяцу через LAG.
WITH monthly AS (
    SELECT DATE_TRUNC('month', o.order_date) AS month,
           SUM(CASE WHEN o.order_date = c.first_order_date THEN o.amount ELSE 0 END) AS new_revenue,
           SUM(CASE WHEN o.order_date > c.first_order_date THEN o.amount ELSE 0 END) AS repeat_revenue,
           SUM(o.amount) AS revenue
    FROM orders o
    JOIN customers c USING (customer_id)
    GROUP BY 1
)
SELECT month,
       new_revenue,
       repeat_revenue,
       revenue,
       ROUND(repeat_revenue * 100.0 / revenue, 1) AS repeat_share_pct,
       ROUND((revenue - LAG(revenue) OVER (ORDER BY month)) * 100.0
             / LAG(revenue) OVER (ORDER BY month), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;
