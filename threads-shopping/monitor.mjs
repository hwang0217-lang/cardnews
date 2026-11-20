import {kstDate,SLOTS,slotTime} from './policy.mjs';
const now=Date.now(),date=kstDate(now),base=process.env.THREADS_SERVER_URL||'https://nordic-log-threads.apollo0217.workers.dev',headers={Authorization:'Bearer '+process.env.THREADS_SHOPPING_ADMIN_KEY};
const response=await fetch(base+'/admin/state',{headers,redirect:'error',signal:AbortSignal.timeout(30000)});
if(!response.ok)throw Error('Server monitor connection failed');
const state=await response.json();
const issues=[];
if(!state.active)issues.push('server_paused');
if(!state.lastTick||now-Date.parse(state.lastTick)>5*60000)issues.push('server_heartbeat_stale');
for(const slot of SLOTS){if(slotTime(date,slot)+15*60000>now)continue;const p=state.posts.find(p=>p.date===date&&p.slot===slot);if(p?.status!=='published_verified'&&!(p?.status==='skipped'&&p.error==='operator_skipped'))issues.push(slot+':'+(p?.status||'missing_queue')+(p?.error?':'+p.error:''));}
// slot_too_late hides why the slot window was missed (e.g. an expired Threads token), so check the account read-only too; 409 = server busy, not a fault
const check=await fetch(base+'/admin/check',{headers,redirect:'error',signal:AbortSignal.timeout(30000)});
if(!check.ok&&check.status!==409)issues.push('threads_account:'+((await check.json().catch(()=>({}))).error||check.status));
console.log(JSON.stringify({date,issues,pcRequired:false}));if(issues.length)process.exitCode=1;
