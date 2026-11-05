"""Read-only model discovery. No content generation, media, or publication."""
import json,os
from pathlib import Path
import requests
key=os.environ.get('GEMINI_API_KEY')
if not key: raise SystemExit('Existing Gemini credential missing')
r=requests.get('https://generativelanguage.googleapis.com/v1beta/models',headers={'x-goog-api-key':key},timeout=40,allow_redirects=False)
if not r.ok: raise SystemExit('Gemini model discovery HTTP '+str(r.status_code))
names=[m['name'].removeprefix('models/') for m in r.json().get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[]) and 'flash' in m['name'] and 'image' not in m['name']]
out={'existing_gemini_auth':True,'model_candidates':names[:30],'generated_content':False,'published':False}
Path('cloud-reports').mkdir(exist_ok=True);Path('cloud-reports/autonomous-preflight.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
