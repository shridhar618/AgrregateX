import time,urllib.request
for _ in range(120):
 try:
  if urllib.request.urlopen('http://127.0.0.1:18081/health',timeout=2).status==200:break
 except Exception:pass
 time.sleep(.5)
else:raise SystemExit('AgrregateX did not become healthy')
