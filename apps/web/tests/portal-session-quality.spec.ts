import {test,expect,type Page} from '@playwright/test';
import {company,goto,detail,isolated} from './company-ux-fixture';

test.setTimeout(150000);
const confirmation=(page:Page)=>page.getByRole('dialog',{name:'저장하지 않은 변경사항이 있습니다',exact:true});
const logout=(page:Page)=>page.getByRole('button',{name:'로그아웃',exact:true});
async function signIn(page:Page,role:string){const c=isolated();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(logout(page)).toBeVisible();}

for(const role of ['ux_editor','operator','admin'])test('quality clean '+role+' logout immediately revokes current session and other tab',async({page})=>{
 await signIn(page,role);
 const protectedPath=new URL(page.url()).pathname,firstProtected=protectedPath+'?session_history=before',secondProtected=protectedPath+'?session_history=logout';
 const cachedRestores:boolean[]=[];
 await page.exposeBinding('__qualityCachedRestore',(_source,visible:boolean)=>{cachedRestores.push(visible);});
 await page.addInitScript(()=>window.addEventListener('pageshow',event=>{if(!event.persisted||!location.pathname.startsWith('/portal/'))return;const root=document.getElementById('root'),view=root?.querySelector('.portal-layout');const visible=!!root&&!!view&&getComputedStyle(root).visibility!=='hidden'&&view.getClientRects().length>0;void (window as unknown as {__qualityCachedRestore:(visible:boolean)=>Promise<void>}).__qualityCachedRestore(visible);}));
 expect((await page.goto(firstProtected))?.status()).toBe(200);await expect(logout(page)).toBeVisible();
 expect((await page.goto(secondProtected))?.status()).toBe(200);await expect(logout(page)).toBeVisible();
 const second=await page.context().newPage();await second.goto(page.url());await expect(logout(second)).toBeVisible();
 const writes:string[]=[];page.on('request',r=>{if(r.method()==='POST'&&!new URL(r.url()).pathname.startsWith('/api/notice/session'))writes.push(new URL(r.url()).pathname);});
 const cookie=(await page.context().cookies()).find(c=>c.name==='datco_session')!.value;
 await logout(page).click();await expect(confirmation(page)).toHaveCount(0);await expect(page).toHaveURL(/\/login$/);await expect(second).toHaveURL(/\/login$/);
 expect((await page.request.get('/api/notice/session',{headers:{Cookie:'datco_session='+cookie}})).status()).toBe(401);expect(writes).toEqual([]);
 const backDocuments:number[]=[];page.on('response',response=>{if(response.request().resourceType()==='document'&&new URL(response.url()).pathname===protectedPath)backDocuments.push(response.status());});
 await page.goBack();await expect(page).toHaveURL(/\/login$/);
 expect(cachedRestores.every(visible=>!visible)).toBe(true);expect(cachedRestores.length>0||backDocuments.includes(303)).toBe(true);
 const privateView=page.locator('#portal-identity,[data-testid=company-business-context],[data-testid=operator-business-context],[data-testid=admin-live]');await expect(privateView).toHaveCount(0);await expect(logout(page)).toHaveCount(0);
 await page.reload();await expect(page).toHaveURL(/\/login$/);await expect(privateView).toHaveCount(0);
 for(const previous of [firstProtected,secondProtected]){const denied=await page.request.get(previous,{headers:{Cookie:'datco_session='+cookie},maxRedirects:0});expect(denied.status()).toBe(303);expect(denied.headers().location).toBe('/login');}
 await page.goto(firstProtected);await expect(page).toHaveURL(/\/login$/);await expect(privateView).toHaveCount(0);await second.reload();await expect(second).toHaveURL(/\/login$/);await expect(second.locator('#portal-identity,.portal-layout')).toHaveCount(0);expect(writes).toEqual([]);await second.close();
});

test('quality actual company draft uses continue/discard and logout failure retains exact draft',async({page})=>{
 const {cid,profile}=await company(page,'logout-draft');await goto(page,cid,'company');const form=page.getByRole('form',{name:'기업 기본정보 수정',exact:true});await expect(form.getByLabel('기업명',{exact:true})).toHaveValue(profile.name);
 const changed='TEST unsaved logout draft';await form.getByLabel('기업명',{exact:true}).fill(changed);
 const writes:string[]=[];page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);});
 await logout(page).click();await expect(confirmation(page)).toBeVisible();await expect(confirmation(page).getByRole('button',{name:'계속 작성',exact:true})).toBeFocused();await confirmation(page).getByRole('button',{name:'계속 작성',exact:true}).click();await expect(form.getByLabel('기업명',{exact:true})).toHaveValue(changed);expect(writes).toEqual([]);
 const pattern='**/api/notice/session/logout';await page.route(pattern,route=>route.fulfill({status:503,contentType:'application/json',body:'{}'}));
 await logout(page).click();await confirmation(page).getByRole('button',{name:'변경을 버리고 로그아웃',exact:true}).click();await expect(page.getByRole('alert').filter({hasText:'작성 내용을 유지했습니다.'})).toBeVisible();await expect(form.getByLabel('기업명',{exact:true})).toHaveValue(changed);expect((await page.request.get('/api/notice/session')).status()).toBe(200);expect((await detail(page,cid)).inputs.at(-1).data.name).toBe(profile.name);
 await page.unroute(pattern);await page.getByRole('button',{name:'작성 화면으로 돌아가기',exact:true}).click();await logout(page).click();await confirmation(page).getByRole('button',{name:'변경을 버리고 로그아웃',exact:true}).click();await expect(page).toHaveURL(/\/login$/);expect(writes.filter(p=>!p.endsWith('/session/logout'))).toEqual([]);
});

test('quality reverted draft and successful save are clean while an inflight save blocks logout',async({page})=>{
 const {cid,profile}=await company(page,'logout-save');await goto(page,cid,'company');const form=page.getByRole('form',{name:'기업 기본정보 수정',exact:true});const name=form.getByLabel('기업명',{exact:true});await expect(name).toHaveValue(profile.name);await name.fill('TEST changed then restored');await name.fill(profile.name);
 let logoutRequests=0;page.on('request',r=>{if(new URL(r.url()).pathname==='/api/notice/session/logout')logoutRequests++;});
 let release:()=>void=()=>{};let started:()=>void=()=>{};const waiting=new Promise<void>(resolve=>{release=resolve;}),intercepted=new Promise<void>(resolve=>{started=resolve;});const pattern='**/api/company/'+cid+'/profile';
 await page.route(pattern,async route=>{started();await waiting;await route.continue();});await name.fill('TEST saved before logout');await form.getByRole('button',{name:'기업정보 저장',exact:true}).click();await intercepted;
 await logout(page).click();await expect(page.getByRole('alert').filter({hasText:'처리 중입니다.'})).toBeVisible();expect(logoutRequests).toBe(0);await expect(confirmation(page)).toHaveCount(0);
 release();await expect(page.getByRole('status').filter({hasText:'기업정보를 저장했습니다.'})).toBeVisible();await page.unroute(pattern);expect((await detail(page,cid)).inputs.at(-1).data.name).toBe('TEST saved before logout');await page.getByRole('button',{name:'작성 화면으로 돌아가기',exact:true}).click();await logout(page).click();await expect(confirmation(page)).toHaveCount(0);await expect(page).toHaveURL(/\/login$/);expect(logoutRequests).toBe(1);
});

test('quality lost save response requires requery before logout and does not save twice',async({page})=>{
 const {cid}=await company(page,'logout-uncertain');await goto(page,cid,'company');const form=page.getByRole('form',{name:'기업 기본정보 수정',exact:true});const pattern='**/api/company/'+cid+'/profile';let calls=0;
 await page.route(pattern,async route=>{calls++;const actual=await route.fetch();expect(actual.status()).toBe(200);await route.abort('failed');});await form.getByLabel('기업명',{exact:true}).fill('TEST saved response lost');await form.getByRole('button',{name:'기업정보 저장',exact:true}).click();await expect(form.getByRole('button',{name:'기업정보 저장',exact:true})).toBeEnabled();await expect(page.getByRole('alert')).toBeVisible();
 let logoutRequests=0;page.on('request',r=>{if(new URL(r.url()).pathname==='/api/notice/session/logout')logoutRequests++;});await logout(page).click();await expect(page.getByRole('alert').filter({hasText:'처리 결과가 불확실합니다.'})).toBeVisible();expect(logoutRequests).toBe(0);
 await page.unroute(pattern);page.once('dialog',dialog=>dialog.accept());await form.getByRole('button',{name:'저장된 내용 다시 불러오기',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'저장된 내용을 불러왔습니다.'})).toBeVisible();await expect(form.getByLabel('기업명',{exact:true})).toHaveValue('TEST saved response lost');expect(calls).toBe(1);expect((await detail(page,cid)).inputs).toHaveLength(2);
 await page.getByRole('button',{name:'작성 화면으로 돌아가기',exact:true}).click();await logout(page).click();await expect(confirmation(page)).toHaveCount(0);await expect(page).toHaveURL(/\/login$/);
});
