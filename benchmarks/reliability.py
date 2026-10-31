import sys,json,time,uuid,subprocess,httpx
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from db import ROOT,sql
sys.path.insert(0,str(Path(__file__).parent))
from functional import headers
out={};event='reliability-'+uuid.uuid4().hex;oid=None
body={'customer_id':1,'product_id':1,'category_id':1,'ordered_at':'2027-04-01T00:00:00Z','quantity':2,'unit_price_cents':111,'status':'placed'}
with httpx.Client(base_url='http://127.0.0.1:18081',timeout=5) as c:
 try:
  r=c.post('/tenants/1/orders',headers=headers(1,event),json=body);r.raise_for_status();oid=r.json()['id'];initial=r.json()
  before=sql('select count(*),sum(quantity::bigint*unit_price_cents) from orders;')
  subprocess.run(['podman','stop','-t','10','agrregatex-postgres-1'],check=True,capture_output=True)
  try:out['temporary_failure_http']=c.get('/health').status_code
  except httpx.HTTPError:out['temporary_failure_http']='connection error'
  subprocess.run(['podman','start','agrregatex-postgres-1'],check=True,capture_output=True)
  for _ in range(60):
   try:
    if c.get('/health').status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.5)
  after=sql('select count(*),sum(quantity::bigint*unit_price_cents) from orders;');out['before']=before;out['after']=after;out['persistence']='PASS' if before==after else 'FAIL'
  subprocess.run(['podman','restart','agrregatex-api-1'],check=True,capture_output=True)
  for _ in range(60):
   try:
    if c.get('/health').status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.5)
  r=c.post('/tenants/1/orders',headers=headers(1,event),json=body);out['replay_after_restart']='PASS' if r.status_code==200 and r.json()==initial else 'FAIL'
  r=c.get('/tenants/1/summary?from=2027-04-01T00:00Z&to=2027-04-02T00:00Z',headers=headers(1));out['rollup_after_restart']='PASS' if r.status_code==200 and r.json()['data']['sales_cents']==222 else 'FAIL'
 finally:
  subprocess.run(['podman','start','agrregatex-postgres-1'],capture_output=True)
  if oid:sql(f'DELETE FROM orders WHERE tenant_id=1 AND id={oid};')
# Inject a failing AFTER trigger, ordered after the real rollup trigger. Its source
# transaction must roll back the earlier rollup changes too. DDL itself rolls back.
before=sql('select sum(n),sum(cents) from daily_product;')
try:
 sql("""BEGIN;
 CREATE FUNCTION public.agrregatex_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'intentional acceptance failure'; END $$;
 CREATE TRIGGER zz_test_fail AFTER INSERT ON orders FOR EACH ROW EXECUTE FUNCTION public.agrregatex_test_fail();
 INSERT INTO orders(tenant_id,customer_id,product_id,category_id,ordered_at,status,quantity,unit_price_cents) VALUES(1,1,1,1,'2027-05-01','placed',2,900);
 COMMIT;""")
 out['injected_failure']='FAIL'
except RuntimeError as exc:out['injected_failure']='PASS' if 'intentional acceptance failure' in str(exc) else 'FAIL'
out['atomic_rollup_rollback']='PASS' if before==sql('select sum(n),sum(cents) from daily_product;') else 'FAIL'
out['worker_restart']='NOT TESTED: no asynchronous worker in selected architecture; PostgreSQL and API restart tested instead'
out['status']='PASS' if all(out[k]=='PASS' for k in ['persistence','replay_after_restart','rollup_after_restart','injected_failure','atomic_rollup_rollback']) else 'FAIL'
(ROOT/'benchmarks/results/reliability.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
