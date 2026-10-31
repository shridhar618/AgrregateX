BEGIN;
SET LOCAL statement_timeout=0;
LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;
TRUNCATE daily_product,hourly_category;
INSERT INTO daily_product SELECT tenant_id,date_trunc('day',ordered_at,'UTC'),product_id,category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4,5;
INSERT INTO hourly_category SELECT tenant_id,date_trunc('hour',ordered_at,'UTC'),category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4;
COMMIT;
ANALYZE daily_product;
ANALYZE hourly_category;
