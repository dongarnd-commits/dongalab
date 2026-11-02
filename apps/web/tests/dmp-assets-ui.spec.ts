import {test,expect,type Page} from '@playwright/test';
const origin=()=>process.env.DATCO_E2E_BASE_URL!;
const context=()=>JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);
async function login(page:Page,role:string){
 const c=context();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(/\/portal\/(company|operator|admin)/);
}
async function saved(page:Page,path='/api/capability/assets'){
 const response=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===path);
 await page.getByRole('button',{name:'기술자산 저장',exact:true}).click();const result=await response;expect(result.status(),await result.text()).toBe(200);return result.json();
}
test('administrator manages real DMP hierarchy and revisions without changing the original import or business roles',async({page,browser})=>{
 test.setTimeout(180000);page.on('dialog',dialog=>dialog.accept());const c=context(),nonce=c.nonce??Date.now().toString();
 await login(page,'admin');const original=await(await page.request.get('/api/capability/features?limit=1')).json();
 await page.getByRole('navigation',{name:'관리자 메뉴'}).getByRole('button',{name:'기준정보·버전',exact:true}).click();
 const assets=page.getByTestId('dmp-assets');await expect(assets.getByRole('heading',{name:'DMP 기술자산 관리',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'실제 DMP 기능·Capability Catalog',exact:true})).not.toBeVisible();
 await page.getByRole('button',{name:'새 시스템 등록',exact:true}).click();await page.getByLabel('기술자산 이름',{exact:true}).fill('TEST 자산 시스템 '+nonce);await page.getByLabel('기술자산 설명',{exact:true}).fill('TEST synthetic system metadata, not a DMP deployment.');
 await page.getByLabel('등록 기술자산 제공 상태',{exact:true}).selectOption('VERIFIED');await page.getByLabel('제공 검증 근거',{exact:true}).fill('TEST synthetic verified parent release, not an actual delivery assurance.');
 const system=await saved(page);await expect(page.getByRole('status').filter({hasText:'기술자산 v1을 저장'})).toBeVisible();
 await page.getByRole('button',{name:'새 모듈 등록',exact:true}).click();await page.getByLabel('기술자산 상위 항목',{exact:true}).selectOption(system.id);await page.getByLabel('기술자산 이름',{exact:true}).fill('TEST 자산 모듈 '+nonce);await page.getByLabel('실제 수행 역할',{exact:true}).fill('TEST 재고 기록과 조회');
 await page.getByLabel('등록 기술자산 제공 상태',{exact:true}).selectOption('VERIFIED');await page.getByLabel('제공 검증 근거',{exact:true}).fill('TEST synthetic verified module release, not an actual delivery assurance.');
 const moduleAsset=await saved(page);await expect(page.getByRole('status').filter({hasText:'기술자산 v1을 저장'})).toBeVisible();
 await page.getByRole('button',{name:'새 기능 등록',exact:true}).click();await page.getByLabel('기술자산 상위 항목',{exact:true}).selectOption(moduleAsset.id);const name='TEST 자산 재고 조회 '+nonce;await page.getByLabel('기술자산 이름',{exact:true}).fill(name);await page.getByLabel('기술자산 설명',{exact:true}).fill('TEST 재고 기록을 확인하는 시험 기능');await page.getByLabel('실제 수행 역할',{exact:true}).fill('TEST 재고 현황 조회');await page.getByLabel('기술자산 적용 업무',{exact:true}).fill('재고 관리');await page.getByLabel('기술자산 해결 가능한 문제',{exact:true}).fill('재고 현황 확인 지연');
 await page.getByLabel('등록 기술자산 제공 상태',{exact:true}).selectOption('VERIFIED');await expect(page.getByRole('button',{name:'기술자산 저장',exact:true})).toBeDisabled();await page.getByLabel('제공 검증 근거',{exact:true}).fill('TEST isolated synthetic evidence, not real delivery verification.');
 const feature=await saved(page);await expect(page.getByRole('status').filter({hasText:'기술자산 v1을 저장'})).toBeVisible();
 const first=await(await page.request.get('/api/capability/assets/'+feature.id)).json();expect(first.current.availability).toBe('VERIFIED');expect(first.versions).toHaveLength(1);expect(first.current.system_id).toBe(system.id);expect(first.current.module_id).toBe(moduleAsset.id);
 await page.getByRole('button',{name:'기술자산 새 버전 작성',exact:true}).click();await page.getByLabel('등록 기술자산 제공 상태',{exact:true}).selectOption('RETIRED');await page.getByLabel('개발·배포 릴리스',{exact:true}).fill('TEST retired revision');
 await saved(page,'/api/capability/assets/'+feature.id+'/versions');const after=await(await page.request.get('/api/capability/assets/'+feature.id)).json();expect(after.versions).toHaveLength(2);expect(after.versions[0]).toEqual(first.versions[0]);expect(after.current.availability).toBe('RETIRED');
 await page.getByLabel('기술자산 검색',{exact:true}).fill(after.current.external_id);await page.getByLabel('기술자산 제공 상태',{exact:true}).selectOption('RETIRED');await expect(assets.locator('tr[data-asset-id="'+feature.id+'"]')).toContainText(name);await expect(assets.locator('tr[data-asset-id="'+feature.id+'"]')).toContainText('사용 중단');
 const originalAfter=await(await page.request.get('/api/capability/features?limit=1')).json();expect(originalAfter.import).toEqual(original.import);expect(originalAfter.total).toBe(original.total);expect(originalAfter.items).toEqual(original.items);
 const operatorContext=await browser.newContext({baseURL:origin()}),operator=await operatorContext.newPage();await login(operator,'operator');const denied=await operator.request.post('/api/capability/assets',{headers:{Origin:origin()},data:{kind:'SYSTEM',data:{name:'TEST forbidden'},idempotency_key:crypto.randomUUID()}});expect(denied.status()).toBe(403);await operatorContext.close();
 const editorContext=await browser.newContext({baseURL:origin()}),editor=await editorContext.newPage();await login(editor,'editor');expect((await editor.request.get('/api/capability/assets')).status()).toBe(403);await editorContext.close();
});
