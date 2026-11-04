import {test,expect,type Page,type APIRequestContext} from '@playwright/test';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
const origin=()=>process.env.DATCO_E2E_BASE_URL!;
type Version={id:string;improvement_id:string;ordinal:number;data:{original_text:string;as_is:string;to_be:string;site_id:string;evidence_ids:string[];fact_version_ids:string[];analysis_basis?:{run_id:string;review_ids:string[];source_version_id:string}};reviews:{outcome:string}[]};
async function login(page:Page,username:string,password:string,role='operator'){
 await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(username);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(new RegExp('/portal/'+role));
}
async function post(client:APIRequestContext,path:string,data:unknown){const response=await client.post('/api/company'+path,{headers:{Origin:origin()},data});expect(response.ok(),await response.text()).toBe(true);return response.json();}

test('MVP fresh company submission to Rule review, explicit source v1 basis, structured v2 ACK and operator CONFIRM',async({page,browser,playwright})=>{
 test.setTimeout(240000);const c=JSON.parse(process.env.DATCO_MVP_CONTEXT!);expect(c.nonce).toBe(process.env.DATCO_TEST_NONCE);
 const companyContext=await browser.newContext({baseURL:origin()}),company=await companyContext.newPage();await login(company,c.accounts.editor,c.password,'company');
 // Normal input APIs create the company/site; no state, review, analysis or decision is seeded.
 const registered=await post(company.request,'',{name:'TEST MVP logistics '+c.nonce,business_number:c.business_number,industry:'물류 서비스'}),cid=registered.id;
 const site=(await post(company.request,'/'+cid+'/sites',{data:{name:'TEST MVP logistics site',address:'TEST synthetic logistics address',industry:'물류',process:'창고 입출고'}})).site;
 const admin=await playwright.request.newContext({baseURL:origin(),extraHTTPHeaders:{Origin:origin()}});expect((await admin.post('/api/notice/session',{data:{username:c.accounts.admin,password:c.password}})).ok()).toBe(true);await post(admin,'/'+cid+'/access',{username:c.accounts.operator});await post(admin,'/'+cid+'/access',{username:c.accounts.approver});await admin.dispose();
 await company.goto('/portal/company?company='+cid+'&screen=needs');await company.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();await company.getByRole('button',{name:'새 개선요구 작성',exact:true}).click();
 const asIs='물류 창고 1개 사업장의 입출고를 Excel로 수기 기록하여 재고 차이가 발생한다. 최근 한 달 재고 오차율은 8%이며 입출고 담당자가 월말 실사로 측정한다. 바코드 리더기 2대를 사용하고 재고 이력을 Excel에 기록한다.';
 const toBe='입출고 이력과 재고 데이터를 연동하여 월 재고 오차율을 2% 이하로 낮추고, 입출고 이력 관리 기능과 재고 조회 기능을 사용하려고 한다. 사업비와 일정은 근거 확인 후 별도 산정한다.';
 await company.getByLabel('현재 업무와 불편한 점',{exact:true}).fill(asIs);await company.getByLabel('개선하고 싶은 모습',{exact:true}).fill(toBe);await company.getByLabel('제약 및 확인 필요사항',{exact:true}).fill('현재 Excel 원본과 동일 사업장의 입출고 범위를 검토한다.');
 const bytes=Buffer.from('TEST SYNTHETIC DOCUMENT — NOT CUSTOMER DATA\n기업명: TEST MVP logistics '+c.nonce+'\n'+asIs+'\n'+toBe,'utf8');const digest=createHash('sha256').update(bytes).digest('hex');
 await company.getByLabel('개선요구 관련파일 선택',{exact:true}).setInputFiles({name:'TEST-MVP-logistics.txt',mimeType:'text/plain',buffer:bytes});await company.getByRole('button',{name:'DATCO에 제출',exact:true}).click();
 await expect(company.getByRole('status').filter({hasText:'DATCO에 제출했습니다.'})).toBeVisible();
 const submitted=await(await company.request.get('/api/company/'+cid)).json(),root=submitted.improvements[0],v1=root.versions[0] as Version;
 expect(v1.data.site_id).toBe(site.id);expect(root.state).toBe('SUBMITTED');expect(v1.reviews.some(r=>r.outcome==='SUBMIT')).toBe(true);expect(v1.data.evidence_ids).toHaveLength(1);expect(submitted.files[0].digest).toBe(digest);const v1Data=structuredClone(v1.data);
 await login(page,c.accounts.operator,c.password);await page.goto('/portal/operator?screen=facts&company='+cid);
 const parsing=page.waitForResponse(r=>r.url().endsWith('/api/company/files/'+submitted.files[0].id+'/parse')&&r.request().method()==='POST');await page.getByRole('button',{name:'TEST-MVP-logistics.txt · 기존 로컬 추출 실행',exact:true}).click();expect((await parsing).ok()).toBe(true);
 const parsed=await(await page.request.get('/api/company/'+cid)).json();const extracted=parsed.candidates.find((candidate:{id:string;mode:string;evidence_id:string})=>candidate.mode==='RULE_BASED_EXTRACTION'&&parsed.evidence.some((e:{id:string;file_id:string})=>e.id===candidate.evidence_id&&e.file_id===submitted.files[0].id));expect(extracted).toBeTruthy();
 const factRow=page.locator('details[data-candidate-id="'+extracted.id+'"]');await factRow.locator(':scope > summary').click();await factRow.getByLabel('company_name Fact 검토 의견',{exact:true}).fill('TEST must wait for company ACK before confirming the actual file value.');await expect(factRow.getByRole('button',{name:'Fact 검토 기록 저장',exact:true})).toBeDisabled();
 await company.reload();await company.locator('aside').getByRole('button',{name:'첨부자료 관리',exact:true}).click();await company.getByText('자료에서 읽은 정보 확인',{exact:true}).click();const companyCandidate=company.locator('article[data-candidate-id="'+extracted.id+'"]');await companyCandidate.getByLabel('확인·정정 사유',{exact:true}).fill('TEST company verified the labelled company name in this exact synthetic original file.');await companyCandidate.getByRole('button',{name:'원문 값 사실확인',exact:true}).click();await expect(company.getByRole('status').filter({hasText:'이 후보의 기업 사실확인을 서버에 기록했습니다.'})).toBeVisible();
 const acknowledged=await(await company.request.get('/api/company/'+cid)).json();expect(acknowledged.facts).toEqual([]);expect(acknowledged.candidates.find((row:{id:string})=>row.id===extracted.id).acknowledgements.at(-1).agreed).toBe(true);
 await page.reload();const reviewedFactRow=page.locator('details[data-candidate-id="'+extracted.id+'"]');await reviewedFactRow.locator(':scope > summary').click();await reviewedFactRow.getByLabel('company_name Fact 검토 의견',{exact:true}).fill('TEST operator verified the exact original file, labelled value and company ACK.');const reviewingFact=page.waitForResponse(r=>r.url().endsWith('/api/company/candidates/'+extracted.id+'/review')&&r.request().method()==='POST');await reviewedFactRow.getByRole('button',{name:'Fact 검토 기록 저장',exact:true}).click();const factResult=await reviewingFact;expect(factResult.ok()).toBe(true);const factVersion=(await factResult.json()).version;expect(factVersion.value).toBe('TEST MVP logistics '+c.nonce);
 await page.goto('/portal/operator?screen=improvement&company='+cid+'&version='+v1.id);
 const panel=page.getByTestId('improvement-analysis');await expect.poll(async()=>{const runs=await(await page.request.get('/api/company/improvements/'+v1.id+'/analysis-runs')).json();return runs.length;},{timeout:60000}).toBeGreaterThan(0);await expect(panel.getByText('현재 입력에 활용 가능한 분석',{exact:true})).toBeVisible({timeout:60000});
 await panel.getByText('상세 분석·근거·실행 이력',{exact:true}).click();await panel.getByText('참고자료 추가·수동 재분석',{exact:true}).click();const provider=panel.getByLabel('분석 방식',{exact:true});await expect(provider).toHaveValue('RULE');for(const id of ['GPT','GEMINI','CLAUDE','GROK'])expect(await provider.locator('option[value="'+id+'"]').evaluate(option=>(option as HTMLOptionElement).disabled)).toBe(true);await provider.focus();await provider.press('ArrowDown');await expect(provider).toHaveValue('RULE');
 const registry=await(await page.request.get('/api/company/analysis/providers')).json();expect(registry.providers.filter((p:{status:string})=>p.status==='NOT_CONFIGURED')).toHaveLength(4);
 const inputs=await(await page.request.get('/api/company/improvements/'+v1.id+'/analysis-inputs')).json();
 for(const external of ['GPT','GEMINI','CLAUDE','GROK']){const denied=await page.request.post('/api/company/improvements/'+v1.id+'/analysis-jobs',{headers:{Origin:origin()},data:{provider:external,selection_token:inputs.selection_token,idempotency_key:crypto.randomUUID(),excluded_files:{},common_file_ids:[],reason:'TEST unavailable external provider must be rejected before any execution'}});expect(denied.status()).toBe(409);expect((await denied.json()).reason).toBe('ANALYSIS_PROVIDER_NOT_CONFIGURED');}
 const runs=await(await page.request.get('/api/company/improvements/'+v1.id+'/analysis-runs')).json(),run=runs.at(-1);expect(run.manifest.version_id).toBe(v1.id);expect(run.run.provider_version).toContain('rule');expect(JSON.stringify(run)).toContain(factVersion.id);
 const candidate=run.candidates.find((x:{category:string})=>x.category==='STRUCTURE');expect(candidate).toBeTruthy();await panel.getByText(/^분석 내용별 근거·검토 ·/).click();const card=panel.locator('article[data-candidate-id="'+candidate.id+'"]');await card.getByText('근거·개별 검토',{exact:true}).click();await card.getByLabel('확인 의견',{exact:true}).fill('TEST checked source evidence; use this bounded structured candidate as the explicit analysis basis.');await card.getByRole('button',{name:'요청 활용',exact:true}).click();await expect(card.getByText(/최근 검토: 요청 활용/)).toBeVisible();
 await page.getByRole('button',{name:'이 개선요구의 구조화·서비스 추천 검토',exact:true}).click();await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',v1.id);
 const attach=page.getByRole('checkbox',{name:'표시한 제출본 분석·최신 활용 검토 기록을 새 구조화 Version의 근거로 명시 연결',exact:true});await expect(attach).toBeEnabled();await attach.check();await page.getByRole('group',{name:'확정된 기업정보 선택',exact:true}).getByRole('checkbox').check();await page.getByLabel('공식 검토 필요 기능',{exact:true}).fill('입출고 이력 관리 및 재고 조회');await page.getByLabel('공식 검토 확인할 문제',{exact:true}).fill('재고 차이가 발생한다.');await page.getByLabel('공식 검토 개선 목표',{exact:true}).fill('월 재고 오차율을 2% 이하로 낮춘다.');
 const saving=page.waitForResponse(r=>r.url().endsWith('/api/company/'+cid+'/improvements')&&r.request().method()==='POST');await page.getByRole('button',{name:'새 구조화 Version 저장·기업 확인 대기',exact:true}).click();const v2=await(await saving).json() as Version;expect(v2.ordinal).toBe(2);expect(v2.data.fact_version_ids).toEqual([factVersion.id]);expect(v2.data.analysis_basis?.source_version_id).toBe(v1.id);expect(v2.data.analysis_basis?.run_id).toBe(run.run.id);expect(v2.data.analysis_basis!.review_ids).toHaveLength(1);
 await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',v2.id);await expect(page.getByText('분석 입력: 제출 v1 · 현재 구조화 v2.',{exact:false})).toBeVisible();await expect(page.getByRole('button',{name:'기업이 확인한 개선요구 공식 확정',exact:true})).toBeDisabled();
 // Company validates the exact new version. No operator can create the company ACK.
 expect((await page.request.post('/api/company/improvements/'+v2.id+'/actions',{headers:{Origin:origin()},data:{action:'ACKNOWLEDGE',note:'TEST operator cannot impersonate company'}})).status()).toBe(403);
 await company.reload();await company.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();await company.locator('article[data-root-id="'+v1.improvement_id+'"]').getByRole('button',{name:'상세보기',exact:true}).click();const acknowledgment=company.getByRole('region',{name:'기업 구조화본 확인'});await expect(acknowledgment).toContainText('v2');await acknowledgment.getByLabel('구조화본 기업 확인 의견',{exact:true}).fill('TEST company checked the exact source-linked structured v2.');await acknowledgment.getByRole('checkbox',{name:'이 Version의 내용·연결 근거를 직접 확인했습니다.',exact:true}).check();await acknowledgment.getByRole('button',{name:'이 구조화 Version 기업 확인',exact:true}).click();await expect(company.getByRole('status').filter({hasText:'정확한 구조화 Version을 기업이 확인했습니다.'})).toBeVisible();
 await page.getByRole('button',{name:'대상·업무 다시 조회',exact:true}).click();await page.getByLabel('공식 확정 검토 의견',{exact:true}).fill('TEST operator confirmed source v1 and company-acknowledged structured v2; no automatic decision.');await expect(page.getByRole('button',{name:'기업이 확인한 개선요구 공식 확정',exact:true})).toBeEnabled();await page.getByRole('button',{name:'기업이 확인한 개선요구 공식 확정',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'정확한 개선요구 Version을 운영자가 확정했습니다.'})).toBeVisible();
 const final=await(await page.request.get('/api/company/'+cid)).json(),confirmed=final.improvements.find((r:{id:string})=>r.id===v1.improvement_id);expect(confirmed.state).toBe('CONFIRMED');expect(confirmed.versions[0].data).toEqual(v1Data);expect(confirmed.versions[1].reviews.map((r:{outcome:string})=>r.outcome)).toEqual(expect.arrayContaining(['ACKNOWLEDGE','CONFIRM']));
 const recommendation=await(await page.request.get('/api/capability/improvements/'+v2.id+'/recommendations')).json();expect(recommendation.context.improvement_version_id).toBe(v2.id);expect(recommendation.analysis_basis.source_version_id).toBe(v1.id);expect(recommendation.analysis_basis.run_id).toBe(run.run.id);
 expect(createHash('sha256').update(await(await page.request.get('/api/company/files/'+submitted.files[0].id+'/download')).body()).digest('hex')).toBe(digest);expect(await(await page.request.get('/api/company/'+cid+'/information-requests')).json()).toEqual([]);
 await page.reload();await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',v2.id);await expect(page.getByText('현재 확정된 개선요구입니다. 추천·구성의 입력으로 사용할 수 있습니다.',{exact:true})).toBeVisible();await companyContext.close();
});


test('text-only submission keeps exact literal source through reviewed structure, company ACK and recommendation',async({page,browser,playwright})=>{
 test.setTimeout(240000);
 const c=JSON.parse(process.env.DATCO_MVP_CONTEXT!);expect(c.nonce).toBe(process.env.DATCO_TEST_NONCE);
 const raw=JSON.parse(readFileSync(resolve('..','api','tests','fixtures','requirements_text_only.json'),'utf8')) as {as_is:string;to_be:string;constraints:string};
 const companyContext=await browser.newContext({baseURL:origin()}),company=await companyContext.newPage();
 await login(company,c.accounts.editor,c.password,'company');
 const prefix=String(Number(c.business_number.slice(0,9))+1).padStart(9,'0'),digits=[...prefix].map(Number),weights=[1,3,7,1,3,7,1,3,5];const number=prefix+String((10-(digits.reduce((sum,digit,i)=>sum+digit*weights[i],0)+Math.floor(digits[8]*5/10))%10)%10);
 const registered=await post(company.request,'',{name:'TEST text-only '+c.nonce,business_number:number,industry:'서비스'}),cid=registered.id;
 await post(company.request,'/'+cid+'/sites',{data:{name:'TEST text-only office',address:'TEST synthetic address',industry:'서비스',process:'주문·배정·출하'}});
 const admin=await playwright.request.newContext({baseURL:origin(),extraHTTPHeaders:{Origin:origin()}});
 expect((await admin.post('/api/notice/session',{data:{username:c.accounts.admin,password:c.password}})).ok()).toBe(true);
 await post(admin,'/'+cid+'/access',{username:c.accounts.operator});await post(admin,'/'+cid+'/access',{username:c.accounts.approver});await admin.dispose();
 await company.goto('/portal/company?company='+cid+'&screen=needs');await company.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();await company.getByRole('button',{name:'새 개선요구 작성',exact:true}).click();
 for(const [field,label] of [['as_is','현재 업무와 불편한 점'],['to_be','개선하고 싶은 모습'],['constraints','제약 및 확인 필요사항']] as const)await company.getByLabel(label,{exact:true}).fill(raw[field]);
 await company.getByRole('button',{name:'초안 저장',exact:true}).click();await expect(company.getByRole('status').filter({hasText:'개선요구 초안을 저장했습니다.'})).toBeVisible();
 await company.reload();await company.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();
 await company.getByRole('button',{name:'상세보기',exact:true}).click();await expect(company.getByText(raw.as_is,{exact:true}).first()).toBeVisible();
 await company.getByRole('button',{name:'DATCO에 제출',exact:true}).click();await expect(company.getByRole('status').filter({hasText:'DATCO에 제출했습니다.'})).toBeVisible();
 const submitted=await(await company.request.get('/api/company/'+cid)).json(),root=submitted.improvements[0],v1=root.versions[0] as Version;
 expect(root.state).toBe('SUBMITTED');expect(root.versions).toHaveLength(1);expect(submitted.files).toEqual([]);expect(v1.data.evidence_ids).toEqual([]);expect(v1.data).toMatchObject({...raw,problem:'',goal:''});const frozen=structuredClone(v1.data);
 await login(page,c.accounts.operator,c.password);await page.goto('/portal/operator?screen=improvement&company='+cid+'&version='+v1.id);
 const panel=page.getByTestId('improvement-analysis');await expect(panel.getByText('현재 입력에 활용 가능한 분석',{exact:true})).toBeVisible({timeout:60000});
 const run=(await(await page.request.get('/api/company/improvements/'+v1.id+'/analysis-runs')).json()).at(-1);
 expect(run.candidates.every((x:{category:string})=>x.category==='STRUCTURE')).toBe(true);
 expect(run.diagnostics.structured_result.structure.problems.some((x:{text:string})=>x.text.includes('어렵'))).toBe(true);
 expect(run.candidates.filter((x:{data:{subject:string}})=>x.data.subject==='required_functions').every((x:{data:{claim_kind:string;uncertainty:string}})=>x.data.claim_kind==='INFERRED'&&x.data.uncertainty.includes('확인 필요'))).toBe(true);
 await panel.getByText('상세 분석·근거·실행 이력',{exact:true}).click();await panel.getByText(/^분석 내용별 근거·검토 ·/).click();
 // Selection alone is not a saved review; use the existing summary-review action.
 await panel.getByRole('checkbox').first().check();
 const pending=(await(await page.request.get('/api/company/improvements/'+v1.id+'/analysis-runs')).json()).at(-1);expect(pending.candidates.every((x:{reviews:unknown[]})=>x.reviews.length===0)).toBe(true);
 await panel.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST literal source and bounded function hypotheses reviewed; no Fact or availability confirmation.');
 await panel.getByRole('button',{name:'요약 내용 확인 · 미검토 내용의 검토 기록 저장',exact:true}).click();await expect(panel.getByRole('button',{name:'요약 내용 확인 · 미검토 내용의 검토 기록 저장',exact:true})).toHaveCount(0);
 // The common note is not itself a submission decision; clear that unsaved draft before moving.
 await panel.getByLabel('운영자 검토 의견',{exact:true}).fill('');
 const reviewed=(await(await page.request.get('/api/company/improvements/'+v1.id+'/analysis-runs')).json()).at(-1);
 const reviewIds=reviewed.candidates.map((x:{reviews:{id:string}[]})=>x.reviews.at(-1)!.id).sort();
 await page.getByRole('button',{name:'이 개선요구의 구조화·서비스 추천 검토',exact:true}).click();
 await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',v1.id);
 await expect(page.getByRole('button',{name:'새 구조화 Version 저장·기업 확인 대기',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'검토한 분석 내용으로 요구사항 정리',exact:true}).click();
 await expect(page.getByLabel('공식 검토 현재 현황',{exact:true})).not.toHaveValue(raw.as_is);
 await expect(page.getByLabel('공식 검토 확인할 문제',{exact:true})).toHaveValue(/어렵/);
 await expect(page.getByLabel('공식 검토 개선 목표',{exact:true})).not.toHaveValue(await page.getByLabel('공식 검토 희망 개선 상태',{exact:true}).inputValue());
 await expect(page.getByLabel('공식 검토 필요 기능',{exact:true})).toHaveValue(/주문 접수·조회/);
 await expect(page.getByLabel('공식 검토 남은 확인사항',{exact:true})).toHaveValue('');
 const constraints=await page.getByLabel('공식 검토 제약',{exact:true}).inputValue();await page.getByRole('button',{name:'검토한 분석 내용으로 요구사항 정리',exact:true}).click();await expect(page.getByLabel('공식 검토 제약',{exact:true})).toHaveValue(constraints);
 await expect(page.getByRole('region',{name:'기업 제출 원문 진술 근거'})).toBeVisible();await page.screenshot({path:test.info().outputPath('reviewed-text-statement.png'),fullPage:true});
 // Unrelated company-input evidence is neither auto-selected nor required.
 expect(await page.getByRole('group',{name:'이 Version에 연결할 실제 근거',exact:true}).getByRole('checkbox',{checked:true}).count()).toBe(0);
 const saving=page.waitForResponse(r=>r.url().endsWith('/api/company/'+cid+'/improvements')&&r.request().method()==='POST');await page.getByRole('button',{name:'새 구조화 Version 저장·기업 확인 대기',exact:true}).click();const saved=await saving;expect(saved.ok()).toBe(true);const v2=await saved.json() as Version;
 expect(v2.ordinal).toBe(2);expect(v2.data.evidence_ids).toEqual([]);expect(v2.data.fact_version_ids).toEqual([]);expect(v2.data.analysis_basis).toMatchObject({run_id:run.run.id,source_version_id:v1.id});expect(v2.data.analysis_basis!.review_ids.toSorted()).toEqual(reviewIds);
 expect((await page.request.get('/api/capability/improvements/'+v2.id+'/recommendations')).status()).toBe(409);
 await company.reload();await company.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();await company.locator('article[data-root-id="'+v1.improvement_id+'"]').getByRole('button',{name:'상세보기',exact:true}).click();
 const ack=company.getByRole('region',{name:'기업 구조화본 확인'});await ack.getByText('기업이 제출한 원문 진술 · 제출 v1',{exact:true}).click();await expect(ack.getByText(raw.as_is,{exact:true}).first()).toBeVisible();
 await ack.getByLabel('구조화본 기업 확인 의견',{exact:true}).fill('TEST exact v2 structure compared with original v1 statement.');await ack.getByRole('checkbox',{name:'이 Version의 내용·연결 근거를 직접 확인했습니다.',exact:true}).check();await ack.getByRole('button',{name:'이 구조화 Version 기업 확인',exact:true}).click();await expect(company.getByRole('status').filter({hasText:'정확한 구조화 Version을 기업이 확인했습니다.'})).toBeVisible();
 await page.getByRole('button',{name:'대상·업무 다시 조회',exact:true}).click();await page.getByLabel('공식 확정 검토 의견',{exact:true}).fill('TEST exact reviewed and company-acknowledged structure, without objective Fact assertion.');
 const confirm=page.getByRole('button',{name:'기업이 확인한 개선요구 공식 확정',exact:true});await expect(confirm).toBeEnabled();
 const current=page.getByLabel('공식 검토 확인할 문제',{exact:true}),before=await current.inputValue();await current.fill(before+' TEST unsaved');await expect(confirm).toBeDisabled();await current.fill(before);await expect(confirm).toBeEnabled();
 await confirm.click();await expect(page.getByRole('status').filter({hasText:'정확한 개선요구 Version을 운영자가 확정했습니다.'})).toBeVisible();
 const final=await(await page.request.get('/api/company/'+cid)).json();expect(final.files).toEqual([]);expect(final.facts).toEqual([]);expect(final.improvements[0].state).toBe('CONFIRMED');expect(final.improvements[0].versions[0].data).toEqual(frozen);
 const recommended=await page.request.get('/api/capability/improvements/'+v2.id+'/recommendations');expect(recommended.ok()).toBe(true);const recommendations=await recommended.json();expect(recommendations.context.current_valid).toBe(true);expect(recommendations.analysis_basis.source_version_id).toBe(v1.id);
 await page.reload();await expect(page.getByText('현재 확정된 개선요구입니다. 추천·구성의 입력으로 사용할 수 있습니다.',{exact:true})).toBeVisible();await page.getByRole('navigation',{name:'운영자 업무 메뉴'}).getByRole('button',{name:'DATCO 서비스 추천',exact:true}).click();await expect(page.getByTestId('operator-mvp-workflow')).toHaveAttribute('data-version-id',v2.id);await expect(page.getByTestId('asset-solution-review')).toBeVisible();await page.screenshot({path:test.info().outputPath('confirmed-text-recommendation.png'),fullPage:true});await companyContext.close();
});
