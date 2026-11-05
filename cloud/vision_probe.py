"""Diagnostic: literal image reading without draft/benchmark priming, no generation/post."""
import base64
import io
import json
import os
import zipfile
from pathlib import Path
import requests
from PIL import Image
from cloud_reel import GitHub, require_export_url

client=GitHub(os.environ['CANVA_GATEWAY_GH_TOKEN'])
run=os.environ['VISION_SOURCE_RUN']
record=client.get('repos/hwang0217-lang/korea-firsttrip/actions/runs/'+run)
if record.get('path')!='.github/workflows/nordic-canva-produce.yml' or record.get('conclusion')!='success':
    raise SystemExit('Existing fresh-production receipt required')
artifacts=client.get('repos/hwang0217-lang/korea-firsttrip/actions/runs/'+run+'/artifacts')['artifacts']
if len(artifacts)!=1:raise SystemExit('One receipt required')
r=requests.get(artifacts[0]['archive_download_url'],headers=client.headers,timeout=45)
with zipfile.ZipFile(io.BytesIO(r.content)) as archive:result=json.loads(archive.read('result.json'))
url=require_export_url(result['urls'][0]);print('::add-mask::'+url)
r=requests.get(url,timeout=45,allow_redirects=False);r.raise_for_status()
image=Image.open(io.BytesIO(r.content));image.thumbnail((540,960));buffer=io.BytesIO();image.convert('RGB').save(buffer,'JPEG')
parts=[{'text':'Describe ONLY the image you actually see. There is no expected topic. Return JSON with literal_subject, main_objects, people_count, and visible_text copied exactly as visible, marking unreadable text. Never invent objects or infer an intended design.'},
       {'inlineData':{'mimeType':'image/jpeg','data':base64.b64encode(buffer.getvalue()).decode()}}]
out={'source_run':run,'results':{},'published':False}
for model in ('gemini-3.5-flash-lite','gemini-3.8-flash'):
    response=requests.post('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',
        headers={'x-goog-api-key':os.environ['GEMINI_API_KEY']},json={'contents':[{'parts':parts}],
        'generationConfig':{'temperature':0,'maxOutputTokens':1500,'responseMimeType':'application/json'}},timeout=120)
    if not response.ok:out['results'][model]={'http':response.status_code};continue
    data=response.json();text=''.join(p.get('text','') for p in data['candidates'][0]['content']['parts'] if not p.get('thought'))
    out['results'][model]=json.loads(text)
Path('cloud-reports').mkdir(exist_ok=True);Path('cloud-reports/autonomous-vision-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
