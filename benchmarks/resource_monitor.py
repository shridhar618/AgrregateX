import subprocess,json,time,pathlib,shutil
p=pathlib.Path(__file__).parent/'results';samples=[]
while not (p/'.monitor-stop').exists():
 try:
  r=subprocess.check_output(['podman','stats','--no-stream','--format','json','agrregatex-postgres-1','agrregatex-api-1'],text=True)
  samples.append({'utc':time.time(),'containers':json.loads(r),'meminfo':pathlib.Path('/proc/meminfo').read_text(),'disk_free':shutil.disk_usage(p).free})
  (p/'resources-sampled.json').write_text(json.dumps(samples,indent=2))
 except Exception:pass
 time.sleep(3)
