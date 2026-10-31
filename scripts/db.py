"""Local administrative harness. Credentials stay in ignored .env; never print them."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sql(query):
 p=subprocess.run(['podman','exec','-i','agrregatex-postgres-1','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','agrregatex_owner','-d','agrregatex'],input=query,text=True,capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return p.stdout.strip()
def query_json(query):return json.loads(sql('SELECT coalesce(json_agg(t),\'[]\'::json) FROM ('+query+') t;'))
def run_python(path,args=()):
 # Execute inside the lightweight API image with existing driver packages.
 code=Path(path).read_text(); env=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line)
 pre="import os,sys\nos.environ['ADMIN_DATABASE_URL']="+repr('postgresql://agrregatex_owner:'+env['DB_PASSWORD']+'@postgres/agrregatex')+"\nsys.argv="+repr([str(path),*args])+"\n"
 return subprocess.run(['podman','exec','-i','agrregatex-api-1','python','-'],input=pre+code,text=True,capture_output=True)
