import {usePortalWorkState} from './portal-work-state';
import {FileSelection} from './file-selection';
import {useEffect,useState} from 'react';
import {BusinessEditor} from './company-editor';
import type {CompanyWorkflow} from './workflow';
import type {Profile} from '../company/client';
import {maxUpload} from '../company/client';
import {storeAttachment} from './company-attachments';
import {BusinessCard,BusinessField,useBusinessDraft,input,primary,secondary} from './business-ui';

type Kind='finance'|'history';
type Financial=Profile['financials'][number];type History=Profile['history'][number];
type Draft={data:Profile;expected:number;kind:Kind|null;index:number;files:File[];form:boolean;editing:boolean;reviewIndices?:number[];initialRows?:string};
const blankFinancial=():Financial=>({year:0,revenue:'',period:'',unit:'원',currency:'KRW'});
const blankHistory=():History=>({name:'',period:'',agency:'',role:''});
const rowsFingerprint=(rows:(Financial|History)[])=>JSON.stringify(rows,(key,value)=>value===null||key==='consistency_note'&&!value?undefined:value);
export function CompanyFinance({w}:{w:CompanyWorkflow}){
 const [draft,setDraft]=useBusinessDraft<Draft>(w,'finance-v14',()=>({data:structuredClone(w.detail!.inputs.at(-1)!.data),expected:w.detail!.company.current_ordinal,kind:null,index:0,files:[],form:false,editing:false,reviewIndices:[]}));
 const [error,setError]=useState(''),[info,setInfo]=useState('');const p=draft.data;
 const section=(kind:Kind)=>kind==='finance'?'financials':'history';
 const initialRows=draft.initialRows??rowsFingerprint(draft.kind?w.detail!.inputs.find(version=>version.ordinal===draft.expected)?.data[section(draft.kind)]??[]:[]);
 const dirty=!!draft.kind&&(draft.files.length>0||draft.form&&(rowsFingerprint(p[section(draft.kind)])!==initialRows||(draft.reviewIndices?.length??0)>0));
 usePortalWorkState({dirty},w.session.id+':'+w.cid+':finance-v14');
 useEffect(()=>{if(!dirty)return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty]);
 function close(){if(dirty&&!window.confirm('저장하지 않은 '+(draft.kind==='finance'?'재무정보':'수행이력')+' 작성을 버리고 닫을까요?'))return;setDraft({...draft,kind:null,files:[],form:false,reviewIndices:[]});setError('');setInfo('');}

 function fresh(kind:Kind,index?:number){const data=structuredClone(w.detail!.inputs.at(-1)!.data);const key=section(kind),i=index??data[key].length;if(index===undefined){if(kind==='finance')data.financials.push(blankFinancial());else data.history.push(blankHistory());}return {data,expected:w.detail!.company.current_ordinal,kind,index:i,files:[],form:true,editing:index!==undefined,reviewIndices:[],initialRows:rowsFingerprint(data[key])} as Draft;}
 function start(kind:Kind,index?:number){if(dirty&&!window.confirm('저장하지 않은 작성 내용을 버리고 다른 입력을 시작할까요?'))return;setError('');setInfo('');setDraft(fresh(kind,index));}
 function change(key:string,value:string|number|null){if(!draft.kind)return;if(draft.kind==='finance'&&typeof value==='string'&&amountKeys.includes(key)){value=value.replace(/,/g,'').trim();if(key!=='revenue'&&!value)value=null;}const data=structuredClone(p);Object.assign(data[section(draft.kind)][draft.index],{[key]:value});setDraft({...draft,data});}
 async function files(kind:Kind,values:File[]){
  if(!values.length)return;
  function invalid(message:string){if(!draft.kind)setDraft({...draft,kind});setError(message);}
  if(values.length>10||values.some(f=>!f.size||f.size>maxUpload||!(/\.pdf$/i.test(f.name)))){invalid('20MB 이하 PDF 파일을 한 번에 최대 10개 선택해 주세요.');return;}
  if((await Promise.all(values.map(f=>f.slice(0,5).text()))).some(m=>m!=='%PDF-')){invalid('실제 PDF 형식의 문서를 선택해 주세요.');return;}
  if(dirty&&!window.confirm('선택·작성 중인 내용을 버리고 새 PDF를 확인할까요?'))return;
  setError('');setInfo('');setDraft({...fresh(kind),files:values,form:false});
 }
 async function analyze(){if(!draft.kind)return;const kind=draft.kind,key=section(kind),data=structuredClone(p);let index=draft.index,missing=false,count=0;const reviewIndices:number[]=[];setInfo('');setError('');
  for(const file of draft.files){const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer())),b=>b.toString(16).padStart(2,'0')).join('');if(w.detail!.files.some(f=>f.digest===digest)&&!window.confirm('이미 등록된 PDF입니다. 원본을 유지하고 이 자료를 다시 분석할까요?'))continue;const stored=await storeAttachment(w,file);const result=await w.request<{error:string|null;entries?:(Financial|History)[]}>('/files/'+stored.id+'/parse?standard=true&purpose='+kind,{});if(result.error||!result.entries?.length){missing=true;continue;}for(const row of result.entries){const existing=kind==='finance'?data.financials.findIndex(x=>x.year===(row as Financial).year):-1;if(existing>=0){if(!window.confirm('같은 연도의 재무정보가 있습니다. 기존 저장본을 보존하고 해당 연도 수정란에 읽은 값을 적용할까요?'))continue;if(data.financials.at(-1)?.year===0&&!data.financials.at(-1)?.revenue)data.financials.pop();index=existing;}const current=data[key][index] as unknown as Record<string,string|number>;const empty=kind==='finance'?!(current.revenue||current.period):!current.name;if(empty||existing>=0)Object.assign(current,row);else{if(kind==='finance')data.financials.push(row as Financial);else data.history.push(row as History);index=data[key].length-1;}if(!reviewIndices.includes(index))reviewIndices.push(index);count++;}}
  if(data[key].length>100)throw Error('등록 가능한 내역은 최대 100개입니다. 자료를 나누어 확인해 주세요.');await w.reload();setDraft({...draft,data,index,files:[],form:count>0,reviewIndices});if(count)setInfo('문서에서 확인한 항목을 검토하고 저장해 주세요.');if(missing)setError('일부 항목을 읽지 못했습니다. 원본은 자료함에서 확인할 수 있으며 직접 입력으로 보완할 수 있습니다.');
 }
 async function save(){
  if(!draft.kind)return;
  const baseline=w.detail!.inputs.find(version=>version.ordinal===draft.expected);
  if(!baseline)throw Error('작성 기준이 된 저장 기록을 확인하지 못했습니다. 작성 내용을 보존하고 기업 자료를 다시 확인해 주세요.');
  // Only this business collection may differ from the exact expected input version.
  // Preserve the original expected ordinal: concurrent changes must still return 409.
  const data=structuredClone(baseline.data);
  if(draft.kind==='finance')data.financials=structuredClone(p.financials);else data.history=structuredClone(p.history);
  await w.request('/'+w.cid+'/profile',{data,expected_ordinal:draft.expected});
  const actual=await w.reload();if(!actual)throw Error('저장한 내용을 다시 확인하지 못했습니다.');setDraft({...draft,data:structuredClone(actual.inputs.at(-1)!.data),expected:actual.company.current_ordinal,kind:null,files:[],form:false,editing:false,reviewIndices:[]});setInfo('');await w.business.refresh();
 }
 return <div className="company-finance-columns">{(['finance','history'] as const).map(kind=>{const finance=kind==='finance',list=finance?w.detail!.inputs.at(-1)!.data.financials:w.detail!.inputs.at(-1)!.data.history,active=draft.kind===kind,open=active&&draft.form;return <BusinessCard key={kind} title={finance?'재무정보':'정부지원사업 수행이력'}>
 <p className="mb-4 text-sm text-slate-600">{finance?'필요한 연도의 표준재무제표증명 PDF를 등록하거나 직접 입력하세요. 한 해만 등록해도 되며 여러 연도도 함께 등록할 수 있습니다.':'기존 정부지원사업의 결과보고서 등을 등록해 주세요.'}</p>
 <FileSelection label={finance?'재무 PDF 파일 선택 또는 끌어놓기':'수행이력 PDF 파일 선택 또는 끌어놓기'} accept=".pdf" files={active?draft.files:[]} disabled={w.busy} onFiles={values=>{void files(kind,values);}} onRemove={index=>setDraft({...draft,files:draft.files.filter((_,i)=>i!==index)})}/>
 {finance&&<p className="text-sm text-slate-500">재무연도·기준기간·금액 단위·통화를 먼저 확인하고 매출액을 입력하세요. 자산·부채·손익 상세는 선택 입력이며 빈 항목은 0으로 저장하지 않습니다.</p>}
 {active&&draft.files.length>0&&<button disabled={w.busy} className={secondary} onClick={()=>void w.run(analyze,'')}>{finance?'재무자료 분석':'수행이력 자료 분석'}</button>}
 <button disabled={w.busy} className={secondary} onClick={()=>start(kind)}>{finance?'재무정보 직접 입력':'수행이력 직접 입력'}</button>
 {list.length>0?<ul className="my-5 space-y-3">{list.map((row,i)=><li key={i} className="rounded-xl border border-slate-200 p-4">{'year' in row?<><p>{row.year}년 · 매출액 {money(row.revenue)}{row.unit}</p><p className="text-sm text-slate-500">기준기간 {row.period} · {row.currency} · {row.source_parse_id?'PDF 연결 자료':'직접 입력'}</p></>:<><p className="whitespace-pre-wrap break-words">{row.name}</p><p className="text-sm text-slate-500">지원기관 {row.agency} · 수행기간 {row.period}</p></>}<button disabled={w.busy} className={secondary} onClick={()=>start(kind,i)}>{finance?'재무정보 수정':'수행이력 수정'}</button></li>)}</ul>:<p className="my-4 text-sm text-slate-500">{finance?'등록된 재무정보가 없습니다.':'수행이력을 아직 등록하지 않았습니다. 수행한 사업이 없다는 확인을 뜻하지 않습니다.'}</p>}
 {active&&!open&&error&&<p role="alert">{error}</p>}{active&&!open&&info&&<p role="status">{info}</p>}
 {open&&<BusinessEditor busy={w.busy} title={finance?((p.financials[draft.index].year?p.financials[draft.index].year+'년':'새')+' 재무정보 '+(draft.editing?'수정':'입력')):'수행이력 '+(draft.editing?'수정':'입력')} close={close}>{(draft.reviewIndices?.length??0)>1&&<BusinessField label="작성할 내역"><select aria-label="작성할 내역" className={input} value={draft.index} onChange={e=>setDraft({...draft,index:Number(e.target.value)})}>{draft.reviewIndices!.map(i=>{const row=p[section(kind)][i];return <option key={i} value={i}>{'year' in row?(row.year||'연도 미입력')+'년':row.name||'새 수행이력'}</option>;})}</select></BusinessField>}
 {finance&&((draft.reviewIndices?.length??0)>1?<section data-testid="finance-save-scope" className="my-4 rounded-xl bg-blue-50 p-4 text-sm"><p><strong>이번 PDF에서 확인·저장할 재무정보 {draft.reviewIndices!.length}건: {draft.reviewIndices!.map(i=>p.financials[i].year?p.financials[i].year+'년':'연도 미입력').join(', ')}</strong></p><p>작성할 내역에서 이 연도들을 확인한 뒤 함께 저장하세요. 그 밖의 연도와 수행이력은 변경하지 않고 보존합니다.</p></section>:<p className="my-4 text-sm text-slate-500">이 연도의 재무정보만 반영합니다. 기존 다른 연도와 수행이력은 변경하지 않고 보존합니다.</p>)}
 <p className="mb-4 text-sm text-slate-600" data-testid="business-entry-mode">{draft.editing?'저장된 내역의 수정본입니다. 저장하면 이전 기록을 보존하고 새 기록을 만듭니다.':p[section(kind)][draft.index].source_parse_id?'PDF에서 읽은 미저장 초안입니다. 필수 항목과 원본을 확인한 뒤 저장하세요.':'직접 입력하는 미저장 초안입니다.'}</p>
 <form onSubmit={e=>{e.preventDefault();void w.run(save,finance?'재무정보를 저장했습니다.':'수행이력을 저장했습니다.');}}>
 {finance?<>
 <section aria-label="기본 재무정보"><h3 className="mb-4 font-bold">기본 재무정보</h3><div className="business-grid grid gap-4 sm:grid-cols-2">{basicFinancialFields.map(([key,label])=><FinancialField key={key} field={key} label={label} row={p.financials[draft.index]} change={change}/>)}</div>{p.financials[draft.index].source_parse_id&&<p className="mb-3 text-sm text-slate-500">PDF에서 읽은 기준기간·금액 단위·통화는 원본 기준을 유지합니다.</p>}<p className="mb-4 text-sm text-slate-500">기준기간은 원문에 맞춰 연도 또는 시작일 ~ 종료일로 입력하세요. 예: 2025 또는 2025-01-01 ~ 2025-12-31</p></section>
 <details open={detailAmountKeys.some(key=>p.financials[draft.index][key]!=null)} data-testid="finance-optional-details"><summary className="cursor-pointer font-semibold">자산·부채·손익 상세 (선택)</summary><p className="my-3 text-sm text-slate-500">상세 금액은 원 단위·KRW로 입력합니다. 확인되지 않은 금액은 비워 두고, 실제 0인 경우에만 0을 입력하세요.</p>{(p.financials[draft.index].unit!=='원'||p.financials[draft.index].currency!=='KRW')&&<p role="status" className="my-3 text-sm text-amber-800">현재 금액 단위·통화에서는 상세 금액을 입력할 수 없습니다. 상세 금액은 원·KRW에서만 입력하며 기존 값은 보존하고 자동 환산하지 않습니다.</p>}<div className="business-grid grid gap-4 sm:grid-cols-2">{detailFinancialFields.map(([key,label])=><FinancialField key={key} field={key} label={label+' (원)'} row={p.financials[draft.index]} change={change}/>)}</div></details>
 <FinancialChecks row={p.financials[draft.index]} previous={p.financials.find(r=>r.year===p.financials[draft.index].year-1)}/>
 </>:<div className="business-grid grid gap-4 sm:grid-cols-2">
 <BusinessField label="수행사업명"><textarea aria-label="수행사업명" required maxLength={500} className={input+' min-h-28'} value={p.history[draft.index].name} onChange={e=>change('name',e.target.value)}/></BusinessField>
 <BusinessField label="지원기관"><textarea aria-label="지원기관" required maxLength={500} className={input} value={p.history[draft.index].agency} onChange={e=>change('agency',e.target.value)}/></BusinessField>
 <HistoryPeriod key={draft.index} value={p.history[draft.index].period} change={value=>change('period',value)}/>
 </div>}
 {!finance&&<p className="my-4 text-sm text-slate-500">수행이력만 반영하며 기존 재무정보와 기업 기본정보는 그대로 보존합니다.</p>}
 <SourceComparison w={w} row={p[section(kind)][draft.index]}/>
 {finance&&hasSumMismatch(p.financials[draft.index])&&<label className="mb-4 block text-sm"><input type="checkbox" required checked={!!p.financials[draft.index].consistency_note} onChange={e=>change('consistency_note',e.target.checked?'기업 사용자가 합계 불일치를 확인하고 입력 금액을 검토함':'')}/> 합계가 일치하지 않는 금액을 원본과 대조해 확인했습니다.</label>}
 {error&&<p role="alert">{error}</p>}{info&&<p role="status">{info}</p>}{w.error&&<p className="text-rose-800">{w.error}</p>}
 <div className="flex flex-wrap gap-3"><button disabled={w.busy} className={primary}>{finance?'재무정보 저장':'수행이력 저장'}</button></div></form></BusinessEditor>}
 </BusinessCard>;})}</div>;
}

export function money(raw:string){return /^-?\d+$/.test(raw)?raw.replace(/\B(?=(\d{3})+(?!\d))/g,','):raw;}
const basicFinancialFields=[['year','재무연도'],['period','기준기간'],['unit','금액 단위'],['currency','통화'],['revenue','매출액']] as const;
const detailFinancialFields=[['current_assets','유동자산'],['noncurrent_assets','비유동자산'],['assets','자산총계'],['current_liabilities','유동부채'],['noncurrent_liabilities','비유동부채'],['liabilities','부채총계'],['capital','자본금'],['equity','자본총계'],['operating_income','영업이익'],['net_income','당기순이익']] as const;
const detailAmountKeys=detailFinancialFields.map(([key])=>key);
const financialFields=[...basicFinancialFields,...detailFinancialFields];
const amountKeys:string[]=['revenue',...detailAmountKeys];
function FinancialField({field,label,row,change}:{field:keyof Financial;label:string;row:Financial;change:(key:string,value:string|number|null)=>void}){
 const amount=amountKeys.includes(field),sourceContext=!!row.source_parse_id&&['period','unit','currency'].includes(field),detailField=detailAmountKeys.some(key=>key===field),detailUnavailable=detailField&&(row.unit!=='원'||row.currency!=='KRW');
 const shownLabel=field==='revenue'?label+' ('+(row.unit||'단위 미입력')+')':label;
 return <BusinessField label={shownLabel}><input aria-label={shownLabel} className={input} required={['year','revenue','period','unit','currency'].includes(field)} readOnly={sourceContext} disabled={detailUnavailable} inputMode={amount?'numeric':undefined} type={field==='year'?'number':'text'} min={field==='year'?1900:undefined} max={field==='year'?2200:undefined} maxLength={field==='unit'?30:field==='currency'?10:100} placeholder={field==='period'?'예: 2025 또는 2025-01-01 ~ 2025-12-31':amount&&field!=='revenue'?'미확인 / 선택 입력':undefined} value={field==='year'?row.year||'':amount?money(String(row[field]??'')):String(row[field]??'')} onChange={e=>change(field,field==='year'?Number(e.target.value):e.target.value)}/></BusinessField>;
}
function hasSumMismatch(row:Financial){return [['assets','liabilities','equity'],['assets','current_assets','noncurrent_assets'],['liabilities','current_liabilities','noncurrent_liabilities']].some(keys=>{const values=keys.map(k=>(row as unknown as Record<string,string>)[k]);return values.every(v=>typeof v==='string'&&/^-?\d+$/.test(v))&&BigInt(values[0])!==BigInt(values[1])+BigInt(values[2]);});}
function HistoryPeriod({value,change}:{value:string;change:(value:string)=>void}){
 const dates=value.match(/^(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})$/);const [start,setStart]=useState(dates?.[1]??''),[end,setEnd]=useState(dates?.[2]??'');
 const legacy=!!value&&!dates&&!start&&!end;
 return <div className="sm:col-span-2" role="group" aria-label="수행기간"><p className="mb-3 font-semibold">수행기간</p>{legacy&&<><BusinessField label="기존 수행기간"><input className={input} required maxLength={100} value={value} onChange={e=>change(e.target.value)}/></BusinessField><p className="mb-3 text-sm text-slate-500">기존 원문 기간을 보존합니다. 정확한 날짜를 확인한 경우에만 아래 시작일·종료일로 바꾸세요.</p></>}<div className="business-grid"><BusinessField label="수행 시작일"><input aria-label="수행 시작일" className={input} type="date" required={!legacy} max={end||undefined} value={start} onChange={e=>{setStart(e.target.value);change(e.target.value+' ~ '+end);}}/></BusinessField><BusinessField label="수행 종료일"><input aria-label="수행 종료일" className={input} type="date" required={!legacy} min={start||undefined} value={end} onChange={e=>{setEnd(e.target.value);change(start+' ~ '+e.target.value);}}/></BusinessField></div><p className="text-sm text-slate-500">시작일과 종료일을 함께 확인하세요. 종료일은 시작일보다 빠를 수 없습니다.</p></div>;
}
function FinancialChecks({row,previous}:{row:Financial;previous:Financial|undefined}){
 function amount(key:keyof Financial){const raw=row[key];return typeof raw==='string'&&/^-?\d+$/.test(raw)?BigInt(raw):null;}
 const a=amount('assets'),l=amount('liabilities'),e=amount('equity'),ca=amount('current_assets'),cl=amount('current_liabilities'),cap=amount('capital');
 const ratio=(n:bigint|null,d:bigint|null)=>{if(n===null||d===null)return '계산에 필요한 금액이 없습니다.';if(d===BigInt(0))return '기준 금액이 0이어서 계산할 수 없습니다.';const sign=(n<BigInt(0))!==(d<BigInt(0))?'-':'',a=(n<BigInt(0)?-n:n)*BigInt(10000),b=d<BigInt(0)?-d:d;let q=a/b;const r=a%b;if(r*BigInt(2)>b||r*BigInt(2)===b&&q%BigInt(2)!==BigInt(0))q+=BigInt(1);return `${q===BigInt(0)?'':sign}${q/BigInt(100)}.${String(q%BigInt(100)).padStart(2,'0')}%`;};
 const prev=previous?.unit===row.unit&&previous?.currency===row.currency&&/^-?\d+$/.test(previous.revenue)?BigInt(previous.revenue):null,revenue=amount('revenue');
 if(!row.year||!row.revenue)return <p className="my-4 text-sm">필수 입력: 재무연도·매출액·기준기간·금액 단위·통화. 나머지 금액은 선택 입력이며 확인된 값으로 비율을 계산합니다.</p>;
 return <div className="my-4 rounded-xl bg-slate-50 p-4 text-sm">{hasSumMismatch(row)&&<p role="alert">자산·부채·자본 또는 유동·비유동 합계가 일치하지 않습니다. 금액을 확인해 주세요.</p>}<p>부채비율 {ratio(l,e)} · 유동비율 {ratio(ca,cl)}</p><p>매출증감률 {previous?ratio(revenue===null||prev===null?null:revenue-prev,prev):'비교할 전년도 자료가 없습니다.'}</p>{e!==null&&cap!==null&&e<cap&&<p>자본잠식 여부를 확인해 주세요.</p>}{a===null&&<p>자산총계가 없어 합계를 확인할 수 없습니다.</p>}</div>;
}
function SourceComparison({w,row}:{w:CompanyWorkflow;row:Financial|History}){
 const run=w.detail?.business_extractions?.find(item=>item.parse_id===row.source_parse_id),source=run?.entries[row.source_index??-1];if(!run||!source)return null;
 const original=run.kind==='finance'?{year:source.year,...source.values}:{name:source.name,period:source.period,agency:source.agency};
 const names:Record<string,string>={...Object.fromEntries(financialFields.map(([k,v])=>[k,v.replace(' (원)','')])),name:'수행사업명',period:run.kind==='finance'?'기준기간':'수행기간',agency:'지원기관'};
 const different=Object.entries(original).filter(([,value])=>value!==null&&value!==undefined).filter(([key,value])=>String(value).trim()!==String((row as unknown as Record<string,unknown>)[key]??'').trim());
 const missing=Object.values(original).some(v=>v===null||v===undefined);
 return <div className="my-4 rounded-xl border border-slate-200 p-4 text-sm"><a className={secondary} href={'/api/company/files/'+run.file_id+'/download'}>분석 원본 PDF 내려받기</a>{different.length?different.map(([key])=><p key={key}>{names[key]??key}이 원본 문서와 다릅니다. 입력 내용을 확인해 주세요.</p>):<p>{missing?'원본에서 확인되지 않은 항목이 있습니다. 직접 확인해 주세요.':run.kind==='finance'?'원본 문서와 주요 재무정보가 일치합니다.':'원본 문서와 수행이력 정보가 일치합니다.'}</p>}</div>;
}
