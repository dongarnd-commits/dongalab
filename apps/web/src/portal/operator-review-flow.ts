/** UI workflow only; every write still passes the existing backend guards. */
export type ListView={search:string;filter:string;page:number;scroll?:number;inbox?:number};
export type ReviewOrigin={page:'dashboard'|'improvement'|'requests';view:ListView};
export const emptyList=():ListView=>({search:'',filter:'',page:1});
const bounded=(value:string|null,max:number)=>Math.min(max,Math.max(0,Number(value)||0));
export function readOrigin(q:URLSearchParams,actor:string):ReviewOrigin|undefined{
 const from=q.get('review_from');
 if(q.get('context_actor')!==actor||!q.get('company')||!['dashboard','improvement','requests'].includes(from??'')||!q.get('version')&&from!=='requests')return;
 return {page:from as ReviewOrigin['page'],view:{search:(q.get('review_search')??'').slice(0,300),filter:(q.get('review_filter')??'').slice(0,40),page:Math.max(1,Math.floor(bounded(q.get('review_page'),100000))),scroll:bounded(q.get('review_scroll'),10000000),inbox:bounded(q.get('review_inbox'),10000000)}};
}
export function writeOrigin(q:URLSearchParams,origin?:ReviewOrigin){
 for(const k of ['review_from','review_search','review_filter','review_page','review_scroll','review_inbox'])q.delete(k);
 if(origin){q.set('review_from',origin.page);q.set('review_search',origin.view.search);q.set('review_filter',origin.view.filter);q.set('review_page',String(origin.view.page));q.set('review_scroll',String(origin.view.scroll??0));q.set('review_inbox',String(origin.view.inbox??0));}
}

type Body=Record<string,unknown>;
type Pending={body:Body;signature:string;uncertain:boolean;result?:unknown};
function signature(body:Body){return JSON.stringify(Object.entries(body).filter(([key])=>!['idempotency_key','expected_ordinal','expected_review_ordinal'].includes(key)).sort(([a],[b])=>a.localeCompare(b)));}
/** Keeps the exact request body/key after uncertainty; never silently retries a POST. */
export class ReviewCommands{
 private pending=new Map<string,Pending>();
 constructor(private uuid:()=>string=()=>crypto.randomUUID()){}
 key(slot:string){return this.pending.get(slot)?.body.idempotency_key as string|undefined;}
 clear(slot:string){this.pending.delete(slot);}
 async execute<T>(slot:string,body:Body,post:(body:Body)=>Promise<T>,lookup:(key:string)=>Promise<T|undefined>):Promise<T>{
  let p=this.pending.get(slot);
  if(p&&p.signature!==signature(body))throw Error('앞선 저장 결과를 다시 확인한 후 입력을 변경해 주세요.');
  if(!p){p={body:{...body,idempotency_key:this.uuid()},signature:signature(body),uncertain:false};this.pending.set(slot,p);}
  if(p.result!==undefined)return p.result as T;
  if(p.uncertain){const found=await lookup(p.body.idempotency_key as string);if(found!==undefined){p.result=found;return found;}}
  try{const result=await post(p.body);p.result=result;return result;}
  catch(error){
   // Existing API 4xx responses reject the entire transaction. Network/5xx may be committed.
   const status=(error as {status?:number})?.status;
   if(status&&[400,401,403,404,409,422].includes(status))this.pending.delete(slot);else p.uncertain=true;
   throw error;
  }
 }
}
export type SavedCandidateReview={id:string;ordinal:number;decision:string;note:string;question:string;request_key?:string};
export function usableReview(review:SavedCandidateReview|undefined,edit:{note?:string;question?:string}){
 return review?.decision==='USE_FOR_REQUEST'&&(!edit.note||review.note===edit.note)&& (edit.question===undefined||review.question===edit.question);
}
export function sameReviews(a:string[],b:string[]){return a.length===b.length&&[...a].sort().every((id,i)=>id===[...b].sort()[i]);}
