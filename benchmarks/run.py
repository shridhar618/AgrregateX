#!/usr/bin/env python3
"""Full HTTP measurements. Every individual request and error retained, no percentile-only PASS."""
import sys,json,time,statistics,concurrent.futures,uuid
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from db import ROOT,sql,query_json
sys.path.insert(0,str(Path(__file__).parent))
from functional import headers,direct
scale=int(sys.argv[1]);nt=10 if scale==1000000 else 100
out={'scale':scale,'dataset':'representative seed42 v1; OFFICIAL DATASET COMPATIBILITY: NOT VERIFIED','requests':[],'correctness':[],'freshness':[]}
ranges=[('day','2026-10-01T00:00:00Z','2026-10-02T00:00:00Z'),('week','2026-10-01T00:00:00Z','2026-10-08T00:00:00Z'),('month','2026-10-01T00:00:00Z','2026-10-31T00:00:00Z'),('boundary','2026-10-01T05:13:17.123Z','2026-10-08T18:29:11.456Z')]
families=[('summary','day'),('trends','day'),('trends','hour'),('top-products','day'),('breakdown','day')]
def path(t,f,a,b,g):return f'/tenants/{t}/{f}?from={a}&to={b}&grain={g}'
def hit(c,t,f,a,b,g,label,mode):
 start=time.perf_counter();r=c.get(path(t,f,a,b,g),headers=headers(t));ms=(time.perf_counter()-start)*1000
 return {'tenant':t,'family':f,'grain':g,'range':label,'mode':mode,'ms':ms,'http':r.status_code}
with httpx.Client(base_url='http://127.0.0.1:18081',timeout=30) as c:
 for t in [1,2,nt]:
  for label,a,b in ranges:
   for f,g in families:
    hit(c,t,f,a,b,g,label,'warmup')
    for _ in range(8):out['requests'].append(hit(c,t,f,a,b,g,label,'sequential'))
 def concurrent_run(t):
  res=[]
  with httpx.Client(base_url='http://127.0.0.1:18081',timeout=30) as c:
   for _ in range(3):
    for label,a,b in ranges:
     for f,g in families:res.append(hit(c,t,f,a,b,g,label,'concurrent4'))
  return res
 with concurrent.futures.ThreadPoolExecutor(4) as ex:
  for result in ex.map(concurrent_run,[1,2,3,nt]):out['requests']+=result
 # Compare all source tenants for aligned week; partial buckets for hot/small tenants;
 # capture data before writes so API/source state is stable.
 for t in range(1,nt+1):
  test_ranges=[ranges[1]]+([ranges[3]] if t in [1,2,nt] else [])
  for label,a,b in test_ranges:
   for f,g in families:
    r=c.get(path(t,f,a,b,g),headers=headers(t));actual=r.json().get('data');expected=direct(t,a,b,f,g)
    out['correctness'].append({'tenant':t,'family':f,'grain':g,'range':label,'status':'PASS' if r.status_code==200 and actual==expected else 'FAIL',**({'actual':actual,'expected':expected} if actual!=expected else {})})
 # Commit observed via source DB, not mutation HTTP response timing.
 for iteration in range(5):
  before=c.get(path(1,'summary','2027-01-01T00:00:00Z','2027-01-02T00:00:00Z','day'),headers=headers(1)).json()['data']
  insert_started=time.perf_counter()
  oid=int(sql("INSERT INTO orders(tenant_id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents) VALUES(1,1,1,1,'2027-01-01T12:34:56Z','placed',2,1234) RETURNING id;"))
  # psql has committed before returning; measured timer is a post-commit observation lower bound.
  # For conservative bound include whole psql roundtrip in a separate field below.
  for operation,statement,n,cents in [
   ('insert',None,before['orders']+1,before['sales_cents']+2468),
   ('update',f'UPDATE orders SET quantity=3,unit_price_cents=2222 WHERE tenant_id=1 AND id={oid};',before['orders']+1,before['sales_cents']+6666),
   ('cancel',f"UPDATE orders SET status='cancelled' WHERE tenant_id=1 AND id={oid};",before['orders']+1,before['sales_cents'])]:
   start=insert_started if operation=='insert' else time.perf_counter()
   if statement:sql(statement)
   commit_observed=time.perf_counter()
   for _ in range(300):
    response=c.get(path(1,'summary','2027-01-01T00:00:00Z','2027-01-02T00:00:00Z','day'),headers=headers(1));d=response.json()['data']
    if d['orders']==n and d['sales_cents']==cents:break
    time.sleep(.1)
   out['freshness'].append({'operation':operation,'iteration':iteration,'post_commit_observation_seconds':time.perf_counter()-commit_observed,'including_sql_roundtrip_seconds':time.perf_counter()-start,'status':'PASS' if d['orders']==n and d['sales_cents']==cents else 'FAIL'})
  sql(f'DELETE FROM orders WHERE tenant_id=1 AND id={oid};')
# Exact maintained table reconciliation, entire dataset, all dimensional keys, one stable logical state.
out['rollup_mismatches']=query_json("SELECT 'daily_product' name,count(*) mismatches FROM ((SELECT tenant_id,bucket,product_id,category_id,status,n,units,cents FROM daily_product WHERE n<>0 EXCEPT ALL SELECT tenant_id,date_trunc('day',ordered_at,'UTC'),product_id,category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4,5) UNION ALL (SELECT tenant_id,date_trunc('day',ordered_at,'UTC'),product_id,category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4,5 EXCEPT ALL SELECT tenant_id,bucket,product_id,category_id,status,n,units,cents FROM daily_product WHERE n<>0)) d UNION ALL SELECT 'hourly_category',count(*) FROM ((SELECT tenant_id,bucket,category_id,status,n,units,cents FROM hourly_category WHERE n<>0 EXCEPT ALL SELECT tenant_id,date_trunc('hour',ordered_at,'UTC'),category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4) UNION ALL (SELECT tenant_id,date_trunc('hour',ordered_at,'UTC'),category_id,status,count(*),sum(quantity),sum(quantity::bigint*unit_price_cents) FROM orders GROUP BY 1,2,3,4 EXCEPT ALL SELECT tenant_id,bucket,category_id,status,n,units,cents FROM hourly_category WHERE n<>0)) d")
def metrics(v):
 x=sorted(v);return {'n':len(x),'p50':statistics.median(x),'p95':x[min(len(x)-1,int(len(x)*.95))],'p99':x[min(len(x)-1,int(len(x)*.99))],'max':max(x),'mean':statistics.mean(x)}
out['latency']={}
for f,g in families:
 for mode in ['sequential','concurrent4']:
  values=[r['ms'] for r in out['requests'] if r['family']==f and r['grain']==g and r['mode']==mode];out['latency'][f+':'+g+':'+mode]=metrics(values)
out['errors']=sum(r['http']!=200 for r in out['requests']);out['query_target']='PASS' if not out['errors'] and max(r['ms'] for r in out['requests'])<200 else 'FAIL'
out['correctness_target']='PASS' if all(x['status']=='PASS' for x in out['correctness']) and all(x['mismatches']==0 for x in out['rollup_mismatches']) else 'FAIL'
(ROOT/'benchmarks/results'/f'benchmark-{scale}.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['requests','correctness','freshness']},indent=2))
