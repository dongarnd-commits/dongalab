import {test,expect,Page} from '@playwright/test';
const data=()=>JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);
async function login(page:Page){const c=data();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts.editor);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page.getByTestId('company-business-context')).toHaveAttribute('data-company-id',c.a.id);}
const menus=['기업 홈','기업정보 등록 시작','추출정보 확인','기업 · 사업장 관리','재무 · 사업이력','개선요구 등록','첨부자료 관리','분석 결과 확인','보완 요청함','받은 제안서'];
test('v04 all ten company screens have no shared banner and preserve actual context',async({page})=>{
 test.setTimeout(120000);const c=data();await login(page);
 for(const [index,name] of menus.entries()){
  await page.locator('aside').getByRole('button',{name,exact:true}).click();
  await expect(page.locator('main').getByRole('heading').first()).toBeVisible();await expect(page.locator('.portal-context')).toHaveCount(0);
  await expect(page.getByRole('region',{name:'기업 업무 정보'})).toHaveCount(0);await expect(page.getByRole('button',{name:'다시 조회',exact:true})).toHaveCount(0);
  await expect(page.getByTestId('company-business-context')).toHaveAttribute('data-company-id',c.a.id);
  await expect(page.getByRole('button',{name:'기존 업무 화면 열기'})).toHaveCount(0);
  for(const label of ['Company ID','Site ID','Improvement Root ID','ImprovementVersion ID','Site Version ordinal'])await expect(page.getByText(label,{exact:true})).toHaveCount(0);
  await expect(page.getByLabel('업무 사업장 선택')).toHaveCount(0);if(name==='기업 · 사업장 관리')await expect(page.getByLabel('수정할 사업장',{exact:true})).toBeVisible();
  await page.screenshot({path:test.info().outputPath('C-'+String(index+1).padStart(2,'0')+'.png'),fullPage:true});
 }
 for(const name of ['기업 홈','기업 · 사업장 관리','개선요구 등록','첨부자료 관리','기업 홈']){await page.locator('aside').getByRole('button',{name,exact:true}).click();await expect(page.getByTestId('company-business-context')).toHaveAttribute('data-company-id',c.a.id);}
});

test('v04 actual 90 seconds idle and three tab returns retain mounted UI and security polling',async({page})=>{
 test.setTimeout(180000);const c=data();await login(page);await page.waitForLoadState('networkidle');const root=page.getByTestId('company-business-context'),errors:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});let navigations=0,sessions=0,navigationReads=0;
 page.on('framenavigated',f=>{if(f===page.mainFrame())navigations++;});page.on('request',r=>{const path=new URL(r.url()).pathname;if(path==='/api/notice/session')sessions++;if(path.endsWith('/navigation'))navigationReads++;});
 await page.evaluate(()=>{const w=window as typeof window & {stability:{missing:number;loading:number;empty:number;node:Element|null;remount:number}};w.stability={missing:0,loading:0,empty:0,node:document.querySelector('[data-testid="company-business-context"]'),remount:0};new MutationObserver(()=>{const state=w.stability,node=document.querySelector('[data-testid="company-business-context"]');if(!document.querySelector('aside'))state.missing++;if(document.querySelector('#root')?.textContent?.includes('세션 확인 중입니다.'))state.loading++;if(node&&!node.getAttribute('data-company-id'))state.empty++;if(node&&node!==state.node){state.remount++;state.node=node;}}).observe(document.getElementById('root')!,{subtree:true,childList:true,attributes:true,characterData:true});});
 const started=Date.now();await page.waitForTimeout(90000);expect(Date.now()-started).toBeGreaterThanOrEqual(90000);await expect(root).toHaveAttribute('data-company-id',c.a.id);expect(sessions).toBeGreaterThanOrEqual(5);expect(sessions).toBeLessThanOrEqual(7);expect(navigationReads).toBeGreaterThanOrEqual(5);expect(navigationReads).toBeLessThanOrEqual(7);
 const idle={sessions,navigationReads};const second=await page.context().newPage();await second.goto('about:blank');
 // Delay real session responses to expose duplicate visibility/focus requests without replacing API data.
 await page.route('**/api/notice/session',async route=>{const response=await route.fetch();await new Promise(r=>setTimeout(r,200));await route.fulfill({response});});
 for(let i=0;i<3;i++){await second.bringToFront();await page.waitForTimeout(150);const before=sessions;await page.bringToFront();await page.waitForTimeout(100);if(sessions===before)await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect.poll(()=>sessions).toBeGreaterThan(before);await page.waitForTimeout(400);expect(sessions-before).toBe(1);await expect(root).toHaveAttribute('data-company-id',c.a.id);}
 // Drain delayed real responses before removing the handler; do not race route.fulfill.
 await page.unrouteAll({behavior:'wait'});await second.close();
 const stability=await page.evaluate(()=>(window as typeof window & {stability:{missing:number;loading:number;empty:number;remount:number}}).stability);expect(stability.missing).toBe(0);expect(stability.loading).toBe(0);expect(stability.empty).toBe(0);expect(stability.remount).toBe(0);expect(navigations).toBe(0);expect(errors).toEqual([]);
 await test.info().attach('90s-stability.json',{body:JSON.stringify({idle,focusReturns:3,navigations,stability,errors}),contentType:'application/json'});await page.screenshot({path:test.info().outputPath('after-90s-focus.png'),fullPage:true});
});

test('v04 denied background scope clears private context and expired session exits',async({page})=>{
 const c=data();await login(page);
 await page.route('**/api/company',route=>route.fulfill({status:403,json:{detail:'Forbidden'}}));await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect(page.getByTestId('company-business-context')).toHaveAttribute('data-company-id','');await expect(page.getByRole('alert')).toContainText('접근권한이 없습니다');await expect(page.getByText(c.a.name,{exact:true})).toHaveCount(0);await page.unroute('**/api/company');
 // Actual logout invalidates the real server session; no synthetic auth success.
 await page.request.post('/api/notice/session/logout',{headers:{Origin:process.env.DATCO_E2E_BASE_URL!}});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page).toHaveURL(/\/login$/);await expect(page.getByTestId('company-business-context')).toHaveCount(0);
});


test('v04 failed cached-page session check reveals only error UI and recovers after revalidation',async({page})=>{
 await login(page);await page.route('**/api/notice/session',route=>route.fulfill({status:503,json:{detail:'Unavailable'}}));
 await page.evaluate(()=>{window.dispatchEvent(new Event('pagehide'));window.dispatchEvent(new Event('pageshow'));});
 await expect(page.getByRole('status')).toContainText('세션을 확인할 수 없습니다');await expect(page.getByRole('status')).toBeVisible();await expect(page.getByTestId('company-business-context')).toHaveCount(0);
 await page.unroute('**/api/notice/session');await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page.getByTestId('company-business-context')).toHaveAttribute('data-company-id',data().a.id);
});
