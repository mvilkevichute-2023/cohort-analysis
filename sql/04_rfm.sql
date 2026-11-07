-- RFM-сегментация на 30.06.2026: давность (R), частота (F) и сумма покупок (M).
-- R и M делим на 5 групп через NTILE. Для F NTILE не подходит: у 42% клиентов
-- одна покупка, и NTILE раскидал бы одинаковых клиентов по разным группам случайно.
-- Поэтому F считаем по порогам.
WITH base AS (
    SELECT customer_id,
           DATE '2026-06-30' - MAX(order_date) AS recency_days,
           COUNT(*)                            AS frequency,
           SUM(amount)                         AS monetary
    FROM orders
    GROUP BY customer_id
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC, customer_id) AS r,
           CASE WHEN frequency >= 6 THEN 5
                WHEN frequency >= 4 THEN 4
                WHEN frequency  = 3 THEN 3
                WHEN frequency  = 2 THEN 2
                ELSE 1 END                            AS f,
           NTILE(5) OVER (ORDER BY monetary, customer_id)          AS m
    FROM base
)
SELECT customer_id, recency_days, frequency, monetary, r, f, m,
       CASE
           WHEN r >= 4 AND f >= 4 THEN 'Чемпионы'
           WHEN r >= 3 AND f >= 3 THEN 'Лояльные'
           WHEN r >= 4 AND f  = 1 THEN 'Новички'
           WHEN r <= 2 AND f >= 4 THEN 'Нельзя потерять'
           WHEN r <= 2 AND f >= 2 THEN 'Под угрозой ухода'
           WHEN r <= 2 AND f  = 1 THEN 'Ушедшие'
           ELSE 'Требуют внимания'
       END AS segment
FROM scored;
