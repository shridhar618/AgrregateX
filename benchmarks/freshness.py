import sys,time,json,httpx
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from db import ROOT,sql
sys.path.insert(0,str(Path(__file__).parent))
from functional import headers
out=[]
with httpx.Client(base_url='http://127.0.0.1:18081') as c:
 for j in range(10):
  oid=None
  try:
   for op,quantity,status in [('insert',2,'placed'),('update',3,'placed'),('cancel',3,'cancelled')]:
    started=time.monotonic()
    if op=='insert':oid=int(sql("insert into orders(tenant_id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents) values(1,1,1,1,'2027-03-01T01:00Z','placed',2,1234) returning id;"))
    else:sql(f"update orders set quantity={quantity},status='{status}' where tenant_id=1 and id={oid};")
    epoch=float(sql(f'select extract(epoch from pg_xact_commit_timestamp(xmin)) from orders where tenant_id=1 and id={oid};'))
    for _ in range(300):
     r=c.get('/tenants/1/summary?from=2027-03-01T00:00Z&to=2027-03-02T00:00Z',headers=headers(1));d=r.json()['data']
     if d['orders']==1 and d['sales_cents']==(0 if status=='cancelled' else quantity*1234):break
     time.sleep(.1)
    out.append({'op':op,'commit_to_response_seconds':time.time()-epoch,'whole_operation_seconds':time.monotonic()-started,'status':'PASS' if d['orders']==1 and d['sales_cents']==(0 if status=='cancelled' else quantity*1234) else 'FAIL'})
  finally:
   if oid:sql(f'delete from orders where tenant_id=1 and id={oid};')
d={'scale':int(sys.argv[1]),'samples':out,'worst_seconds':max(x['commit_to_response_seconds'] for x in out),'status':'PASS' if all(x['status']=='PASS' and x['commit_to_response_seconds']<30 for x in out) else 'FAIL','clock':'PostgreSQL tracked source xmin commit timestamp to complete HTTP response; containers share host wall clock'}
(ROOT/'benchmarks/results'/f'freshness-{sys.argv[1]}.json').write_text(json.dumps(d,indent=2));print(json.dumps(d,indent=2))
