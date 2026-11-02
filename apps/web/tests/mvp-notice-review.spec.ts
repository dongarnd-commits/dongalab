import {test,expect} from '@playwright/test';

test('MVP unanalysed synthetic Notice runs actual Worker and exposes only human-reviewed matching scope',async({page})=>{
 test.setTimeout(150000);
 const c=JSON.parse(process.env.DATCO_MVP_CONTEXT!),origin=process.env.DATCO_E2E_BASE_URL!;
 expect(c.notice.id).toBeTruthy();
 expect((await page.request.post('/api/notice/session',{headers:{Origin:origin},data:{username:c.accounts.operator,password:c.password}})).ok()).toBe(true);
 const beforeResponse=await page.request.get('/api/notice/'+c.notice.id);expect(beforeResponse.ok()).toBe(true);
 const before=await beforeResponse.json(),input=before.versions.find((v:{id:string})=>v.id===c.notice.version_id);
 expect(input.jobs).toEqual([]);expect(input.runs).toEqual([]);expect(input.confirmed).toEqual([]);expect(input.sources.length).toBeGreaterThan(0);
 await page.goto('/portal/operator?screen=grants');
 const row=page.locator('tr[data-notice-id="'+c.notice.id+'"]');await expect(row).toHaveAttribute('data-notice-version-id',c.notice.version_id);await row.getByRole('button',{name:'이 공고 원문·요건 검토',exact:true}).click();
 const requirements=page.getByLabel('매칭 공고 요건 Version',{exact:true});await expect(requirements.locator('option')).toHaveCount(1);await expect(requirements).toHaveValue('');
 const queued=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/notice/analysis'&&response.request().method()==='POST');
 await page.getByRole('button',{name:'이 공고의 기존 요건 분석 실행',exact:true}).click();const response=await queued;expect(response.ok(),await response.text()).toBe(true);
 expect(response.request().postDataJSON()).toMatchObject({expected_version:c.notice.version_id});expect(response.request().postDataJSON()).not.toHaveProperty('version_id');
 const job=await response.json();expect(job.state).toBe('QUEUED');expect(job.version_id).toBe(c.notice.version_id);
 await expect.poll(async()=>{const data=await(await page.request.get('/api/notice/'+c.notice.id)).json();return data.versions.find((v:{id:string})=>v.id===c.notice.version_id).jobs.find((j:{id:string})=>j.id===job.id)?.state;},{timeout:60000}).toBe('SUCCEEDED');
 const analyzed=await(await page.request.get('/api/notice/'+c.notice.id)).json(),version=analyzed.versions.find((v:{id:string})=>v.id===c.notice.version_id);expect(version.confirmed).toEqual([]);expect(version.runs).toHaveLength(1);expect(version.runs[0].candidates.length).toBeGreaterThan(0);
 const candidate=version.runs[0].candidates[0],card=page.locator('article[data-notice-candidate-id="'+candidate.id+'"]');await expect(card).toBeVisible({timeout:10000});await expect(card.locator('blockquote')).toContainText(candidate.evidence.text);expect(candidate.evidence.source_id).toBeTruthy();
 expect((await page.request.get('/api/notice/sources/'+candidate.evidence.source_id+'/download')).ok()).toBe(true);
 await card.getByRole('checkbox',{name:'원문과 이 요건의 실제 근거를 확인했습니다.',exact:true}).check();await card.getByLabel('요건 검토 의견',{exact:true}).fill('TEST operator checked the exact synthetic original clause and its limited review scope.');
 const confirming=page.waitForResponse(r=>r.url().endsWith('/api/notice/candidates/'+candidate.id+'/confirm')&&r.request().method()==='POST');await card.getByRole('button',{name:'이 요건의 근거 검토 저장',exact:true}).click();const confirmed=await confirming;expect(confirmed.ok(),await confirmed.text()).toBe(true);const receipt=await confirmed.json();
 await expect(requirements.locator('option[value="'+receipt.id+'"]')).toHaveCount(1);await requirements.selectOption(receipt.id);await expect(requirements).toHaveValue(receipt.id);
 const after=await(await page.request.get('/api/notice/'+c.notice.id)).json(),reviewed=after.versions.find((v:{id:string})=>v.id===c.notice.version_id);expect(reviewed.confirmed).toHaveLength(1);expect(reviewed.confirmed[0].id).toBe(receipt.id);expect(reviewed.confirmed[0].items).toHaveLength(1);expect(reviewed.runs[0].candidates.find((row:{id:string})=>row.id===candidate.id).reviews[0].outcome).toBe('CONFIRM');
 const catalog=await(await page.request.get('/api/notice/catalog?q='+encodeURIComponent(c.notice.title))).json();const saved=catalog.items.find((row:{id:string})=>row.id===c.notice.id);expect(saved.version_id).toBe(c.notice.version_id);expect(saved.requirement_version_id).toBe(receipt.id);expect(saved.requirement_state).toBe('REVIEWED_SCOPE');
 await expect(page.getByText('검토된 일부 요건은 공고 전체 자격 확인과 다릅니다. 미확인 조건을 적합으로 처리하지 않습니다.',{exact:true})).toBeVisible();
});
