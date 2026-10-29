import {test,expect,type Page} from '@playwright/test';
import {randomUUID} from 'node:crypto';
type Playwright={request:typeof import('@playwright/test').request};
const config=()=>{const c=JSON.parse(process.env.DATCO_HANDOFF_CONTEXT!);return {...c,accounts:{editor:c.accounts.slice1_editor,operator:c.accounts.slice1_operator,admin:c.accounts.slice1_admin}};};
async function login(page:Page,role='operator'){
 const c=config();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(new RegExp('/portal/'+(role==='editor'?'company':'operator')));
}
async function setup(page:Page,playwright:Playwright){
 const c=config(),origin=process.env.DATCO_E2E_BASE_URL!,tag=randomUUID();await login(page,'editor');
 const post=async(p:string,data:unknown)=>{const r=await page.request.post('/api/company'+p,{headers:{Origin:origin},data});expect(r.ok(),await r.text()).toBe(true);return r.json();};
 const digits=String(Math.floor(100000000+Math.random()*899999999)).split('').map(Number),weights=[1,3,7,1,3,7,1,3,5],sum=digits.reduce((n,d,i)=>n+d*weights[i],0)+Math.floor(digits[8]*5/10);
 const company=await post('',{name:'TEST Requests '+tag,business_number:digits.join('')+String((10-sum%10)%10)}),cid=company.id;
 const site=(await post('/'+cid+'/sites',{data:{name:'TEST logistics',address:'TEST synthetic'}})).site;
 const version=await post('/'+cid+'/improvements',{data:{title:'TEST Task '+tag,original_text:'TEST logistics task',site_id:site.id}});await post('/improvements/'+version.id+'/actions',{action:'SUBMIT',note:'TEST submit'});
 const admin=await playwright.request.newContext({baseURL:origin,extraHTTPHeaders:{Origin:origin}});await admin.post('/api/notice/session',{data:{username:c.accounts.admin,password:c.password}});expect((await admin.post('/api/company/'+cid+'/access',{data:{username:c.accounts.operator}})).ok()).toBe(true);await admin.dispose();
 const op=await playwright.request.newContext({baseURL:origin,extraHTTPHeaders:{Origin:origin}});expect((await op.post('/api/notice/session',{data:{username:c.accounts.operator,password:c.password}})).ok()).toBe(true);
 const operatorPost=async(p:string,data:unknown)=>{const r=await op.post('/api/company'+p,{data});expect(r.ok(),await r.text()).toBe(true);return r.json();};
 const request=async(title:string,common=false)=>{const r=await operatorPost('/'+cid+'/information-requests',{title,message:'TEST actual request '+title,due_date:'2026-12-20',...common?{}:{improvement_version_id:version.id}});await operatorPost('/information-requests/'+r.id+'/send',{});return r;};
 return {company,cid,version,post,operatorPost,request,op,origin};
}

test('dashboard exact response route, 409 and lost review response keep context and return only after observation',async({page,playwright})=>{
 test.setTimeout(180000);const {company,cid,version,post,request,op}=await setup(page,playwright);
 const r=await request('TEST latest response');await post('/information-requests/'+r.id+'/responses',{message:'TEST earlier draft',expected_ordinal:0,file_ids:[],submit:false});
 const reply=await post('/information-requests/'+r.id+'/responses',{message:'TEST submitted latest',expected_ordinal:1,file_ids:[],submit:true});
 await request('TEST second pending request');await request('TEST common request',true);
 await login(page);await page.getByLabel('접수목록 검색',{exact:true}).fill(version.data.title);
 const overview=await(await page.request.get('/api/company/operator/intake')).json();expect(overview.request_items.filter((x:{company_id:string})=>x.company_id===cid)).toHaveLength(3);
 await expect(page.getByLabel('전체 업무 현황')).toContainText('답변 대기 요청');
 await page.locator('tr[data-version-id="'+version.id+'"]').getByRole('button',{name:'기업 답변 검토',exact:true}).click();
 await expect(page).toHaveURL(u=>u.searchParams.get('request')===r.id&&u.searchParams.get('response')===reply.id);
 await expect(page.getByTestId('improvement-analysis')).toHaveCount(0);const card=page.locator('article[data-request-id="'+r.id+'"]');await expect(card.getByLabel('최신 제출 답변')).toContainText('TEST submitted latest');await expect(card.getByText('제출 첨부자료 없음',{exact:true}).first()).toBeVisible();
 await expect(card.getByText('TEST earlier draft',{exact:true})).not.toBeVisible();await expect(page.getByLabel('요청 제목',{exact:true})).not.toBeVisible();
 const pattern='**/information-requests/'+r.id+'/review';await page.route(pattern,route=>route.fulfill({status:409,json:{reason:'STALE_INPUT_VERSION'}}));
 await card.getByLabel('확인 또는 재보완 사유',{exact:true}).fill('TEST review actual latest');await card.getByRole('button',{name:'재보완 요청',exact:true}).click();await expect(card.getByRole('alert').first()).toBeVisible();await expect(card).toBeVisible();
 await expect(card.getByRole('button',{name:'재보완 요청',exact:true})).toBeEnabled();await page.unroute(pattern);let posts=0;await page.route(pattern,async route=>{posts++;await route.fetch();await route.abort();});
 await card.getByRole('button',{name:'재보완 요청',exact:true}).evaluate((b:HTMLButtonElement)=>{b.click();b.click();});await expect.poll(()=>posts).toBe(1);await expect(card.getByRole('alert').first()).toBeVisible();
 await card.getByRole('button',{name:'답변·검토 저장 상태 확인',exact:true}).click();await expect(page.getByRole('heading',{name:'업무 대시보드',exact:true})).toBeVisible();
 await expect(page.locator('.intake-feedback')).toHaveCount(0);await expect(page.getByLabel('접수목록 검색',{exact:true})).toHaveValue(version.data.title);
 const rows=await(await page.request.get('/api/company/'+cid+'/information-requests')).json(),saved=rows.find((x:{id:string})=>x.id===r.id);expect(rows).toHaveLength(3);expect(saved.state).toBe('REVISION_REQUESTED');expect(saved.reviews).toHaveLength(1);expect(saved.reviews[0].response_id).toBe(reply.id);
 await page.locator('aside').getByRole('button',{name:'보완자료 요청',exact:true}).click();await page.getByLabel('요청 검색',{exact:true}).fill(company.name);await expect(page.locator('.intake-inbox tbody tr')).toHaveCount(3);await expect(page.locator('tr[data-request-id="'+r.id+'"]')).toContainText('재보완 요청');
 await page.locator('tr[data-request-id="'+r.id+'"]').getByRole('button').click();await expect(card.getByLabel('재보완 판단')).toContainText('TEST review actual latest');await expect(card.getByLabel('재보완 판단')).toContainText('같은 요청의 다음 답변을 기다리고 있습니다.');await expect(card.getByLabel('재보완 판단')).not.toContainText('DATCO 담당자가 추가 보완을 요청했습니다.');await op.dispose();
});

test('multiple pending requests require explicit selection and request list preserves filters across F5 and review',async({page,playwright})=>{
 test.setTimeout(180000);const {cid,version,post,request,op}=await setup(page,playwright);
 const requests:{id:string}[]=[];for(const title of ['TEST Choice A','TEST Choice B']){const r=await request(title);await post('/information-requests/'+r.id+'/responses',{message:'TEST response '+title,expected_ordinal:0,file_ids:[],submit:true});requests.push(r);}
 await login(page);await page.getByLabel('접수목록 검색',{exact:true}).fill(version.data.title);await page.locator('tr[data-version-id="'+version.id+'"]').getByRole('button',{name:'기업 답변 검토',exact:true}).click();
 expect(new URL(page.url()).searchParams.get('request')).toBeNull();await expect(page.getByTestId('improvement-analysis')).toHaveCount(0);await expect(page.getByRole('heading',{name:'TEST Choice A',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'TEST Choice B',exact:true})).toBeVisible();await expect(page.getByLabel('확인 또는 재보완 사유',{exact:true})).toHaveCount(0);
 await page.locator('aside').getByRole('button',{name:'보완자료 요청',exact:true}).click();await page.getByLabel('요청 검색',{exact:true}).fill('TEST Choice');await page.getByLabel('요청 상태 필터',{exact:true}).selectOption('REVIEW_REQUIRED');
 await page.locator('tr[data-request-id="'+requests[1].id+'"]').getByRole('button',{name:'기업 답변 검토',exact:true}).click();await page.reload();
 const card=page.locator('article[data-request-id="'+requests[1].id+'"]');await expect(card.getByLabel('최신 제출 답변')).toContainText('TEST response TEST Choice B');await card.getByLabel('확인 또는 재보완 사유',{exact:true}).fill('TEST verified exact response');await card.getByRole('button',{name:'확인 완료',exact:true}).click();
 await expect(page.getByLabel('요청 검색',{exact:true})).toHaveValue('TEST Choice');await expect(page.getByLabel('요청 상태 필터',{exact:true})).toHaveValue('REVIEW_REQUIRED');await expect(page.locator('tr[data-request-id="'+requests[1].id+'"]')).toHaveCount(0);
 const rows=await(await page.request.get('/api/company/'+cid+'/information-requests')).json();expect(rows.find((r:{id:string})=>r.id===requests[0].id).state).toBe('REVIEW_REQUIRED');expect(rows.find((r:{id:string})=>r.id===requests[1].id).state).toBe('VERIFIED');
 const blocked=JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);await page.goto('/portal/operator?screen=requests&company='+cid+'&version='+version.id+'&request='+blocked.foreign.id);await expect(page.getByRole('alert')).toContainText('요청 대상 기업·제출 Version을 확인할 수 없습니다.');
 await op.dispose();
});

test('editor selected files, draft unlink, upload-success save-failure retry and revision preserve all past evidence',async({page,playwright})=>{
 test.setTimeout(180000);const {cid,post,request,operatorPost,op}=await setup(page,playwright);const r=await request('TEST file response'),parallel=await request('TEST parallel response',true);
 await page.goto('/portal/company?company='+cid);await page.locator('aside').getByRole('button',{name:'보완 요청함',exact:true}).click();
 const card=page.locator('article[data-request-id="'+r.id+'"]'),attachment=card.getByLabel('답변 첨부자료',{exact:true});
 const otherCard=page.locator('article[data-request-id="'+parallel.id+'"]');await otherCard.getByLabel('보완 답변',{exact:true}).fill('TEST parallel answer');await card.getByLabel('보완 답변',{exact:true}).fill('TEST editable response');await attachment.setInputFiles([{name:'TEST-A.txt',mimeType:'text/plain',buffer:Buffer.from('TEST original A')},{name:'TEST-B.txt',mimeType:'text/plain',buffer:Buffer.from('TEST unused B')}]);await card.getByRole('button',{name:'TEST-B.txt 선택 취소',exact:true}).click();await expect(card).toContainText('선택 파일 1건');
 await page.evaluate(({a,b})=>{for(const id of [a,b]){const card=document.querySelector('article[data-request-id="'+id+'"]');const button=Array.from(card?.querySelectorAll('button')??[]).find(x=>x.textContent==='답변 초안 저장');button?.click();}},{a:r.id,b:parallel.id});await expect(page.getByRole('status').filter({hasText:'보완 답변 초안을 저장했습니다.'})).toBeVisible();
 const get=async()=> (await(await page.request.get('/api/company/'+cid+'/information-requests')).json()).find((x:{id:string})=>x.id===r.id);
 const first=await get();expect(first.responses).toHaveLength(1);const a=first.responses[0].file_ids[0];let detail=await(await page.request.get('/api/company/'+cid)).json();expect(detail.files.some((f:{name:string})=>f.name==='TEST-B.txt')).toBe(false);await otherCard.getByRole('button',{name:'답변 초안 저장',exact:true}).click();await expect.poll(async()=>{const rows=await(await page.request.get('/api/company/'+cid+'/information-requests')).json();return rows.find((x:{id:string})=>x.id===parallel.id).responses.length;}).toBe(1);
 await card.getByRole('button',{name:'현재 답변에서 제외',exact:true}).click();await attachment.setInputFiles({name:'TEST-C.txt',mimeType:'text/plain',buffer:Buffer.from('TEST replacement C')});
 let uploads=0;page.on('request',req=>{if(req.method()==='POST'&&new URL(req.url()).pathname==='/api/company/'+cid+'/files')uploads++;});
 await page.route('**/information-requests/'+r.id+'/responses',route=>route.abort(),{times:1});await card.getByRole('button',{name:'답변 초안 저장',exact:true}).click();await expect(card.getByRole('alert').first()).toBeVisible();await expect(card.getByLabel('현재 답변 작성').getByRole('status')).toHaveText('저장 결과 확인 필요');expect(uploads).toBe(1);expect((await get()).responses).toHaveLength(1);
 await card.getByRole('button',{name:'답변·검토 저장 상태 확인',exact:true}).click();await card.getByRole('button',{name:'답변 초안 저장',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'보완 답변 초안을 저장했습니다.'})).toBeVisible();expect(uploads).toBe(1);
 const second=await get();expect(second.responses).toHaveLength(2);expect(second.responses[0].file_ids).toEqual([a]);expect(second.responses[1].file_ids).not.toContain(a);expect((await page.request.get('/api/company/files/'+a+'/download')).status()).toBe(200);
 await card.getByRole('button',{name:'보완답변 제출',exact:true}).click();await expect(card.getByText('보완답변 제출 완료',{exact:true})).toBeVisible();await expect(card).toContainText('DATCO 담당자 확인 대기');await expect(card.getByText('TEST editable response',{exact:true}).filter({visible:true})).toHaveCount(1);await expect(card.getByText('작성 이력 v1 · 저장한 초안',{exact:true})).not.toBeVisible();
 await page.reload();await expect(card.getByText('보완답변 제출 완료',{exact:true})).toBeVisible();await expect(card.locator('p').first()).toContainText('DATCO 담당자 확인 대기');expect(await card.textContent()).not.toContain('MANUAL_operator_');
 const submitted=await get();await operatorPost('/information-requests/'+r.id+'/review',{response_id:submitted.responses.at(-1).id,outcome:'REVISION_REQUESTED',note:'TEST clarify again'});await page.reload();
 const answer=card.getByLabel('보완 답변',{exact:true}),status=card.getByLabel('현재 답변 작성').getByRole('status'),restored='이전 제출 답변을 불러왔습니다. 수정 후 다시 제출해 주세요.';
 await expect(answer).toHaveValue('TEST editable response');await expect(status).toHaveText(restored);await expect(card.getByLabel('재보완 판단')).toContainText('TEST clarify again');await expect(card.getByLabel('재보완 판단')).toContainText('DATCO 담당자가 추가 보완을 요청했습니다. 답변을 수정하고 다시 제출해 주세요.');await expect(card.getByLabel('재보완 판단')).not.toContainText('같은 요청의 다음 답변을 기다리고 있습니다.');
 await page.reload();await expect(status).toHaveText(restored);expect((await get()).responses).toEqual(submitted.responses);
 await answer.fill('TEST changed revision');await expect(status).toHaveText('저장되지 않은 변경사항');await answer.fill('TEST editable response');await expect(status).toHaveText(restored);
 await attachment.setInputFiles({name:'TEST-D.txt',mimeType:'text/plain',buffer:Buffer.from('TEST selected only')});await expect(status).toHaveText('저장되지 않은 변경사항');await card.getByRole('button',{name:'TEST-D.txt 선택 취소',exact:true}).click();await expect(status).toHaveText(restored);
 await card.getByRole('button',{name:'현재 답변에서 제외',exact:true}).click();await expect(status).toHaveText('저장되지 않은 변경사항');await answer.fill('TEST revision without files');
 let resumeSave!:()=>void;const saveGate=new Promise<void>(resolve=>{resumeSave=resolve;});await page.route('**/information-requests/'+r.id+'/responses',async route=>{await saveGate;await route.continue();},{times:1});
 try{await card.getByRole('button',{name:'답변 초안 저장',exact:true}).click();await expect(status).toHaveText('저장 중');}finally{resumeSave();}
 await expect(status).toHaveText('답변 초안 저장 완료');const draft=await get();expect(draft.responses).toHaveLength(4);expect(draft.responses[3].submitted).toBe(false);expect(draft.responses[3].file_ids).toEqual([]);
 await page.reload();await expect(answer).toHaveValue('TEST revision without files');await expect(status).toHaveText('답변 초안 저장 완료');await page.goto('/portal/company?company='+cid);await page.locator('aside').getByRole('button',{name:'보완 요청함',exact:true}).click();await expect(status).toHaveText('답변 초안 저장 완료');
 await card.getByRole('button',{name:'보완답변 제출',exact:true}).click();await expect(card.getByText('보완답변 제출 완료',{exact:true})).toBeVisible();
 const revised=await get();expect(revised.id).toBe(r.id);expect(revised.responses).toHaveLength(5);expect(revised.responses.slice(0,3)).toEqual(submitted.responses);expect(revised.responses[3]).toEqual(draft.responses[3]);expect(revised.responses[4].submitted).toBe(true);expect(revised.responses[4].file_ids).toEqual([]);expect(revised.responses[2].file_ids).toEqual(submitted.responses[2].file_ids);expect(revised.reviews).toHaveLength(1);expect(revised.reviews[0].response_id).toBe(submitted.responses[2].id);
 detail=await(await page.request.get('/api/company/'+cid)).json();expect(detail.files).toHaveLength(2);await page.setViewportSize({width:390,height:844});await expect.poll(()=>page.locator('aside').evaluate(el=>el.getBoundingClientRect().right)).toBeLessThanOrEqual(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)).toBe(false);await page.screenshot({path:test.info().outputPath('request-current-response-mobile.png'),fullPage:true,animations:'disabled'});await op.dispose();void post;
});
