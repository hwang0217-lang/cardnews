import {admin,coupang,request,originalUrl,text} from './generate.mjs';
import {SLOTS,kstDate,slotTime} from './policy.mjs';
const now=Date.now(),date=process.env.TARGET_DATE||kstDate();
const slot=process.env.TARGET_SLOT||SLOTS.find(s=>slotTime(date,s)>=now&&slotTime(date,s)-now<=90*60000);
if(!slot)throw Error('No upcoming slot is eligible for verification');
const state=await admin('state');
const post=state.posts.find(p=>p.date===date&&p.slot===slot);
if(!post)throw Error('Missing prepared post');
if(post.status==='published_verified'){console.log('Already published; no changes or duplicate publication.');process.exit(0)}
const keyword=post.searchKeyword||post.product.productName.slice(0,80);
const products=await coupang('GET','/v2/providers/affiliate_open_api/apis/openapi/v1/products/search','keyword='+encodeURIComponent(keyword)+'&limit=10&imageSize=1024x1024');
if(!(products.productData||[]).some(p=>p.productId==post.product.productId&&originalUrl(p)===post.product.originalUrl))throw Error('Exact product option is no longer found in official API');
const article=text(await (await request(post.evidence.url)).text());
const normalize=s=>s.normalize('NFKC').replace(/\s+/g,' ').trim();
if(!normalize(article).includes(normalize(post.evidence.quote)))throw Error('Source evidence changed; hold publication');
const result=await admin('revalidate',{key:post.key,productId:post.product.productId,originalUrl:post.product.originalUrl,sourceUrl:post.evidence.url,verifiedAt:new Date().toISOString()});
console.log(JSON.stringify({date,slot,productVerified:true,sourceVerified:true,result,published:false}));
