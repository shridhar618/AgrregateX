"""Runs inside API container: direct operational transactions, paired dashboard-off/on runs.
Dashboard load fixed at 20 HTTP requests/sec, 4 concurrent clients; 3 paired trials.
Both arms retain identical transactional rollup maintenance and durability.
"""
import psycopg,httpx,threading,time,json,statistics,random
from psycopg.rows import dict_row
secrets=json.load(open('secrets.json'));samples=[];errors=[]
conn=psycopg.connect(os.environ['ADMIN_DATABASE_URL'],row_factory=dict_row,autocommit=True)
ids=conn.execute('select id from orders where tenant_id=1 order by id limit 100').fetchall();ids=[x['id'] for x in ids]
# Operational mutation is an isolated dedicated order, restoring it after benchmark.
oid=conn.execute("insert into orders(tenant_id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents) values(1,1,1,1,'2027-02-01','placed',1,100) returning id").fetchone()['id']
def load(stop,tenant):
 families=['summary','trends','top-products','breakdown'];j=0
 with httpx.Client(base_url='http://127.0.0.1:8000',timeout=10) as c:
  while not stop.is_set():
   start=time.perf_counter()
   try:
    r=c.get(f'/tenants/{tenant}/{families[j%4]}?from=2026-10-01T05:13:17Z&to=2026-10-08T18:29:11Z',headers={'Authorization':'Bearer '+secrets['tenants'][str(tenant)]});
    if r.status_code!=200:errors.append(r.status_code)
   except Exception as e:errors.append(type(e).__name__)
   j+=1;stop.wait(max(0,.2-(time.perf_counter()-start)))
try:
 for pair in range(3):
  # Alternate arm ordering to reduce time/drift bias.
  for loaded in ([False,True] if pair%2==0 else [True,False]):
   stop=threading.Event();workers=[]
   if loaded:
    workers=[threading.Thread(target=load,args=(stop,t)) for t in [1,2,3,10]]
    for w in workers:w.start()
    time.sleep(1)
   with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True,row_factory=dict_row) as op:
    for j in range(240):
     begin=time.perf_counter()
     with op.transaction():
      op.execute("select set_config('app.tenant','1',true)")
      t=time.perf_counter();op.execute('select customer_id,product_id,status,quantity,unit_price_cents from orders where tenant_id=1 and id=%s',(ids[j%len(ids)],)).fetchone();read_ms=(time.perf_counter()-t)*1000
      t=time.perf_counter();op.execute('update orders set quantity=%s,version=version+1 where tenant_id=1 and id=%s',(1+j%2,oid));write_ms=(time.perf_counter()-t)*1000
     samples.append({'pair':pair,'dashboard':loaded,'read_ms':read_ms,'write_statement_ms':write_ms,'transaction_ms':(time.perf_counter()-begin)*1000})
     time.sleep(max(0,.025-(time.perf_counter()-begin)))
   stop.set()
   for w in workers:w.join()
finally:conn.execute('delete from orders where tenant_id=1 and id=%s',(oid,))
out={'dashboard_rps_target':20,'dashboard_clients':4,'operational_rps_target':40,'pairs':3,'operations_per_arm':720,'samples':samples,'dashboard_errors':errors,'metrics':{}}
for metric in ['read_ms','write_statement_ms','transaction_ms']:
 arms={str(loaded):[r[metric] for r in samples if r['dashboard']==loaded] for loaded in [False,True]}
 means={k:statistics.mean(v) for k,v in arms.items()};p95={k:sorted(v)[int(len(v)*.95)] for k,v in arms.items()}
 out['metrics'][metric]={'baseline_mean':means['False'],'loaded_mean':means['True'],'slowdown_percent':(means['True']/means['False']-1)*100,'baseline_p95':p95['False'],'loaded_p95':p95['True'],'p95_slowdown_percent':(p95['True']/p95['False']-1)*100}
out['status']='PASS' if not errors and all(v['slowdown_percent']<10 and v['p95_slowdown_percent']<10 for v in out['metrics'].values()) else 'FAIL'
print(json.dumps(out))
