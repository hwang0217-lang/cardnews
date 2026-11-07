import {DurableObject} from 'cloudflare:workers';
import {ACCOUNT,SLOTS,kstDate,validateRecord,duplicate,safeError,fetchPartnerImage} from './policy.mjs';
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const actor=env=>env.STATE.get(env.STATE.idFromName('nordic-log-threads-v1'));
export default {
 async fetch(request,env){
  const path=new URL(request.url).pathname;
  if(path==='/health')return json({service:'nordic-log-threads',build:env.BUILD_ID,clock:'Asia/Seoul',scheduleKst:SLOTS,pcRequired:false});
  if(!env.ADMIN_KEY||request.headers.get('Authorization')!=='Bearer '+env.ADMIN_KEY)return json({error:'unauthorized'},401);
  return actor(env).fetch(request);
 },
 async scheduled(event,env,ctx){ctx.waitUntil(actor(env).fetch(new Request('https://internal/tick',{method:'POST'})));}
};
export class ShoppingState extends DurableObject {
 constructor(ctx,env){super(ctx,env);this.s=ctx.storage;this.env=env;this.busy=false;}
 async rows(){return [...(await this.s.list({prefix:'post:'})).values()]}
 async save(r){await this.s.put('post:'+r.key,r)}
 async token(){return (await this.s.get('internal:token'))||this.env.THREADS_TOKEN}
 async api(path,form){
  let response;
  try{response=await fetch('https://graph.threads.net/v1.0/'+path,{method:form?'POST':'GET',redirect:'manual',headers:{Authorization:'Bearer '+await this.token(),...(form?{'Content-Type':'application/x-www-form-urlencoded'}:{})},body:form?new URLSearchParams(form):undefined,signal:AbortSignal.timeout(30000)});}catch(e){let detail=String(e.message||'').slice(0,500);for(const value of [await this.token(),this.env.ADMIN_KEY])if(value)detail=detail.split(value).join('[redacted]');detail=detail.replace(/[A-Za-z0-9+_\/-]{45,}/g,'[redacted]');await this.s.put('internal:transportDiagnostic',detail.slice(0,180));throw Error('threads_transport_'+String(e.name||'error').replace(/[^a-z]/gi,'').toLowerCase())}
  if(!response.ok)throw Error('threads_http:'+response.status);
  let data;try{data=await response.json()}catch{throw Error('threads_invalid_json')};if(data.error)throw Error('threads_error');return data;
 }
 async profile(){const p=await this.api('me?fields=id,username');if(p.id!==ACCOUNT.id||p.username!==ACCOUNT.username)throw Error('wrong_account');return p;}
 async recent(){await this.profile();return (await this.api('me/threads?fields=id,text,permalink,media_type,media_url,timestamp&limit=100')).data||[];}
 async reconcile(r){
  const posts=await this.recent();const found=posts.filter(x=>x.text===r.caption);
  if(found.length>1)throw Error('multiple_matching_posts');
  if(found.length===1){if(found[0].media_type!=='IMAGE')throw Error('wrong_published_media');r.status='published_verified';r.mediaId=found[0].id;r.permalink=found[0].permalink;r.publishedAt=found[0].timestamp;await this.save(r);return true}
  return false;
 }
 async prepare(r){
  if(['published_verified','publish_requested','ambiguous_publish_result','preparing','preparation_unknown','skipped'].includes(r.status))return;
  if(await this.reconcile(r))return;
  if(r.creationId){const c=await this.api(r.creationId+'?fields=status');r.containerStatus=c.status;if(c.status==='FINISHED')r.status='ready';else if(c.status==='ERROR'||c.status==='EXPIRED')r.status='rejected';await this.save(r);return}
  if(duplicate(await this.rows(),r))throw Error('duplicate_product');
  r.status='preparing';await this.save(r);
  try{
   const image=await fetchPartnerImage(r.product.productImage,'HEAD');
   if(!image.ok||!image.headers.get('Content-Type')?.startsWith('image/'))throw Error('image_unavailable');
   const container=await this.api(ACCOUNT.id+'/threads',{media_type:'IMAGE',image_url:r.product.productImage,text:r.caption,alt_text:r.product.productName});
   if(!container.id)throw Error('missing_creation_id');r.creationId=container.id;r.status='container_created';await this.save(r);
   const c=await this.api(r.creationId+'?fields=status');r.containerStatus=c.status;if(c.status==='FINISHED')r.status='ready';await this.save(r);
  }catch(e){r.status=r.creationId?'container_created':'preparation_unknown';r.error=safeError(e);await this.save(r);throw e}
 }
 async publish(r,now){
  if(now<r.publishAt)return;
  if(r.status==='published_verified'||r.status==='skipped'||r.status==='rejected')return;
  if(['publish_requested','ambiguous_publish_result'].includes(r.status)){await this.reconcile(r);return;}
  if(now-r.publishAt>15*60000){r.status='skipped';r.error='slot_too_late';await this.save(r);return}
  await this.prepare(r);
  if(r.status!=='ready')return;
  if(await this.reconcile(r))return;
  if(duplicate(await this.rows(),r))throw Error('duplicate_product');
  r.status='publish_requested';r.attemptedAt=new Date(now).toISOString();await this.save(r);
  try{
   const p=await this.api(ACCOUNT.id+'/threads_publish',{creation_id:r.creationId});
   if(!p.id)throw Error('missing_published_id');r.mediaId=p.id;await this.save(r);
   const post=await this.api(p.id+'?fields=id,text,permalink,media_type,media_url,timestamp,username');
   if(post.text!==r.caption||post.username!==ACCOUNT.username||post.media_type!=='IMAGE'||!post.permalink)throw Error('readback_mismatch');
   r.status='published_verified';r.permalink=post.permalink;r.publishedAt=post.timestamp;await this.save(r);
  }catch(e){r.status='ambiguous_publish_result';r.error=safeError(e);await this.save(r);throw e}
 }
 async refresh(now){
  const last=await this.s.get('internal:refreshedAt')||Number(this.env.TOKEN_ISSUED_AT)*1000;
  if(now-last<36*3600000)return;
  const response=await fetch('https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token',{headers:{Authorization:'Bearer '+await this.token()},redirect:'manual',signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw Error('refresh_http:'+response.status);const t=await response.json();if(!t.access_token)throw Error('refresh_missing_token');
  await this.s.put({'internal:token':t.access_token,'internal:refreshedAt':now,'internal:expiresAt':now+t.expires_in*1000});
 }
 async tick(){
  const now=Date.now();if(this.env.ACTIVE!=='1')return {status:'paused'};
  const rows=await this.rows();
  for(const r of rows){if(r.publishAt>now&&r.publishAt-now<=10*60000)await this.prepare(r);if(now>=r.publishAt&&now-r.publishAt<86400000)await this.publish(r,now)}
  if(new Date(now).getUTCHours()===22)await this.refresh(now);
  await this.s.put('internal:lastTick',new Date(now).toISOString());
  const waiting=(await this.rows()).some(r=>!['published_verified','skipped','rejected','ambiguous_publish_result','publish_requested','preparation_unknown'].includes(r.status)&&now>=r.publishAt&&now-r.publishAt<=15*60000);
  if(waiting)await this.s.setAlarm(now+5000);
  return {status:'checked',dateKst:kstDate(now)};
 }
 async alarm(){if(this.busy){await this.s.setAlarm(Date.now()+5000);return}this.busy=true;try{await this.tick()}catch(e){await this.s.put('internal:lastError',{error:safeError(e),at:new Date().toISOString()})}finally{this.busy=false}}
 async fetch(request){
  if(this.busy)return json({error:'busy'},409);this.busy=true;
  try{
   const path=new URL(request.url).pathname;
   if(path==='/tick')return json(await this.tick());
   if(path==='/admin/state')return json({active:this.env.ACTIVE==='1',build:this.env.BUILD_ID,lastTick:await this.s.get('internal:lastTick'),lastError:await this.s.get('internal:lastError'),transportDiagnostic:await this.s.get('internal:transportDiagnostic'),refreshedAt:await this.s.get('internal:refreshedAt'),posts:await this.rows()});
   if(path==='/admin/check'){await this.profile();return json({account:ACCOUNT.username,verified:true})}
   if(request.method!=='POST')return json({error:'method_not_allowed'},405);
   if(path==='/admin/claim-generation'){
    const {date}=await request.json();if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('invalid_date');
    if(await this.s.get('generation:'+date))return json({claimed:false});
    await this.s.put('generation:'+date,{at:new Date().toISOString()});return json({claimed:true});
   }
   if(path==='/admin/queue'){
    const input=await request.json();if(!Array.isArray(input.posts)||input.posts.length!==3)throw Error('expected_three_posts');
    const posts=input.posts.map(r=>validateRecord(r));if(new Set(posts.map(r=>r.slot)).size!==3||new Set(posts.map(r=>r.date)).size!==1||new Set(posts.map(r=>r.category)).size!==3||new Set(posts.map(r=>r.product.productId)).size!==3)throw Error('invalid_daily_mix');
    const rows=await this.rows();for(const r of posts){if(rows.some(x=>x.key===r.key)||duplicate([...rows,...posts],r))throw Error('duplicate_queue')}
    for(const r of posts)await this.save(r);return json({queued:posts.map(r=>r.key)});
   }
   if(path==='/admin/repair-generation'){
    const {date,revision}=await request.json();
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!/^\w{40}$/.test(revision)||date<kstDate()||date>kstDate(Date.now()+86400000))throw Error('invalid_repair');
    const previous=await this.s.get('repair:'+date);const repairs=previous?(Array.isArray(previous)?previous:[previous]):[];
    if(repairs.length>=2||repairs.some(r=>r.revision===revision)||(await this.rows()).some(r=>r.date===date))throw Error('repair_already_used');
    repairs.push({revision,at:new Date().toISOString(),reason:'operator_verified_code_fix'});await this.s.put('repair:'+date,repairs);await this.s.delete('generation:'+date);return json({repairAuthorized:true,date});
   }
   if(path==='/admin/seed'){
    const {posts}=await request.json();if(!Array.isArray(posts)||posts.length>10)throw Error('invalid_seed');
    const recent=await this.recent();
    for(const p of posts){const found=recent.find(x=>x.id===p.mediaId&&x.text===p.caption&&x.permalink===p.permalink);if(!found)throw Error('seed_not_verified');const r={...p,key:'seed-'+p.mediaId,status:'published_verified',publishedAt:found.timestamp};await this.save(r)}return json({seeded:posts.length});
   }
   if(path==='/admin/prepare'){
    const {key}=await request.json();const r=await this.s.get('post:'+key);if(!r||r.publishAt<Date.now()||r.publishAt>Date.now()+23*3600000)throw Error('invalid_prepare_target');await this.prepare(r);return json({key:r.key,status:r.status,containerStatus:r.containerStatus});
   }
   return json({error:'not_found'},404);
  }catch(e){const error=safeError(e);await this.s.put('internal:lastError',{error,at:new Date().toISOString()});return json({error},500)}finally{this.busy=false}
 }
}
