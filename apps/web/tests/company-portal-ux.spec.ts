import {test,expect} from '@playwright/test';
import {company,goto,detail,headers,financial,history,optionalDetails,profileResponse,menu,fixture,login} from './company-ux-fixture';
test.setTimeout(180000);

test('company home uses current stored states and profile/site reload preserves unsaved choice',async({page})=>{
 const {cid,sid,profile}=await company(page,'home',{financials:[financial(2024)],history:[history]});
 const home=page.getByLabel('실제 기업 현황');
 await expect(home.getByRole('heading',{name:profile.name,exact:true})).toBeVisible();
 await expect(page.getByLabel('5단계 업무 진행')).toHaveCount(0);
 await expect(home.getByText('지금 답변할 요청이 없습니다.',{exact:true})).toBeVisible();
 await expect(home.getByText('내 계정에 도착한 제안서가 없습니다.',{exact:true})).toBeVisible();
 const d={title:'TEST submitted then edited',original_text:'TEST original need',site_id:sid,as_is:'TEST stock input',to_be:'TEST less duplicate work',problem:'TEST stock input',goal:'TEST less duplicate work'};
 const first=await page.request.post('/api/company/'+cid+'/improvements',{headers:headers(),data:{data:d}});expect(first.status()).toBe(200);const v=await first.json();
 expect((await page.request.post('/api/company/improvements/'+v.id+'/actions',{headers:headers(),data:{action:'SUBMIT',note:'TEST explicit submit'}})).status()).toBe(200);
 expect((await page.request.post('/api/company/'+cid+'/improvements',{headers:headers(),data:{data:{...d,to_be:'TEST revised goal'},improvement_id:v.improvement_id,expected_ordinal:1}})).status()).toBe(200);
 await page.reload();
 await expect(home.getByLabel('개선요구 현재 상태')).toContainText('작성 중 1건 · 제출 후 검토 대기 0건');
 await home.getByText('집계 기준',{exact:true}).click();await expect(home).toContainText('현재 검토 완료 건수가 아닙니다.');
 await expect(home).toContainText('제출 이력이 있는 개선요구 1건');
 await goto(page,cid,'company');
 const form=page.getByRole('form',{name:'기업 기본정보 수정'});await expect(form.getByLabel('기업명',{exact:true})).toHaveValue(profile.name);
 await form.getByText('이전에 입력한 업종 정보',{exact:true}).click();await expect(form.getByLabel('기존 업종',{exact:true})).toHaveValue('TEST legacy industry');
 await form.getByLabel('기업명',{exact:true}).fill('TEST unsaved company');
 page.once('dialog',d=>d.dismiss());await form.getByRole('button',{name:'저장된 내용 다시 불러오기',exact:true}).click();await expect(form.getByLabel('기업명',{exact:true})).toHaveValue('TEST unsaved company');
 page.once('dialog',d=>d.accept());await form.getByRole('button',{name:'저장된 내용 다시 불러오기',exact:true}).click();await expect(form.getByLabel('기업명',{exact:true})).toHaveValue(profile.name);
 await expect(page.locator('main [data-site-id="'+sid+'"]')).toContainText('TEST local site address');
 expect((await detail(page,cid)).inputs).toHaveLength(1);
 await page.screenshot({path:test.info().outputPath('company-profile-site.png'),fullPage:true});
});

test('finance single row, nullable details and stale save preserve other years and history',async({page})=>{
 const {cid}=await company(page,'finance',{financials:[financial(2023,'3000'),financial(2024,'4000')],history:[history]});
 const baseline=(await detail(page,cid)).inputs.at(-1).data;
 await goto(page,cid,'finance');await page.getByRole('button',{name:'재무정보 직접 입력',exact:true}).click();
 const editor=page.getByRole('dialog');await expect(editor.getByTestId('finance-save-scope')).toHaveCount(0);await expect(editor.getByLabel('작성할 내역',{exact:true})).toHaveCount(0);
 await editor.getByLabel('재무연도',{exact:true}).fill('2025');await editor.getByLabel('기준기간',{exact:true}).fill('2025');await editor.getByLabel('매출액 (원)',{exact:true}).fill('5000');
 await optionalDetails(page);await editor.getByLabel('자산총계 (원)',{exact:true}).fill('123');await editor.getByLabel('자산총계 (원)',{exact:true}).fill('');
 let response=profileResponse(page);await editor.getByRole('button',{name:'재무정보 저장',exact:true}).click();const saved=await response;expect(saved.status()).toBe(200);
 const sent=saved.request().postDataJSON();expect(sent.data.history).toEqual(baseline.history);expect(sent.data.industry).toEqual(baseline.industry);
 let current=await detail(page,cid);expect(current.inputs.at(-1).data.history).toEqual(baseline.history);expect(current.inputs.at(-1).data.financials.slice(0,2)).toEqual(baseline.financials);expect(current.inputs.at(-1).data.financials.at(-1).assets).toBeUndefined();expect(current.inputs[0].data).toEqual(baseline);
 await page.getByRole('button',{name:'재무정보 수정',exact:true}).last().click();await optionalDetails(page);await page.getByLabel('자산총계 (원)',{exact:true}).fill('0');
 response=profileResponse(page);await page.getByRole('button',{name:'재무정보 저장',exact:true}).click();expect((await response).status()).toBe(200);
 current=await detail(page,cid);expect(current.inputs.at(-1).data.financials.at(-1).assets).toBe('0');
 await page.getByRole('button',{name:'재무정보 수정',exact:true}).last().click();await page.getByLabel('매출액 (원)',{exact:true}).fill('5555');
 const concurrent=structuredClone(current.inputs.at(-1).data);concurrent.history.push({...history,name:'TEST concurrent support project'});
 expect((await page.request.post('/api/company/'+cid+'/profile',{headers:headers(),data:{data:concurrent,expected_ordinal:current.company.current_ordinal}})).status()).toBe(200);
 response=profileResponse(page);await page.getByRole('button',{name:'재무정보 저장',exact:true}).click();expect((await response).status()).toBe(409);await expect(page.getByLabel('매출액 (원)',{exact:true})).toHaveValue('5,555');
 const final=await detail(page,cid);expect(final.inputs.at(-1).data.history).toEqual(concurrent.history);expect(final.inputs.at(-1).data.financials).toEqual(concurrent.financials);
 await page.screenshot({path:test.info().outputPath('finance-stale-preserves-draft.png'),fullPage:true});
 page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'편집창 닫기',exact:true}).click();
});

test('history dates and required fields keep finance intact without inventing no-history records',async({page})=>{
 const {cid}=await company(page,'history',{financials:[financial(2025,'987654')]});
 await goto(page,cid,'finance');await expect(page.getByText('수행이력을 아직 등록하지 않았습니다. 수행한 사업이 없다는 확인을 뜻하지 않습니다.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'수행이력 직접 입력',exact:true}).click();
 const dialog=page.getByRole('dialog');await dialog.getByLabel('수행사업명',{exact:true}).fill('TEST government support project');await dialog.getByLabel('지원기관',{exact:true}).fill('TEST agency');
 await dialog.getByLabel('수행 시작일',{exact:true}).fill('2025-04-01');await dialog.getByLabel('수행 종료일',{exact:true}).fill('2025-03-31');
 expect(await dialog.getByLabel('수행 종료일',{exact:true}).evaluate((e:HTMLInputElement)=>e.validity.valid)).toBe(false);
 await dialog.getByRole('button',{name:'수행이력 저장',exact:true}).click();expect((await detail(page,cid)).inputs).toHaveLength(1);
 await dialog.getByLabel('수행 종료일',{exact:true}).fill('2025-04-30');
 const pending=profileResponse(page);await dialog.getByRole('button',{name:'수행이력 저장',exact:true}).click();const response=await pending;expect(response.status()).toBe(200);
 expect(response.request().postDataJSON().data.financials).toEqual([financial(2025,'987654')]);
 const stored=await detail(page,cid);expect(stored.inputs.at(-1).data.financials).toEqual(stored.inputs[0].data.financials);expect(stored.inputs.at(-1).data.history[0].period).toBe('2025-04-01 ~ 2025-04-30');
 await page.reload();await expect(page.getByText('TEST government support project',{exact:true})).toBeVisible();
});

test('need draft close/navigation/file help do not lose unsaved input or require attachments',async({page})=>{
 const {cid}=await company(page,'draft');await goto(page,cid,'needs');
 await expect(page.getByText('작성한 개선요구가 없습니다.',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'새 개선요구 작성',exact:true}).click();await expect(page.getByRole('button',{name:'새 개선요구 작성',exact:true})).toHaveCount(0);
 await expect(page.getByText('첨부 해제는 저장 후 반영되며 이전 제출 이력과 원본은 변경하지 않습니다.',{exact:true})).toHaveCount(0);
 await expect(page.getByLabel('제출 전 확인')).toContainText('개선하고 싶은 모습을 입력해 주세요.');
 await expect(page.getByText(/파일당20MB 이하를 한 번에 최대10개/)).toBeVisible();
 await page.getByLabel('현재 업무와 불편한 점',{exact:true}).fill('TEST keep unsaved stock input');
 await page.getByLabel('개선하고 싶은 모습',{exact:true}).fill('TEST reduce duplicate entry');
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'작성 닫기',exact:true}).click();await expect(page.getByLabel('현재 업무와 불편한 점',{exact:true})).toHaveValue('TEST keep unsaved stock input');
 await menu(page,'첨부자료 관리');await menu(page,'개선요구 등록');await expect(page.getByLabel('현재 업무와 불편한 점',{exact:true})).toHaveValue('TEST keep unsaved stock input');
 const save=page.waitForResponse(r=>r.request().method()==='POST'&&/^\/api\/company\/[^/]+\/improvements$/.test(new URL(r.url()).pathname));
 await page.getByRole('button',{name:'초안 저장',exact:true}).click();expect((await save).status()).toBe(200);
 const draft=(await detail(page,cid)).improvements[0];expect(draft.state).toBe('DRAFT');expect(draft.versions[0].data.evidence_ids).toEqual([]);
 await page.reload();await expect(page.getByRole('button',{name:'새 개선요구 작성',exact:true})).toBeVisible();
});

test('requests and proposals distinguish real empty, loading and failed reads in current account scope',async({page})=>{
 const {cid}=await company(page,'inbox');
 await goto(page,cid,'requests');await expect(page.getByText(/보완 요청이 없습니다/)).toBeVisible();
 const requestPattern='**/api/company/'+cid+'/information-requests';let release:()=>void=()=>{};const delay=new Promise<void>(resolve=>{release=resolve;});
 await page.route(requestPattern,async route=>{await delay;await route.continue();});await page.reload();await expect(page.getByRole('status').filter({hasText:/보완 요청을 불러오고 있습니다/})).toBeVisible();release();await expect(page.getByText(/보완 요청이 없습니다/)).toBeVisible();await page.unroute(requestPattern);
 await page.route(requestPattern,route=>route.fulfill({status:503,contentType:'application/json',body:'{"reason":"STORAGE_UNAVAILABLE"}'}));await page.reload();await expect(page.getByRole('alert').filter({hasText:/보완 요청/})).toBeVisible();await expect(page.getByText(/보완 요청이 없습니다/)).toHaveCount(0);await page.unroute(requestPattern);
 await goto(page,cid,'proposals');await expect(page.getByText(/제안서가 없습니다|제안서가 도착하지/)).toBeVisible();await expect(page.getByRole('button',{name:'내부 승인근거 기록 및 승인 전달',exact:true})).toHaveCount(0);
 const inbox='**/api/proposal/inbox/'+cid;await page.route(inbox,route=>route.fulfill({status:503,contentType:'application/json',body:'{"reason":"STORAGE_UNAVAILABLE"}'}));await page.reload();await expect(page.getByRole('alert').filter({hasText:/제안서/})).toBeVisible();await expect(page.getByText(/제안서가 없습니다|제안서가 도착하지/)).toHaveCount(0);await page.unroute(inbox);
});

test('narrow company screens keep keyboard editor and supported upload help inside viewport',async({page})=>{
 const {cid}=await company(page,'mobile');await page.setViewportSize({width:390,height:844});await goto(page,cid,'finance');
 await page.getByRole('button',{name:'재무정보 직접 입력',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();
 await expect(page.getByRole('dialog').getByRole('heading',{name:'기본 재무정보',exact:true})).toBeVisible();await page.keyboard.press('Tab');await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
 await page.screenshot({path:test.info().outputPath('company-finance-narrow.png'),fullPage:true});
});

test('legacy units remain intact while exact won details and unsaved closing are guarded',async({page})=>{
 const legacy={...financial(2024,'100'),unit:'백만원',currency:'USD'};
 const {cid}=await company(page,'legacy-unit',{financials:[legacy]});await goto(page,cid,'finance');
 await page.getByRole('button',{name:'재무정보 수정',exact:true}).click();await optionalDetails(page);
 const dialog=page.getByRole('dialog');await expect(dialog.getByLabel('금액 단위',{exact:true})).toHaveValue('백만원');await expect(dialog.getByLabel('자산총계 (원)',{exact:true})).toBeDisabled();
 await dialog.getByLabel('매출액 (백만원)',{exact:true}).fill('200');page.once('dialog',d=>d.dismiss());await page.keyboard.press('Escape');await expect(dialog.getByLabel('매출액 (백만원)',{exact:true})).toHaveValue('200');
 page.once('dialog',d=>d.accept());await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);expect((await detail(page,cid)).inputs).toHaveLength(1);
 await page.getByRole('button',{name:'재무정보 수정',exact:true}).click();await page.getByLabel('매출액 (백만원)',{exact:true}).fill('200');
 const response=profileResponse(page);await page.getByRole('button',{name:'재무정보 저장',exact:true}).click();expect((await response).status()).toBe(200);
 expect((await detail(page,cid)).inputs.at(-1).data.financials).toEqual([{...legacy,revenue:'200'}]);
});

test('replacement selection and cancellation do not write or change the registered original',async({page})=>{
 const {cid}=await company(page,'file-choice');const raw=Buffer.from('TEST retained original');
 const r=await page.request.post('/api/company/'+cid+'/files',{headers:{...headers(),'X-Upload-Name':'TEST-original.txt'},data:raw});expect(r.status()).toBe(200);const file=await r.json();
 await goto(page,cid,'files');const card=page.locator('article[data-file-id="'+file.id+'"]');await expect(card).toBeVisible();
 await card.getByText('파일 교체',{exact:true}).click();
 const before=await detail(page,cid),writes:string[]=[];page.on('request',r=>{if(r.method()!=='GET')writes.push(new URL(r.url()).pathname);});
 await card.getByLabel(file.name+' 교체 파일',{exact:true}).setInputFiles({name:'TEST-choice.txt',mimeType:'text/plain',buffer:Buffer.from('TEST unsubmitted choice')});
 await expect(card.getByRole('button',{name:'파일 교체 적용',exact:true})).toBeEnabled();expect(writes).toEqual([]);
 await card.getByRole('button',{name:'TEST-choice.txt 선택 취소',exact:true}).click();await expect(card.getByRole('button',{name:'파일 교체 적용',exact:true})).toBeDisabled();expect(writes).toEqual([]);
 expect((await detail(page,cid)).files).toEqual(before.files);expect((await page.request.get('/api/company/files/'+file.id+'/download')).status()).toBe(200);expect(await(await page.request.get('/api/company/files/'+file.id+'/download')).body()).toEqual(raw);
});

test('pending PDF selection survives cancelled mode changes and invalid new files',async({page})=>{
 const {cid}=await company(page,'pdf-mode');await goto(page,cid,'finance');
 const file=fixture().business_documents.financial,filename=file.split(/[\\/]/).at(-1);
 const selection=page.getByLabel('재무 PDF 파일 선택 또는 끌어놓기',{exact:true});await selection.setInputFiles(file);
 await expect(page.getByRole('button',{name:filename+' 선택 취소',exact:true})).toBeVisible();
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'재무정보 직접 입력',exact:true}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('button',{name:filename+' 선택 취소',exact:true})).toBeVisible();
 await selection.setInputFiles({name:'TEST-invalid.pdf',mimeType:'application/pdf',buffer:Buffer.from('not pdf')});
 await expect(page.getByRole('alert').filter({hasText:'실제 PDF 형식'})).toBeVisible();await expect(page.getByRole('button',{name:filename+' 선택 취소',exact:true})).toBeVisible();
 expect((await detail(page,cid)).files).toEqual([]);
 page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'재무정보 직접 입력',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByRole('button',{name:filename+' 선택 취소',exact:true})).toHaveCount(0);
});

test('company lookup loading, failure, empty and multiple unselected companies stay distinct',async({page})=>{
 let release:()=>void=()=>{};const pending=new Promise<void>(resolve=>{release=resolve;});
 const pattern='**/api/company';await page.route(pattern,async route=>{await pending;await route.continue();});
 await login(page,'ux_empty');await expect(page.getByRole('status').filter({hasText:'조회 중입니다.'})).toBeVisible();await expect(page.getByRole('heading',{name:'등록된 기업정보가 없습니다',exact:true})).toHaveCount(0);
 release();await expect(page.getByRole('heading',{name:'등록된 기업정보가 없습니다',exact:true})).toBeVisible();await page.unroute(pattern);
 await page.route(pattern,route=>route.fulfill({status:503,contentType:'application/json',body:'{"reason":"STORAGE_UNAVAILABLE"}'}));await page.reload();await expect(page.getByRole('alert').filter({hasText:'조회를 완료하지 못했습니다.'})).toBeVisible();await expect(page.getByRole('heading',{name:'등록된 기업정보가 없습니다',exact:true})).toHaveCount(0);await page.unroute(pattern);
 const first=await company(page,'multiple-first');await company(page,'multiple-second');await page.goto('/portal/company');
 await expect(page.getByRole('heading',{name:'기업을 선택해 주세요',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'등록된 기업정보가 없습니다',exact:true})).toHaveCount(0);await page.getByLabel('업무 기업 선택',{exact:true}).selectOption(first.cid);
 await expect(page.getByLabel('실제 기업 현황')).toContainText(first.profile.name);
});
