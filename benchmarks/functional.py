#!/usr/bin/env python3
import sys,json,time,uuid,concurrent.futures
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from db import sql,query_json,ROOT
BASE='http://127.0.0.1:18081';secret=json.loads((ROOT/'.secrets.json').read_text());tests=[]
def check(name,ok,detail=None):
 tests.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail});assert ok,(name,detail)
def headers(t,event=None):
 h={'Authorization':'Bearer '+secret['tenants'][str(t)]}
 if event:h['Idempotency-Key']=event
 return h
client=httpx.Client(base_url=BASE,timeout=30)
def req(method,path,t=1,body=None,event=None):return client.request(method,path,headers=headers(t,event),json=body)
def direct(t,a,b,family,grain='day'):
 where=f"tenant_id={t} AND ordered_at>='{a}'::timestamptz AND ordered_at<'{b}'::timestamptz"
 if family=='summary':s=f"SELECT count(*)::bigint orders,coalesce(sum(quantity) FILTER(WHERE status<>'cancelled'),0)::bigint units,coalesce(sum(quantity::bigint*unit_price_cents) FILTER(WHERE status<>'cancelled'),0)::bigint sales_cents FROM orders WHERE {where}"
 elif family=='top-products':s=f"SELECT product_id,sum(quantity)::bigint units,sum(quantity::bigint*unit_price_cents)::bigint sales_cents FROM orders WHERE {where} AND status<>'cancelled' GROUP BY product_id ORDER BY sales_cents DESC,units DESC,product_id LIMIT 10"
 elif family=='breakdown':s=f"SELECT status,category_id,count(*)::bigint orders,coalesce(sum(quantity::bigint*unit_price_cents) FILTER(WHERE status<>'cancelled'),0)::bigint sales_cents FROM orders WHERE {where} GROUP BY status,category_id ORDER BY status,category_id"
 else:
  step='1 hour' if grain=='hour' else '1 day'
  s=f"SELECT s.bucket,coalesce(x.orders,0)::bigint orders,coalesce(x.sales_cents,0)::bigint sales_cents FROM generate_series(date_trunc('{grain}','{a}'::timestamptz,'UTC'),'{b}'::timestamptz,interval '{step}') s(bucket) LEFT JOIN (SELECT date_trunc('{grain}',ordered_at,'UTC') bucket,count(*) orders,sum(CASE WHEN status<>'cancelled' THEN quantity::bigint*unit_price_cents ELSE 0 END) sales_cents FROM orders WHERE {where} GROUP BY 1) x USING(bucket) WHERE s.bucket<'{b}'::timestamptz ORDER BY 1"
 data=query_json(s)
 if family=='trends':
  # PostgreSQL JSON timestamptz uses +00:00; FastAPI uses Z.
  for x in data:x['bucket']=x['bucket'].replace('Z','+00:00')
 return data[0] if family=='summary' else data

def reconcile(t,a,b,label):
 for fam,grain in [('summary','day'),('trends','day'),('trends','hour'),('top-products','day'),('breakdown','day')]:
  if grain=='hour' and (b[:10]=='2026-11-01' and a[:10]=='2026-08-01'):continue
  r=req('GET',f'/tenants/{t}/{fam}?from={a}&to={b}&grain={grain}',t)
  check(f'{label}:{t}:{fam}:{grain}',r.status_code==200,r.text[:300] if r.status_code!=200 else None)
  actual=r.json()['data'];expected=direct(t,a,b,fam,grain)
  check(f'{label}:{t}:{fam}:{grain}:oracle',actual==expected,{'actual':actual,'expected':expected} if actual!=expected else None)

def fixtures():
 sql("INSERT INTO tenants VALUES(1,'Store 1'),(2,'Store 2') ON CONFLICT DO NOTHING; INSERT INTO products SELECT t,i,1+(i-1)%8,'Product '||i FROM generate_series(1,2) t CROSS JOIN generate_series(1,32) i ON CONFLICT DO NOTHING; INSERT INTO customers SELECT t,i FROM generate_series(1,2) t CROSS JOIN generate_series(1,100) i ON CONFLICT DO NOTHING;")
 ids=[];prefix=uuid.uuid4().hex
 body={'customer_id':1,'product_id':1,'category_id':1,'ordered_at':'2026-10-01T00:00:00Z','quantity':2,'unit_price_cents':1234,'status':'placed'}
 try:
  for t in [1,2]:
   r=req('POST',f'/tenants/{t}/orders',t,body,prefix+f'create{t}');check('create'+str(t),r.status_code==200,r.text);ids.append((t,r.json()['id']))
  r=req('POST','/tenants/1/orders',1,body,prefix+'create1');check('duplicate-create',r.status_code==200 and r.json()['id']==ids[0][1])
  r=req('POST','/tenants/1/orders',1,{**body,'quantity':9},prefix+'create1');check('conflicting-event',r.status_code==409)
  for t in [1,2]:
   for a,b in [('2026-10-01T00:00:00Z','2026-10-03T00:00:00Z'),('2026-10-01T00:00:00.001Z','2026-10-02T00:00:00Z'),('2026-10-01T00:00:00Z','2026-10-01T00:00:00.001Z'),('2026-10-03T00:00:00Z','2026-10-04T00:00:00Z')]:reconcile(t,a,b,'fixture')
  oid=ids[0][1]
  for j,patch in enumerate([{'status':'cancelled'},{'quantity':5,'unit_price_cents':2000},{'ordered_at':'2026-10-02T00:00:01Z','status':'shipped','product_id':2,'category_id':2},{'ordered_at':'2026-09-30T23:59:59.999Z'}]):
   r=req('PATCH',f'/tenants/1/orders/{oid}',1,patch,prefix+f'patch{j}');check('patch'+str(j),r.status_code==200,r.text)
   replay=req('PATCH',f'/tenants/1/orders/{oid}',1,patch,prefix+f'patch{j}');check('replayed-update'+str(j),replay.json()==r.json())
   reconcile(1,'2026-09-30T00:00:00Z','2026-10-04T00:00:00Z','mutation'+str(j))
  for fam in ['summary','trends','top-products','breakdown','freshness']:
   check('cross-tenant-'+fam,req('GET',f'/tenants/2/{fam}?from=2026-10-01T00:00:00Z&to=2026-10-02T00:00:00Z',1).status_code==403)
  check('unauthorized-update',req('PATCH',f'/tenants/2/orders/{ids[1][1]}',1,{'quantity':9},prefix+'attack').status_code==403)
  check('other-order-hidden',req('PATCH',f'/tenants/1/orders/{ids[1][1]}',1,{'quantity':9},prefix+'attack2').status_code==404)
  check('tenant-body-rejected',req('POST','/tenants/1/orders',1,{**body,'tenant_id':2},prefix+'attack3').status_code==422)
  r=req('GET','/tenants/1/summary?from=2026-10-01T00:00:00Z&to=2026-10-02T00:00:00Z&tenant_id=2',1);check('query-override-ignored',r.json()['tenant_id']==1)
  check('no-token',client.get('/tenants/1/freshness').status_code==401)
  check('admin-monitoring-denied',req('GET','/monitoring',1).status_code==403)
  check('admin-monitoring',client.get('/monitoring',headers={'Authorization':'Bearer '+secret['admin']}).status_code==200)
  check('openapi',client.get('/openapi.json').json()['info']['title'].startswith('AgrregateX'))
  # Rollback must atomically retract a failed source transaction.
  before=sql('select sum(n),sum(cents) from daily_product;')
  try:sql("BEGIN; INSERT INTO orders(tenant_id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents) VALUES(1,1,1,1,now(),'placed',2,900); SELECT 1/0; COMMIT;")
  except RuntimeError:pass
  check('failed-transaction-atomic',sql('select sum(n),sum(cents) from daily_product;')==before)
  # Concurrent same-key requests must collapse to one order.
  def create_duplicate(_):
   with httpx.Client(base_url=BASE,timeout=20) as c:return c.post('/tenants/1/orders',headers=headers(1,prefix+'concurrent'),json=body)
  with concurrent.futures.ThreadPoolExecutor(2) as ex:replies=list(ex.map(create_duplicate,range(2)))
  check('concurrent-duplicate',all(r.status_code==200 for r in replies) and replies[0].json()==replies[1].json());ids.append((1,replies[0].json()['id']))
 finally:
  for t,oid in ids:
   r=req('DELETE',f'/tenants/{t}/orders/{oid}',t,event=prefix+f'del{t}-{oid}');check('delete-test-record',r.status_code==200,r.text)
 # Dedicated RLS connection test executes inside API container separately.
 (ROOT/'benchmarks/results/functional.json').write_text(json.dumps({'tests':tests,'status':'PASS' if all(t['status']=='PASS' for t in tests) else 'FAIL'},indent=2))
 print('Functional checks:',len(tests),'PASS')
if __name__=='__main__':fixtures()
