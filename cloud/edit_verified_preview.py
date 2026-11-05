"""Diagnostic editing of the exact newly-created, OCR/visual-QA-passed Canva pages.

No new Canva generation and no public publish path. Only same-day failed-video previews.
"""
import base64
import hashlib
import io
import json
import os
import zipfile
from datetime import datetime
import requests
from cloud_reel import GitHub, PublicationState, OUT, KST, require_export_url
from autonomous import fetch_image, LEDGER
from autonomous_media import ensure_detail_crops, render_video, video_review_prompt, deliver_video
from gemini_editor import generate_video_json, validate_literal_inventory

def main():
    source=os.environ['VISION_SOURCE_RUN']
    if not source.isdigit():raise RuntimeError('Source run ID required')
    state=PublicationState();rows,_=state.read(LEDGER);old=rows.get('preview-'+source,{})
    if (old.get('published') or old.get('day')!=datetime.now(KST).date().isoformat() or
            old.get('format')!='reel' or old.get('visual_review',{}).get('verdict')!='pass' or
            old.get('error')!='Final encoded video failed real model QA; no publication'):
        raise RuntimeError('Only same-day, image-verified, unpublished video diagnostic may be edited')
    gh=GitHub(os.environ['CANVA_GATEWAY_GH_TOKEN']);run=old['canva_run_id']
    record=gh.get('repos/hwang0217-lang/korea-firsttrip/actions/runs/'+run)
    if record.get('path')!='.github/workflows/nordic-canva-produce.yml' or record.get('conclusion')!='success':
        raise RuntimeError('Original fresh Canva receipt mismatch')
    artifacts=gh.get('repos/hwang0217-lang/korea-firsttrip/actions/runs/'+run+'/artifacts')['artifacts']
    if len(artifacts)!=1:raise RuntimeError('One existing Canva receipt required')
    reply=requests.get(artifacts[0]['archive_download_url'],headers=gh.headers,timeout=45)
    if not reply.ok:raise RuntimeError('Existing receipt unavailable')
    with zipfile.ZipFile(io.BytesIO(reply.content)) as archive:
        if archive.namelist()!=['result.json']:raise RuntimeError('Unexpected receipt payload')
        result=json.loads(archive.read('result.json'))
    if result.get('designId')!=old['canva_design_id'] or not result['requestId'].startswith('nordic-auto-'+source+'-'):
        raise RuntimeError('Not the exact previously reviewed Canva source')
    api=GitHub(os.environ['GITHUB_TOKEN'])
    item=api.get('repos/hwang0217-lang/cardnews/contents/cloud/autonomous/requests/'+result['requestId']+'.json?ref='+result['registryRevision'])
    request=json.loads(base64.b64decode(item['content']))['request']
    draft={'topic':old['topic'],'sections':request['sections']}
    validate_literal_inventory(old['literal_inventory'],draft['sections'])
    OUT.mkdir(exist_ok=True);pages=[]
    from PIL import Image
    for n,url in enumerate(result['urls'],1):
        require_export_url(url);data,image,_=fetch_image(url)
        if hashlib.sha256(data).hexdigest()!=old['page_sha256'][n-1]:raise RuntimeError('Reviewed Canva export changed')
        path=OUT/f'canva-{n:02d}.jpg';path.write_bytes(data);pages.append(path)
        image.thumbnail((390,693));image.save(OUT/f'page-{n:02d}.png')
    key='edit-preview-'+os.environ['GITHUB_RUN_ID'];row={'source_nordic_run':source,'canva_run_id':run,
        'canva_design_id':result['designId'],'format':'reel','stage':'editing','published':False,'pc_media_downloads':0}
    state.put(LEDGER,key,row,absent=True)
    def persist():
        state.put(LEDGER,key,row)
        (OUT/'autonomous-result.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        row['detail_crop_review']=ensure_detail_crops(pages,draft);persist()
        video,details=render_video(pages,draft,OUT,old['day']);row.update(details);persist()
        review,_=generate_video_json(video_review_prompt('reel'),video.read_bytes());row['video_review']=review;persist()
        if review.get('verdict')!='pass' or any(review.get(k) is not True for k in
                ('readable','no_overlap','full_video_checked','music_present','edit_quality')):
            raise RuntimeError('Edited diagnostic video failed actual complete-video QA')
        # Actual encoded frame samples, including every detail insert, remain inspectable.
        import subprocess
        from cloud_reel import FFMPEG
        subprocess.run([FFMPEG,'-v','error','-i',str(video),'-vf','fps=1,scale=390:-1',str(OUT/'scene-%02d.png')],check=True,capture_output=True)
        plan={'account':'nordic_log','canva_design_id':result['designId'],'purpose':'diagnostic',
              'date':old['day'],'format':'reel','caption':'비공개 서버 전송 점검 · 게시 금지'}
        deliver_video(video,plan,'delivery-check',row,persist)
        row['stage']='unpublished_FINISHED';persist()
    except Exception as exc:
        row.update(stage='blocked',error='Diagnostic edit/delivery failed: '+type(exc).__name__)
        persist();raise

if __name__=='__main__':
    try:main()
    except Exception as exc:raise SystemExit(str(exc) if not isinstance(exc,requests.RequestException) else 'Network operation failed; reconcile without retry')
