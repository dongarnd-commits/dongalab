"use client";
import {ReactNode} from "react";
import {useWorkspace,roles} from "./context";

function Card({title,children}:{title:string;children:ReactNode}) {
  return <article className="workspace-card"><h2>{title}</h2>{children}</article>;
}
export default function Home() {
  const {data,identity,company,refresh}=useWorkspace();
  if(!data&&identity)return <section className="workspace-home"><h1>업무 현황 조회 대기</h1><p>사용자 인증은 확인했습니다. 현황 API 연결을 다시 확인해 주세요. 상단 로그아웃은 사용할 수 있습니다.</p><button onClick={refresh}>다시 조회</button></section>;
  if(!data)return <section className="workspace-home"><h1>DATCO 업무 공간</h1><p>로그인하면 역할에 맞는 업무와 허용된 기업이 표시됩니다.</p><a className="workspace-primary" href="/login">로그인하여 시작</a></section>;
  const admin=data.actor.role==='DATCO_ADMIN',operator=data.actor.role==='DATCO_OPERATOR',approver=data.actor.role==='COMPANY_APPROVER';
  const companies=company?[company]:data.companies;
  const total=(key:'files'|'pending_facts'|'improvements'|'facts')=>companies.reduce((n,c)=>n+(c.counts?.[key]??0),0);
  const proposals=data.proposals.filter(p=>!company||p.company_id===company.id);
  const compositions=data.compositions.filter(p=>!company||p.company_id===company.id);
  const matches=data.matches.filter(p=>!company||p.company_id===company.id);
  function href(target:string) {
    const u=new URL(target,'http://local');
    if(company){u.searchParams.set('company',company.id);
      if(typeof window!=='undefined'){const q=new URLSearchParams(window.location.search);for(const k of ['site','improvement']){const v=q.get(k);if(v)u.searchParams.set(k,v);}}
    }
    return u.pathname+u.search;
  }
  const next=admin?['Catalog·Version 관리','/capability?view=catalog']:approver?['제안서 확인·승인','/proposal']:operator?['기업자료·Fact 검토하기','/company?tab=facts']:['기업 증빙자료 제출하기','/company?tab=onboarding'];
  return <section className="workspace-home">
    <header className="workspace-home-heading"><div><p className="workspace-eyebrow">{roles[data.actor.role]} · {data.actor.username}</p><h1>{admin?'운영 대시보드':operator?'업무 대시보드':'내 기업 홈'}</h1><p>{admin?'관리자 대시보드':operator?'운영자 대시보드':'수요기업 업무 홈'} · {company?.name??(admin?'기준정보와 접근권한 관리':'상단에서 업무 기업을 선택해 주세요')}</p></div><button onClick={refresh}>업무 현황 새로고침</button></header>
    <section className="workspace-start" aria-label="업무 시작"><div><p className="workspace-eyebrow">다음 업무</p><h2>{admin?'확인된 서비스와 접근관계를 관리하세요':approver?'전달받은 제안서의 정확한 Version을 확인하세요':operator?'기업의 원문과 개선요구부터 검토하세요':'기업 증빙자료부터 제출해 주세요'}</h2><p>{admin?'기능 원천 → Capability 검토 → 발행·Version → 기업 접근관계':approver?'지정된 승인 요청에 한해 승인·수정요청·거절을 기록합니다.':operator?'기업 선택 → Fact·Evidence → 개선요구 → 서비스 조합 → 매칭 → 제안서': '자료 제출 → 추출 후보 확인 → 기업정보 확인 → 개선요구 → DATCO 검토'}</p></div><a className="workspace-primary" href={href(next[1])}>{next[0]}</a></section>
    {!admin&&!company&&<p className="workspace-hint">{data.companies.length?'아래 목록 또는 상단에서 기업을 선택하세요. 선택 전 건수는 접근 가능한 기업의 합계입니다.':approver?'접근 가능한 기업이 없습니다. 담당자에게 기업 접근권한과 승인 요청을 확인해 주세요.':'기업정보가 없다면 먼저 기업을 등록하세요. 자료는 등록한 기업에 연결해 저장합니다.'}{!approver&&!data.companies.length&&<a href="/company?tab=profile">기업정보 등록하기</a>}</p>}
    <div className="workspace-cards">
      {admin?<>
        <Card title="DMP Inventory"><p className="workspace-stat">{data.catalog?.features??0}</p><p>저장된 기능 원천입니다. 실제 DMP 연동 상태를 의미하지 않습니다.</p><a href="/capability?view=features">기능 원천 조회</a></Card>
        <Card title="Capability Catalog"><p className="workspace-stat">{data.catalog?.published??0}</p><p>발행 이력이 있는 Capability 수입니다. 상세 Version과 발행 조건을 확인하세요.</p><a href="/capability?view=catalog">Catalog·Version 관리</a></Card>
        <Card title="사용자·기업 접근관계"><p>등록 기업 {data.companies.length}개</p><p>기존 계정에 기업 접근관계를 명시적으로 부여합니다.</p><a href="/company">사용자·기업 접근권한</a></Card>
        <Card title="공고·분석·감사 안내"><p>공고 운영은 DATCO 운영자 권한이 필요합니다. 관리자에게 자동 부여되지 않습니다.</p><p>기존 실행·오류 기록은 각 업무에서 허용된 범위로 확인합니다. 통합 분석·감사 화면은 준비 중입니다.</p><span className="workspace-badge">통합 관리 화면 준비 중</span></Card>
      </>:<>
        <Card title={operator?'접근 가능한 기업':'현재 기업정보'}><p>{company?company.name:`접근 가능한 기업 ${data.companies.length}개`}</p>{company&&<p>사업장 {company.sites?.length??0}개 · 확정 Fact {total('facts')}개</p>}<div className="workspace-company-list">{data.companies.map(c=><a key={c.id} href={'/?company='+c.id}>{c.name}</a>)}</div>{!approver&&<a href={href('/company?tab=profile')}>기업정보 등록·수정</a>}</Card>
        {!approver&&<>
          <Card title="제출자료"><p className="workspace-stat">{total('files')}<small>개 저장</small></p><p>업로드 원문과 기존 파싱·규칙 추출 결과를 확인합니다.</p><a href={href('/company?tab=files')}>자료 제출·파싱 결과</a></Card>
          <Card title="기업정보 확인 필요사항"><p className="workspace-stat">{total('pending_facts')}<small>개 후보 검토 필요</small></p><p>미검토 후보 수입니다. 필수자료 충족이나 기업 자격 확정을 의미하지 않습니다.</p><a href={href('/company?tab=facts')}>원문과 후보 검토</a></Card>
          <Card title="개선요구 등록 현황"><p className="workspace-stat">{total('improvements')}<small>개 과제 저장</small></p>{companies.flatMap(c=>(c.improvements??[]).map(i=><p key={i.id}>{c.name} · {i.title} <span className="workspace-badge">{i.state==='DRAFT'?'작성 중':i.state==='SUBMITTED'?'DATCO 검토 요청':i.state==='CONFIRMED'?'운영자 검토 확정':i.state==='REVIEW_REQUIRED'?'구조화 내용 확인 필요':i.state==='REVISION_REQUIRED'?'보완 필요':i.state}</span></p>))}<a href={href('/company?tab=improvement')}>{operator?'개선요구 검토':'개선요구 입력·관련자료 첨부'}</a></Card>
          {!operator&&<Card title="DATCO 검토 진행현황"><p>개선과제별 현재 상태와 검토 근거는 상세 화면에서 확인하세요. 저장·제출은 검토 완료가 아닙니다.</p><a href={href('/company?tab=improvement')}>개선요구 분석·검토 기록 확인</a><p>외부 AI 의미 분석과 별도 자료보완 요청함은 준비 중입니다.</p></Card>}
        </>}
        {(operator||approver)&&<Card title="제안서·승인 요청"><p>{proposals.filter(p=>p.pending).length}개 현재 승인요청</p>{proposals.map(p=><a key={p.id} href={'/proposal?proposal='+p.id+'&company='+p.company_id+'&improvement='+p.improvement_version_id}>{p.title} · Version {p.ordinal}</a>)}{!proposals.length&&<p>전달된 업무가 없습니다.</p>}<a href={href('/proposal')}>{approver?'제안서 확인·승인':'제안서 업무 열기'}</a></Card>}
        {!operator&&!approver&&<Card title="받은 제안서·승인 안내"><p>현재 기업 담당자 계정에는 Proposal 승인 권한이 없습니다. 지정 기업 승인자 계정으로 전달된 제안서를 확인해 주세요.</p><p>기업 담당자용 제안서 조회는 아직 연결되지 않았습니다.</p></Card>}
        {operator&&<><Card title="서비스 조합 업무"><p>저장된 조합 {compositions.length}개</p><a href={href('/capability?view=composer')}>서비스 조합 검토</a><p>운영자가 확인한 개선과제를 바탕으로 조합합니다. 자동 조합은 준비 중입니다.</p></Card><Card title="지원사업 매칭 업무"><p>저장된 매칭 후보 {matches.length}개</p><a href={href('/capability?view=matching')}>매칭 결과 검토</a><a href="/notice">정부지원사업 공고 관리</a><p>기존 후보·근거·사람 검토를 사용합니다. 신규 공고 자동 추천은 준비 중입니다.</p></Card></>}
      </>}
    </div>
    <section className="workspace-card workspace-boundary"><h2>업무 진행 안내</h2><p>건수와 상태는 저장된 데이터의 조회값입니다. 자료 누락·자격 적합성·검토 완료·기업 승인을 자동 확정하지 않습니다.</p><p>자동 솔루션 추천·정부지원사업 자동 추천·전주기 운영은 준비 중입니다. 실제 업무 전환은 각 상세 화면의 권한과 필수 검토 조건을 따릅니다.</p></section>
  </section>;
}
