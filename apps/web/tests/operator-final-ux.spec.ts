import {test,expect,Page} from '@playwright/test';
type Playwright={request:typeof import('@playwright/test').request};
import {randomUUID} from 'node:crypto';
import {readFile} from 'node:fs/promises';
const fixture=()=>{const c=JSON.parse(process.env.DATCO_HANDOFF_CONTEXT!);return {...c,accounts:{...c.accounts,editor:c.accounts.slice1_editor,operator:c.accounts.slice1_operator,admin:c.accounts.slice1_admin}};};
async function login(page:Page,label='operator',keep=false){const c=fixture();if(!keep)await page.goto('/login');else await page.waitForLoadState('load');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[label]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(new RegExp('/portal/'+(label==='editor'?'company':'operator')));}
async function setup(page:Page,playwright:Playwright,options:{neutral?:boolean;unsupported?:boolean}={}){
 const c=fixture(),tag=randomUUID(),origin=process.env.DATCO_E2E_BASE_URL!;
 await login(page,'editor');
 const post=async(path:string,data:unknown)=>{const r=await page.request.post('/api/company'+path,{headers:{Origin:origin},data});expect(r.ok(),await r.text()).toBe(true);return r.json();};
 const digits=String(Math.floor(100000000+Math.random()*899999999)).split('').map(Number),weights=[1,3,7,1,3,7,1,3,5],sum=digits.reduce((n,d,i)=>n+d*weights[i],0)+Math.floor(digits[8]*5/10),number=digits.join('')+String((10-sum%10)%10);
 const company=await post('',{name:'TEST Final '+tag,business_number:number}),cid=company.id;
 const site=(await post('/'+cid+'/sites',{data:{name:'TEST service site',address:'TEST synthetic'}})).site;
 const evidence_ids:string[]=[];
 if(options.unsupported){const raw=await readFile(JSON.parse(process.env.DATCO_COMPANY_CONTEXT!).documents.find((p:string)=>p.endsWith('.png')));const uploaded=await page.request.post('/api/company/'+cid+'/files?site_id='+site.id,{headers:{Origin:origin,'X-Upload-Name':'TEST-unprocessed.png'},data:raw});expect(uploaded.ok()).toBe(true);const file=await uploaded.json();const evidence=await post('/'+cid+'/evidence',{file_id:file.id,site_id:site.id,descriptor:'TEST direct image',transcription:'TEST unprocessed image source'});evidence_ids.push(evidence.id);}
 const data={title:'TEST Final task '+tag,original_text:options.neutral?'TEST neutral':'서비스 업무 처리시간 개선 및 시스템 연계, 예산 검토와 희망 일정',as_is:options.neutral?'':'처리시간 개선 필요',to_be:options.neutral?'':'시스템 연계로 업무 개선',site_id:site.id,evidence_ids};
 const version=await post('/'+cid+'/improvements',{data});await post('/improvements/'+version.id+'/actions',{action:'SUBMIT',note:'TEST submit'});
 const admin=await playwright.request.newContext({baseURL:origin,extraHTTPHeaders:{Origin:origin}});await admin.post('/api/notice/session',{data:{username:c.accounts.admin,password:c.password}});expect((await admin.post('/api/company/'+cid+'/access',{data:{username:c.accounts.operator}})).ok()).toBe(true);await admin.dispose();
 await login(page);await page.getByLabel('접수목록 검색',{exact:true}).fill(data.title);await page.getByRole('button',{name:'제출 내용 검토',exact:true}).click();
 const panel=page.getByTestId('improvement-analysis');await expect(panel.getByText('현재 입력에 활용 가능한 분석',{exact:true})).toBeVisible({timeout:60000});
 const run=(await(await page.request.get('/api/company/improvements/'+version.id+'/analysis-runs')).json()).at(-1);
 return {company,cid,version,data,run,panel,tag};
}

test('compact candidates: explicit selection, partial review recovery, persistent draft and verified send return',async({page,playwright})=>{
 test.setTimeout(180000);const {cid,company,version,run,panel,data}=await setup(page,playwright);
 const missing=run.candidates.filter((c:{category:string})=>c.category==='MISSING_INFORMATION');expect(missing.length).toBeGreaterThanOrEqual(2);
 await expect(panel.locator('[aria-label="시스템 분석 요약"]')).toContainText(missing.length+'건');
 expect(await panel.locator('textarea:visible').count()).toBe(1);await expect(panel.locator('details.intake-structure')).not.toHaveAttribute('open','');
 expect(await page.getByText(data.as_is,{exact:true}).evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length>0).length)).toBe(1);
 const cards=missing.slice(0,2).map((c:{id:string})=>panel.locator('article[data-candidate-id="'+c.id+'"]'));
 for(const card of cards)await card.getByRole('checkbox').check();
 let current=(await(await page.request.get('/api/company/analysis-runs/'+run.run.id)).json());expect(current.candidates.every((c:{reviews:unknown[]})=>c.reviews.length===0)).toBe(true);
 await cards[0].getByText('근거·개별 검토',{exact:true}).click();await cards[0].getByLabel('기업에 확인할 질문',{exact:true}).fill('TEST edited specific question');
 await cards[0].getByText('적용 규칙·원문 근거',{exact:true}).click();await expect(cards[0].locator('blockquote').first()).toBeVisible();
 await panel.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST common human review');
 let failed=false,firstPosts=0;
 const reviewPattern='**/analysis-candidates/*/reviews';
 await page.route(reviewPattern,route=>{const url=route.request().url();if(url.includes(missing[0].id))firstPosts++;if(url.includes(missing[1].id)&&!failed){failed=true;return route.abort();}return route.continue();});
 await panel.getByRole('button',{name:'보완요청 작성',exact:true}).click();await expect(panel.getByRole('alert')).toBeVisible();
 await expect(panel.getByRole('heading',{name:'Rule 기반 사전 분석 결과'})).toBeVisible();
 current=(await(await page.request.get('/api/company/analysis-runs/'+run.run.id)).json());
 expect(current.candidates.find((c:{id:string})=>c.id===missing[0].id).reviews).toHaveLength(1);expect(current.candidates.find((c:{id:string})=>c.id===missing[1].id).reviews).toHaveLength(0);
 expect(await(await page.request.get('/api/company/improvements/'+version.id+'/analysis-drafts')).json()).toEqual([]);
 await panel.getByRole('button',{name:'보완요청 작성',exact:true}).click();await expect(panel.getByRole('heading',{name:'분석 기반 보완요청 초안',exact:true})).toBeVisible();
 expect(firstPosts).toBe(1);await page.unroute(reviewPattern);
 current=(await(await page.request.get('/api/company/analysis-runs/'+run.run.id)).json());
 for(const c of current.candidates){if(missing.slice(0,2).some((m:{id:string})=>m.id===c.id)){expect(c.reviews).toHaveLength(1);expect(c.reviews[0].decision).toBe('USE_FOR_REQUEST');expect(c.reviews[0].note).toBe('TEST common human review');}else expect(c.reviews).toEqual([]);}
 const drafts=await(await page.request.get('/api/company/improvements/'+version.id+'/analysis-drafts')).json();expect(drafts).toHaveLength(1);expect(drafts[0].versions[0].review_ids).toHaveLength(2);
 await expect(panel.getByLabel('분석 요청 내용',{exact:true})).toHaveValue(/TEST edited specific question/);
 await panel.getByLabel('분석 요청 제목',{exact:true}).fill('TEST compact saved');await panel.getByRole('button',{name:'분석 초안 저장',exact:true}).click();await expect(panel.getByText('서버 저장본',{exact:true})).toBeVisible();
 await page.reload();await panel.getByRole('button',{name:'TEST compact saved · v2',exact:true}).click();await expect(panel.getByLabel('분석 요청 내용',{exact:true})).toHaveValue(/TEST edited specific question/);
 await panel.getByRole('button',{name:'분석 초안 발송 확인',exact:true}).click();const dialog=panel.getByRole('dialog');await expect(dialog).toContainText('제출본 v1');
 expect(await(await page.request.get('/api/company/'+cid+'/information-requests')).json()).toEqual([]);
 await dialog.getByRole('button',{name:'발송 취소',exact:true}).click();await expect(panel.getByRole('button',{name:'분석 초안 발송 확인',exact:true})).toBeFocused();
 await panel.getByRole('button',{name:'분석 초안 발송 확인',exact:true}).click();
 let deliveryProbe=true;
 await page.route('**/analysis-drafts/'+drafts[0].id,route=>{if(deliveryProbe&&route.request().method()==='GET'){deliveryProbe=false;return route.abort();}return route.continue();});
 await dialog.getByRole('button',{name:'분석 초안 최종 발송',exact:true}).evaluate((b:HTMLButtonElement)=>{b.click();b.click();});await expect(dialog.getByRole('alert')).toBeVisible();
 await expect(dialog.getByRole('button',{name:'분석 초안 최종 발송',exact:true})).toBeDisabled();await expect(panel).toBeVisible();
 await dialog.getByRole('button',{name:'저장·발송 상태 확인',exact:true}).click();
 await expect(page.getByRole('heading',{name:'업무 대시보드',exact:true})).toBeVisible();await expect(page.getByRole('status').filter({hasText:'보완요청 발송이 확인되었습니다.'})).toContainText(company.name);
 await expect(page.getByLabel('접수목록 검색',{exact:true})).toHaveValue(data.title);await expect(page.getByRole('row').filter({hasText:data.title})).toContainText('보완요청 발송·답변 대기');
 const requests=await(await page.request.get('/api/company/'+cid+'/information-requests')).json();expect(requests).toHaveLength(1);expect(requests[0].improvement_version_id).toBe(version.id);
 await page.screenshot({path:test.info().outputPath('final-compact-send-return.png'),fullPage:true});
});

test('judgement errors and response loss stay in detail, exact history reconciliation prevents duplicates',async({page,playwright})=>{
 test.setTimeout(150000);const {version,panel}=await setup(page,playwright,{neutral:true});
 const path='**/improvements/'+version.id+'/submission-reviews';await panel.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST explicit hold');
 await page.route(path,route=>route.request().method()==='POST'?route.fulfill({status:409,json:{reason:'STALE_SUBMISSION_REVIEW'}}):route.continue());
 await panel.getByRole('button',{name:'추가 확인 필요 — 판단 보류',exact:true}).click();await expect(panel.getByRole('alert')).toBeVisible();await expect(panel).toBeVisible();
 await page.unroute(path);
 expect((await(await page.request.get('/api/company/improvements/'+version.id+'/submission-reviews')).json()).history).toHaveLength(0);
 await page.route(path,async route=>{if(route.request().method()==='POST'){await route.fetch();await route.abort();}else await route.continue();});
 await panel.getByRole('button',{name:'추가 확인 필요 — 판단 보류',exact:true}).evaluate((b:HTMLButtonElement)=>{b.click();b.click();});
 await expect(panel.getByRole('alert')).toBeVisible();await expect(panel.getByRole('button',{name:'확인한 결과로 목록 복귀',exact:true})).toBeVisible();await expect(panel).toBeVisible();
 const saved=await(await page.request.get('/api/company/improvements/'+version.id+'/submission-reviews')).json();expect(saved.history).toHaveLength(1);expect(saved.history[0].decision).toBe('NEEDS_CHECK');
 await panel.getByRole('button',{name:'확인한 결과로 목록 복귀',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'검토 판단 저장이 확인되었습니다.'})).toContainText('추가 확인 필요');
});

test('list origin, search filter page and filtered-out success survive F5 and re-login',async({page,playwright})=>{
 test.setTimeout(180000);const {cid,version,panel,tag}=await setup(page,playwright,{neutral:true});
 await page.getByRole('button',{name:'검토 목록으로 돌아가기',exact:true}).click();await page.locator('aside').getByRole('button',{name:'개선요구 검토',exact:true}).click();
 const augment='**/api/company/operator/intake';
 await page.route(augment,async route=>{const real=await(await route.fetch()).json();const companies=real.companies.filter((x:{company:{id:string}})=>x.company.id===cid);const current=companies[0].receipts[0];current.submitted_at='2020-01-01T00:00:00Z';for(let i=0;i<105;i++)companies.push({company:{id:'TEST-'+i,name:'TEST Final '+tag+' fake '+i},receipts:[{...current,root_id:'TEST-root-'+i,version_id:'TEST-version-'+i,title:'TEST fake '+i,submitted_at:'2025-01-01T00:00:00Z',work:{status:'NEEDS_REVIEW',label:'검토 필요',next_action:'제출 내용 검토'}}]});await route.fulfill({json:{...real,companies,company_count:companies.length}});});
 await page.reload();await page.getByLabel('접수목록 검색',{exact:true}).fill('TEST Final '+tag);await page.getByLabel('업무 상태 필터',{exact:true}).selectOption('NEEDS_REVIEW');
 for(let i=0;i<5;i++)await page.getByRole('button',{name:'다음 페이지',exact:true}).click();
 await page.locator('tr[data-version-id="'+version.id+'"]').getByRole('button',{name:'제출 내용 검토',exact:true}).click();await expect(panel).toBeVisible();
 await page.reload();await expect(panel).toBeVisible();await page.getByRole('button',{name:'로그아웃',exact:true}).first().click();await page.getByRole('dialog').getByRole('button',{name:'로그아웃',exact:true}).click();await expect(page).toHaveURL(/login\?returnTo=/);await login(page,'operator',true);await expect(panel).toBeVisible();
 await panel.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST hold from filtered page');await panel.getByRole('button',{name:'추가 확인 필요 — 판단 보류',exact:true}).click();
 await expect(page.getByRole('heading',{name:'개선요구 검토',exact:true})).toBeVisible();await expect(panel).toHaveCount(0);await expect(page.getByLabel('접수목록 검색',{exact:true})).toHaveValue('TEST Final '+tag);await expect(page.getByLabel('업무 상태 필터',{exact:true})).toHaveValue('NEEDS_REVIEW');
 await expect(page.getByRole('navigation',{name:'목록 페이지'})).toContainText('6 / 6');await expect(page.locator('tr[data-version-id="'+version.id+'"]')).toHaveCount(0);
 await expect(page.getByRole('status').filter({hasText:'검토 판단이 저장되었습니다.'})).toContainText('추가 확인 필요');
 expect((await(await page.request.get('/api/company/improvements/'+version.id+'/submission-reviews')).json()).history).toHaveLength(1);
});

test('unprocessed direct evidence is separated from information absence and preserves inspection details',async({page,playwright})=>{
 test.setTimeout(150000);const {panel,run}=await setup(page,playwright,{unsupported:true});expect(run.status).toBe('PARTIAL');
 await expect(panel.getByRole('region',{name:'미검사·자료 처리 한계'})).toBeVisible();await expect(panel.getByText('읽지 못한 자료를 정보가 없다는 근거로 판단하지 않습니다.',{exact:true})).toBeVisible();
 expect(run.candidates.some((c:{category:string})=>c.category==='MISSING_INFORMATION')).toBe(false);
 expect(run.inspections[0].data.status).toBe('FAILED');expect(run.inspections[0].data.limitations.join(' ')).toContain('manual review required');
 await panel.getByText('상세 분석·근거·실행 이력',{exact:true}).click();await panel.getByText('실제 자료 검사 범위와 한계',{exact:true}).click();await expect(panel.getByRole('heading',{name:'TEST-unprocessed.png · FAILED',exact:true})).toBeVisible();
});
