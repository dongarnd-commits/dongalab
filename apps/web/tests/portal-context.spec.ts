import {test,expect,Page} from '@playwright/test';
const fixture=()=>JSON.parse(process.env.DATCO_PORTAL_CONTEXT??'null');
const origin=()=>process.env.DATCO_E2E_BASE_URL!;
async function login(page:Page,role='editor'){
 const c=fixture();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(new RegExp(role==='admin'?'/portal/admin':role==='operator'||role==='blocked_operator'?'/portal/operator':'/portal/company'));
}
const bar=(page:Page)=>page.locator('[data-testid="company-business-context"],[data-testid="operator-business-context"],section[aria-label="기업 업무 정보"]');
async function assertContext(page:Page,cid:string,sid:string,root:string,version:string){for(const [key,value] of [['company',cid],['site',sid],['improvement',root],['version',version]])await expect(bar(page)).toHaveAttribute('data-'+key+'-id',value);}
async function deepSelection(page:Page,changes:Record<string,string|null>){await page.evaluate(changes=>{const url=new URL(location.href);for(const [key,value] of Object.entries(changes)){if(value)url.searchParams.set(key,value);else url.searchParams.delete(key);}history.replaceState({},'',url);dispatchEvent(new PopStateEvent('popstate'));},changes);}
async function chooseCompany(page:Page,id:string){if(new URL(page.url()).pathname==='/portal/company'){await page.locator('aside').getByRole('button',{name:'기업 · 사업장 관리',exact:true}).click();const own=page.getByLabel('소속 기업',{exact:true});if(await own.isVisible())await own.selectOption(id);else await page.getByLabel('업무 기업 선택',{exact:true}).selectOption(id);}else{await page.getByRole('navigation',{name:'운영자 업무 메뉴'}).getByRole('button',{name:'기업 통합 업무',exact:true}).click();await page.getByLabel('업무 기업 선택',{exact:true}).selectOption(id);}}
async function chooseVersion(page:Page,id:string){if(new URL(page.url()).pathname==='/portal/company'){const cid=new URL(page.url()).searchParams.get('company')!;const r=await page.request.get('/api/company/'+cid+'/navigation?version_id='+id);expect(r.ok()).toBe(true);const selection=(await r.json()).selection;await deepSelection(page,{site:selection.site_id,site_version:String(selection.site_ordinal),improvement:selection.improvement_id,version:id});return;}const field=page.getByLabel('개선요구 수정 이력',{exact:true});if(!await field.isVisible())await page.getByText('수정 이력',{exact:true}).click();await field.selectOption(id);}
async function chooseA(page:Page){const c=fixture();await expect(bar(page)).toHaveAttribute('data-company-id',c.a.id);if(new URL(page.url()).pathname==='/portal/company'){await page.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();await deepSelection(page,{company:c.a.id,site:c.a1.id,site_version:null,improvement:c.av1.improvement_id,version:c.av2.id});}else{await page.getByRole('navigation',{name:'운영자 업무 메뉴'}).getByRole('button',{name:'기업 통합 업무',exact:true}).click();await page.getByLabel('업무 사업장 선택',{exact:true}).selectOption(c.a1.id);await page.getByRole('navigation',{name:'운영자 업무 메뉴'}).getByRole('button',{name:'개선요구 검토',exact:true}).click();await page.getByLabel('업무 개선요구 선택',{exact:true}).selectOption(c.av1.improvement_id);await chooseVersion(page,c.av2.id);}await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av2.id);}


test('0b single company auto selection and exact historical version survives all menus and refresh',async({page})=>{
 test.setTimeout(120000);const c=fixture(),writes:string[]=[];await login(page);page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);});
 await chooseA(page);await expect(page.getByLabel('업무 기업 선택')).toHaveCount(0);
 await chooseVersion(page,c.av1.id);await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);
 const selected=await(await page.request.get('/api/company/'+c.a.id+'/navigation?version_id='+c.av1.id)).json();expect(selected.selection.is_latest_version).toBe(false);
 for(const name of ['기업정보 등록 시작','추출정보 확인','기업 · 사업장 관리','재무 · 사업이력','개선요구 등록','첨부자료 관리','분석 결과 확인','보완 요청함','받은 제안서','기업 홈']){
  await page.locator('aside').getByRole('button',{name,exact:true}).click();await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);
 }
 await page.reload();await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);
 await page.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();const history=await(await page.request.get('/api/company/'+c.a.id+'/navigation?version_id='+c.av1.id)).json();const historical=history.improvements.find((i:{id:string})=>i.id===c.av1.improvement_id).versions.find((v:{id:string})=>v.id===c.av1.id);expect(historical.data.original_text).toBe(c.av1.data.original_text);expect(historical.data.to_be).toBe(c.av1.data.to_be);expect(writes).toEqual([]);
 await page.screenshot({path:test.info().outputPath('company-real-historical-context.png'),fullPage:true});
});

test('0b multiple memberships reset children and empty company does not invent sites',async({page})=>{
 test.setTimeout(90000);const c=fixture();await login(page,'multi');await chooseCompany(page,c.b.id);await assertContext(page,c.b.id,c.bs.id,c.bv.improvement_id,c.bv.id);
 await chooseCompany(page,c.a.id);await expect(bar(page)).toHaveAttribute('data-company-id',c.a.id);await expect(bar(page)).toHaveAttribute('data-version-id','');expect(new URL(page.url()).searchParams.get('version')).toBeNull();
 await page.locator('aside').getByRole('button',{name:'기업 · 사업장 관리',exact:true}).click();await deepSelection(page,{site:c.a2.id,site_version:null,improvement:null,version:null});await assertContext(page,c.a.id,c.a2.id,c.other_site.improvement_id,c.other_site.id);
 await chooseCompany(page,c.empty.id);await expect(bar(page)).toHaveAttribute('data-company-id',c.empty.id);await expect(bar(page)).toHaveAttribute('data-site-id','');await expect(bar(page)).toContainText('등록된 사업장이 없습니다');
 await expect(page.getByText(c.bv.data.original_text,{exact:true})).toHaveCount(0);
});

test('0b zero-company editor and operator have real empty scope with no default company',async({page})=>{
 const c=fixture();await login(page,'zero');await expect(page.getByText('접근 가능한 기업이 없습니다',{exact:false})).toHaveCount(0);await expect(bar(page)).toHaveAttribute('data-company-id','');expect(await(await page.request.get('/api/company')).json()).toEqual([]);
 await login(page,'blocked_operator');await expect(bar(page)).toContainText('접근 가능한 기업이 없습니다');await expect(bar(page)).toHaveAttribute('data-company-id','');expect((await page.request.get('/api/company/'+c.a.id+'/navigation')).status()).toBe(404);
});

test('0b operator sees only allowed companies and exactly the editor Company Site Root Version',async({page})=>{
 test.setTimeout(120000);const c=fixture();await login(page,'operator');const listing=await(await page.request.get('/api/company')).json();expect(listing.map((x:{id:string})=>x.id).sort()).toEqual([c.a.id,c.b.id].sort());
 await chooseCompany(page,c.a.id);await chooseA(page);await chooseVersion(page,c.av1.id);await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);
 const controls=page.getByRole('navigation',{name:'운영자 업무 메뉴'});for(const button of await controls.getByRole('button').all()){await button.click();await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);}
 const url='/api/company/'+c.a.id+'/navigation?version_id='+c.av1.id;const operator=await(await page.request.get(url)).json();
 await login(page,'editor');const editor=await(await page.request.get(url)).json();expect(editor).toEqual(operator);
 await login(page,'operator');await chooseCompany(page,c.b.id);await assertContext(page,c.b.id,c.bs.id,c.bv.improvement_id,c.bv.id);await page.reload();await assertContext(page,c.b.id,c.bs.id,c.bv.improvement_id,c.bv.id);
 await page.screenshot({path:test.info().outputPath('operator-real-context.png'),fullPage:true});
});

test('0b tampered Company Site Root Version URL is rejected by HTTP and clears old display',async({page})=>{
 test.setTimeout(120000);const c=fixture();await login(page);await chooseA(page);
 for(const query of ['site_id='+c.fs.id,'version_id='+c.fv.id,'improvement_id='+c.fv.improvement_id,'version_id='+c.av1.id+'&site_id='+c.a2.id,'version_id='+crypto.randomUUID()])expect((await page.request.get('/api/company/'+c.a.id+'/navigation?'+query)).status()).toBe(404);
 await page.goto('/portal/company?company='+c.foreign.id+'&site='+c.fs.id+'&version='+c.fv.id);await expect(bar(page).getByRole('alert')).toContainText('없거나 접근할 수 없습니다');await expect(bar(page)).toHaveAttribute('data-company-id','');await expect(page.getByText(c.foreign.name,{exact:true})).toHaveCount(0);await expect(page.getByText(c.a.name,{exact:true})).toHaveCount(0);
 await bar(page).getByRole('button',{name:'선택 초기화'}).click();await chooseA(page);
 await page.goto('/portal/company?company='+c.a.id+'&site='+c.a1.id+'&version='+c.fv.id);await expect(bar(page).getByRole('alert')).toBeVisible();await expect(bar(page)).toHaveAttribute('data-version-id','');
});

test('0b new backend version does not silently replace pinned historical version',async({page,playwright})=>{
 test.setTimeout(90000);const c=fixture();await login(page);await chooseA(page);await chooseVersion(page,c.av1.id);await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);
 const other=await playwright.request.newContext({baseURL:origin(),extraHTTPHeaders:{Origin:origin()}});await other.post('/api/notice/session',{data:{username:c.accounts.editor,password:c.password}});
 const current=await(await other.get('/api/company/'+c.a.id+'/navigation?version_id='+c.av1.id)).json();const currentOrdinal=current.improvements.find((i:{id:string})=>i.id===c.av1.improvement_id).current_ordinal;
 const next=await other.post('/api/company/'+c.a.id+'/improvements',{data:{data:{...c.av2.data,title:'TEST external next version '+Date.now()},improvement_id:c.av1.improvement_id,expected_ordinal:currentOrdinal}});expect(next.ok()).toBe(true);const v3=await next.json();await other.dispose();
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);const updated=await(await page.request.get('/api/company/'+c.a.id+'/navigation?version_id='+c.av1.id)).json();expect(updated.selection.improvement_version_id).toBe(c.av1.id);expect(updated.improvements.find((i:{id:string})=>i.id===c.av1.improvement_id).versions.some((v:{id:string})=>v.id===v3.id)).toBe(true);
 await page.reload();await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,c.av1.id);await chooseVersion(page,v3.id);await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,v3.id);
});

test('0b account and role switching never carries old business context into another actor',async({page})=>{
 test.setTimeout(120000);const c=fixture();await login(page);await chooseA(page);await page.getByRole('button',{name:'로그아웃',exact:true}).first().click();await expect(page).toHaveURL(/\/login$/);
 await login(page,'other');await expect(bar(page)).toHaveAttribute('data-company-id',c.foreign.id);await expect(page.getByText(c.a.name,{exact:true})).toHaveCount(0);
 expect((await page.request.get('/api/company/'+c.a.id+'/navigation')).status()).toBe(404);
 await login(page,'admin');await expect(page.getByRole('heading',{name:'통합 운영 관제'})).toBeVisible();await expect(bar(page)).toHaveCount(0);expect((await page.request.get('/api/company/'+c.a.id+'/navigation')).status()).toBe(403);await expect(page.getByText(c.a.name,{exact:true})).toHaveCount(0);
});

test('0b admin reuses only approved catalog metadata and has no business detail scope',async({page})=>{
 const c=fixture();await login(page,'admin');const projection=await(await page.request.get('/api/workspace')).json();
 await page.getByRole('navigation',{name:'관리자 메뉴'}).getByRole('button',{name:'기준정보·버전',exact:true}).click();
 await expect(page.getByTestId('admin-feature-count')).toHaveText(String(projection.catalog.features));await expect(page.getByTestId('admin-published-count')).toHaveText(String(projection.catalog.published));
 await expect(page.getByRole('region',{name:'허용된 기준정보 요약'})).toContainText('목록·버전·동기화 상태는 별도 미연결');
 expect((await page.request.get('/api/company/'+c.a.id+'/navigation')).status()).toBe(403);await expect(bar(page)).toHaveCount(0);await expect(page.getByText(c.a.name,{exact:true})).toHaveCount(0);
 await page.screenshot({path:test.info().outputPath('admin-allowed-summary.png'),fullPage:true});
});


test('0b business UI cleanup hides technical fields and legacy entries while preserving real selection',async({page})=>{
 test.setTimeout(120000);const c=fixture();await login(page);await expect(bar(page)).toHaveAttribute('data-company-id',c.a.id);
 await expect(page.getByRole('button',{name:'기존 업무 화면 열기'})).toHaveCount(0);
 await expect(page.locator('a[href="/company"],a[href="/capability"],a[href="/notice"],a[href="/proposal"]')).toHaveCount(0);
 await expect(page.getByLabel('업무 사업장 선택')).toHaveCount(0);await expect(page.getByLabel('업무 개선요구 선택')).toHaveCount(0);
 for(const text of ['업무 Context','Company ID','Site ID','Improvement Root ID','ImprovementVersion ID','Site Version ordinal','선택 ID·Version 확인'])await expect(page.getByText(text,{exact:true})).toHaveCount(0);
 await expect(page.locator('.portal-context')).toHaveCount(0);await page.screenshot({path:test.info().outputPath('01-company-home.png'),fullPage:true});
 await page.locator('aside').getByRole('button',{name:'기업정보 등록 시작',exact:true}).click();await page.screenshot({path:test.info().outputPath('02-company-registration.png'),fullPage:true});
 await chooseA(page);await page.locator('aside').getByRole('button',{name:'기업 · 사업장 관리',exact:true}).click();await page.screenshot({path:test.info().outputPath('03-real-sites.png'),fullPage:true});
 await expect(page.getByRole('button',{name:'이 사업장의 개선요구 확인',exact:true})).toHaveCount(0);await page.locator('aside').getByRole('button',{name:'개선요구 등록',exact:true}).click();await page.locator('article[data-root-id="'+c.av1.improvement_id+'"]').getByRole('button',{name:'수정·상세보기',exact:true}).click();await expect(page.getByRole('button',{name:'초안 저장',exact:true})).toHaveCount(0);const detail=await(await page.request.get('/api/company/'+c.a.id)).json(),root=detail.improvements.find((i:{id:string})=>i.id===c.av1.improvement_id),latest=root.versions.find((v:{ordinal:number})=>v.ordinal===root.current_ordinal);await assertContext(page,c.a.id,c.a1.id,c.av1.improvement_id,latest.id);await expect(page.locator('article[data-improvement-id="'+root.id+'"]').getByText(latest.data.to_be,{exact:true})).toBeVisible();await page.screenshot({path:test.info().outputPath('04-real-improvement.png'),fullPage:true});
 for(const id of [c.a.id,c.a1.id,c.av1.improvement_id,c.av2.id])expect(await page.locator('body').innerText()).not.toContain(id);
 await login(page,'operator');await chooseCompany(page,c.a.id);await chooseA(page);await page.screenshot({path:test.info().outputPath('05-operator-business-selection.png'),fullPage:true});
 await login(page,'admin');await expect(page.getByRole('heading',{name:'통합 운영 관제'})).toBeVisible();await page.screenshot({path:test.info().outputPath('06-admin-control.png'),fullPage:true});
 for(const role of ['editor','operator','admin']){await login(page,role);await expect(page.getByRole('button',{name:'기존 업무 화면 열기'})).toHaveCount(0);}
 // Legacy backend/compatibility UI remains accessible to its existing authorized role.
 await login(page,'editor');expect((await page.request.get('/company')).status()).toBe(200);await page.screenshot({path:test.info().outputPath('07-logout-available.png'),fullPage:true});
});
