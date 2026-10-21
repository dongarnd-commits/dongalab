import type {CompanyWorkflow} from './workflow';
import {BusinessCard,secondary} from './business-ui';
export function CompanyLibrary({w}:{w:CompanyWorkflow}){
 return <>{!w.detail?.files.length&&<BusinessCard><p>등록된 첨부자료가 없습니다.</p><p>기업등록·재무·사업이력·개선요구 화면에서 자료를 첨부해 주세요.</p></BusinessCard>}{w.detail?.files.map(file=>{
  const versions=w.detail!.improvements.flatMap(root=>root.versions.filter(v=>v.data.evidence_ids.some(id=>w.detail!.evidence.some(e=>e.id===id&&e.file_id===file.id))).map(v=>({name:v.data.title,site:v.data.site_id})));
  const parses=file.parses as (typeof file.parses[number]&{parser_version?:string})[];
  const uses=[...new Set([...parses.flatMap(p=>p.parser_version?.startsWith('company-business-finance-')?['재무정보 분석']:p.parser_version?.startsWith('company-business-history-')?['사업이력 분석']:p.parser_version?.startsWith('company-registration-')?['기업등록']:[]),...(versions.length?['개선요구']:[])])];
  return <BusinessCard key={file.id}><article data-file-id={file.id}><h3 className="mb-3 font-bold">{file.name}</h3><p className="text-sm text-slate-500">등록일 {file.created_at?new Date(file.created_at).toLocaleDateString('ko-KR'):'확인 필요'}</p><p className="my-3 text-sm">연결 업무: {uses.join(' · ')||'업무 미분류'}</p>{file.site_id&&<p>사업장: {w.detail!.sites.find(s=>s.id===file.site_id)?.name??'확인 필요'}</p>}{[...new Set(versions.map(v=>v.name))].map(name=><p className="my-2 text-sm" key={name}>개선요구: {name}</p>)}<a className={secondary} href={'/api/company/files/'+file.id+'/download'}>원본 다운로드</a></article></BusinessCard>;
 })}</>;
}
