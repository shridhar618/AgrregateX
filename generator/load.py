#!/usr/bin/env python3
"""REPRESENTATIVE dataset, NOT official organizer generator. Algorithm version 1, seed 42.
Server-side bounded INSERT SELECT avoids millions of Python objects. Resume by max ID.
Offline maintenance window: source lock and trigger disabled in ONE transaction; a failure rolls back.
"""
import sys,time,json,shutil,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from db import sql,query_json,ROOT
n=int(sys.argv[1]);tenants=int(sys.argv[2]);assert n in (1000000,10000000) and tenants in (10,100)
if shutil.disk_usage(ROOT).free<30*1024**3:raise SystemExit('BLOCKED: require 30 GiB free for source/index/WAL headroom')
start=time.monotonic();existing=int(sql('select count(*) from orders;'))
if existing>n:raise SystemExit('Refuse smaller target; preserve existing data')
# Bulk IDs are negative, API-generated IDs positive. Isolates fixture/API records.
loaded=int(sql('select count(*) from orders where id<0;'))
if existing!=loaded:raise SystemExit('Remove only your dedicated test records before bulk loading; source contains non-benchmark rows')
if loaded==n:raise SystemExit('Already loaded; refusing redundant rebuild')
commands=["BEGIN; SET LOCAL statement_timeout=0; SET LOCAL TIME ZONE 'UTC'; LOCK TABLE orders IN ACCESS EXCLUSIVE MODE; ALTER TABLE orders DISABLE TRIGGER rollups; DROP INDEX orders_time;",
 f"INSERT INTO tenants SELECT i,'Store '||i FROM generate_series(1,{tenants}) i ON CONFLICT DO NOTHING;",
 f"INSERT INTO products SELECT t,i,1+(i-1)%8,'Product '||i FROM generate_series(1,{tenants}) t CROSS JOIN generate_series(1,32) i ON CONFLICT DO NOTHING;",
 f"INSERT INTO customers SELECT t,i FROM generate_series(1,{tenants}) t CROSS JOIN generate_series(1,100) i ON CONFLICT DO NOTHING;"]
for a in range(loaded+1,n+1,100000):
 b=min(n,a+99999)
 # Seeded independent hashes prevent tenant/time/product correlation.
 commands.append(f"""INSERT INTO orders(tenant_id,id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents)
 SELECT CASE WHEN h<400000 THEN 1 WHEN h<600000 THEN 2 ELSE 3+(h%{tenants-2})::int END,-i,
 1+(hc%100)::int,1+(hp%32)::int,1+(hp%32)::int%8,
 '2026-08-03 00:00:00+00'::timestamptz+make_interval(secs=>(ht%7776000)::double precision),
 CASE WHEN hs%10=0 THEN 'cancelled' WHEN hs%10<5 THEN 'shipped' ELSE 'placed' END,
 1+(hq%4)::int,100+(hm%50000)
 FROM (SELECT i,(hashtextextended(i::text,42)&9223372036854775807)%1000000 h,
 (hashtextextended(i::text,43)&9223372036854775807) hc,(hashtextextended(i::text,44)&9223372036854775807) hp,
 (hashtextextended(i::text,45)&9223372036854775807) ht,(hashtextextended(i::text,46)&9223372036854775807) hs,
 (hashtextextended(i::text,47)&9223372036854775807) hq,(hashtextextended(i::text,48)&9223372036854775807) hm
 FROM generate_series({a}::bigint,{b}::bigint) i) x;
 SELECT 'batch {b}';""")
# Fix category matches product IDs (product id1=>category1).
commands=[s.replace('1+(hp%32)::int%8','1+((hp%32)::int%8)') for s in commands]
# Product id = 1+hp%32; category = 1+((id-1)%8), correct.
commands += ["SELECT 'source_loaded',clock_timestamp();", "CREATE INDEX orders_time ON orders(tenant_id,ordered_at) INCLUDE(product_id,category_id,status,quantity,unit_price_cents); SELECT 'index_built',clock_timestamp();", "TRUNCATE daily_product,hourly_category;",
 "INSERT INTO daily_product SELECT tenant_id,date_trunc('day',ordered_at,'UTC'),product_id,category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4,5; SELECT 'daily_built',clock_timestamp();",
 "INSERT INTO hourly_category SELECT tenant_id,date_trunc('hour',ordered_at,'UTC'),category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4; SELECT 'hourly_built',clock_timestamp();",
 "ALTER TABLE orders ENABLE TRIGGER rollups; COMMIT; VACUUM (ANALYZE) orders; ANALYZE daily_product; ANALYZE hourly_category;"]
# Transaction rollback protects source and trigger status on interruption; do not serve API during load.
t0=time.monotonic();result=sql('\n'.join(commands));elapsed=time.monotonic()-t0
out={'dataset':'REPRESENTATIVE, official compatibility NOT VERIFIED','version':1,'seed':42,'target':n,'tenants':tenants,'added':n-loaded,'elapsed_seconds':elapsed,'prior_rows':loaded,'first_million_tenant_domain':10 if loaded else tenants,'sql_progress':result,'sizes':query_json("select relname,pg_relation_size(relid) heap_bytes,pg_indexes_size(relid) index_bytes,pg_total_relation_size(relid) total_bytes from pg_statio_user_tables where relname in ('orders','daily_product','hourly_category')"),'distribution':query_json('select tenant_id,count(*) n from orders group by tenant_id order by n desc')}
(ROOT/'benchmarks/results'/f'load-{n}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
