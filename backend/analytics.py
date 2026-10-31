from datetime import timedelta

def aligned(t,grain):
 return t.replace(minute=0,second=0,microsecond=0, **({'hour':0} if grain=='day' else {}))

def aggregate(conn,tenant,start,end,family,grain='day',limit=10):
 # Complete buckets plus disjoint exact edges. No overlap, [start,end).
 unit=timedelta(days=1) if grain=='day' else timedelta(hours=1)
 floor=aligned(start,grain); lo=floor if floor==start else floor+unit
 hi=aligned(end,grain)
 table='daily_product' if grain=='day' else 'hourly_category'
 if lo>=hi:
  sql="SELECT ordered_at bucket,product_id,category_id,status,1::bigint n,quantity::bigint units,CASE WHEN status='cancelled' THEN 0 ELSE quantity::bigint*unit_price_cents END cents FROM orders WHERE tenant_id=%s AND ordered_at>=%s AND ordered_at<%s"
  args=[tenant,start,end]
 else:
  product='product_id' if grain=='day' else '0 product_id'
  sql=f"SELECT bucket,{product},category_id,status,n,units,cents FROM {table} WHERE tenant_id=%s AND bucket>=%s AND bucket<%s UNION ALL SELECT ordered_at bucket,product_id,category_id,status,1::bigint n,quantity::bigint units,CASE WHEN status='cancelled' THEN 0 ELSE quantity::bigint*unit_price_cents END cents FROM orders WHERE tenant_id=%s AND ((ordered_at>=%s AND ordered_at<%s) OR (ordered_at>=%s AND ordered_at<%s))"
  args=[tenant,lo,hi,tenant,start,lo,hi,end]
 # Rollups retain cancelled gross amounts so status transitions are reversible.
 # Query cancels sales and units, but includes cancelled orders in order counts.
 if family=='summary':
  select="SELECT coalesce(sum(n),0)::bigint orders,coalesce(sum(CASE WHEN status<>'cancelled' THEN units ELSE 0 END),0)::bigint units,coalesce(sum(CASE WHEN status<>'cancelled' THEN cents ELSE 0 END),0)::bigint sales_cents FROM data"
 elif family=='top':
  select="SELECT product_id,coalesce(sum(units),0)::bigint units,coalesce(sum(cents),0)::bigint sales_cents FROM data WHERE status<>'cancelled' GROUP BY product_id HAVING sum(n)>0 ORDER BY sales_cents DESC,units DESC,product_id LIMIT %s";args.append(limit)
 elif family=='breakdown':
  select="SELECT status,category_id,sum(n)::bigint orders,sum(CASE WHEN status<>'cancelled' THEN cents ELSE 0 END)::bigint sales_cents FROM data GROUP BY status,category_id HAVING sum(n)>0 ORDER BY status,category_id"
 elif family=='trend':
  select=f"SELECT date_trunc('{grain}',bucket,'UTC') bucket,sum(n)::bigint orders,sum(CASE WHEN status<>'cancelled' THEN cents ELSE 0 END)::bigint sales_cents FROM data GROUP BY 1 ORDER BY 1"
 else:raise ValueError(family)
 rows=conn.execute('WITH data AS ('+sql+') '+select,args).fetchall()
 if family=='trend':
  found={x['bucket']:x for x in rows};cursor=aligned(start,grain);out=[]
  while cursor<end:
   out.append(found.get(cursor,{'bucket':cursor,'orders':0,'sales_cents':0}));cursor+=unit
  return out
 return rows[0] if family=='summary' else rows
