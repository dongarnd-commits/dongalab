'use client';
import type {AdminCatalogRead} from "../../portal/admin";
import type {PortalIdentity} from "../../portal/types";

import React,{useMemo,useState} from 'react';
import {
 Activity,AlertTriangle,ArrowRight,BarChart3,Bell,BrainCircuit,Building2,CalendarRange,
 CheckCircle2,ChevronRight,ClipboardCheck,ClipboardList,Database,
 Gauge,History,Layers3,LayoutDashboard,Menu,RefreshCcw,Server,
 ShieldCheck,ShieldAlert,Users,UserRound,UserRoundCog,Workflow,X,Search,
 TrendingUp,FileText,ArrowLeftRight,Info
} from 'lucide-react';
import {disconnectedSnapshot} from './dataSource';
import type {Page} from './AdminPortal';
import {DonutChart,WorkloadBars,TrendChart,FunnelChart,GanttChart,HeatMap,Sparkline,EmptyChart,fmt} from './charts';
import type {Filter,Screen,Snapshot,Period,HealthState,ControlAlert} from './types';
import './admin-control.css';

const groups: Array<{label:string;items:Array<{id:Screen;name:string;icon:React.ComponentType<{size?:number}>}>}>=[
 {label:'통합 운영',items:[{id:'overview',name:'통합 관제 홈',icon:LayoutDashboard},{id:'intake',name:'기업 접수 현황',icon:Building2},{id:'assignments',name:'업무 배정·재배정',icon:ArrowLeftRight},{id:'operators',name:'운영자 업무량',icon:Users},{id:'journey',name:'전체 E2E 진행',icon:Workflow},{id:'schedule',name:'일정·마감·간트',icon:CalendarRange}]},
 {label:'기술·AI 관제',items:[{id:'infrastructure',name:'서버·연동 모니터링',icon:Server},{id:'ai-quality',name:'AI 실행·품질',icon:BrainCircuit}]},
 {label:'기준·접근 관리',items:[{id:'reference',name:'기준정보·버전',icon:Database},{id:'users',name:'사용자·권한',icon:UserRoundCog},{id:'portals',name:'포털 운영현황',icon:Activity},{id:'audit',name:'경보·감사 이력',icon:ShieldCheck}]},
];
const title:Record<Screen,{heading:string;desc:string;code:string}>={
 overview:{heading:'통합 운영 관제',desc:'수요기업·운영자·AI·기술 인프라 상태를 하나의 화면에서 확인합니다.',code:'CONTROL TOWER'},
 intake:{heading:'기업 접수 현황',desc:'접수 건과 실제 담당자·업무 단계를 조회하고 미배정 작업을 찾습니다.',code:'INTAKE'},
 assignments:{heading:'업무 배정·재배정',desc:'시스템의 배정 추천 근거와 차단 조건을 확인한 후 담당자를 지정합니다.',code:'ASSIGNMENTS'},
 operators:{heading:'운영자별 업무량',desc:'운영자 업무 배분, 처리·대기 비중 및 단계별 병목을 비교합니다.',code:'WORKFORCE'},
 journey:{heading:'전체 E2E 진행',desc:'수요기업 접수부터 Fact 검토·매칭·제안서·기업 확인까지 단계별 상태를 분석합니다.',code:'WORKFLOW'},
 schedule:{heading:'업무 일정·마감',desc:'확인된 기한이 있는 작업을 간트 차트로 보고 실제 작업 일정을 확인합니다.',code:'SCHEDULE'},
 infrastructure:{heading:'서버·연동 모니터링',desc:'Web·API·DB·Storage·Worker의 실제 측정값과 시스템 동작 상태를 조회합니다.',code:'INFRASTRUCTURE'},
 'ai-quality':{heading:'AI 실행·품질 관제',desc:'실제 AI, 규칙 추출, 수동 검토를 구분하고 오류와 검증 표본 기반 품질을 평가합니다.',code:'AI QUALITY'},
 reference:{heading:'기준정보·서비스 버전',desc:'DMP Feature·Capability·공고 요건 데이터의 유효 버전·출처·동기화 상태를 봅니다.',code:'REFERENCE DATA'},
 users:{heading:'사용자·권한 현황',desc:'수요기업·운영자·관리자 계정과 접근범위 현황을 확인합니다.',code:'ACCESS CONTROL'},
 portals:{heading:'사용자 포털 운영현황',desc:'수요기업 포털과 DATCO 운영자 포털의 사용·오류·가용 상태를 확인합니다.',code:'PORTAL HEALTH'},
 audit:{heading:'시스템 경보·감사 이력',desc:'조치할 항목과 권한·배정·데이터 변경 이력을 추적합니다.',code:'ALERT & AUDIT'},
};
const badge=(state:HealthState):{label:string;style:string}=>{
 if(state==='UP')return {label:'정상',style:'healthy'};
 if(state==='DEGRADED')return {label:'성능저하',style:'degraded'};
 if(state==='DOWN')return {label:'장애',style:'down'};
 return {label:'미측정',style:'unknown'};
};
function Box({children,className=''}:{children:React.ReactNode;className?:string}){return <section className={'da-box '+className}>{children}</section>}
function BoxTitle({icon:Icon,heading,extra}:{icon:React.ComponentType<{size?:number}>;heading:string;extra?:React.ReactNode}){
 return <div className="da-box-heading"><div><Icon size={17}/><h3>{heading}</h3></div>{extra}</div>;
}
function NumberCard({label,value,icon:Icon,help,onClick}:{label:string;value:number|null|undefined;icon:React.ComponentType<{size?:number}>;help?:string;onClick?:()=>void}){
 return <button type="button" className="da-number-card" onClick={onClick} disabled={!onClick}><div className="da-kpi-head"><span>{label}</span><Icon size={19}/></div><div className="da-number-value">{fmt(value)}</div><p>{help??'데이터 연결 후 표시'}</p></button>;
}
function SourceTag({s}:{s:Snapshot}){return <div className="da-source-tag"><span>원천: {s.source.origin||'출처 미확인'}</span><span>기준: {s.source.asOf?new Date(s.source.asOf).toLocaleString('ko-KR'):'갱신시간 미수집'}</span></div>}
function LimitValue({num,suffix,denominator,precision=1}:{num:number|null|undefined;suffix?:string;denominator?:number|null;precision?:number}){
 if(num===null||num===undefined||!Number.isFinite(num))return <strong className="da-unmeasured">평가 데이터 없음</strong>;
 if(denominator!==undefined&& (denominator===null||denominator<=0))return <strong className="da-unmeasured">평가 데이터 없음</strong>;
 const v=denominator===undefined?num:num/denominator*100;
 return <strong>{v.toLocaleString('ko-KR',{maximumFractionDigits:precision})}{suffix||(denominator!==undefined?'%':'')}</strong>;
}
function EmptyRow({cols,text}:{cols:number;text:string}){return <tr><td colSpan={cols} className="da-table-empty">{text}</td></tr>}
function Status({value}:{value:HealthState}){const {label,style}=badge(value);return <span className={'da-status da-status-'+style}>{label}</span>}
function AlertList({alerts,onGo}:{alerts:ControlAlert[];onGo:(a:ControlAlert)=>void}){
 return <div className="da-alerts">{alerts.length?alerts.slice(0,8).map(a=><button type="button" key={a.id} onClick={()=>onGo(a)} className="da-alert-row"><span className={'da-alert-mark '+a.severity}/><span className="da-alert-copy"><b>{a.title}</b><small>{a.detail}</small></span><ChevronRight size={15}/></button>):<div className="da-empty-list">제공된 경보가 없습니다. 경보 수집 API 연결 여부를 확인해 주세요.</div>}</div>;
}

export default function AdminControlCenter({session,catalogRead,onLogout,renderDetails,renderLive}:{catalogRead?:AdminCatalogRead;session?:PortalIdentity;onLogout:()=>void;renderDetails:(page:Page,onNavigate:(page:Page)=>void)=>React.ReactNode;renderLive?:(screen:Screen,detail:Page|null)=>React.ReactNode}){
 const [page,setPage]=useState<Screen>('overview');
 const [detail,setDetail]=useState<Page|null>(null);
 const [history,setHistory]=useState<Array<{page:Screen;detail:Page|null}>>([]);
 const [period,setPeriod]=useState<Period>('30d');
 const [operatorFilter,setOperatorFilter]=useState('');
 const [stageFilter,setStageFilter]=useState('');
 const [mobile,setMobile]=useState(false);
 const [search,setSearch]=useState('');
 const [assignReason,setAssignReason]=useState('');
 const filter:Filter=useMemo(()=>({period,...(operatorFilter?{operatorId:operatorFilter}:{}),...(stageFilter?{stage:stageFilter}:{})}),[period,operatorFilter,stageFilter]);
 const snap=useMemo(()=>disconnectedSnapshot(filter),[filter]);
 const refresh=()=>{setOperatorFilter('');setStageFilter('');setSearch('')};
 const navigate=(dest:Screen,nextDetail:Page|null=null)=>{setHistory(h=>[...h,{page,detail}]);setPage(dest);setDetail(nextDetail);setMobile(false);document.querySelector(".da-main")?.scrollTo({top:0});};
 const detailParent=(p:Page):Screen=>p==='analysis'||p==='quality'?'ai-quality':p==='users'||p==='access'?'users':p==='integrations'?'infrastructure':p==='audit'?'audit':'reference';
 const openDetail=(p:Page)=>navigate(detailParent(p),p);
 const back=()=>{const prev=history.at(-1);if(prev){setPage(prev.page);setDetail(prev.detail);setHistory(h=>h.slice(0,-1));}};
 const drillAlert=(a:ControlAlert)=>navigate(a.category==='assignment'?'assignments':a.category==='workflow'?'journey':a.category==='ai'?'ai-quality':a.category==='infrastructure'?'infrastructure':a.category==='security'?'users':a.category==='integration'?'reference':'audit');
 const goStage=(stage:string)=>{setStageFilter(stage);navigate('intake')};
 const goOperator=(id:string)=>{setOperatorFilter(id);navigate('operators')};
 const goWork=(id:string)=>{setSearch(id);navigate('intake')};
 const totals=snap?.totals;
 const liveContent=renderLive?.(page,detail)??null;
 return <div className="datco-admin" lang="ko">
  <div className="da-mobile-shade" data-open={mobile} onClick={()=>setMobile(false)}/>
  <aside className={'da-sidebar '+(mobile?'da-sidebar-open':'')}>
   <div className="da-brand"><span className="da-brand-logo"><Layers3 size={22}/></span><div><b>DATCO <em>ONE</em></b><small>통합 시스템 관리</small></div><button className="da-mobile-close" onClick={()=>setMobile(false)} aria-label="메뉴 닫기"><X size={18}/></button></div>
   <nav className="da-nav" aria-label="관리자 메뉴">{groups.map(g=><div key={g.label} className="da-nav-group"><p>{g.label}</p>{g.items.map(item=><button className={'da-nav-link '+(page===item.id?'active':'')} key={item.id} onClick={()=>navigate(item.id)}><item.icon size={17}/><span>{item.name}</span>{page===item.id&&<span className="da-nav-dot"/>}</button>)}</div>)}</nav>
   <div className="da-side-bottom"><ShieldCheck size={18}/><div><b>역할별 접근통제</b><small>{session?session.role:"서버 권한 연결 전"}</small></div></div>
  </aside>
  <div className="da-body"><header className="da-topbar"><div className="da-crumb"><button aria-label="메뉴 열기" className="da-menu-btn" onClick={()=>setMobile(true)}><Menu size={21}/></button><span>관리자 포털</span><ChevronRight size={14}/><b>{title[page].heading}</b></div><div className="da-top-actions"><button className="da-icon-btn" onClick={()=>navigate('audit')} aria-label="경보 이력 확인"><Bell size={19}/>{snap?.alerts.length? <i/>:null}</button><span className="da-top-divider"/><span className="da-user-round"><UserRound size={18}/></span><button className="da-btn da-btn-outline da-top-logout" onClick={onLogout}>{session?"로그아웃":"미리보기 종료"}</button><span className="da-user-name">{session?.name??snap?.viewer.name??'관리자 세션 확인 필요'}</span></div></header>
   <main className="da-main">
    <div className="da-page-heading"><div><p className="da-eyebrow">{`M-${String(Object.keys(title).indexOf(page)+1).padStart(2,'0')} · ${title[page].code}`}</p><h1>{title[page].heading}</h1><p>{title[page].desc}</p></div><div className="da-heading-tools"><select className="da-select" aria-label="조회기간" value={period} onChange={e=>setPeriod(e.target.value as Period)}><option value="7d">최근 7일</option><option value="30d">최근 30일</option><option value="90d">최근 90일</option></select><button className="da-btn da-btn-outline" onClick={refresh}><RefreshCcw size={15}/>화면 새로고침</button></div></div>
    <div className="da-detail-nav"><label>운영자 필터 <input aria-label="운영자 필터" className="da-input" value={operatorFilter} onChange={e=>setOperatorFilter(e.target.value)} placeholder="운영자 검색어"/></label><label>단계 필터 <select className="da-select" aria-label="단계 필터" value={stageFilter} onChange={e=>setStageFilter(e.target.value)}><option value="">전체 단계</option><option value="fact_review">Fact 검토</option><option value="grant_matching">지원사업 매칭</option><option value="proposal">제안서</option></select></label><button className="da-btn da-btn-outline" onClick={refresh}>필터 초기화</button><small>미연결 · 선택값만 유지</small></div>
    {snap&&<SourceTag s={snap}/>}
    <div className="da-detail-nav"><button className="da-btn da-btn-outline" onClick={back} disabled={!history.length}>이전 화면</button><button className="da-btn da-btn-outline" onClick={()=>navigate('overview')}>관리 홈</button></div>
    {(detailMenus[page]??[]).length>0&&<nav aria-label="상세 관리 메뉴" className="da-detail-nav">{detailMenus[page]!.map(p=><button key={p.id} className={'da-btn '+(detail===p.id?'da-btn-primary':'da-btn-outline')} onClick={()=>openDetail(p.id)}>{p.label}</button>)}</nav>}
    {liveContent&&<>{page==='reference'&&session&&<p className="da-chart-footnote" role="region" aria-label="허용된 기준정보 요약">{catalogRead?.status==='ready'?<>등록 기능 레코드 <b data-testid="mvp-admin-feature-count">{catalogRead.data?.features}</b> · 발행 참조가 있는 Capability <b data-testid="mvp-admin-published-count">{catalogRead.data?.published}</b> · 기존 요약의 목록·버전·동기화 상태는 별도 미연결입니다. 실제 목록·발행 Version은 아래 연결된 관리 화면에서 조회합니다.</>:catalogRead?.status==='error'?'기준정보 메타데이터 조회 실패':'기준정보 메타데이터 조회 중'}</p>}{liveContent}</>}
    <div hidden={!detail||Boolean(liveContent)}>{renderDetails(detail??'features',openDetail)}</div><div hidden={detail!==null||Boolean(liveContent)}>
    {page==='overview'&&<>
     <div className="da-kpi-grid"><NumberCard label="접수 기업" value={totals?.distinctCompanies} icon={Building2} onClick={()=>navigate('intake')}/><NumberCard label="접수 개선요구" value={totals?.requests} icon={ClipboardList} onClick={()=>navigate('intake')}/><NumberCard label="미배정 요청" value={totals?.unassigned} icon={UserRoundCog} onClick={()=>navigate('assignments')}/><NumberCard label="진행 중 업무" value={totals?.inProgress} icon={ClipboardCheck} onClick={()=>navigate('journey')}/><NumberCard label="검토·보완 대기" value={totals?.reviewWaiting} icon={ClipboardCheck} onClick={()=>navigate('journey')}/><NumberCard label="제안서" value={null} icon={FileText} onClick={()=>navigate('journey')}/></div>
     <div className="da-chart-grid"><Box><BoxTitle icon={BarChart3} heading="업무 상태 분포" extra={<button className="da-text-link" onClick={()=>navigate('journey')}>전체 보기 →</button>}/>{snap?<DonutChart items={snap.stages} onSelect={goStage}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={Users} heading="운영자별 업무 배분" extra={<button className="da-text-link" onClick={()=>navigate('operators')}>전체 보기 →</button>}/>{snap?<WorkloadBars items={snap.operatorLoads} onSelect={goOperator}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={TrendingUp} heading="접수·완료 추이" extra={<button className="da-text-link" onClick={()=>navigate('journey')}> 추이 상세 →</button>}/>{snap?<TrendChart data={snap.throughput} onSelect={()=>navigate('journey')}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={Workflow} heading="E2E 단계별 진행" extra={<button className="da-text-link" onClick={()=>navigate('journey')}> 단계 상세 →</button>}/>{snap?<FunnelChart items={snap.stageReached??[]} onSelect={goStage}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={CalendarRange} heading="업무 간트 미리보기" extra={<button className="da-text-link" onClick={()=>navigate('schedule')}> 일정 상세 →</button>}/>{snap?<GanttChart items={snap.schedules} onSelect={()=>navigate('schedule')}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={Activity} heading="서버·AI 측정 현황"/>{snap?<div className="da-system-glance"><div><span>모니터링 서비스</span><b>{snap.services.length?fmt(snap.services.length)+'개':'연결 확인 필요'}</b></div><div><span>실제 AI 실행</span><b>{fmt(snap.ai?.totalRuns)}</b></div><div><span>AI 기술 실패</span><b>{fmt(snap.ai?.failedRuns)}</b></div><div><span>품질 평가 표본</span><b>{fmt(snap.ai?.quality?.evaluatedCases)}</b></div><button className="da-btn da-btn-outline" onClick={()=>navigate('infrastructure')}>서버 상세 <ArrowRight size={15}/></button><button className="da-btn da-btn-outline" onClick={()=>navigate('ai-quality')}>AI 품질 상세 <ArrowRight size={15}/></button></div>:<EmptyChart/>}</Box></div>
     <div className="da-chart-grid"><Box><BoxTitle icon={BrainCircuit} heading="AI 품질·근거 충족"/><DonutChart items={[]} emptyLabels={['정답 평가','사람 정정','근거 참조']} onSelect={()=>navigate('ai-quality')}/><button className="da-text-link" onClick={()=>navigate('ai-quality')}>AI 품질 상세 →</button></Box><Box><BoxTitle icon={Server} heading="자원 사용 추이"/><Sparkline points={[]} label="CPU·메모리·저장공간 추이" onSelect={()=>navigate('infrastructure')}/><button className="da-text-link" onClick={()=>navigate('infrastructure')}>서버 자원 상세 →</button></Box></div>
     <Box><BoxTitle icon={Bell} heading="관리 조치 항목" extra={<button className="da-text-link" onClick={()=>navigate('audit')}>경보 전체 →</button>}/>{snap?<AlertList alerts={snap.alerts} onGo={drillAlert}/>:<div className="da-empty-list">연동된 경보 데이터가 없습니다.</div>}</Box>
    </>}

    {page==='intake'&&<><div className="da-kpi-grid"><NumberCard label="접수 기업" value={null} icon={Building2}/><NumberCard label="개선요구" value={null} icon={ClipboardList}/></div><Box><BoxTitle icon={Building2} heading="기업·사업장·개선요구 접수"/><div className="da-searchbar"><Search size={16}/><input aria-label="기업명·요청명 검색" value={search} onChange={e=>setSearch(e.target.value)} placeholder="기업명·개선요구 검색"/></div><p className="da-note">기업별 복수 사업장·복수 개선요구를 구분합니다. 기업 수와 개선요구 수는 별도 집계입니다.</p><EmptyTable headings={['기업','사업장','개선요구','담당자','업무 단계','접수시각']}/><button className="da-btn da-btn-outline" onClick={()=>navigate('assignments')}>업무 배정 화면으로 이동</button></Box></>}
    {page==='assignments'&&<><div className="da-two-col"><Box><BoxTitle icon={ClipboardList} heading="배정 대상 개선요구"/><input className="da-input" aria-label="배정 대상 검색" value={search} onChange={e=>setSearch(e.target.value)} placeholder="기업·사업장·개선요구 검색"/><EmptyTable headings={['기업','개선요구','현재 담당자']}/></Box><Box><BoxTitle icon={UserRoundCog} heading="담당자 배정·재배정 검토"/><div className="da-assignment"><label>배정 대상<select className="da-select" disabled><option>접수 데이터 연결 필요</option></select></label><label>배정할 운영자<select className="da-select" disabled><option>운영자 후보 연결 필요</option></select></label><label>배정·재배정 이유<textarea aria-label="배정·재배정 이유" className="da-input" value={assignReason} onChange={e=>setAssignReason(e.target.value)} rows={4} placeholder="화면에서 작성만 가능하며 서버에 저장하지 않습니다."/></label><p className="da-assignment-note">추천 근거·가용성·담당자 후보: 데이터 연결 후 표시<br/>차단 사유: 배정 API·배정 정책·변경 권한 미연결. 자동 추천하지 않습니다.</p><button className="da-btn da-btn-primary" disabled title="배정 정책·권한·API 미연결">배정 반영 · 미연결</button></div></Box></div><Box><BoxTitle icon={History} heading="배정·재배정 이력"/><EmptyTable headings={['개선요구','이전 담당자','새 담당자','사유','시각']}/></Box><Box><BoxTitle icon={Users} heading="운영자별 현재 업무량"/><WorkloadBars items={[]} onSelect={goOperator}/></Box></>}
    {page==='operators'&&<><div className="da-chart-grid"><Box><BoxTitle icon={BarChart3} heading="담당자별 진행·대기·완료"/>{snap?<WorkloadBars items={snap.operatorLoads} onSelect={id=>setOperatorFilter(id)}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={Layers3} heading="운영자 × 업무 단계 히트맵" extra={<button className="da-text-link" onClick={()=>navigate('intake')}> 업무 목록 →</button>}/>{snap?<HeatMap items={snap.heatmap} onSelect={(id,stage)=>{setOperatorFilter(id);setStageFilter(stage);navigate('intake')}}/>:<EmptyChart/>}</Box></div><Box><BoxTitle icon={Users} heading="운영자별 세부 업무량"/><div className="da-table-scroll"><table className="da-table"><thead><tr><th>운영자</th><th>배정</th><th>진행</th><th>대기</th><th>완료</th><th>기한 초과</th><th>가용 여부</th></tr></thead><tbody>{snap?.operatorLoads.length?snap.operatorLoads.map(o=><tr key={o.operatorId}><td><button className="da-link" onClick={()=>{setOperatorFilter(o.operatorId);navigate('intake')}}>{o.operatorName}</button></td><td>{fmt(o.assigned)}</td><td>{fmt(o.inProgress)}</td><td>{fmt(o.waiting)}</td><td>{fmt(o.completed)}</td><td>{fmt(o.overdue)}</td><td>{o.available===null||o.available===undefined?'미확인':o.available?'가능':'불가'}</td></tr>):<EmptyRow cols={7} text="운영자 배정 통계 API를 연결해 주세요."/>}</tbody></table></div>{operatorFilter&&<button className="da-btn da-btn-outline" onClick={()=>setOperatorFilter('')}>운영자 필터 해제</button>}</Box></>}

    {page==='journey'&&<><div className="da-chart-grid"><Box><BoxTitle icon={Workflow} heading="E2E 단계별 업무 건수"/>{snap?<FunnelChart items={snap.stageReached??[]} onSelect={goStage}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={BarChart3} heading="단계별 현재 분포"/>{snap?<DonutChart items={snap.stages} onSelect={goStage}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={TrendingUp} heading="미완료 업무 잔량 변화"/>{snap?<TrendChart data={snap.throughput} metric="backlog"/>:<EmptyChart/>}</Box><Box><BoxTitle icon={Activity} heading="조회·정의 기준"/><div className="da-info-stack"><p><b>업무 모수:</b> 기업 수, 개선요구 수, 검토 건수, 제안서 수를 서로 혼용하지 않습니다.</p><p><b>중복 방지:</b> 1개 기업의 복수 과제를 개별 요청 ID로 구분합니다.</p><p><b>전환 의미:</b> 현 상태 분포와 특정 단계 도달 누적은 별도 차트로 계산합니다.</p><p><b>완료 판정:</b> 완료 증빙과 서버 검증 근거를 사용합니다.</p></div></Box></div></>}

    {page==='journey'&&<Box><BoxTitle icon={AlertTriangle} heading="지연·병목 확인"/><EmptyTable headings={['단계','확정 기한','대기 원인','지연 업무']}/><button className="da-text-link" onClick={()=>navigate('schedule')}>일정·마감 상세 →</button><p className="da-note">기한·이력 연결 전에는 미확인을 지연으로 판정하지 않습니다.</p></Box>}
    {page==='schedule' &&<><Box><BoxTitle icon={CalendarRange} heading="담당자별 주요 업무 간트"/>{snap?<GanttChart items={snap.schedules} onSelect={goWork}/>:<EmptyChart/>}</Box><Box><BoxTitle icon={ClipboardList} heading="기한이 설정된 작업"/><div className="da-table-scroll"><table className="da-table"><thead><tr><th>작업</th><th>담당자</th><th>시작</th><th>마감</th><th>상태</th></tr></thead><tbody>{snap?.schedules.length?snap.schedules.map(x=><tr key={x.id}><td><button className="da-link" onClick={()=>goWork(x.id)}>{x.label}</button></td><td>{x.operator}</td><td>{x.startAt?.slice(0,10)}</td><td>{x.dueAt?.slice(0,10)}</td><td>{x.status}</td></tr>):<EmptyRow cols={5} text="확정된 시작일·기한이 있는 작업이 없습니다."/>}</tbody></table></div></Box></>}

    {page==='infrastructure'&&<><div className="da-infra-grid">{['Web','API','PostgreSQL','파일 저장소','Worker','외부 연동'].map(name=><Box key={name} className="da-infra-card"><div className="da-infra-top"><b>{name}</b><Status value="UNKNOWN"/></div><p>측정시각: 미측정 · 원천 미연결</p><div className="da-infra-stats">{['CPU (%)','메모리 (%)','저장공간 (%)','오류율 (%)','응답 P95 (ms)','DB 연결·성능','작업 대기열 (건)'].map(m=><div key={m}><span>{m}</span><b>미측정</b></div>)}</div><Sparkline points={[]} label={name+' 시간별 자원 추이'}/></Box>)}</div><button className="da-btn da-btn-outline" onClick={()=>navigate('audit')}>장애·경보 상세</button><Box><BoxTitle icon={Info} heading="관리 기능과 기술 조치 권한 분리"/><p className="da-plain">실측 원천 미연결. 서버 재시작·배포·DB 복구·AI 설정을 실행하지 않습니다.</p></Box></>}
    {page==='ai-quality'&&<><div className="da-kpi-grid"><NumberCard label="전체 분석 실행" value={snap?.ai?.totalRuns} icon={BrainCircuit}/><NumberCard label="성공" value={snap?.ai?.successfulRuns} icon={CheckCircle2}/><NumberCard label="실패" value={snap?.ai?.failedRuns} icon={AlertTriangle}/><NumberCard label="대기" value={snap?.ai?.pendingRuns} icon={Activity}/><NumberCard label="평가 표본" value={snap?.ai?.quality?.evaluatedCases} icon={ClipboardCheck}/><NumberCard label="평균 실행시간(ms)" value={snap?.ai?.avgLatencyMs} icon={Gauge}/></div><div className="da-chart-grid"><Box><BoxTitle icon={BrainCircuit} heading="실행 유형별 건수"/><DonutChart items={[]} emptyLabels={['실제 AI','규칙 추출','수동 검토','미지원','정책 차단']}/></Box><Box><BoxTitle icon={ClipboardCheck} heading="검증 표본 기반 품질"/><div className="da-quality-metrics"><div><span>정답 일치율</span><LimitValue num={snap?.ai?.quality?.correctCases} denominator={snap?.ai?.quality?.evaluatedCases}/></div><div><span>사람 정정 비율</span><LimitValue num={snap?.ai?.quality?.correctionCount} denominator={snap?.ai?.quality?.correctionReviewed}/></div><div><span>근거 참조 충족률</span><LimitValue num={snap?.ai?.quality?.evidenceWithReferences} denominator={snap?.ai?.quality?.evidenceReviewed}/></div><div><span>평가 방법·버전</span><strong>{snap?.ai?.quality?.evaluationMethod||'미정의'} / {snap?.ai?.quality?.evaluationVersion||'미확인'}</strong></div></div><p className="da-chart-footnote">API 호출 성공률 ≠ AI 정답률. 정확도는 승인된 정답 표본과 검증 방법이 있을 때만 표시합니다.</p></Box></div></>}

    {page==='ai-quality'&&<div className="da-chart-grid"><Box><BoxTitle icon={Gauge} heading="분석 비용"/><div className="da-quality-metrics"><div><span>실행 비용 (원)</span><strong>미측정</strong></div><div><span>토큰 사용량</span><strong>미측정</strong></div></div><p className="da-note">과금·모델 원천 미연결 · 추정 비용을 생성하지 않습니다.</p></Box><Box><BoxTitle icon={BrainCircuit} heading="모델·문서 유형별 품질 비교"/><EmptyTable headings={['모델·버전','문서 유형','평가 표본','정답 일치율','근거 품질']}/></Box></div>}
    {page==='reference' &&<><Box><BoxTitle icon={Database} heading="DMP·Capability·공고·기준정보"/>{session&&<p className="da-chart-footnote" role="region" aria-label="허용된 기준정보 요약">{catalogRead?.status==='ready'?<>등록 기능 레코드 <b data-testid="admin-feature-count">{catalogRead.data?.features}</b> · 발행 참조가 있는 Capability <b data-testid="admin-published-count">{catalogRead.data?.published}</b> · 원천: Workspace 관리자 Projection. 목록·버전·동기화 상태는 별도 미연결입니다.</>:catalogRead?.status==='error'?'기준정보 메타데이터 조회 실패':'기준정보 메타데이터 조회 중'}</p>}<div className="da-table-scroll"><table className="da-table"><thead><tr><th>종류</th><th>기준정보</th><th>버전</th><th>데이터 상태</th><th>확인 시점</th><th>원천</th></tr></thead><tbody>{snap?.references.length?snap.references.map(x=><tr key={x.id}><td>{x.domain}</td><td><strong>{x.label}</strong></td><td>{x.version||'미확인'}</td><td>{x.dataStatus}</td><td>{x.verifiedAt?.slice(0,16).replace('T',' ')||'미확인'}</td><td>{x.source}</td></tr>):<EmptyRow cols={6} text="실제 DMP/공고/Capability 버전 데이터가 연결되지 않았습니다."/>}</tbody></table></div><p className="da-chart-footnote">DMP 649개 기능의 적재 여부는 실제 Source·SHA·Version 검증 결과가 있어야 표시합니다. 공고 검토와 DATCO 업무 결정 권한을 임의 통합하지 않습니다.</p></Box></>}

    {page==='users'&&<><Box><BoxTitle icon={ShieldCheck} heading="접근권한 관리 원칙"/><div className="da-info-stack"><p><b>사용자 인증:</b> 현재 Repository의 인증 계층을 재사용하고 향후 DMP SSO에 어댑터로 연계합니다.</p><p><b>회사별 접근범위:</b> 관리자·운영자·기업 사용자의 Company Scope를 서버에서 검증합니다.</p><p><b>권한 분리:</b> 배정권한과 Fact 확정, 서비스 발행, 제안서 승인권한은 별개입니다.</p><p><b>설정 변경:</b> 계정·권한 변경은 승인된 정책·서버 Action·감사로그를 통해 처리합니다.</p></div></Box><Box><BoxTitle icon={Users} heading="사용자·역할·접근범위"/><div className="da-table-scroll"><table className="da-table"><thead><tr><th>계정</th><th>역할</th><th>상태</th><th>기업 Scope</th><th>담당 요청</th><th>마지막 활동</th></tr></thead><tbody>{snap?.users.length?snap.users.map(u=><tr key={u.userId}><td>{u.name}<small>{u.userId}</small></td><td>{u.roleLabels.join(' / ')}</td><td>{u.accountStatus}</td><td>{fmt(u.companyScopes)}</td><td>{fmt(u.assignedRequests)}</td><td>{u.lastActiveAt?.slice(0,16).replace('T',' ')||'미측정'}</td></tr>):<EmptyRow cols={6} text="사용자 계정 및 접근범위 조회 API를 연결해 주세요."/>}</tbody></table></div></Box></>}

    {page==='portals'&&<div className="da-two-col">{(['company','operator'] as const).map(id=>{const p=snap?.portals.find(x=>x.id===id);return <Box key={id}><BoxTitle icon={id==='company'?Building2:Users} heading={id==='company'?'수요기업 포털':'DATCO 운영자 포털'}/><button className="da-text-link" onClick={()=>navigate('audit')}>관련 오류·감사 상세 →</button><div className="da-portal-score"><Status value={p?.health||'UNKNOWN'}/><p>최근 실측: {p?.asOf?new Date(p.asOf).toLocaleString('ko-KR'):'미측정'}</p></div><div className="da-infra-stats"><div><span>활성 사용자</span><b>{fmt(p?.usersActive)}</b></div><div><span>실패한 업무 Action</span><b>{fmt(p?.failedActions)}</b></div></div><p className="da-chart-footnote">사용자 입력·검토·승인 상태는 동일 Company·Version 계약을 통해 관리하며, 관리자에게 무제한 수정·승인권한을 부여하지 않습니다.</p></Box>})}</div>}

    {page==='audit'&&<><Box><BoxTitle icon={ShieldAlert} heading="조치 필요 경보"/>{snap?<AlertList alerts={snap.alerts} onGo={drillAlert}/>:<EmptyChart message="경보 API 미연결"/>}</Box><Box><BoxTitle icon={History} heading="관리 Action 감사 이력"/><div className="da-table-scroll"><table className="da-table"><thead><tr><th>시간</th><th>실행자</th><th>작업</th><th>대상</th><th>세부</th></tr></thead><tbody>{snap?.audits.length?snap.audits.map(x=><tr key={x.id}><td>{x.at?.slice(0,16).replace('T',' ')}</td><td>{x.actor}</td><td>{x.action}</td><td>{x.subject}</td><td>{x.summary}</td></tr>):<EmptyRow cols={5} text="관리자 및 운영자의 실제 Audit Event 기록을 연결해 주세요."/>}</tbody></table></div></Box></>}

    </div><footer className="da-footer"><span>DATCO ONE · 통합 운영통제 및 기술·AI 관제</span><span>실제 업무·모니터링 데이터 연결 전에는 집계값을 생성하지 않습니다.</span></footer>
   </main></div>
 </div>;
}

const detailMenus:Partial<Record<Screen,Array<{id:Page;label:string}>>>={
 'ai-quality':[{id:'analysis',label:'AI 분석 운영'},{id:'quality',label:'데이터 품질'}],
 reference:[{id:'features',label:'DMP 기능 목록'},{id:'capabilities',label:'Capability 관리'},{id:'publishing',label:'서비스 버전·발행'},{id:'notices',label:'정부지원사업 공고'},{id:'requirements',label:'공고 분석·요건 검토'}],
 users:[{id:'users',label:'사용자·계정'},{id:'access',label:'권한·기업 접근범위'}],
 infrastructure:[{id:'integrations',label:'DMP·외부 연동'}],audit:[{id:'audit',label:'감사·변경 이력'}],
};
function EmptyTable({headings}:{headings:string[]}){return <div className="da-table-scroll"><table className="da-table"><thead><tr>{headings.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody><EmptyRow cols={headings.length} text="데이터 연결 후 표시"/></tbody></table></div>}
