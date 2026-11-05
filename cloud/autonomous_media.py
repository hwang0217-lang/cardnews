"""Runner-only editing and official resumable upload. No public video storage or PC file."""
import hashlib
import json
import os
import re
import subprocess
import time
from urllib.parse import urlparse
from datetime import datetime
import requests
from cloud_reel import FFMPEG, KST, PublicationState, enforce_publish, graph

def approved_music(mood, directory, day):
    tracks = json.loads(os.environ.get('NORDIC_APPROVED_MUSIC', '[]'))
    if len(tracks) != 10: raise RuntimeError('Approved ten-track server library missing')
    choices = [t for t in tracks if t['mood'] == mood]
    if not choices: raise RuntimeError('Requested music mood unavailable')
    track = choices[datetime.fromisoformat(day).toordinal() % len(choices)]
    u = urlparse(track['url'])
    if u.scheme != 'https' or u.username or u.password or u.port or not u.hostname:
        raise RuntimeError('Invalid approved music URL')
    print('::add-mask::' + track['url'])
    r = requests.get(track['url'], timeout=90, allow_redirects=False)
    if not r.ok or len(r.content) > 20_000_000 or hashlib.sha256(r.content).hexdigest() != track['sha256']:
        raise RuntimeError('Approved music bytes unavailable or changed; no generation fallback')
    path = directory / 'approved-music.mp3'; path.write_bytes(r.content)
    return path, track['id']

def render_video(pages, draft, directory, day):
    """Canva is the final visual source; only cropping/reveal/edit/music happen here."""
    durations = [max(3.5, min(7, (len(s['title']) + len(s.get('body', ''))) / 7 + 1.5)) for s in draft['sections']]
    if sum(durations) > 29: raise RuntimeError('Too much text; edit the script instead of speeding up cuts')
    mood=draft.get('music_mood')
    if mood not in ('warm','bright','playful','calm','clean'):
        text=json.dumps(draft,ensure_ascii=False)
        mood=next((m for m,words in [('calm',('휴식','저녁')),('playful',('실수','공감')),('clean',('비교','단위')),('bright',('정리','수납','동선'))] if any(w in text for w in words)),'warm')
    music, track = approved_music(mood, directory, day)
    clips = []; insert_seconds = 0; inserts = 0
    for n, (page, seconds) in enumerate(zip(pages, durations)):
        clip = directory / f'clip-{n:02d}.mp4'
        frames = round(seconds * 30)
        # A brief detail view pulls back to the complete readable composition; then holds.
        # Final motion suitability is reviewed on the whole encoded video, never inferred here.
        vf = ("scale=1080:1920,zoompan=z='if(lte(on,24),1.06-0.0025*on,1)':"
              "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=" + str(frames) + ":s=1080x1920:fps=30,format=yuv420p")
        regions=draft['sections'][n].get('reveal_regions',[])
        if regions:
            vf='scale=1080:1920,loop=loop='+str(frames-1)+':size=1:start=0,setpts=N/(30*TB),format=yuv420p'
            for region in regions:
                x,y,w,h=[region.get(k) for k in ('x','y','w','h')]
                delay=region.get('at_seconds');color=region.get('bg','')
                if (any(type(v) not in (int,float) for v in (x,y,w,h,delay)) or
                        not (0<=x<x+w<=1080 and 0<=y<y+h<=1920 and w>0 and h>0 and 0.5<=delay<=1.5) or
                        not re.fullmatch(r'#[0-9a-fA-F]{6}',color) or not region.get('role')):
                    raise RuntimeError('Invalid actual-diagram reveal region')
                vf+=f",drawbox=x={round(x)}:y={round(y)}:w={round(w)}:h={round(h)}:color=0x{color[1:]}:t=fill:enable='lt(t,{delay})'"
        subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', str(page), '-vf', vf, '-an',
                        '-r','30','-frames:v',str(frames),'-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-threads', '2', str(clip)],
                       check=True, capture_output=True)
        clips.append(clip)
        crop = draft['sections'][n].get('detail_crop')
        if crop and inserts < 2 and n < len(pages)-1:
            x,y,w,h=[crop.get(k) for k in ('x','y','w','h')]
            if (any(type(v) not in (int,float) for v in (x,y,w,h)) or
                    not (0<=x<x+w<=1080 and 0<=y<y+h<=1920 and w>=120 and h>=120)):
                raise RuntimeError('Detail crop must identify an actual photo rectangle')
            detail=directory/f'detail-{n:02d}.mp4'
            subprocess.run([FFMPEG,'-v','error','-y','-loop','1','-i',str(page),'-t','1',
                '-vf',f'crop={round(w)}:{round(h)}:{round(x)}:{round(y)},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p',
                '-r','30','-c:v','libx264','-threads','2','-preset','fast','-crf','20',str(detail)],check=True,capture_output=True)
            clips.append(detail);inserts+=1;insert_seconds+=1

    listing = directory / 'concat.txt'
    listing.write_text('\n'.join("file '" + p.name + "'" for p in clips))
    target = directory / 'server-only.mp4'
    total = sum(round(s * 30) / 30 for s in durations) + insert_seconds
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-i', str(music), '-filter_complex',
                    f'[1:a]volume=0.5,afade=t=in:d=0.2,afade=t=out:st={total-1}:d=1[a]',
                    '-map', '0:v', '-map', '[a]', '-t', str(total), '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '160k', '-movflags', '+faststart', str(target)], check=True, capture_output=True)
    subprocess.run([FFMPEG, '-v', 'error', '-i', str(target), '-f', 'null', '-'], check=True, capture_output=True)
    return target, {'duration_seconds': total, 'scene_seconds': durations, 'music_track': track,
                    'video_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                    'edit_segments': len(clips), 'canva_visual_source': True, 'full_decode': True, 'pc_video_download': False}

def require_upload_target(uri, container_id):
    u = urlparse(uri)
    if (u.scheme != 'https' or u.hostname != 'rupload.facebook.com' or u.username or u.password or
            u.port or u.query or u.fragment or not re.fullmatch(r'\d+', str(container_id)) or
            not re.fullmatch(r'/ig-api-upload/v\d+\.\d+/' + str(container_id), u.path)):
        raise RuntimeError('Untrusted resumable destination; no credential sent')
    return uri

def deliver_video(file, plan, mode, row, persist):
    identity = graph('GET', 'me?fields=id,username')
    if identity.get('username') != 'nordic_log': raise RuntimeError('Wrong account')
    if os.environ.get('PUBLISH_PAUSED', '1') != '0': raise RuntimeError('Account paused')
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    state = PublicationState(); key = datetime.now(KST).date().isoformat() + '-cloud'
    if mode == 'publish':
        journals = [state.read('cardnews/' + n)[0] for n in ('managed-state.json', 'reels-state.json')]
        posts = graph('GET', 'me/media?fields=id,permalink,timestamp&limit=15').get('data', [])
        enforce_publish(plan, digest, posts, journals, datetime.now(KST))
        state.put('cardnews/managed-state.json', key, {'status': 'pending', 'at': datetime.now(KST).isoformat(),
                  'canva_design_id': plan['canva_design_id'], 'format': plan['format'], 'sha256': digest}, absent=True)
    row['upload_status'] = 'creating'; persist()
    session = graph('POST', identity['id'] + '/media', {'media_type': 'REELS', 'upload_type': 'resumable',
        'caption': plan['caption'], 'share_to_feed': 'true', 'is_ai_generated': 'true', 'thumb_offset': '1000'})
    uri = require_upload_target(session['uri'], session['id'])
    row.update(container_id=session['id'], upload_status='uploading'); persist()
    data = file.read_bytes()
    r = requests.post(uri, data=data, headers={'Authorization': 'OAuth ' + os.environ['IG_ACCESS_TOKEN'],
        'offset': '0', 'file_size': str(len(data)), 'Content-Type': 'application/octet-stream'},
        timeout=180, allow_redirects=False)
    if not r.ok or r.json().get('success') is not True:
        row['upload_status'] = 'unknown'; persist(); raise RuntimeError('Binary upload unconfirmed; reconcile without retry')
    row['upload_status'] = 'processing'; persist()
    for _ in range(80):
        status = graph('GET', session['id'] + '?fields=status_code')['status_code']
        if status == 'FINISHED': break
        if status in ('ERROR', 'EXPIRED'): raise RuntimeError('Instagram rejected prepared video')
        time.sleep(5)
    else: raise RuntimeError('Instagram processing pending; reconcile existing container')
    row.update(upload_status='FINISHED', published=False); persist()
    if mode != 'publish': return
    row['upload_status'] = 'publishing'; persist()
    media = graph('POST', identity['id'] + '/media_publish', {'creation_id': session['id']})
    row['media_id'] = media['id']; persist()
    actual = graph('GET', media['id'] + '?fields=id,permalink,media_product_type,timestamp,media_url')
    if actual.get('media_product_type') != 'REELS' or not actual.get('permalink'):
        raise RuntimeError('Public result uncertain; never repeat')
    row.update(published=True, permalink=actual['permalink'], upload_status='published_verified'); persist()
    entry = {'status': 'published', 'at': actual['timestamp'], 'canva_design_id': plan['canva_design_id'],
             'format': plan['format'], 'sha256': digest, 'permalink': actual['permalink'], 'media_id': media['id']}
    for name in ('managed-state.json', 'reels-state.json'): state.put('cardnews/' + name, key, entry)
    # Public result verification happens after durable publication recording. A playback
    # error can never cause a second publish, and the media never reaches the user's PC.
    if not actual.get('media_url'): raise RuntimeError('Published ID recorded; playback URL verification unavailable')
    print('::add-mask::' + actual['media_url'])
    r=requests.get(actual['media_url'],timeout=120,allow_redirects=False)
    if not r.ok or len(r.content)>150_000_000: raise RuntimeError('Published media recorded; playback retrieval needs review')
    verified=file.with_name('public-transcode-check.mp4');verified.write_bytes(r.content)
    subprocess.run([FFMPEG,'-v','error','-i',str(verified),'-f','null','-'],check=True,capture_output=True)
    row['public_playback_decode_verified']=True;persist()
