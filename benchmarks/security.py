import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from db import ROOT,run_python
r=run_python(ROOT/'benchmarks/security_remote.py')
if r.returncode:raise RuntimeError(r.stderr)
d=json.loads(r.stdout);(ROOT/'benchmarks/results/security.json').write_text(json.dumps(d,indent=2));print('Security:',d['status'],len(d['tenants']),'tenant credentials')
