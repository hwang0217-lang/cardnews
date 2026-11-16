import {admin,coupang,request,originalUrl,text} from './generate.mjs';
import {kstDate,verificationSlots} from './policy.mjs';
const now=Date.now(),date=process.env.TARGET_DATE||kstDate();
const slots=verificationSlots(date,process.env.TARGET_SLOT,now);
// GitHub 예약이 늦게 돌면 검증할 슬롯이 없다: 할 일이 없는 것이지 오류가 아니다
if(!slots.length){console.log('No upcoming shopping slot within 90 minutes; nothing to verify.');process.exit(0)}
const state=await admin('state');
for(const slot of slots){
const post=state.posts.find(p=>p.date===date&&p.slot===slot);
if(!post)throw Error('Missing prepared post');
if(post.type==='info'){console.log('Info post has no product or source to recheck.');continue}
if(post.status==='published_verified'){console.log('Already published; no changes or duplicate publication.');continue}
// 검색 순위가 바뀌면 상위 10개에서 빠질 수 있으므로 정확한 상품명으로 한 번 더 찾는다
let found=false;
for(const keyword of new Set([post.searchKeyword,post.product.productName.slice(0,80)].filter(Boolean))){
const products=await coupang('GET','/v2/providers/affiliate_open_api/apis/openapi/v1/products/search','keyword='+encodeURIComponent(keyword)+'&limit=10&imageSize=1024x1024');
if((products.productData||[]).some(p=>p.productId==post.product.productId&&originalUrl(p)===post.product.originalUrl)){found=true;break}
}
if(!found)throw Error('Exact product option is no longer found in official API');
const article=text(await (await request(post.evidence.url)).text());
const normalize=s=>s.normalize('NFKC').replace(/\s+/g,' ').trim();
if(!normalize(article).includes(normalize(post.evidence.quote)))throw Error('Source evidence changed; hold publication');
const result=await admin('revalidate',{key:post.key,productId:post.product.productId,originalUrl:post.product.originalUrl,sourceUrl:post.evidence.url,verifiedAt:new Date().toISOString()});
console.log(JSON.stringify({date,slot,productVerified:true,sourceVerified:true,result,published:false}));
}
