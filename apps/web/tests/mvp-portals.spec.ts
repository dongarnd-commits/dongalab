import {test,expect,type Page} from '@playwright/test';
import {createHash} from 'node:crypto';
const context=()=>JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);
const origin=()=>process.env.DATCO_E2E_BASE_URL!;
async function login(page:Page,username:string,password:string,portal='operator'){
 expect((await page.request.post('/api/notice/session',{headers:{Origin:origin()},data:{username,password}})).ok()).toBe(true);
 await page.goto('/portal/'+portal);
}

test('MVP admin uses real summaries, source catalog, existing grant and unconfigured external status',async({page})=>{
 test.setTimeout(90000);const c=context();await login(page,c.accounts.admin,c.password,'admin');
 await expect(page.getByRole('heading',{name:'MVP 관리 업무',exact:true})).toBeVisible();
 const overview=await(await page.request.get('/api/admin/overview')).json();expect(overview.accounts).toBeGreaterThan(0);
 const nav=page.getByRole('navigation',{name:'관리자 메뉴'});await nav.getByRole('button',{name:'기준정보·버전',exact:true}).click();
 await expect(page.getByRole('heading',{name:'실제 DMP 기능·Capability Catalog',exact:true})).toBeVisible();
 const inventory=await(await page.request.get('/api/capability/features?limit=25')).json();await expect(page.getByText('조회된 실제 기능 '+inventory.total+'건',{exact:false})).toBeVisible();
 await nav.getByRole('button',{name:'사용자·권한',exact:true}).click();
 const before=await(await page.request.get('/api/admin/access')).json();expect(JSON.stringify(before)).not.toContain('password_hash');
 await page.getByLabel('접근권한 대상 계정',{exact:true}).selectOption(c.accounts.operator);await page.getByLabel('접근권한 허용 기업',{exact:true}).selectOption(c.a.id);
 await page.getByRole('button',{name:'선택한 기업 접근권한 부여',exact:true}).click();await expect(page.getByRole('status')).toContainText('기업 접근권한을 저장했습니다');
 const after=await(await page.request.get('/api/admin/access')).json();expect(after.memberships).toEqual(before.memberships);
 await nav.getByRole('button',{name:'서버·연동 모니터링',exact:true}).click();await expect(page.getByRole('heading',{name:'분석 실행 제공자',exact:true})).toBeVisible();
 await expect(page.getByText('NOT_CONFIGURED — 연결 미설정',{exact:true})).toHaveCount(4);
 expect((await page.request.get('/api/company/'+c.a.id)).status()).toBe(403);
 await page.reload();await expect(page.getByRole('heading',{name:'MVP 관리 업무',exact:true})).toBeVisible();
});

test('MVP operator keeps six menus, exact historical input and cross-company guards without automatic mutations',async({page})=>{
 test.setTimeout(120000);const c=context();await login(page,c.accounts.operator,c.password);const writes:string[]=[];
 page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);});
 for(const name of ['DATCO 서비스 추천','서비스 조합 검토','정부지원사업 추천','매칭·자격 검토','맞춤형 제안서','전달·검토 이력']){
  await page.getByRole('navigation',{name:'운영자 업무 메뉴'}).getByRole('button',{name,exact:true}).click();
  await expect(page.getByLabel('솔루션 대상 기업',{exact:true})).toBeVisible();await expect(page.getByLabel('솔루션 대상 개선요구 Version',{exact:true})).toBeDisabled();
 }
 await page.getByRole('navigation',{name:'운영자 업무 메뉴'}).getByRole('button',{name:'DATCO 서비스 추천',exact:true}).click();
 await page.getByLabel('솔루션 대상 기업',{exact:true}).selectOption(c.a.id);await page.getByLabel('솔루션 대상 개선요구 Version',{exact:true}).selectOption(c.av1.id);
 await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',c.av1.id);
 await expect(page.getByText('과거 Version은 읽기 전용입니다. 현재 Version으로 다시 검토해야 합니다.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'새 구조화 Version 저장·기업 확인 대기',exact:true})).toBeDisabled();
 await page.reload();await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',c.av1.id);
 expect(writes).toEqual([]);
 await page.goto('/portal/operator?screen=recommendations&company='+c.foreign.id+'&version='+c.fv.id);
 await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText(c.foreign.name,{exact:true})).toHaveCount(0);
 expect((await page.request.get('/api/admin/access')).status()).toBe(403);
 expect((await page.request.get('/api/company/'+c.foreign.id)).status()).toBe(404);
});

test('MVP real matching review to 16-section documents, safe native send confirmation and company revision',async({page,browser})=>{
 test.setTimeout(240000);const c=JSON.parse(process.env.DATCO_PROPOSAL_CONTEXT!),headers={Origin:origin()};
 await login(page,c.operator,c.password);const vid=c.composition_data.improvement_version_id;
 const comp=await page.request.post('/api/capability/compositions',{headers,data:{data:c.composition_data,idempotency_key:crypto.randomUUID()}});expect(comp.ok()).toBe(true);const cv=await comp.json();
 const matchResponse=await page.request.post('/api/capability/matches',{headers,data:{composition_version_id:cv.version_id,notice_id:c.notice.notice_id,requirement_version_id:c.notice.requirement_version_id,idempotency_key:crypto.randomUUID()}});expect(matchResponse.ok()).toBe(true);const candidate=await matchResponse.json();
 await page.goto('/portal/operator?screen=matching&company='+c.company_id+'&version='+vid);
 await page.getByLabel('저장된 매칭 후보',{exact:true}).selectOption(candidate.candidate_id);
 const prep=await(await page.request.get('/api/capability/matches/'+candidate.candidate_id+'/proposal-preparation')).json();expect(prep.review_evidence.length).toBeGreaterThan(0);
 for(const task of prep.review_tasks){await page.getByLabel(task.id+' 검토 의견',{exact:true}).fill('TEST checked exact company proof and recorded source requirement.');await page.getByLabel(task.id+' 현재 확정 근거',{exact:true}).selectOption(prep.review_evidence[0].id);}
 await page.getByLabel('매칭 전체 검토 의견',{exact:true}).fill('TEST reviewed all prerequisites without treating unknown eligibility as true.');
 await page.getByRole('button',{name:'근거 검토 완료·제안 가능 판단',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('항목별 근거와 제안 가능 판단을 저장했습니다');
 await page.getByRole('button',{name:'동일 대상의 제안서 작성',exact:true}).click();
 await page.getByLabel('제안서 매칭 후보',{exact:true}).selectOption(candidate.candidate_id);const title='TEST MVP16 browser '+Date.now();await page.getByLabel('표준 제안서 제목',{exact:true}).fill(title);
 await expect(page.getByRole('button',{name:'표준 16개 항목 제안 초안 생성',exact:true})).toBeEnabled();
 const creating=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/proposal'&&r.request().method()==='POST');await page.getByRole('button',{name:'표준 16개 항목 제안 초안 생성',exact:true}).click();const created=await(await creating).json();
 await expect(page.getByRole('heading',{name:title+' · v1',exact:true})).toBeVisible();
 const saved=await(await page.request.get('/api/proposal/'+created.proposal_id)).json();expect(saved.versions[0].sections).toHaveLength(16);expect(saved.versions[0].manifest.template_version).toBe('MVP_16');
 await page.getByLabel('제안내용 검토 의견',{exact:true}).fill('TEST reviewed every section, actual capabilities and uncertain financial/schedule values.');await page.getByRole('button',{name:'이 Version 제안내용 확인',exact:true}).click();
 await expect(page.getByRole('button',{name:'DOCX 파일 생성',exact:true})).toBeEnabled();
 for(const kind of ['DOCX','PDF']){await page.getByRole('button',{name:kind+' 파일 생성',exact:true}).click();const link=page.getByRole('link',{name:'v1 '+kind+' 다운로드',exact:true});await expect(link).toBeVisible();const r=await page.request.get((await link.getAttribute('href'))!);expect(r.ok()).toBe(true);const bytes=await r.body();const details=await(await page.request.get('/api/proposal/'+created.proposal_id)).json();const f=details.files.find((f:{kind:string;version_id:string})=>f.kind===kind&&f.version_id===created.version_id);expect(createHash('sha256').update(bytes).digest('hex')).toBe(f.digest);}
 await page.getByLabel('기업 제안 검토 방식',{exact:true}).selectOption('COMPANY_RECORDED_AUTHORIZATION');await page.getByLabel('전달할 기업 담당자 아이디',{exact:true}).fill(c.company_editor);await page.getByRole('button',{name:'기업 담당자 확인',exact:true}).click();
 const open=page.getByRole('button',{name:'기업 전달·검토 요청 확인',exact:true});await expect(open).toBeEnabled();const sends:string[]=[];page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/approval'))sends.push(r.url());});
 await open.click();const modal=page.getByRole('dialog',{name:'정확한 제안서 Version을 기업에 전달하시겠습니까?',exact:true});await expect(modal.getByRole('button',{name:'취소',exact:true})).toBeFocused();await expect(open.click({timeout:500})).rejects.toThrow();await expect(modal).toBeVisible();await page.keyboard.press('Escape');await expect(modal).toHaveCount(0);await expect(open).toBeFocused();
 await open.click();await modal.getByRole('button',{name:'취소',exact:true}).click();expect(sends).toEqual([]);expect((await(await page.request.get('/api/proposal/'+created.proposal_id)).json()).requests).toHaveLength(0);
 await open.click();const sending=page.waitForResponse(r=>r.url().endsWith('/approval')&&r.request().method()==='POST');await modal.getByRole('button',{name:'최종 확인·기업 검토 요청',exact:true}).evaluate(el=>{(el as HTMLButtonElement).click();(el as HTMLButtonElement).click();});expect((await sending).ok()).toBe(true);await expect(page.getByRole('status')).toContainText('정확한 ProposalVersion을 지정된 기업 계정에 전달했습니다');expect(sends).toHaveLength(1);
 await page.reload();await expect(page.getByRole('heading',{name:title+' · v1',exact:true})).toBeVisible();
 const companyContext=await browser.newContext({baseURL:origin()}),company=await companyContext.newPage();await login(company,c.company_editor,c.password,'company');await company.locator('aside').getByRole('button',{name:'받은 제안서',exact:true}).click();
 const card=company.getByRole('heading',{name:title,exact:true}).locator('..');await card.getByRole('button',{name:'제안서 본문 확인',exact:true}).click();await expect(company.getByText('이 전달 Version의 본문 16개 항목',{exact:true})).toBeVisible();
 await company.getByLabel('검토 의견·수정 요청사항',{exact:true}).fill('TEST company requests a revised integration scope.');await company.getByRole('button',{name:'제안서 수정 요청',exact:true}).click();await expect(company.getByRole('status')).toContainText('제안서 수정 요청을 기록했습니다.');
 await company.reload();await expect(company.getByText(/REVISION_REQUEST · TEST company requests/)).toBeVisible();
 const after=await(await page.request.get('/api/proposal/'+created.proposal_id)).json();expect(after.versions[0].id).toBe(created.version_id);expect(after.decisions[0].outcome).toBe('REVISION_REQUEST');expect(after.files).toHaveLength(2);await companyContext.close();
});
