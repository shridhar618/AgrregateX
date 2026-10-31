import psycopg,json,concurrent.futures,httpx
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
keys=json.load(open('secrets.json'))['tenants'];results=[]
with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row) as c:
 role=c.execute('select rolname,rolsuper,rolbypassrls from pg_roles where rolname=current_user').fetchone();assert not role['rolsuper'] and not role['rolbypassrls'];results.append({'test':'non-superuser-nobypassrls','status':'PASS'})
 c.execute("select set_config('app.tenant','1',true)")
 assert c.execute('select count(*) n from orders where tenant_id<>1').fetchone()['n']==0
 assert not c.execute('select distinct tenant_id from daily_product where tenant_id<>1').fetchall()
 try:
  with c.transaction():c.execute("insert into orders(tenant_id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents) values(2,1,1,1,now(),'placed',1,1)")
  raise AssertionError('RLS accepted foreign tenant')
 except psycopg.errors.InsufficientPrivilege:pass
 results.append({'test':'source-aggregate-and-write-RLS','status':'PASS'})
with ConnectionPool(os.environ['DATABASE_URL'],min_size=1,max_size=1,kwargs={'row_factory':dict_row}) as p:
 for tenant in [1,2,1,2]:
  with p.connection() as c:
   with c.transaction():
    c.execute("select set_config('app.tenant',%s,true)",(str(tenant),))
    assert all(r['tenant_id']==tenant for r in c.execute('select distinct tenant_id from daily_product'))
  with p.connection() as c:
   assert not c.execute('select tenant_id from daily_product limit 1').fetchall()
results.append({'test':'pooled-connection-context-reset','status':'PASS'})
def tenant_test(t):
 with httpx.Client(base_url='http://127.0.0.1:8000') as c:
  auth={'Authorization':'Bearer '+keys[str(t)]}
  for family in ['summary','trends','top-products','breakdown']:
   r=c.get(f'/tenants/{t}/{family}?from=2026-10-01T00:00Z&to=2026-10-02T00:00Z',headers=auth);assert r.status_code==200 and r.json()['tenant_id']==t
   r=c.get(f'/tenants/{(t%100)+1}/{family}?from=2026-10-01T00:00Z&to=2026-10-02T00:00Z',headers=auth);assert r.status_code==403
  for other in range(1,101):
   if other!=t:
    r=c.get(f'/tenants/{other}/freshness',headers=auth);assert r.status_code==403
  r=c.patch(f'/tenants/{(t%100)+1}/orders/1',headers={**auth,'Idempotency-Key':'attack'},json={'quantity':999});assert r.status_code==403
 return {'tenant':t,'status':'PASS'}
with concurrent.futures.ThreadPoolExecutor(4) as e:tenants=list(e.map(tenant_test,range(1,101)))
print(json.dumps({'status':'PASS','tests':results,'tenants':tenants,'concurrency':4,'cross_tenant_pairs_rejected':9900}))
