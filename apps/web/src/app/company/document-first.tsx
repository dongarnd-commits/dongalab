"use client";
import {useState} from "react";
import type {Candidate,Detail,Profile} from "./workspace";
import "./document-first.css";

type Choice={selected:boolean;value:string};
type Applied={candidate:Candidate;value:string};
const labels:Record<string,string>={company_name:'기업명',business_number:'사업자번호',industry:'업종',representative:'대표자',address:'사업장 소재지',revenue:'매출액',employees:'직원수'};
const empty:Profile={name:'',business_number:'',industry:'',representative:'',contact:'',overview:'',financials:[],history:[]};
const errors:Record<string,string>={UPLOAD_SIZE_INVALID:'20MB 이하 파일을 선택해 주세요.',UNSUPPORTED_FORMAT:'지원하지 않는 형식입니다. PDF·DOCX·XLSX·TXT 또는 이미지 원본을 사용하세요.',FORMAT_MISMATCH:'파일 내용과 확장자가 일치하지 않습니다.',DUPLICATE_COMPANY_FILE:'이미 등록한 동일 파일입니다. 목록의 원본을 사용하세요.',DOCUMENT_PARSE_FAILED:'문서를 읽지 못했습니다. 원본을 확인하거나 직접 입력해 주세요.'};
export default function DocumentFirst({detail,request,onRegistered,onReload}:{detail:Detail|null;request:<T>(path:string,body?:unknown)=>Promise<T>;onRegistered:(id:string)=>Promise<void>;onReload:()=>Promise<void>}) {
  const [step,setStep]=useState(1),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  const [form,setForm]=useState<Profile>(detail?.inputs.at(-1)?.data??empty),[siteId,setSiteId]=useState(''),[site,setSite]=useState({name:'',address:'',industry:'',process:''});
  const [file,setFile]=useState<File|null>(null),[category,setCategory]=useState('사업자등록 관련 자료');
  const [choices,setChoices]=useState<Record<string,Choice>>({}),[replace,setReplace]=useState(false),[applied,setApplied]=useState<Applied[]>([]),[saved,setSaved]=useState(false);
  const [savedInput,setSavedInput]=useState<string|null>(null),[traceDone,setTraceDone]=useState<string[]>([]);
  const candidates=(detail?.candidates??[]).filter(c=>c.mode==='RULE_BASED_EXTRACTION');
  const cid=detail?.company.id;
  async function run(work:()=>Promise<void>){if(busy)return;setBusy(true);setError('');setMessage('');try{await work();}catch(e){setError(e instanceof Error?e.message:'처리하지 못했습니다. 다시 시도하세요.');}finally{setBusy(false);}}
  function change(key:keyof Profile,value:Profile[keyof Profile]){setForm({...form,[key]:value});setSaved(false);setSavedInput(null);}
  function choice(c:Candidate){return choices[c.id]??{selected:false,value:c.value};}
  function current(c:Candidate){const key={company_name:'name',business_number:'business_number',industry:'industry',representative:'representative'}[c.field] as keyof Profile|undefined;return key?String(form[key]):c.field==='address'?site.address:c.field==='revenue'?form.financials.filter(f=>f.period===c.period&&f.unit===c.unit&&f.currency===c.currency).map(f=>f.revenue).join(' / '):'';}
  function apply(){
    setError('');setMessage('');const selected=candidates.filter(c=>choice(c).selected);
    const keys=selected.map(c=>c.field+':'+c.period+':'+c.unit+':'+c.currency);
    if(new Set(keys).size!==keys.length){setError('같은 항목·기간의 후보가 여러 개 선택됐습니다. 출처를 비교하고 한 후보만 선택하세요.');return;}
    const next=structuredClone(form),nextSite={...site};const records:Applied[]=[],skipped:string[]=[];
    for(const c of selected){const value=choice(c).value.trim();if(!value){skipped.push(labels[c.field]??c.field);continue;}
      if(current(c)&&current(c)!==value&&!replace){skipped.push((labels[c.field]??c.field)+' — 기존 입력 유지');continue;}
      if(c.field==='business_number'){if(value.replace(/-/g,'')!==form.business_number)skipped.push('사업자번호 — 기업 식별 변경은 별도 검토');continue;}
      const key={company_name:'name',industry:'industry',representative:'representative'}[c.field] as 'name'|'industry'|'representative'|undefined;
      if(key)next[key]=value;
      else if(c.field==='address')nextSite.address=value;
      else if(c.field==='revenue'){
        if(!/^\d{4}$/.test(c.period)||!c.unit||!c.currency){skipped.push('매출액 — 연도·기간·단위·통화 확인 필요');continue;}
        const index=next.financials.findIndex(f=>f.period===c.period&&f.unit===c.unit&&f.currency===c.currency);
        const row={year:Number(c.period),period:c.period,unit:c.unit,currency:c.currency,revenue:value};if(index<0)next.financials.push(row);else next.financials[index]=row;
      } else {skipped.push((labels[c.field]??c.field)+' — 기존 Fact 후보 검토 화면에서 확인');continue;}
      records.push({candidate:c,value});
    }
    setForm(next);setSite(nextSite);setApplied(records);setSaved(false);setSavedInput(null);setStep(3);
    setMessage(`${records.length}개 선택 정보를 입력폼 초안에 반영했습니다. DB 저장·Fact 확정은 아직 아닙니다.${skipped.length?' 제외: '+skipped.join(', '):''}`);
  }
  async function save(){
    if(!cid)return;
    let version=savedInput;
    if(!version){const v=await request<{id:string}>('/'+cid+'/profile',{data:form,expected_ordinal:detail!.company.current_ordinal});version=v.id;setSavedInput(v.id);}
    await preserveSources('profile',version);
    setSaved(true);setMessage('기업·재무·사업이력을 DB에 새 Version으로 저장했습니다. 출처 연결은 사용자 적용 기록이며 기업 사실확인·운영자 Fact 검토는 별도입니다.');await onReload();
  }
  async function preserveSources(target:'profile'|'site',version:string){
    for(const a of applied){
      if((a.candidate.field==='address')!==(target==='site'))continue;
      const key=a.candidate.id+':'+version;if(traceDone.includes(key))continue;
      const value=current(a.candidate);if(!value)continue;
      const original=detail!.evidence.find(e=>e.id===a.candidate.evidence_id);if(!original?.file_id)continue;
      const evidence=await request<{id:string}>('/'+cid+'/evidence',{file_id:original.file_id,site_id:original.site_id,descriptor:'사용자 선택 적용 / '+target+' Version '+version+' / 원후보 '+a.candidate.id,transcription:'원후보 값: '+a.candidate.value+'\n초안 적용값: '+a.value+'\n사용자가 저장한 값: '+value+'\n원본 위치: '+original.descriptor+'\n기업 입력 저장이며 Fact 확정 아님'});
      await request('/'+cid+'/candidates',{evidence_id:evidence.id,site_id:original.site_id,field:a.candidate.field,value,period:a.candidate.period,unit:a.candidate.unit,currency:a.candidate.currency,valid_from:a.candidate.valid_from});
      setTraceDone(done=>[...done,key]);
    }
  }
  return <section className="document-first" aria-label="증빙 우선 기업정보 등록">
    <header><p className="intake-eyebrow">DATCO ONE · COMPANY INTAKE</p><h2>서류로 기업정보 가져오기</h2><p>증빙에서 가져온 후보를 직접 확인하고, 필요한 정보만 입력폼에 적용해 저장하세요.</p></header>
    <ol className="intake-steps">{['기업 증빙자료 제출','추출정보 확인','기업정보 확인·저장','개선요구 등록','DATCO 검토 요청'].map((s,i)=><li key={s} aria-current={step===i+1?'step':undefined}>{i+1}. {s}</li>)}</ol>
    <p>파싱 시도 {detail?.files.reduce((n,f)=>n+f.parses.length,0)??0}회 · 규칙 후보 {candidates.length}개 · 기업 입력 Version {detail?.company.current_ordinal??0}. 이 수치는 업무 완료율이 아닙니다.</p>
    {error&&<p role="alert">{savedInput?'기업 입력은 저장됐습니다. 출처 기록은 미완료입니다. 같은 화면에서 저장을 재시도하세요. ':''}{error}</p>}{message&&<p role="status">{message}</p>}{busy&&<p role="status">서버에서 처리 중입니다. 완료 결과를 기다려 주세요.</p>}
    {!detail?<form onSubmit={e=>{e.preventDefault();void run(async()=>{const c=await request<{id:string}>('',{...empty,name:form.name,business_number:form.business_number});await onRegistered(c.id);});}}><h3>자료를 연결할 기업 식별</h3><p>기업명과 사업자번호만 먼저 등록합니다. 재무·사업장 정보는 서류 확인 후 입력할 수 있습니다.</p><label>등록 기업명<input required value={form.name} onChange={e=>change('name',e.target.value)}/></label><label>등록 사업자번호 10자리<input required pattern="[0-9]{10}" value={form.business_number} onChange={e=>change('business_number',e.target.value)}/></label><button disabled={busy}>기업 식별 등록 후 자료 제출</button></form>:<>
      <nav aria-label="기업정보 가져오기 단계"><button disabled={busy} onClick={()=>setStep(1)}>서류로 가져오기</button><button disabled={busy} onClick={()=>setStep(2)}>추출정보 확인</button><button disabled={busy} onClick={()=>setStep(3)}>직접 입력</button></nav>
      {step===1&&<section><h3>기업 증빙자료 제출</h3><label>자료 유형<select value={category} onChange={e=>setCategory(e.target.value)}>{['사업자등록 관련 자료','기업 소개자료','재무자료','정부지원사업 수행이력','사업장 자료'].map(x=><option key={x}>{x}</option>)}</select></label><p>유형은 제출 안내용이며 DB 분류 Enum이나 자동 판정으로 저장하지 않습니다: {category}</p><label>가져올 파일<input type="file" accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg" disabled={busy} onChange={e=>setFile(e.target.files?.[0]??null)}/></label>{file&&<p>{file.name} · {file.size.toLocaleString()} bytes · {file.type||'형식 확인 필요'}</p>}<button disabled={busy||!file} onClick={()=>void run(async()=>{if(!file)return;if(file.size>20*1024*1024)throw Error('20MB 이하 파일을 선택해 주세요.');const r=await fetch('/api/company/'+cid+'/files',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Upload-Name':encodeURIComponent(file.name)},body:file});const data=await r.json();if(!r.ok)throw Error(errors[data.reason]??'파일 제출에 실패했습니다. 로그인·기업 권한·원본을 확인하세요.');setFile(null);await onReload();setMessage('원본 파일을 Private Storage에 저장했습니다. 아래 분석 실행은 별도입니다.');})}>증빙자료 업로드</button><p>PDF 텍스트·DOCX 문단·XLSX 셀·TXT만 추출합니다. 스캔·이미지 OCR와 외부 AI 의미 분석은 실행하지 않습니다.</p>
        {detail.files.map(f=><article key={f.id}><h4>{f.name}</h4><p>{f.size?.toLocaleString()} bytes · {f.media_type} · SHA-256 {f.digest.slice(0,12)}…</p><a href={'/api/company/files/'+f.id+'/download'}>원본 다운로드</a><button disabled={busy} onClick={()=>void run(async()=>{const result=await request<{error:string|null;limitations:string[]}>('/files/'+f.id+'/parse',{});await onReload();setMessage(result.error?'추출 실패: '+result.error:'로컬 문서 파싱을 실행했습니다. 후보와 원문을 확인하세요. 외부 AI 실행 아님.');})}>분석 실행</button>{f.parses.map((p,i)=><p key={i}>{p.error?'추출 실패: '+p.error:'파싱 기록 있음 · AI 실행 아님'} · {p.limitations.join(' / ')}</p>)}<details><summary>원문 위치·추출 텍스트</summary>{detail.evidence.filter(e=>e.file_id===f.id).map(e=><blockquote key={e.id}>{e.descriptor}<pre>{e.text}</pre></blockquote>)}</details></article>)}<button onClick={()=>setStep(2)}>추출정보 확인으로</button><button onClick={()=>setStep(3)}>추출 불가·누락 정보 직접 입력</button>
      </section>}
      {step===2&&<section><h3>추출된 기업정보 확인</h3><p>체크한 후보만 초안에 적용합니다. 담당자·정부사업 세부 이력 등 현재 규칙이 추출하지 않는 항목은 직접 입력하세요. 직원수는 기존 Fact 후보 화면에서 검토하며 기업 Profile 필드로 임의 추가하지 않습니다.</p>{!candidates.length&&<p>추출된 후보가 없습니다. 원문 위치를 확인하고 직접 입력하세요. 재무정보는 연도·단위·통화가 명확해야 합니다.</p>}
        {candidates.map(c=>{const selected=choice(c),ev=detail.evidence.find(e=>e.id===c.evidence_id),source=detail.files.find(f=>f.id===ev?.file_id);return <article className="intake-candidate" key={c.id} aria-label={(labels[c.field]??c.field)+' 후보 '+c.id}><label><input type="checkbox" checked={selected.selected} onChange={e=>setChoices({...choices,[c.id]:{...selected,selected:e.target.checked}})}/>{labels[c.field]??c.field} 적용</label><label>적용할 값<input value={selected.value} onChange={e=>setChoices({...choices,[c.id]:{...selected,value:e.target.value}})}/></label><p>원본 추출값: {c.value}</p><p>현재 입력값: {current(c)||'미등록'} · {c.period} {c.unit} {c.currency}</p><p>출처: {source?.name} · {ev?.descriptor}{ev?.page?' / '+ev.page+'페이지':''}</p>{detail.facts.filter(f=>f.field===c.field).map(f=>f.versions.map(v=><p key={v.id}>보존된 Fact Version {v.ordinal}: {v.value} · {f.period} {f.unit} {f.currency} · {v.current_valid?'현재 유효':'과거·재검토 필요'}</p>))}<details><summary>원본 출처 확인</summary><blockquote>{ev?.text}</blockquote>{ev?.file_id&&<a href={'/api/company/files/'+ev.file_id+'/download'}>원본 다운로드</a>}</details></article>;})}
        <label><input type="checkbox" checked={replace} onChange={e=>setReplace(e.target.checked)}/>비어 있지 않은 입력값도 선택 후보로 교체하도록 허용</label><p>기존 확정 Fact는 변경하지 않습니다. 같은 항목·기간의 충돌 후보는 하나씩 비교해 선택하세요.</p><button disabled={busy||!candidates.some(c=>choice(c).selected)} onClick={apply}>선택한 정보 적용</button><button onClick={()=>setStep(3)}>누락 항목 직접 입력</button>
      </section>}
      {step===3&&<section><h3>기업정보 확인·저장</h3><p>입력폼은 초안입니다. 저장은 기업 입력 Version이며 Fact 확정이 아닙니다.</p>{(['name','industry','representative','contact','overview'] as const).map((k,i)=><label key={k}>{['확인 기업명','확인 업종','확인 대표자','확인 담당자','확인 기본현황'][i]}<input value={form[k]} onChange={e=>change(k,e.target.value)}/></label>)}<p>사업자번호: {form.business_number} — 식별 변경은 별도 검토가 필요합니다.</p>
        <h3>기준연도별 재무·사업이력</h3><p>명시된 매출 규칙: 매출액(2025,원,KRW): 1000000. 기간·단위·통화가 없는 값은 자동 적용하지 않습니다.</p>{form.financials.map((f,i)=><fieldset key={i}><legend>확인 재무 {i+1}</legend>{(['year','revenue','period','unit','currency'] as const).map((k,j)=><label key={k}>{['확인 기준연도','확인 매출액','확인 기준기간','확인 단위','확인 통화'][j]}<input type={k==='year'?'number':'text'} value={f[k]} onChange={e=>change('financials',form.financials.map((r,n)=>n===i?{...r,[k]:k==='year'?Number(e.target.value):e.target.value}:r))}/></label>)}<button onClick={()=>change('financials',form.financials.filter((_,n)=>n!==i))}>이 재무 초안 제외</button></fieldset>)}<button onClick={()=>change('financials',[...form.financials,{year:new Date().getFullYear(),revenue:'',period:'',unit:'',currency:''}])}>재무정보 직접 추가</button>
        {form.history.map((h,i)=><fieldset key={i}><legend>확인 사업이력 {i+1}</legend>{(['name','period','agency','role'] as const).map((k,j)=><label key={k}>{['확인 사업명','확인 수행기간','확인 지원주체','확인 수행역할'][j]}<input value={h[k]} onChange={e=>change('history',form.history.map((r,n)=>n===i?{...r,[k]:e.target.value}:r))}/></label>)}<button onClick={()=>change('history',form.history.filter((_,n)=>n!==i))}>이 이력 초안 제외</button></fieldset>)}<button onClick={()=>change('history',[...form.history,{name:'',period:'',agency:'',role:''}])}>사업이력 직접 추가</button><button disabled={busy} onClick={()=>void run(save)}>확인한 기업정보 DB 저장</button>{saved&&<p>기업정보 저장 완료 · 새로고침 후 같은 기업을 선택해 재조회할 수 있습니다.</p>}
        <h3>사업장 확인·저장</h3><label>확인 사업장 선택<select value={siteId} onChange={e=>{setSiteId(e.target.value);const found=detail.sites.find(s=>s.id===e.target.value);setSite(found?.versions.at(-1)?.data??{name:'',address:'',industry:'',process:''});}}><option value="">새 사업장</option>{detail.sites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>{(['name','address','industry','process'] as const).map((k,i)=><label key={k}>{['확인 사업장명','확인 소재지','확인 사업장 업종','확인 공정'][i]}<input value={site[k]} onChange={e=>setSite({...site,[k]:e.target.value})}/></label>)}<button disabled={busy||!site.name||!site.address} onClick={()=>void run(async()=>{const result=await request<{site:{id:string};version:{id:string}}>('/'+cid+'/sites',{data:site,site_id:siteId||null,expected_ordinal:detail.sites.find(s=>s.id===siteId)?.current_ordinal??0});setSiteId(result.site.id);await preserveSources('site',result.version.id);await onReload();setMessage('사업장 새 Version 저장 완료. 확정 Fact는 변경하지 않았습니다.');})}>확인한 사업장 DB 저장</button>
        {saved&&<a className="intake-next" href={'/company?tab=improvement&company='+cid+(siteId?'&site='+siteId:'')}>개선요구 입력하기</a>}
      </section>}
    </>}
  </section>;
}
