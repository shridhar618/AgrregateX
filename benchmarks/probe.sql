\timing on
CREATE TABLE architecture_probe(id bigint PRIMARY KEY,tenant_id int,ordered_at timestamptz,product_id int,status text,quantity int,cents bigint);
INSERT INTO architecture_probe SELECT i,1,now(),i%8,'placed',2,100 FROM generate_series(1,10000) i;
SELECT pgtrickle.create_stream_table('architecture_stream',$$SELECT tenant_id,date_trunc('hour',ordered_at,'UTC') bucket,product_id,status,count(*) n,sum(quantity) units,sum(quantity::bigint*cents) amount FROM architecture_probe GROUP BY 1,2,3,4$$,'1s','DIFFERENTIAL');
UPDATE architecture_probe SET quantity=3,status='cancelled',ordered_at=ordered_at-interval '2 days' WHERE id=1;
SELECT pgtrickle.refresh_stream_table('architecture_stream');
SELECT count(*) AS mismatches FROM ((SELECT tenant_id,bucket,product_id,status,n,units,amount FROM architecture_stream EXCEPT ALL SELECT tenant_id,date_trunc('hour',ordered_at,'UTC'),product_id,status,count(*),sum(quantity),sum(quantity::bigint*cents) FROM architecture_probe GROUP BY 1,2,3,4) UNION ALL (SELECT tenant_id,date_trunc('hour',ordered_at,'UTC'),product_id,status,count(*),sum(quantity),sum(quantity::bigint*cents) FROM architecture_probe GROUP BY 1,2,3,4 EXCEPT ALL SELECT tenant_id,bucket,product_id,status,n,units,amount FROM architecture_stream)) d;
SELECT * FROM pgtrickle.pgt_status();
SELECT pgtrickle.drop_stream_table('architecture_stream');
DROP TABLE architecture_probe;
