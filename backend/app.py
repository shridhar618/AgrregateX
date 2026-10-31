import os,json,time,secrets,hashlib,threading
from contextlib import contextmanager,asynccontextmanager
from datetime import datetime,timezone
from typing import Literal
from pathlib import Path
from fastapi import FastAPI,Depends,HTTPException,Query,Header,Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel,ConfigDict,Field,field_validator
from psycopg_pool import ConnectionPool,PoolTimeout
from psycopg import OperationalError
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from analytics import aggregate

credentials=json.loads(Path('secrets.json').read_text())
pool=ConnectionPool(os.environ['DATABASE_URL'],min_size=1,max_size=6,check=ConnectionPool.check_connection,kwargs={'row_factory':dict_row},open=False)
@asynccontextmanager
async def lifespan(app):
 pool.open();pool.wait();yield;pool.close()
app=FastAPI(title='AgrregateX — Multi-Tenant Real-Time Aggregation Layer',version='1.0.0',lifespan=lifespan)
@app.exception_handler(OperationalError)
@app.exception_handler(PoolTimeout)
async def unavailable(request,exc):
 return JSONResponse(status_code=503,content={'detail':'Database temporarily unavailable; retry idempotent request'},headers={'Retry-After':'1'})
bearer=HTTPBearer(auto_error=False)
limits={};lock=threading.Lock()
def identity(auth:HTTPAuthorizationCredentials=Depends(bearer)):
 if not auth:raise HTTPException(401,'Bearer tenant token required')
 for tenant,token in credentials['tenants'].items():
  if secrets.compare_digest(auth.credentials,token):return int(tenant)
 raise HTTPException(401,'Invalid tenant token')
def admin(auth:HTTPAuthorizationCredentials=Depends(bearer)):
 if not auth or not secrets.compare_digest(auth.credentials,credentials['admin']):raise HTTPException(403,'Admin token required')
 return True
@contextmanager
def connection(tenant):
 with lock:
  if limits.get(tenant,0)>=2:raise HTTPException(429,'Tenant concurrency limit reached')
  limits[tenant]=limits.get(tenant,0)+1
 try:
  with pool.connection(timeout=3) as conn:
   with conn.transaction():
    conn.execute("SELECT set_config('app.tenant',%s,true)",(str(tenant),))
    conn.execute("SET LOCAL TIME ZONE 'UTC'")
    yield conn
 finally:
  with lock:limits[tenant]-=1

def bounds(start,end,grain):
 if start.tzinfo is None or end.tzinfo is None:raise HTTPException(422,'Timezone required')
 start=start.astimezone(timezone.utc);end=end.astimezone(timezone.utc)
 if start>=end or (end-start).total_seconds()>366*86400:raise HTTPException(422,'Require 0 < range <= 366 days')
 if grain=='hour' and (end-start).total_seconds()>31*86400:raise HTTPException(422,'Hourly trends limited to 31 days')
 return start,end

def analytics(family,tenant_id,start,end,grain,limit,tenant):
 if tenant_id!=tenant:raise HTTPException(403,'Tenant mismatch')
 start,end=bounds(start,end,grain);t=time.perf_counter()
 with connection(tenant) as c:
  value=aggregate(c,tenant,start,end,family,grain,limit)
  stamp=c.execute('SELECT transaction_timestamp() observed_at').fetchone()['observed_at']
 return {'tenant_id':tenant,'data':value,'freshness':{'mode':'transactional','source_and_rollups_same_commit':True,'observed_at':stamp},'query_ms':round((time.perf_counter()-t)*1000,3)}

@app.get('/tenants/{tenant_id}/summary')
def summary(tenant_id:int,start:datetime=Query(alias='from'),end:datetime=Query(alias='to'),tenant:int=Depends(identity)):
 return analytics('summary',tenant_id,start,end,'day',10,tenant)
@app.get('/tenants/{tenant_id}/orders/count')
def count(tenant_id:int,start:datetime=Query(alias='from'),end:datetime=Query(alias='to'),tenant:int=Depends(identity)):
 return analytics('summary',tenant_id,start,end,'day',10,tenant)
@app.get('/tenants/{tenant_id}/trends')
def trends(tenant_id:int,start:datetime=Query(alias='from'),end:datetime=Query(alias='to'),grain:Literal['hour','day']='day',tenant:int=Depends(identity)):
 return analytics('trend',tenant_id,start,end,grain,10,tenant)
@app.get('/tenants/{tenant_id}/top-products')
def top(tenant_id:int,start:datetime=Query(alias='from'),end:datetime=Query(alias='to'),limit:int=Query(10,ge=1,le=100),tenant:int=Depends(identity)):
 return analytics('top',tenant_id,start,end,'day',limit,tenant)
@app.get('/tenants/{tenant_id}/breakdown')
def breakdown(tenant_id:int,start:datetime=Query(alias='from'),end:datetime=Query(alias='to'),tenant:int=Depends(identity)):
 return analytics('breakdown',tenant_id,start,end,'day',10,tenant)

class Order(BaseModel):
 model_config=ConfigDict(extra='forbid')
 customer_id:int=Field(ge=1)
 product_id:int=Field(ge=1)
 category_id:int=Field(ge=1)
 ordered_at:datetime
 status:Literal['placed','shipped','cancelled']='placed'
 quantity:int=Field(ge=1,le=100000)
 unit_price_cents:int=Field(ge=0,le=1000000000)
 @field_validator('ordered_at')
 @classmethod
 def aware(cls,v):
  if v.tzinfo is None:raise ValueError('Timezone required')
  return v.astimezone(timezone.utc)
class Patch(BaseModel):
 model_config=ConfigDict(extra='forbid')
 customer_id:int|None=Field(default=None,ge=1)
 product_id:int|None=Field(default=None,ge=1)
 category_id:int|None=Field(default=None,ge=1)
 ordered_at:datetime|None=None
 status:Literal['placed','shipped','cancelled']|None=None
 quantity:int|None=Field(default=None,ge=1,le=100000)
 unit_price_cents:int|None=Field(default=None,ge=0,le=1000000000)
 @field_validator('ordered_at')
 @classmethod
 def aware(cls,v):
  if v is not None and v.tzinfo is None:raise ValueError('Timezone required')
  return v

def mutate(tenant_id,tenant,event,verb,order_id,body):
 if tenant_id!=tenant:raise HTTPException(403,'Tenant mismatch')
 if not event or len(event)>128:raise HTTPException(422,'Idempotency-Key (1–128 chars) required')
 payload=body.model_dump(mode='json',exclude_unset=True) if body else {}
 if any(v is None for v in payload.values()):raise HTTPException(422,'Null patch fields are not allowed')
 fp=hashlib.sha256(json.dumps([verb,order_id,payload],sort_keys=True).encode()).hexdigest()
 try:
  with connection(tenant) as c:
   c.execute('INSERT INTO events(tenant_id,event_id,fingerprint) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(tenant,event,fp))
   old=c.execute('SELECT * FROM events WHERE tenant_id=%s AND event_id=%s FOR UPDATE',(tenant,event)).fetchone()
   if old['fingerprint']!=fp:raise HTTPException(409,'Idempotency key reused for different request')
   if old['result'] is not None:return old['result']
   if verb=='POST':
    values=body.model_dump();keys=list(values)
    result=c.execute('INSERT INTO orders(tenant_id,'+','.join(keys)+') VALUES('+','.join(['%s']*(len(keys)+1))+') RETURNING id,version',(tenant,*[values[k] for k in keys])).fetchone()
   else:
    source=c.execute('SELECT * FROM orders WHERE tenant_id=%s AND id=%s FOR UPDATE',(tenant,order_id)).fetchone()
    if not source:raise HTTPException(404,'Order not found')
    if verb=='DELETE':
     c.execute('DELETE FROM orders WHERE tenant_id=%s AND id=%s',(tenant,order_id));result={'id':order_id,'deleted':True}
    else:
     changes=body.model_dump(exclude_unset=True)
     changes={k:v for k,v in changes.items() if source[k]!=v}
     if changes:
      result=c.execute('UPDATE orders SET '+','.join(k+'=%s' for k in changes)+',version=version+1 WHERE tenant_id=%s AND id=%s RETURNING id,version',(*changes.values(),tenant,order_id)).fetchone()
     else:result={'id':order_id,'version':source['version']}
   c.execute('UPDATE events SET result=%s WHERE tenant_id=%s AND event_id=%s',(Jsonb(result),tenant,event))
  # Exiting transaction commits source, rollups and idempotency record together.
  return result
 except HTTPException:raise
 except Exception as exc:
  from psycopg.errors import ForeignKeyViolation,CheckViolation,DeadlockDetected,SerializationFailure
  if isinstance(exc,(ForeignKeyViolation,CheckViolation)):raise HTTPException(422,'Invalid tenant-scoped order reference or value')
  if isinstance(exc,(DeadlockDetected,SerializationFailure)):raise HTTPException(503,'Retry with the same Idempotency-Key')
  raise
@app.post('/tenants/{tenant_id}/orders')
def create(tenant_id:int,body:Order,tenant:int=Depends(identity),event:str=Header(alias='Idempotency-Key')):
 return mutate(tenant_id,tenant,event,'POST',None,body)
@app.patch('/tenants/{tenant_id}/orders/{order_id}')
def update(tenant_id:int,order_id:int,body:Patch,tenant:int=Depends(identity),event:str=Header(alias='Idempotency-Key')):
 return mutate(tenant_id,tenant,event,'PATCH',order_id,body)
@app.delete('/tenants/{tenant_id}/orders/{order_id}')
def delete(tenant_id:int,order_id:int,tenant:int=Depends(identity),event:str=Header(alias='Idempotency-Key')):
 return mutate(tenant_id,tenant,event,'DELETE',order_id,None)
@app.get('/tenants/{tenant_id}/freshness')
def freshness(tenant_id:int,tenant:int=Depends(identity)):
 if tenant!=tenant_id:raise HTTPException(403,'Tenant mismatch')
 with connection(tenant) as c:return {'tenant_id':tenant,'mode':'transactional','observed_at':c.execute('select transaction_timestamp() t').fetchone()['t'],'committed_writes_visible_in_rollups':True}
@app.get('/health')
def health():
 with pool.connection() as c:c.execute('select 1')
 return {'application':'AgrregateX','status':'ok'}
@app.get('/monitoring')
def monitoring(ok=Depends(admin)):
 p=Path('results/acceptance.json')
 return {'application':'AgrregateX','engine':'transactional PostgreSQL rollups','pool':pool.get_stats(),'acceptance':json.loads(p.read_text()) if p.exists() else {'status':'NOT TESTED'}}
@app.get('/',response_class=HTMLResponse)
def dashboard():return Path('dashboard.html').read_text()
