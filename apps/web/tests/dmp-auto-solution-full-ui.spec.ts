import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {test,expect,type Page} from '@playwright/test';
test.use({actionTimeout:30000});
const data=()=>JSON.parse(process.env.DATCO_REACCEPTANCE_CONTEXT!);
const origin=()=>process.env.DATCO_E2E_BASE_URL!;
async function read(page:Page,path:string){const r=await page.request.get('/api/'+path,{maxRetries:2});expect(r.ok(),path).toBe(true);return r.json();}
async function login(page:Page,c:ReturnType<typeof data>,role:string){
 await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();
 await expect(page).toHaveURL(/\/portal\/(company|operator|admin)/);
}
async function menu(page:Page,label:string){await page.locator('aside').getByRole('button',{name:label,exact:true}).click();}
test('fresh DMP full UI: zero published capabilities, verified assets, generated composition and reviewed company proposal',async({browser})=>{
 test.setTimeout(720000);const c=data(),contexts=await Promise.all([0,1,2].map(()=>browser.newContext({baseURL:origin()})));
 const [company,operator,admin]=await Promise.all(contexts.map(context=>context.newPage()));
 for(const page of [company,operator,admin])page.on('dialog',d=>d.accept());
 try{
  await login(admin,c,'admin');const initial=await read(admin,'admin/overview');expect(initial.companies).toBe(0);expect(initial.published_capabilities).toBe(0);

  await login(company,c,'editor');expect((await read(company,'company')).length).toBe(0);await menu(company,'기업정보 등록 시작');
  await company.getByLabel('최초 등록 PDF 선택',{exact:true}).setInputFiles(c.registration_document);
  await expect(company.getByText('TEST-registration.pdf',{exact:true}).first()).toBeVisible();
  await company.getByRole('button',{name:'TEST-registration.pdf 선택 취소',exact:true}).click();await expect(company.getByText('새로 선택한 파일이 없습니다.',{exact:true})).toBeVisible();
  await company.getByLabel('최초 등록 PDF 선택',{exact:true}).setInputFiles(c.registration_document);
  await company.getByRole('button',{name:'문서 분석',exact:true}).click();await expect(company.getByLabel('등록 기업명',{exact:true})).toBeVisible({timeout:65000});
  // Human correction stays explicit; no OCR word substitution or silent acceptance.
  await company.getByLabel('등록 기업명',{exact:true}).fill(c.company_name);await company.getByLabel('등록 사업자등록번호',{exact:true}).fill(c.business_number);
  await company.getByLabel('등록 업태',{exact:true}).fill('제조업');await company.getByLabel('등록 종목',{exact:true}).fill('TEST 장비 제조 및 재고 관리');
  await company.getByRole('button',{name:'기업정보 등록',exact:true}).click();await expect(company.getByRole('heading',{name:'기업 · 사업장 관리',exact:true})).toBeVisible({timeout:60000});
  const cid=new URL(company.url()).searchParams.get('company')!;expect(cid).toBeTruthy();
  await company.reload();await expect(company.getByLabel('기업명',{exact:true})).toHaveValue(c.company_name);await expect(company.getByText(/사업장 1곳이 등록/)).toBeVisible();
  expect((await read(company,'company/'+cid)).sites).toHaveLength(1);
  await menu(company,'재무 · 사업이력');
  await company.getByLabel('재무 PDF 파일 선택 또는 끌어놓기',{exact:true}).setInputFiles(c.financial_documents);
  await expect(company.getByText('선택한 파일 2개',{exact:false})).toBeVisible();
  await company.getByRole('button',{name:'재무자료 분석',exact:true}).click();
  await expect(company.getByRole('button',{name:'재무정보 저장',exact:true})).toBeVisible({timeout:60000});
  const savingFinance=company.waitForResponse(r=>new URL(r.url()).pathname==='/api/company/'+cid+'/profile'&&r.request().method()==='POST');
  await company.getByRole('button',{name:'재무정보 저장',exact:true}).click();expect((await savingFinance).ok()).toBe(true);
  await company.reload();const finances=(await read(company,'company/'+cid)).inputs.at(-1).data.financials;
  expect(finances.map((f:{year:number})=>f.year).sort()).toEqual([2023,2024]);expect(finances.every((f:{source_parse_id:string})=>!!f.source_parse_id)).toBe(true);
  // The admin grants actual scope through the UI after the company exists.
  await admin.reload();await admin.getByRole('navigation',{name:'관리자 업무 바로가기'}).getByRole('button',{name:'2. 사용자·기업 접근권한',exact:true}).click();
  for(const role of ['operator','approver']){
   await admin.getByLabel('접근권한 대상 계정',{exact:true}).selectOption(c.accounts[role]);await admin.getByLabel('접근권한 허용 기업',{exact:true}).selectOption(cid);
   await expect(admin.getByRole('button',{name:'선택한 기업 접근권한 부여',exact:true})).toBeEnabled();await admin.getByRole('button',{name:'선택한 기업 접근권한 부여',exact:true}).click();
   await expect(admin.getByText('선택한 계정은 이미 이 기업에 접근할 수 있습니다.',{exact:true})).toBeVisible();
   await expect(admin.getByRole('button',{name:'선택한 기업 접근권한 부여',exact:true})).toBeDisabled();
  }
  // Only source inputs exist. Management and verification are explicit UI actions.
  const originalImport=await read(admin,'capability/features?limit=100');
  expect(originalImport.total).toBe(2);expect((await read(admin,'capability/catalog')).length).toBe(0);
  const capabilityWrites:string[]=[];admin.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname.startsWith('/api/capability/catalog'))capabilityWrites.push(r.url());});
  await admin.getByRole('navigation',{name:'관리자 메뉴'}).getByRole('button',{name:'기준정보·버전',exact:true}).click();
  const assetPanel=admin.getByTestId('dmp-assets');await expect(assetPanel.getByRole('heading',{name:'DMP 기술자산 관리',exact:true})).toBeVisible();
  async function saveAsset(){
   const response=admin.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/capability/assets');
   await admin.getByRole('button',{name:'기술자산 저장',exact:true}).click();const saved=await response;expect(saved.ok(),await saved.text()).toBe(true);
   await expect(admin.getByRole('status').filter({hasText:'기술자산 v1을 저장'})).toBeVisible();return saved.json();
  }
  async function verifySynthetic(){
   await admin.getByLabel('등록 기술자산 제공 상태',{exact:true}).selectOption('VERIFIED');
   await expect(admin.getByRole('button',{name:'기술자산 저장',exact:true})).toBeDisabled();
   await admin.getByLabel('제공 검증 근거',{exact:true}).fill('TEST isolated synthetic provision evidence for this exact release; not an actual DMP delivery assurance.');
  }
  const assetSystemName='TEST 합성 창고 시스템 '+c.nonce;
  await admin.getByRole('button',{name:'새 시스템 등록',exact:true}).click();
  await admin.getByLabel('기술자산 이름',{exact:true}).fill(assetSystemName);
  await admin.getByLabel('기술자산 설명',{exact:true}).fill('TEST 합성 창고의 입출고 이력과 재고 조회 정보를 관리하는 시험 시스템');
  await admin.getByLabel('실제 수행 역할',{exact:true}).fill('TEST 창고 1곳의 재고·입출고 기록 관리');
  await admin.getByLabel('개발·배포 릴리스',{exact:true}).fill('TEST-release-1');await verifySynthetic();const assetSystem=await saveAsset();
  const assetModuleName='TEST 합성 재고·입출고 모듈 '+c.nonce;
  await admin.getByRole('button',{name:'새 모듈 등록',exact:true}).click();
  await admin.getByLabel('기술자산 상위 항목',{exact:true}).selectOption(assetSystem.id);
  await admin.getByLabel('기술자산 이름',{exact:true}).fill(assetModuleName);
  await admin.getByLabel('기술자산 설명',{exact:true}).fill('TEST 입출고 이력과 재고 현황을 함께 기록·조회하는 단독 시험 모듈');
  await admin.getByLabel('실제 수행 역할',{exact:true}).fill('TEST 입고·출고와 재고 수량 현황 기록 및 조회');
  await admin.getByLabel('기술자산 적용 업무',{exact:true}).fill('창고 재고 관리\n입출고 관리');
  await admin.getByLabel('개발·배포 릴리스',{exact:true}).fill('TEST-release-1');await verifySynthetic();const assetModule=await saveAsset();
  const assetFeatures:{id:string;version_id:string;ordinal:number}[]=[];
  for(const feature of c.source_features){
   const row=assetPanel.locator('tr[data-asset-id="'+feature.id+'"]');
   await row.getByRole('button',{name:'기술자산 상세·이력',exact:true}).click();
   await admin.getByRole('button',{name:'이 원천 기능을 관리 등록',exact:true}).click();
   await admin.getByLabel('기술자산 상위 항목',{exact:true}).selectOption(assetModule.id);
   await expect(admin.getByLabel('기술자산 이름',{exact:true})).toHaveValue(feature.name);
   await admin.getByLabel('기술자산 설명',{exact:true}).fill(feature.name+' — TEST 창고 1곳의 입출고 이력·재고 수량을 기록하고 통합 조회하는 합성 기능. 실제 납품 확약이 아님.');
   await admin.getByLabel('실제 수행 역할',{exact:true}).fill(feature.name+'의 기록·조회 역할');
   await admin.getByLabel('기술자산 적용 업무',{exact:true}).fill('재고 관리\n입출고 이력 관리');
   await admin.getByLabel('기술자산 해결 가능한 문제',{exact:true}).fill('창고 수기·엑셀 입출고 관리\n재고 불일치 확인\n입출고 이력 통합과 중복 입력 감소');
   await admin.getByLabel('기술자산 적용조건',{exact:true}).fill('TEST 승인된 합성 창고 1곳과 시험 데이터에 한정. 비용·일정은 별도 확인.');
   await admin.getByLabel('개발·배포 릴리스',{exact:true}).fill('TEST-release-1');
   await verifySynthetic();const managed=await saveAsset();assetFeatures.push(managed);
   const stored=await read(admin,'capability/assets/'+managed.id);
   expect(stored.current.availability).toBe('VERIFIED');
   expect(stored.source_revisions[0].id).toBe(feature.revision_id);
  }
  expect((await read(admin,'admin/overview')).published_capabilities).toBe(0);
  expect(await read(admin,'capability/catalog')).toEqual([]);expect(capabilityWrites).toEqual([]);
  const preservedImport=await read(admin,'capability/features?limit=100');
  expect(preservedImport.import).toEqual(originalImport.import);expect(preservedImport.items).toEqual(originalImport.items);
  console.log('ASSET_FULL_UI_STAGE: verified_assets_zero_capabilities');
  await menu(company,'개선요구 등록');await company.getByRole('button',{name:'새 개선요구 작성',exact:true}).click();
  const asIs='창고 입출고 내역을 엑셀과 수기로 관리하고, 재고 수량이 실제 재고와 일치하지 않는 경우가 발생합니다.';
  const goal='입출고 이력과 재고정보를 통합 관리하고, 데이터 입력 중복을 줄여 재고 현황을 신속하게 확인하는 것입니다.';
  await company.getByLabel('현재 업무와 불편한 점',{exact:true}).fill(asIs);await company.getByLabel('개선하고 싶은 모습',{exact:true}).fill(goal);
  await company.getByLabel('제약 및 확인 필요사항',{exact:true}).fill('TEST 실제 연계·비용·일정은 검토 필요');
  await company.getByLabel('개선요구 관련파일 선택',{exact:true}).setInputFiles(c.demand_document);await company.getByRole('button',{name:'DATCO에 제출',exact:true}).click();
  await expect(company.getByRole('status').filter({hasText:'DATCO에 제출했습니다.'})).toBeVisible();
  let detail=await read(company,'company/'+cid),root=detail.improvements[0];const v1=root.versions[0];
  await login(operator,c,'operator');await operator.goto('/portal/operator?screen=facts&company='+cid);
  const inputs=await read(company,'company/'+cid);
  for(const field of ['company_name','industry']){
   const candidate=inputs.candidates.find((x:{id:string;field:string;acknowledgements:{agreed:boolean}[]})=>x.field===field&&x.acknowledgements.at(-1)?.agreed);
   expect(candidate,'registered, explicitly company-confirmed source '+field).toBeTruthy();
   const entry=operator.locator('details[data-candidate-id="'+candidate.id+'"]');await entry.locator(':scope > summary').click();
   await entry.getByLabel(field+' Fact 검토 의견',{exact:true}).fill('TEST 등록 당시 기업이 확인한 값과 원본을 검토했습니다.');
   const savingFact=operator.waitForResponse(r=>r.url().endsWith('/candidates/'+candidate.id+'/review')&&r.request().method()==='POST');
   await entry.getByRole('button',{name:'Fact 검토 기록 저장',exact:true}).click();expect((await savingFact).ok()).toBe(true);
  }
  await menu(operator,'업무 대시보드');await operator.getByRole('button',{name:'신규 접수·검토 필요 목록',exact:true}).click();
  // A dashboard work counter is a button, not a static duplicate total.
  const row=operator.locator('tr[data-version-id="'+v1.id+'"]');await row.getByRole('button').click();
  await expect(operator.getByRole('region',{name:'요구사항 분석 요약'})).toBeVisible({timeout:65000});
  let runs=await read(operator,'company/improvements/'+v1.id+'/analysis-runs'),run=runs.at(-1);
  expect(run.candidates.filter((x:{category:string;content:string})=>x.category==='STRUCTURE'&&x.content===goal)).toHaveLength(1);
  expect(run.diagnostics.structured_result.structure.required_functions.length).toBeGreaterThan(0);
  await operator.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST 원문 역할과 근거를 확인했습니다. 기능은 추론 후보로 검토합니다.');
  const question=run.candidates.find((x:{category:string;data:{rule_id:string}})=>x.category==='MISSING_INFORMATION'&&x.data.rule_id==='R04');
  expect(question,'scope actually absent in the submitted case').toBeTruthy();
  await operator.locator('[data-candidate-id="'+question.id+'"]').getByRole('checkbox').check();
  const creatingDraft=operator.waitForResponse(r=>new URL(r.url()).pathname==='/api/company/analysis-drafts'&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'보완요청 작성',exact:true}).click();expect((await creatingDraft).ok()).toBe(true);
  await expect(operator.getByLabel('보완자료 요청 제목',{exact:true})).toBeVisible({timeout:30000});
  const drafts=await read(operator,'company/improvements/'+v1.id+'/analysis-drafts');expect(drafts).toHaveLength(1);
  expect(await read(company,'company/'+cid+'/information-requests')).toHaveLength(0);
  await operator.reload();
  if(!await operator.getByLabel('보완자료 요청 제목',{exact:true}).isVisible()){
   await operator.getByRole('button',{name:new RegExp(drafts[0].versions.at(-1).title.replace(/[.*+?^$()|[\]\\]/g,'\\$&'))}).first().click();
  }
  const sendRequest=operator.getByRole('button',{name:'수요기업에 보완요청 보내기',exact:true});
  await sendRequest.click();await operator.keyboard.press('Escape');
  expect(await read(company,'company/'+cid+'/information-requests')).toHaveLength(0);
  await sendRequest.click();const requestDialog=operator.getByRole('dialog',{name:'보완요청 발송 전 확인',exact:true});
  const delivered=operator.waitForResponse(r=>r.url().endsWith('/analysis-drafts/'+drafts[0].id+'/send')&&r.request().method()==='POST');
  await requestDialog.getByRole('button',{name:'수요기업에 발송하기',exact:true}).evaluate(el=>{(el as HTMLButtonElement).click();(el as HTMLButtonElement).click();});
  expect((await delivered).ok()).toBe(true);
  const requests=await read(company,'company/'+cid+'/information-requests');expect(requests).toHaveLength(1);const request=requests[0];
  await menu(company,'보완 요청함');const reply=company.locator('[data-request-id="'+request.id+'"]');
  await reply.getByLabel('보완 답변',{exact:true}).fill('적용 범위: 본사 창고 1개 사업장의 입고·출고와 재고 조회입니다.\n현재 재고 불일치는 월말 실사로 측정하며 오차율은 8%입니다.\n기존 시스템: 엑셀과 수기 기록입니다. 예산은 미정입니다.');
  const responded=company.waitForResponse(r=>r.url().endsWith('/information-requests/'+request.id+'/responses')&&r.request().method()==='POST');
  await reply.getByRole('button',{name:'보완답변 제출',exact:true}).click();expect((await responded).ok()).toBe(true);
  await menu(operator,'보완자료 요청');await operator.locator('tr[data-request-id="'+request.id+'"]').getByRole('button',{name:'기업 답변 검토',exact:true}).click();
  const reviewReply=operator.getByRole('region',{name:'운영자 답변 판단',exact:true});
  await reviewReply.getByLabel('확인 또는 재보완 사유',{exact:true}).fill('TEST 같은 기업·제출본의 답변을 확인했습니다. 기업정보 자동 확정은 하지 않습니다.');
  const verified=operator.waitForResponse(r=>r.url().endsWith('/information-requests/'+request.id+'/review')&&r.request().method()==='POST');
  await reviewReply.getByRole('button',{name:'확인 완료',exact:true}).click();expect((await verified).ok()).toBe(true);
  await operator.goto('/portal/operator?screen=improvement&company='+cid+'&version='+v1.id);
  await expect.poll(async()=>(await read(operator,'company/improvements/'+v1.id+'/analysis-runs')).length,{timeout:65000}).toBe(2);
  runs=await read(operator,'company/improvements/'+v1.id+'/analysis-runs');run=runs.at(-1);
  expect(run.candidates.some((x:{data:{rule_id:string};category:string})=>x.category==='MISSING_INFORMATION'&&x.data.rule_id==='R04')).toBe(false);
  expect(runs[0].candidates.some((x:{reviews:unknown[]})=>x.reviews.length>0)).toBe(true);
  await expect(operator.getByRole('button',{name:'요약 내용 확인 · 미검토 내용의 검토 기록 저장',exact:true})).toBeVisible();
  await operator.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST 검토한 기업 답변을 포함한 최신 원문·기능 후보를 확인했습니다.');
  await operator.getByRole('button',{name:'요약 내용 확인 · 미검토 내용의 검토 기록 저장',exact:true}).click();
  await expect(operator.getByRole('button',{name:'요약 내용 확인 · 미검토 내용의 검토 기록 저장',exact:true})).toHaveCount(0,{timeout:60000});
  const completingReview=operator.waitForResponse(r=>r.url().endsWith('/improvements/'+v1.id+'/submission-reviews')&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'검토 완료 — 추가 보완요청 없음',exact:true}).click();expect((await completingReview).ok()).toBe(true);
  await expect(operator.getByLabel('업무 상태 필터',{exact:true})).toBeVisible();await operator.getByLabel('업무 상태 필터',{exact:true}).selectOption('COMPLETED');
  await operator.locator('tr[data-version-id="'+v1.id+'"]').getByRole('button').click();
  await operator.getByRole('button',{name:'이 개선요구의 구조화·서비스 추천 검토',exact:true}).click();
  await operator.getByRole('button',{name:'검토한 분석 내용으로 요구사항 정리',exact:true}).click();
  await expect(operator.getByLabel('공식 검토 필요 기능',{exact:true})).not.toHaveValue('');
  // The operator reads remaining rule/processing uncertainty. It stays explicit
  // in the structured constraints and later scoped technical review; it is not a fact
  // or a silently fulfilled requirement. Required scope is from the verified reply.
  const remaining=await operator.getByLabel('공식 검토 남은 확인사항',{exact:true}).inputValue();
  const constraints=operator.getByLabel('공식 검토 제약',{exact:true});
  await constraints.fill((await constraints.inputValue())+'\nTEST 운영자 검토: 답변의 창고 1곳·현재 재고 측정값을 확인. 예산·일정 및 자료 한계는 미확정으로 제안 범위에 명시한다.\n'+remaining);
  await operator.getByLabel('공식 검토 남은 확인사항',{exact:true}).fill('');
  const facts=operator.getByRole('group',{name:'확정된 기업정보 선택',exact:true});
  for(const checkbox of await facts.getByRole('checkbox').all())await checkbox.check();
  const savingStructure=operator.waitForResponse(r=>new URL(r.url()).pathname==='/api/company/'+cid+'/improvements'&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'새 구조화 Version 저장·기업 확인 대기',exact:true}).click();
  const structured=await savingStructure;expect(structured.ok(),await structured.text()).toBe(true);
  const structuredVersion=await structured.json();await expect(operator).toHaveURL(new RegExp('version='+structuredVersion.id));
  await expect(operator.getByRole('button',{name:'기업이 확인한 개선요구 공식 확정',exact:true})).toBeDisabled();
  detail=await read(company,'company/'+cid);root=detail.improvements[0];const v2=root.versions.at(-1);expect(v2.ordinal).toBe(2);expect(v1.id).not.toBe(v2.id);
  await company.reload();await menu(company,'개선요구 등록');await company.locator('article[data-root-id="'+root.id+'"]').getByRole('button',{name:'상세보기',exact:true}).click();
  const ack=company.getByRole('region',{name:'기업 구조화본 확인'});
  await ack.getByLabel('구조화본 기업 확인 의견',{exact:true}).fill('TEST 정리된 내용과 원문 근거를 확인했습니다.');
  await ack.getByRole('checkbox',{name:'이 Version의 내용·연결 근거를 직접 확인했습니다.',exact:true}).check();
  await ack.getByRole('button',{name:'이 구조화 Version 기업 확인',exact:true}).click();
  await operator.reload();await operator.getByLabel('공식 확정 검토 의견',{exact:true}).fill('TEST 기업의 정확한 작성본 확인과 연결된 근거를 검토했습니다.');
  const confirmed=operator.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/company/improvements/'+v2.id+'/actions'));
  await operator.getByRole('button',{name:'기업이 확인한 개선요구 공식 확정',exact:true}).click();
  const confirmResponse=await confirmed;expect(confirmResponse.status(),await confirmResponse.text()).toBe(200);
  await expect.poll(async()=>(await read(company,'company/'+cid)).improvements[0].state).toBe('CONFIRMED');
  await operator.screenshot({path:test.info().outputPath('fresh-reviewed-confirmed.png'),fullPage:true});
  expect((await read(company,'company/'+cid)).improvements[0].state).toBe('CONFIRMED');
  console.log('FRESH_UI_STAGE: confirmed');
  const auto=operator.getByTestId('asset-solution-review');
  await expect(auto.getByRole('heading',{name:'기업 요구에 맞는 시스템·모듈 추천',exact:true})).toBeVisible();
  expect(await read(operator,'capability/improvements/'+v2.id+'/asset-solutions')).toEqual([]);
  expect(await read(operator,'capability/catalog')).toEqual([]);
  expect((await read(operator,'workspace')).compositions).toEqual([]);
  const generating=operator.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/capability/improvements/'+v2.id+'/asset-solutions');
  await auto.getByRole('button',{name:'자동 추천 구성안 생성',exact:true}).click();
  const generatedResponse=await generating;expect(generatedResponse.ok(),await generatedResponse.text()).toBe(true);const generated=await generatedResponse.json();
  expect(generated.current_valid).toBe(true);expect(generated.improvement_version_id).toBe(v2.id);
  expect(generated.data.candidates.length).toBeGreaterThan(0);
  const solutionProof=test.info().outputPath('synthetic-asset-solution.json');
  await writeFile(solutionProof,JSON.stringify(generated.data,null,2));
  await test.info().attach('synthetic-asset-solution', {path:solutionProof,contentType:'application/json'});
  const alternative=generated.data.alternatives.find((a:{modules:{id:string}[];feature_selections:unknown[];coverage:{feature_revision_ids:string[]}[]})=>a.modules.length===1&&a.modules[0].id===assetModule.id&&a.feature_selections.length===2&&a.coverage.every(row=>row.feature_revision_ids.length>0));
  expect(alternative,'verified single module must cover this synthetic warehouse demand').toBeTruthy();
  expect(alternative.integrations).toEqual([]);expect(alternative.features.every((f:{availability:string})=>f.availability==='VERIFIED')).toBe(true);
  expect(alternative.coverage.every((row:{role:string;addressed_scope:string;unaddressed_scope:string;missing_information:string[];status:string})=>row.role.trim()&&row.addressed_scope.trim()&&row.unaddressed_scope.trim()&&row.missing_information.length&&row.status==='PARTIAL')).toBe(true);
  for(const a of generated.data.alternatives.slice(0,2))await auto.locator('article[data-alternative-id="'+a.id+'"]').getByRole('checkbox',{name:a.name+' 비교',exact:true}).check();
  await expect(auto.getByRole('region',{name:'추천 구성안 비교',exact:true})).toBeVisible();
  await auto.locator('article[data-alternative-id="'+alternative.id+'"]').getByRole('button',{name:'이 구성안 검토',exact:true}).click();
  await expect(auto.getByLabel('기술자산 조합 이름',{exact:true})).toHaveValue(alternative.name);
  const prefilledRoles=auto.getByLabel(/^자산 해결범위 \d+ 수행 역할$/);expect(await prefilledRoles.count()).toBe(alternative.coverage.length);
  for(const input of await prefilledRoles.all())expect((await input.inputValue()).trim()).not.toBe('');
  await expect(auto.getByRole('button',{name:'검토한 기술자산 조합 저장',exact:true})).toBeDisabled();
  expect((await read(operator,'workspace')).compositions).toEqual([]);
  await operator.reload();await expect(operator.getByLabel('기술자산 조합 이름',{exact:true})).toHaveValue(alternative.name);
  for(let index=0;index<alternative.coverage.length;index++){
   const n=index+1,row=alternative.coverage[index];
   await operator.getByLabel('자산 해결범위 '+n+' 수행 역할',{exact:true}).fill(row.role+' · TEST 합성 제공 근거와 동일 창고 범위를 운영자가 확인');
   await operator.getByLabel('자산 해결범위 '+n+' 설명',{exact:true}).fill('TEST 제공 검증된 합성 입출고·재고 기능으로 창고 1곳의 다음 범위를 확인: '+row.requirement);
   await operator.getByLabel('자산 해결범위 '+n+' 제외·미해결 범위',{exact:true}).fill('');
   await operator.getByLabel('자산 해결범위 '+n+' 추가 확인사항',{exact:true}).fill('');
   await operator.getByLabel('자산 해결범위 '+n+' 해결 상태',{exact:true}).selectOption('ADDRESSED');
  }
  await operator.getByLabel('기술자산 조합 이름',{exact:true}).fill('TEST 자동 생성 단독 구성 '+c.nonce);
  await operator.getByLabel('자산 구성 미해결 사항',{exact:true}).fill('');
  await operator.getByLabel('기술자산 조합 검토 의견',{exact:true}).fill('TEST 제공 검증된 정확한 시스템·모듈·기능 버전과 합성 원문을 대조했습니다. 창고 1곳의 기록·조회 범위만 확인했으며 비용·일정이나 실제 고객 성과를 확정하지 않습니다.');
  await operator.getByRole('checkbox',{name:'기술자산 조합 근거·제공상태·연계 검토',exact:true}).check();
  const savingAsset=operator.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/capability/compositions');
  await expect(operator.getByRole('button',{name:'검토한 기술자산 조합 저장',exact:true})).toBeEnabled();
  await operator.getByRole('button',{name:'검토한 기술자산 조합 저장',exact:true}).click();const savedAssetResponse=await savingAsset;expect(savedAssetResponse.ok(),await savedAssetResponse.text()).toBe(true);const composite=await savedAssetResponse.json();
  await expect(operator.getByRole('status').filter({hasText:'검토한 기술자산 조합 v1을 저장'})).toBeVisible();
  const history=await read(operator,'capability/compositions/'+composite.id);
  expect(history.versions).toHaveLength(1);expect(history.versions[0].data.source_mode).toBe('DMP_ASSET');expect(history.versions[0].data.capability_version_ids).toEqual([]);
  expect(history.versions[0].data.asset_basis).toEqual({recommendation_id:generated.id,alternative_id:alternative.id});
  expect(history.versions[0].data.asset_selections).toHaveLength(2);expect(history.versions[0].data.coverage.every((row:{status:string})=>row.status==='ADDRESSED')).toBe(true);
  expect(history.versions[0].data.asset_integrations).toEqual([]);
  expect((await read(admin,'admin/overview')).published_capabilities).toBe(0);expect(capabilityWrites).toEqual([]);
  await operator.reload();await expect(operator.getByRole('button',{name:'검토한 기술자산 조합 새 버전 저장',exact:true})).toBeVisible();
  const afterReload=await read(operator,'capability/compositions/'+composite.id);expect(afterReload.versions[0]).toEqual(history.versions[0]);
  console.log('ASSET_FULL_UI_STAGE: generated_prefilled_reviewed_composition');
  await operator.getByRole('button',{name:'이 조합의 지원사업 검토·매칭',exact:true}).click();
  await operator.locator('tr[data-notice-id="'+c.notice.id+'"]').getByRole('button',{name:'이 공고 원문·요건 검토',exact:true}).click();
  const analysingNotice=operator.waitForResponse(r=>new URL(r.url()).pathname==='/api/notice/analysis'&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'이 공고의 기존 요건 분석 실행',exact:true}).click();expect((await analysingNotice).ok()).toBe(true);
  await expect.poll(async()=>{const n=await read(operator,'notice/'+c.notice.id);return n.versions.find((v:{id:string})=>v.id===c.notice.version_id).runs.length;},{timeout:65000}).toBe(1);
  const clause=operator.locator('[data-notice-candidate-id]').filter({hasText:'Manufacturing'}).first();
  await expect(clause).toBeVisible();await clause.getByRole('checkbox',{name:'원문과 이 요건의 실제 근거를 확인했습니다.',exact:true}).check();
  await clause.getByLabel('요건 검토 의견',{exact:true}).fill('TEST 합성 제조기업 대상 요건의 원문만 검토했습니다. 전체 신청자격 확정이 아닙니다.');
  const reviewingNotice=operator.waitForResponse(r=>r.url().includes('/api/notice/candidates/')&&r.url().endsWith('/confirm')&&r.request().method()==='POST');
  await clause.getByRole('button',{name:'이 요건의 근거 검토 저장',exact:true}).click();const noticeReview=await reviewingNotice;expect(noticeReview.ok()).toBe(true);const requirement=await noticeReview.json();
  await operator.getByLabel('매칭 공고 요건 Version',{exact:true}).selectOption(requirement.id);
  await operator.getByLabel('매칭 서비스 조합 Version',{exact:true}).selectOption(composite.version_id);
  const matching=operator.waitForResponse(r=>new URL(r.url()).pathname==='/api/capability/matches'&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'선택한 3개 입력으로 매칭 후보 생성',exact:true}).click();const matched=await matching;expect(matched.ok(),await matched.text()).toBe(true);const match=await matched.json();
  const prep=await read(operator,'capability/matches/'+match.candidate_id+'/proposal-preparation');expect(prep.review_evidence.length).toBeGreaterThan(0);
  for(const task of prep.review_tasks){
   await operator.getByLabel(task.id+' 검토 의견',{exact:true}).fill('TEST 정확한 기업 확인자료와 선택 요건 및 제공범위를 사람이 검토했습니다. 실제 사업자격 확정이 아닙니다.');
   await operator.getByLabel(task.id+' 현재 확정 근거',{exact:true}).selectOption(prep.review_evidence[0].id);
  }
  await operator.getByLabel('매칭 전체 검토 의견',{exact:true}).fill('TEST 선택 요건과 부분 서비스 범위의 제안 가능성만 검토. 실제 신청 전 공급자격·연계·비용 확인 필요.');
  const reviewingMatch=operator.waitForResponse(r=>r.url().endsWith('/matches/'+match.candidate_id+'/review')&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'근거 검토 완료·제안 가능 판단',exact:true}).click();expect((await reviewingMatch).ok()).toBe(true);
  await operator.getByRole('button',{name:'동일 대상의 제안서 작성',exact:true}).click();
  await operator.getByLabel('제안서 매칭 후보',{exact:true}).selectOption(match.candidate_id);
  const proposalTitle='TEST 전체 화면 제안 '+c.nonce;await operator.getByLabel('표준 제안서 제목',{exact:true}).fill(proposalTitle);
  console.log('FRESH_UI_STAGE: matching_reviewed');
  const creatingProposal=operator.waitForResponse(r=>new URL(r.url()).pathname==='/api/proposal'&&r.request().method()==='POST');
  await operator.getByRole('button',{name:'표준 16개 항목 제안 초안 생성',exact:true}).click();const proposalResponse=await creatingProposal;expect(proposalResponse.ok(),await proposalResponse.text()).toBe(true);const proposal=await proposalResponse.json();
  await expect(operator.getByRole('heading',{name:proposalTitle+' · v1',exact:true})).toBeVisible();
  const proposalVersion=(await read(operator,'proposal/'+proposal.proposal_id)).versions[0];
  expect(proposalVersion.sections).toHaveLength(16);expect(proposalVersion.manifest.template_version).toBe('MVP_16');
  expect(proposalVersion.manifest.refs.composition_version_id).toBe(composite.version_id);
  expect(proposalVersion.manifest.asset_review.basis).toEqual({recommendation_id:generated.id,alternative_id:alternative.id});
  expect(proposalVersion.manifest.asset_features).toHaveLength(2);
  expect(proposalVersion.manifest.refs.asset_version_ids).toEqual(expect.arrayContaining(assetFeatures.map(feature=>feature.version_id)));
  const proposalBody=proposalVersion.sections.map((section:{body:string})=>section.body).join('\n');
  expect(proposalBody).toContain(assetSystemName);expect(proposalBody).toContain(assetModuleName);
  for(const feature of c.source_features)expect(proposalBody).toContain(feature.name);
  await operator.getByLabel('제안내용 검토 의견',{exact:true}).fill('TEST 16개 항목과 실제 제공범위·미확정 비용 및 일정을 원문과 대조했습니다.');
  await operator.getByRole('button',{name:'이 Version 제안내용 확인',exact:true}).click();
  for(const kind of ['DOCX','PDF']){
   await operator.getByRole('button',{name:kind+' 파일 생성',exact:true}).click();
   const link=operator.getByRole('link',{name:'v1 '+kind+' 다운로드',exact:true});await expect(link).toBeVisible();
   const downloading=operator.waitForEvent('download');await link.click();const download=await downloading;
   const path=test.info().outputPath('TEST-full-ui.'+kind.toLowerCase());await download.saveAs(path);
   const record=(await read(operator,'proposal/'+proposal.proposal_id)).files.find((f:{kind:string;version_id:string})=>f.kind===kind&&f.version_id===proposal.version_id);
   expect(createHash('sha256').update(await readFile(path)).digest('hex')).toBe(record.digest);
  }
  await operator.getByLabel('기업 제안 검토 방식',{exact:true}).selectOption('COMPANY_RECORDED_AUTHORIZATION');
  await operator.getByLabel('전달할 기업 담당자 아이디',{exact:true}).fill(c.accounts.editor);
  await operator.getByRole('button',{name:'기업 담당자 확인',exact:true}).click();
  const open=operator.getByRole('button',{name:'기업 전달·검토 요청 확인',exact:true});await expect(open).toBeEnabled();
  await open.click();await operator.keyboard.press('Escape');expect((await read(operator,'proposal/'+proposal.proposal_id)).requests).toHaveLength(0);
  await open.click();const dialog=operator.getByRole('dialog',{name:'정확한 제안서 Version을 기업에 전달하시겠습니까?',exact:true});
  const sendingProposal=operator.waitForResponse(r=>r.url().endsWith('/versions/'+proposal.version_id+'/approval')&&r.request().method()==='POST');
  await dialog.getByRole('button',{name:'최종 확인·기업 검토 요청',exact:true}).evaluate(el=>{(el as HTMLButtonElement).click();(el as HTMLButtonElement).click();});expect((await sendingProposal).ok()).toBe(true);
  expect((await read(operator,'proposal/'+proposal.proposal_id)).requests).toHaveLength(1);
  await company.reload();await menu(company,'받은 제안서');
  await company.getByRole('heading',{name:proposalTitle,exact:true}).locator('..').getByRole('button',{name:'제안서 본문 확인',exact:true}).click();
  await expect(company.getByText('이 전달 Version의 본문 16개 항목',{exact:true})).toBeVisible();
  await company.getByLabel('검토 의견·수정 요청사항',{exact:true}).fill('TEST 제공범위와 연계 조건의 설명을 보완해 주세요.');
  const revision=company.waitForResponse(r=>r.url().includes('/proposal/approvals/')&&r.url().endsWith('/decision')&&r.request().method()==='POST');
  await company.getByRole('button',{name:'제안서 수정 요청',exact:true}).click();expect((await revision).ok()).toBe(true);
  await company.reload();await expect(company.getByText(/REVISION_REQUEST · TEST 제공범위/)).toBeVisible();
  expect((await read(admin,'admin/overview')).published_capabilities).toBe(0);expect(capabilityWrites).toEqual([]);
  const final=await read(operator,'proposal/'+proposal.proposal_id);expect(final.decisions[0].outcome).toBe('REVISION_REQUEST');expect(final.files).toHaveLength(2);expect(final.versions[0].id).toBe(proposal.version_id);
  await company.screenshot({path:test.info().outputPath('full-ui-company-revision.png'),fullPage:true});
  await operator.screenshot({path:test.info().outputPath('full-ui-delivered-proposal.png'),fullPage:true});
 }finally{await Promise.all(contexts.map(context=>context.close()));}
});
