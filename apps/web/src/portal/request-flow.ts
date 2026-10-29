export type RequestWork={id:string;company_id:string;company_name:string;title:string;improvement_version_id:string|null;version_ordinal:number|null;improvement_title:string|null;state:string;due_date:string|null;created_at:string;response_id:string|null;response_ordinal:number};
export const requestLabels:Record<string,string>={DRAFT:'작성 중',WAITING_RESPONSE:'답변 대기',REVIEW_REQUIRED:'기업 답변 검토 필요',VERIFIED:'확인 완료',REVISION_REQUESTED:'재보완 요청'};
export const nextLabels:Record<string,string>={NEW_RECEIPT:'개선요구 검토',ANALYZING:'분석 상태 보기',NEEDS_REVIEW:'분석 결과 검토',NEEDS_CHECK:'개선요구 재검토',COMPLETED:'검토 결과 보기',PREPARING_REQUEST:'작성 중인 요청',WAITING_RESPONSE:'보완요청 현황',RESPONSE_REVIEW:'기업 답변 검토',REREVIEW:'재검토'};
export function requestTargets(rows:RequestWork[],version:string,status:string){
 const states=status==='RESPONSE_REVIEW'?['REVIEW_REQUIRED']:status==='WAITING_RESPONSE'?['WAITING_RESPONSE','REVISION_REQUESTED']:['DRAFT'];
 return rows.filter(r=>r.improvement_version_id===version&&states.includes(r.state));
}
export type ResponseRecord={id:string;ordinal:number;message:string;submitted:boolean;file_ids:string[];actor_id?:string;created_at?:string};
export type ReviewRecord={id:string;response_id:string;actor_id:string;outcome:string;note:string;created_at?:string};
export function savedResponse(rows:ResponseRecord[],body:{expected_ordinal:number;message:string;submit:boolean;file_ids:string[]},actor:string){
 return rows.find(r=>r.ordinal===body.expected_ordinal+1&&r.actor_id===actor&&r.message===body.message.trim()&&r.submitted===body.submit&&sameIds(r.file_ids,body.file_ids));
}
export function savedReview(rows:ReviewRecord[],body:{response_id:string;outcome:string;note:string},actor:string){return rows.find(r=>r.response_id===body.response_id&&r.actor_id===actor&&r.outcome===body.outcome&&r.note===body.note.trim());}
export const sameIds=(a:string[],b:string[])=>a.length===b.length&&[...a].sort().every((v,i)=>v===[...b].sort()[i]);
