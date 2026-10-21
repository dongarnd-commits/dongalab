import {useState,useRef,useEffect} from 'react';
import type {CompanyWorkflow} from './workflow';
import {emptyProfile,companyReasons,type Profile,type CompanyData} from '../company/client';
import {BusinessCard,BusinessField,BusinessHeading,input,primary,secondary} from './business-ui';

type Candidate={field:string;source_label?:string;value:string;page:number|null;descriptor:string;text:string};
type Document={file:File;digest?:string;candidates:Candidate[];locations:{descriptor:string;text:string;page:number|null}[];error:string;analyzed?:boolean;fileId?:string;parsed?:boolean};
type Draft={mode:string;profile:Profile;documents:Document[];created:string;error:string;address:string;siteId:string;businessType:string;businessItems:string;saving:boolean};
const blank=():Draft=>({mode:'documents',profile:structuredClone(emptyProfile),documents:[],created:'',error:'',address:'',siteId:'',businessType:'',businessItems:'',saving:false});
const names:Record<string,string>={company_name:'기업명',business_number:'사업자등록번호',representative:'대표자',industry:'업종',address:'사업장 소재지'};
const industry=(businessType:string,businessItems:string)=>[businessType&&'업태: '+businessType,businessItems&&'종목: '+businessItems].filter(Boolean).join('\n');
function validNumber(value:string){if(!/^(?:[0-9]{10}|[0-9]{3}-[0-9]{2}-[0-9]{5})$/.test(value.trim()))return false;const n=value.trim().replaceAll('-','');const d=[...n].map(Number),weights=[1,3,7,1,3,7,1,3,5];const total=weights.reduce((s,w,i)=>s+w*d[i],0)+Math.floor(d[8]*5/10);return new Set(n).size>1&&(10-total%10)%10===d[9];}
function Original({file}:{file:File}){
 const [url,setUrl]=useState('');useEffect(()=>{const value=URL.createObjectURL(file);const t=setTimeout(()=>setUrl(value),0);return()=>{clearTimeout(t);URL.revokeObjectURL(value);};},[file]);
 return <a className="text-blue-700 underline" href={url||undefined} target="_blank" rel="noopener noreferrer">{file.name} 원본 열기</a>;
}
export function InitialRegistration({w,goto}:{w:CompanyWorkflow;goto:(s:string)=>void}){
 // Actor-memory only: survives the initial company selection, never browser storage.
 const request=useRef<AbortController|null>(null),continuing=useRef(false);useEffect(()=>()=>request.current?.abort(),[]);
 const [draft,setState]=useState<Draft>(()=>w.drafts.get('initial-registration') as Draft??blank()),[busy,setBusy]=useState(false),[drag,setDrag]=useState(false);
 const update=(patch:Partial<Draft>)=>{const next={...(w.drafts.get('initial-registration') as Draft??draft),...patch};w.drafts.set('initial-registration',next);setState(next);return next;};
 const setProfile=(patch:Partial<Profile>)=>update({profile:{...draft.profile,...patch}});
 function add(files:File[]){if(files.length+draft.documents.length>2||files.some(f=>!f.size||f.size>20*1024*1024||!f.name.toLowerCase().endsWith('.pdf'))){update({error:'PDF를 최대 2개, 파일당 20MB 이하로 선택해 주세요.'});return;}update({documents:[...draft.documents,...files.map(file=>({file,candidates:[],locations:[],error:''}))],error:''});}
 async function analyze(){
  if(busy||request.current&&!request.current.signal.aborted)return;
  const controller=new AbortController();request.current=controller;setBusy(true);update({error:''});
  try{const total=(w.drafts.get('initial-registration') as Draft).documents.length;
   for(let index=0;index<total;index++){
    const doc=(w.drafts.get('initial-registration') as Draft).documents[index];
    if(doc.analyzed&&!doc.error)continue;
    const response=await fetch('/api/company/registration/preview',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Upload-Name':encodeURIComponent(doc.file.name)},body:doc.file,credentials:'same-origin',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(55000)])});
    const data=await response.json();if(controller.signal.aborted)return;
    if(!response.ok)throw Error(companyReasons[data.reason]??'문서를 분석하지 못했습니다. 직접 입력으로 진행해 주세요.');
    const current=w.drafts.get('initial-registration') as Draft;if(current.documents[index]?.file!==doc.file)return;
    const documents=current.documents.map((d,i)=>i===index?{...d,...data,analyzed:true,error:data.error?'문서의 일부 내용을 읽지 못했습니다. 직접 확인·입력해 주세요.':''}:d);
    const profile={...current.profile};let address=current.address,businessType=current.businessType,businessItems=current.businessItems;
    const extracted=data.candidates as Candidate[];
    for(const c of extracted){const key=c.field==='company_name'?'name':c.field;if(['name','business_number','representative'].includes(key)&&!profile[key as keyof Profile])Object.assign(profile,{[key]:c.value});if(c.field==='address'&&!address)address=c.value;}
    const unique=(label:string)=>Array.from(new Set(extracted.filter(c=>c.field==='industry'&&c.source_label===label).map(c=>c.value))).join('\n');
    businessType=businessType||unique('업태');businessItems=businessItems||unique('종목');
    const unspecified=extracted.filter(c=>c.field==='industry'&&!c.source_label).map(c=>c.value).join('\n');
    profile.industry=industry(businessType,businessItems)||profile.industry||unspecified;
    update({documents,profile,address,businessType,businessItems});
   }
  }catch(e){if(!controller.signal.aborted)update({error:e instanceof Error?e.message:'문서 분석을 완료하지 못했습니다.'});}
  finally{if(request.current===controller){request.current=null;setBusy(false);}}
 }
 async function preserve(cid:string){let current=w.drafts.get('initial-registration') as Draft;update({created:cid,error:''});try{
  if(current.address&&!current.siteId){const s=await w.request<{site:{id:string}}>('/'+cid+'/sites',{data:{name:'본사',address:current.address,industry:current.profile.industry,process:''},expected_ordinal:0});current=update({siteId:s.site.id});}
  for(let index=0;index<current.documents.length;index++){let doc=current.documents[index];if(!doc.fileId){const digest=doc.digest??Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await doc.file.arrayBuffer())),b=>b.toString(16).padStart(2,'0')).join('');const known=await w.request<CompanyData>('/'+cid);let f=known.files.find(f=>f.digest===digest);if(!f)f=await w.uploadTo(cid,doc.file);current=update({documents:current.documents.map((d,i)=>i===index?{...d,digest,fileId:f!.id}:d)});doc=current.documents[index];}
   if(!doc.parsed){const parsed=await w.request<{error:string|null}>('/files/'+doc.fileId+'/parse?registration=true',{});if(parsed.error)throw Error(companyReasons[parsed.error]??'원본은 보존되었지만 문서 근거 추출은 미완료입니다. 다시 시도하세요.');current=update({documents:current.documents.map((d,i)=>i===index?{...d,parsed:true}:d)});}
  }
  const actual=await w.request<CompanyData>('/'+cid);
  // Clicking register is the editor's explicit review action for the visible form.
  // Record it using existing ACK/manual-correction commands, never Fact confirm.
  const reviewed:Record<string,string>={company_name:current.profile.name,business_number:current.profile.business_number.trim().replaceAll('-',''),representative:current.profile.representative,industry:current.profile.industry,address:current.address};
  const sourceFiles=new Set(current.documents.map(d=>d.fileId));
  for(const candidate of actual.candidates){const source=actual.evidence.find(e=>e.id===candidate.evidence_id);if(candidate.mode!=='RULE_BASED_EXTRACTION'||!source?.file_id||!sourceFiles.has(source.file_id)||!reviewed[candidate.field])continue;
   const selected=reviewed[candidate.field],agreed=(candidate.field==='business_number'?candidate.value.replaceAll('-',''):candidate.value)===selected,note='기업 최초등록 화면에서 원문 후보와 최종 입력값을 확인함';
   if(!candidate.acknowledgements.some(a=>a.agreed===agreed&&a.note===note))await w.request('/candidates/'+candidate.id+'/acknowledge',{agreed,note});
   if(!agreed){let correction=actual.candidates.find(c=>c.mode==='MANUAL_REVIEW'&&c.field===candidate.field&&c.value===selected&&actual.evidence.find(e=>e.id===c.evidence_id)?.descriptor==='최초등록 기업 정정 / 원후보 '+candidate.id);
    if(!correction){const evidence=await w.request<{id:string}>('/'+cid+'/evidence',{file_id:source.file_id,site_id:candidate.site_id,descriptor:'최초등록 기업 정정 / 원후보 '+candidate.id,transcription:'원후보값: '+candidate.value+'\n기업 최종 확인값: '+selected+'\n원문 위치: '+source.descriptor});correction=await w.request('/'+cid+'/candidates',{evidence_id:evidence.id,site_id:candidate.site_id,field:candidate.field,value:selected,period:candidate.period,unit:candidate.unit,currency:candidate.currency,valid_from:candidate.valid_from});}
    if(correction&&!correction.acknowledgements?.some(a=>a.agreed&&a.note===note))await w.request('/candidates/'+correction.id+'/acknowledge',{agreed:true,note});
   }
  }
if(current.documents.some(d=>!actual.files.some(f=>f.id===d.fileId&&(!d.digest||f.digest===d.digest))))throw Error('원본 보존 결과를 재확인하지 못했습니다.');update({error:''});
 }catch(e){update({saving:false,error:'기업정보는 등록되었지만 자료 저장이 완료되지 않았습니다. 다시 시도해 주세요. '+(e instanceof Error?e.message:'원본 보존이 미완료입니다.')});throw e;}}
 // Registration remains two guarded server phases, but continuation is automatic.
 // Wait for the new Company context/epoch to settle before preserving sources.
 useEffect(()=>{
  if(!draft.created||!draft.saving||w.cid!==draft.created||!w.detail||w.busy||continuing.current)return;
  const timer=setTimeout(()=>{
   if(continuing.current)return;continuing.current=true;
   void w.run(async()=>{try{await preserve(draft.created);await w.reload();update(blank());goto('company');}catch(e){update({saving:false});throw e;}},'기업정보를 등록했습니다.').finally(()=>{continuing.current=false;});
  },0);
  return()=>clearTimeout(timer);
 });
 const existing=!!w.cid&&!draft.created;
 if(existing)return <><BusinessHeading title="기업정보 등록 시작" description="등록된 기업정보와 첨부자료를 확인할 수 있습니다."/><BusinessCard><button className={primary} onClick={()=>goto('company')}>기업정보 확인·수정</button><button className={secondary} onClick={()=>goto('files')}>첨부자료 관리</button></BusinessCard></>;
 const saving=draft.saving,locked=busy||saving||w.busy;
 const candidates=draft.documents.flatMap(doc=>doc.candidates.map(c=>({...c,file:doc.file.name})));
 const conflicts=Object.entries(names).filter(([field])=>field!=='industry'&&new Set(candidates.filter(c=>c.field===field).map(c=>field==='business_number'?c.value.trim().replaceAll('-',''):c.value)).size>1).map(([,label])=>label);
 for(const label of ['업태','종목']){const perDocument=draft.documents.map(d=>Array.from(new Set(d.candidates.filter(c=>c.source_label===label).map(c=>c.value))).join('\n')).filter(Boolean);if(new Set(perDocument).size>1)conflicts.push(label);}
 const showForm=draft.mode==='direct'||draft.documents.some(d=>d.analyzed)||!!draft.created;
 return <><BusinessHeading title="기업정보 등록 시작" description="서류를 올려 정보를 가져오거나 직접 입력해 주세요."/>{draft.error&&<p role="alert">{draft.error}</p>}
 {draft.mode==='documents'?<BusinessCard title="사업자등록 서류 업로드"><p>사업자등록증 또는 사업자등록증명원 PDF 중 하나만 있어도 됩니다.</p>
 <div className={'mt-4 rounded-xl border-2 border-dashed p-6 '+(drag?'border-blue-500 bg-blue-50':'border-slate-200')} onDragOver={e=>{e.preventDefault();setDrag(true);}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);if(!locked&&!draft.created)add(Array.from(e.dataTransfer.files));}}>
 <BusinessField label="최초 등록 PDF 선택"><input className="block w-full min-w-0" disabled={locked||!!draft.created} type="file" multiple accept=".pdf,application/pdf" onChange={e=>{add(Array.from(e.target.files??[]));e.currentTarget.value='';}}/></BusinessField><p>파일 선택 또는 드래그 앤 드롭 · 최대 2개 · 각 20MB</p>
 </div><div className="mt-4 flex flex-wrap items-center gap-3" aria-label="서류 작업">
 <button className={primary} disabled={locked||!!draft.created||!draft.documents.length} onClick={()=>void analyze()}>문서 분석</button>
 <button className={secondary} disabled={locked||!!draft.created||!draft.documents.length} onClick={()=>update({documents:[],error:''})}>선택 취소</button>
 <button className={secondary} disabled={locked||!!draft.created} onClick={()=>update({mode:'direct',error:''})}>직접 입력으로 진행</button></div>
 {draft.documents.map((doc,i)=><article className="mt-4" key={i}><p>{doc.file.name}{doc.analyzed&&!doc.error?' · 분석 완료':''}</p>{doc.error&&<p role="alert">{doc.error}</p>}</article>)}
 {busy&&<div role="status"><p>문서를 읽고 있습니다. 잠시 기다려 주세요.</p><button className={secondary} onClick={()=>{request.current?.abort();setBusy(false);update({error:'분석을 취소했습니다. 직접 입력으로 진행할 수 있습니다.'});}}>분석 취소</button></div>}
 </BusinessCard>:<BusinessCard title="기업정보 직접 입력"><p>아래 내용을 작성해 주세요.</p><button disabled={locked||!!draft.created} className={secondary} onClick={()=>update({mode:'documents',error:''})}>서류로 등록</button></BusinessCard>}
 {showForm&&<BusinessCard title="기업정보 확인·수정"><p>내용을 확인하고 틀린 부분을 수정한 후 기업정보 등록을 눌러 주세요.</p>
 {conflicts.map(label=><p role="alert" key={label}>{label}: 서류 간 값이 다릅니다. 원본과 입력 내용을 확인해 주세요.</p>)}
 <form onSubmit={e=>{e.preventDefault();if(locked||!validNumber(draft.profile.business_number))return;
  if(draft.created){update({saving:true,error:''});return;}
  update({saving:true,error:''});void w.run(async()=>{try{await w.register(draft.profile,async id=>{update({created:id});});}catch(e){update({saving:false,error:e instanceof Error?e.message:'등록하지 못했습니다. 다시 확인해 주세요.'});throw e;}},'');
 }}>
 <div className="business-grid grid gap-4 sm:grid-cols-2">{([['name','등록 기업명'],['business_number','등록 사업자등록번호'],['representative','등록 대표자']] as const).map(([key,label])=><BusinessField key={key} label={label}><input className={input} required={key!=='representative'} readOnly={saving||!!draft.created} maxLength={key==='business_number'?12:200} value={draft.profile[key]} onChange={e=>setProfile({[key]:e.target.value})}/></BusinessField>)}
 <BusinessField label="등록 사업장 소재지"><input className={input} maxLength={1000} readOnly={saving||!!draft.created} value={draft.address} onChange={e=>update({address:e.target.value})}/></BusinessField>
 {([['businessType','등록 업태'],['businessItems','등록 종목']] as const).map(([key,label])=><BusinessField key={key} label={label}><textarea aria-label={label} placeholder={draft.mode==='documents'?'원본을 확인하고 입력해 주세요.':undefined} className={input} rows={3} readOnly={saving||!!draft.created} value={draft[key]} onChange={e=>{const values={businessType:draft.businessType,businessItems:draft.businessItems,[key]:e.target.value};update({...values,profile:{...draft.profile,industry:industry(values.businessType,values.businessItems)}});}}/></BusinessField>)}</div>
 {draft.profile.industry.length>500&&<p role="alert">업태와 종목을 합쳐 500자 이내로 입력해 주세요.</p>}
 {draft.profile.business_number&&!validNumber(draft.profile.business_number)&&<p role="alert">사업자등록번호를 확인해 주세요. 숫자 10자리 또는 000-00-00000으로 입력합니다.</p>}
 {draft.documents.length>0&&<details className="my-4"><summary>원본 확인</summary>{draft.documents.map((doc,i)=><div key={i}><Original file={doc.file}/>{doc.locations.map((l,n)=><details key={n}><summary>{l.page?l.page+'쪽':'추출된 원문'}</summary><pre className="business-evidence">{l.text}</pre></details>)}</div>)}</details>}
 <div className="mt-6 flex flex-wrap gap-3"><button className={primary} disabled={locked||!draft.profile.name.trim()||!validNumber(draft.profile.business_number)||draft.profile.industry.length>500}>{saving?'등록 중…':draft.created?'등록 다시 시도':'기업정보 등록'}</button>
 {!draft.created&&<button type="button" className={secondary} disabled={locked} onClick={()=>{if(window.confirm('입력과 선택한 서류를 취소할까요?')){w.drafts.set('initial-registration',blank());setState(blank());}}}>등록 취소</button>}</div>
 {saving&&<p role="status">기업정보와 첨부서류를 저장하고 있습니다.</p>}
 </form></BusinessCard>}</>;
}
