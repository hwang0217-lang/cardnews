"""Reconcile existing real-photo previews. No Canva creation or Instagram writes."""
import base64
import hashlib
import io
import json
import os
import re
import zipfile
from pathlib import Path
import requests
from autonomous import fetch_image,review_images,read_literal_images,LEDGER,ROOT
from cloud_reel import GitHub,PublicationState,OUT,graph,require_export_url
from gemini_editor import validate_literal_inventory,generate_video_json
from photo_editorial import validate_photo_plan


def main():
    source=os.environ['VISION_SOURCE_RUN'];day=os.environ.get('NORDIC_PLAN_DATE','')
    if not source.isdigit() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):raise RuntimeError('Existing preview and saved plan date required')
    state=PublicationState();rows,_=state.read(LEDGER);old=rows.get('preview-'+source,{})
    if old.get('published') is not False or old.get('mode')!='preview' or old.get('design_policy')!='impeccable-real-photo-v1':raise RuntimeError('Unpublished real-photo preview required')
    approved=json.loads((ROOT/f'cloud/reviews/{day}-impeccable-preview.json').read_text(encoding='utf-8'))
    if approved.get('source_run')!=source or approved.get('native_and_390_human_review') is not True:raise RuntimeError('Hash-bound direct image review required')
    client=GitHub(os.environ['CANVA_GATEWAY_GH_TOKEN']);run=old['canva_run_id'];record=client.get('repos/hwang0217-lang/korea-firsttrip/actions/runs/'+run)
    if record.get('path')!='.github/workflows/nordic-canva-produce.yml' or record.get('conclusion')!='success':raise RuntimeError('Existing Canva receipt invalid')
    artifacts=client.get('repos/hwang0217-lang/korea-firsttrip/actions/runs/'+run+'/artifacts')['artifacts']
    matches=[a for a in artifacts if a['name']=='nordic-fresh-'+old['request_id'] and not a['expired']]
    if len(matches)!=1:raise RuntimeError('Exact one existing Canva artifact required')
    response=requests.get(matches[0]['archive_download_url'],headers=client.headers,timeout=45);response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        if z.namelist()!=['result.json']:raise RuntimeError('Unexpected receipt payload')
        result=json.loads(z.read('result.json'))
    if result.get('requestId')!=old['request_id'] or result.get('designId')!=approved['canva_design_id']:raise RuntimeError('Wrong existing Canva source')
    item=GitHub(os.environ['GITHUB_TOKEN']).get('repos/hwang0217-lang/cardnews/contents/cloud/autonomous/requests/'+old['request_id']+'.json?ref='+result['registryRevision'])
    original=json.loads(base64.b64decode(item['content']))['request'];draft=json.loads((ROOT/f'cloud/editorial-plans/{day}.json').read_text(encoding='utf-8'))
    if draft['sections']!=original['sections']:raise RuntimeError('Existing pixels may only be reviewed against unchanged exact sections')
    catalog=json.loads((ROOT/'cloud/photo-catalog.json').read_text(encoding='utf-8'));validate_photo_plan(draft,catalog,1920)
    row={'source_nordic_run':source,'canva_run_id':run,'canva_design_id':result['designId'],'published':False,'instagram_writes':0,'canva_creations':0,'pc_video_downloads':0,'stage':'reviewing_existing'}
    key='photo-review-'+os.environ['GITHUB_RUN_ID'];state.put(LEDGER,key,row,absent=True);OUT.mkdir(exist_ok=True)
    def persist():
        state.put(LEDGER,key,row);(OUT/'autonomous-existing-photo.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        pages=[];images=[];hashes=[]
        for n,url in enumerate(result['urls'],1):
            require_export_url(url);data,im,jpeg=fetch_image(url);digest=hashlib.sha256(data).hexdigest()
            if digest!=approved['pages'][n-1]['sha256'] or im.size!=(1080,1920):raise RuntimeError('Reviewed export pixels changed')
            path=OUT/f'canva-{n:02}.jpg';path.write_bytes(data);pages.append(path);images.append(jpeg);hashes.append(digest)
            im.thumbnail((390,694));im.save(OUT/f'page-{n:02}.png')
        inventory,_=read_literal_images(images,draft['sections']);row['literal_inventory']=inventory;persist();validate_literal_inventory(inventory,draft['sections'])
        if graph('GET','me?fields=id,username').get('username')!='nordic_log':raise RuntimeError('Wrong account')
        posts=graph('GET','me/media?fields=id,media_type,media_url,thumbnail_url,children{media_url}&limit=9').get('data',[])
        if len(posts)!=9:raise RuntimeError('Nine real recent posts required')
        references=[]
        for post in posts:
            urls=[post.get('thumbnail_url') if post.get('media_type')=='VIDEO' else post.get('media_url')]+[c['media_url'] for c in post.get('children',{}).get('data',[])[1:]]
            for url in urls:
                if not url:continue
                _,im,_=fetch_image(url);im.thumbnail((540,675));buf=io.BytesIO();im.convert('RGB').save(buf,'JPEG');references.append(buf.getvalue())
        review,_=review_images(draft,images,references,'reel');row.update(visual_review=review,reference_images_compared=len(references),page_sha256=hashes);persist()
        if review.get('verdict')!='pass':raise RuntimeError('Existing design not accepted by actual image review')
        from autonomous_media import ensure_detail_crops,render_video,video_review_prompt
        for section,p in zip(draft['sections'],review['pages']):section['detail_crop']=p.get('detail_crop')
        row['detail_crop_review']=ensure_detail_crops(pages,draft);persist()
        video,details=render_video(pages,draft,OUT,day);row.update(details,stage='video_review');persist()
        review,_=generate_video_json(video_review_prompt('reel'),video.read_bytes());row['video_review']=review;persist()
        if review.get('verdict')!='pass' or any(review.get(k) is not True for k in ('readable','no_overlap','full_video_checked','music_present','edit_quality')):raise RuntimeError('Existing design video did not pass full-file model QA')
        row['stage']='ready_preview';persist()
    except Exception as exc:
        row.update(stage='blocked',error='Existing photo review failed: '+(type(exc).__name__ if isinstance(exc,requests.RequestException) else re.sub(r'https?://\S+','[url]',str(exc))[:300]));persist();raise RuntimeError(row['error']) from None


if __name__=='__main__':main()
