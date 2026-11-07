export const ACCOUNT={id:'39841850798795933',username:'nordic_log'};
export const SLOTS=['09:00','12:00','15:00'];
export const DISCLOSURE='쿠팡 제휴 링크 포함 · 구매 시 수수료를 받습니다.';
export const LINK_INTRO='물어보는 분들 많아서 링크 남겨 둘게';
export const SOURCE_HOSTS=['www.shinsegaegroupnewsroom.com','news.samsung.com','cjnews.cj.net','newsroom.cj.net'];
export function kstDate(now=Date.now()){return new Date(now+9*3600000).toISOString().slice(0,10)}
export function slotTime(date,slot){if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!SLOTS.includes(slot))throw Error('invalid_slot');return Date.parse(date+'T'+slot+':00+09:00')}
export function validateRecord(r,now=Date.now()){
 if(!r||!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!SLOTS.includes(r.slot))throw Error('invalid_slot');
 const when=slotTime(r.date,r.slot);
 if(when<now-15*60000||when>now+48*3600000)throw Error('invalid_window');
 if(!/^\d+$/.test(String(r.product?.productId)))throw Error('invalid_product');
 const original=new URL(r.product.originalUrl),image=new URL(r.product.productImage),link=new URL(r.product.shortUrl);
 if(original.origin!=='https://www.coupang.com'||original.pathname!=='/vp/products/'+r.product.productId||!original.searchParams.get('itemId')||!original.searchParams.get('vendorItemId'))throw Error('product_target_mismatch');
 if(image.origin!=='https://ads-partners.coupang.com'||link.origin!=='https://link.coupang.com'||!/^\/a\/[a-zA-Z0-9]+$/.test(link.pathname))throw Error('untrusted_partner_asset');
 if(r.caption!==r.body+'\n\n'+LINK_INTRO+'\n'+r.product.shortUrl+'\n'+DISCLOSURE||[...r.caption].length>500)throw Error('invalid_caption');
 if(/https?:\/\//.test(r.body)||/내돈내산|써보니|내가 찍|품절 대란|같은 공장|동일 품질/.test(r.body))throw Error('unsupported_copy');
 if(!r.category||!r.evidence?.quote||r.evidence.quote.length<8||!SOURCE_HOSTS.includes(new URL(r.evidence.url).hostname)||r.evidence.verified!==true||r.visualReview?.pass!==true||r.imageUsage!=='official_unmodified_partner_ad')throw Error('unverified_evidence');
 if(Date.parse(r.evidence.publishedAt)<now-8*86400000||Date.parse(r.evidence.publishedAt)>now+3600000||!Number.isFinite(Date.parse(r.evidence.publishedAt)))throw Error('stale_evidence');
 return {...r,key:r.date+'-'+r.slot.replace(':',''),publishAt:when,status:'queued'};
}
export function duplicate(records,r,now=Date.now()){
 return records.some(x=>x.key!==r.key&&(x.product?.productId==r.product.productId||x.caption===r.caption)&&(!x.publishedAt||Date.parse(x.publishedAt)>now-30*86400000)&&!['skipped','rejected','failed_before_publish'].includes(x.status));
}
export function safeError(e){return /^[a-z_]+(?::\d+)?$/.test(e.message)?e.message:'operation_failed'}
