import {test,expect,type Page} from '@playwright/test';
import {company,headers,isolated} from './company-ux-fixture';

test.setTimeout(180000);
async function signIn(page:Page,role:string){const c=isolated();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page.getByRole('button',{name:'로그아웃',exact:true})).toBeVisible();}
async function grant(page:Page,cid:string){await signIn(page,'admin');const c=isolated();expect((await page.request.post('/api/company/'+cid+'/access',{headers:headers(),data:{username:c.accounts.operator}})).status()).toBe(200);await signIn(page,'operator');}

test('quality request-purpose company selection opens composer without saving or sending',async({page})=>{
 const {cid,profile}=await company(page,'request-composer');await grant(page,cid);await page.goto('/portal/operator?screen=requests');
 await page.getByText('새 기업 공통정보 보완요청 작성',{exact:true}).click();const row=page.getByRole('row').filter({hasText:profile.name});await row.getByRole('button',{name:'기업 공통정보 보완요청',exact:true}).click();
 const composer=page.locator('details.request-manual-compose');await expect(composer).toHaveAttribute('open','');await expect(composer.getByLabel('요청 제목',{exact:true})).toBeFocused();await expect(page.getByRole('heading',{name:'보완요청 대상',exact:true}).locator('..')).toContainText(profile.name);expect(new URL(page.url()).searchParams.get('company')).toBe(cid);
 expect((await page.request.get('/api/company/'+cid+'/information-requests')).status()).toBe(200);expect(await(await page.request.get('/api/company/'+cid+'/information-requests')).json()).toEqual([]);
 const writes:string[]=[];page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);});await composer.getByLabel('요청 제목',{exact:true}).fill('TEST explicit draft');await composer.getByLabel('확인·보완할 내용',{exact:true}).fill('TEST request only the missing period');await page.getByRole('button',{name:'로그아웃',exact:true}).click();await page.getByRole('dialog',{name:'저장하지 않은 변경사항이 있습니다',exact:true}).getByRole('button',{name:'계속 작성',exact:true}).click();await expect(composer.getByLabel('요청 제목',{exact:true})).toHaveValue('TEST explicit draft');expect(writes).toEqual([]);
});

test('quality operator menus and refresh retain exact historical submission and site',async({page})=>{
 const {cid,sid}=await company(page,'historical-operator');const data={site_id:sid,title:'TEST historical submission',original_text:'TEST original source retained',as_is:'TEST existing manual stock entry',to_be:'TEST remove duplicate entry',constraints:'TEST existing device retained'};
 const response=await page.request.post('/api/company/'+cid+'/improvements',{headers:headers(),data:{data}});expect(response.status()).toBe(200);const old=await response.json();expect((await page.request.post('/api/company/improvements/'+old.id+'/actions',{headers:headers(),data:{action:'SUBMIT',note:'TEST explicit historical submit'}})).status()).toBe(200);
 expect((await page.request.post('/api/company/'+cid+'/improvements',{headers:headers(),data:{data:{...data,title:'TEST latest unsubmitted version',as_is:'TEST changed latest content'},improvement_id:old.improvement_id,expected_ordinal:1}})).status()).toBe(200);
 await grant(page,cid);await page.goto('/portal/operator?screen=improvement&company='+cid+'&version='+old.id);const target=page.getByTestId('operator-business-context');await expect(target).toHaveAttribute('data-site-id',sid);await expect(target).toHaveAttribute('data-version-id',old.id);await expect(page.getByRole('heading',{name:'TEST latest unsubmitted version',exact:true})).toHaveCount(0);
 for(const name of ['DATCO 서비스 추천','서비스 조합 검토','정부지원사업 추천','매칭·자격 검토','맞춤형 제안서','전달·검토 이력']){await page.locator('aside').getByRole('button',{name,exact:true}).click();await expect(page.getByLabel('솔루션 대상 개선요구 Version',{exact:true})).toHaveValue(old.id);await expect(page.getByRole('status').filter({hasText:'과거 Version을 조회 중입니다.'})).toBeVisible();expect(new URL(page.url()).searchParams.get('version')).toBe(old.id);}
 await page.reload();await expect(page.getByLabel('솔루션 대상 개선요구 Version',{exact:true})).toHaveValue(old.id);await page.locator('aside').getByRole('button',{name:'개선요구 검토',exact:true}).click();await expect(target).toHaveAttribute('data-version-id',old.id);await expect(target).toHaveAttribute('data-site-id',sid);await expect(page.getByText('TEST original source retained',{exact:true}).first()).toBeAttached();
});


test('quality analysis draft reverted to its saved baseline is clean on logout',async({page})=>{
 const {cid,sid}=await company(page,'request-baseline');const data={site_id:sid,title:'TEST saved analysis request',original_text:'서비스 업무 처리시간 개선 및 시스템 연계, 예산 검토와 희망 일정',as_is:'처리시간 개선 필요',to_be:'시스템 연계로 업무 개선'};
 const created=await page.request.post('/api/company/'+cid+'/improvements',{headers:headers(),data:{data}});expect(created.status()).toBe(200);const version=await created.json();expect((await page.request.post('/api/company/improvements/'+version.id+'/actions',{headers:headers(),data:{action:'SUBMIT',note:'TEST explicit submit'}})).status()).toBe(200);
 await grant(page,cid);await page.goto('/portal/operator?screen=improvement&company='+cid+'&version='+version.id);const panel=page.getByTestId('improvement-analysis');await expect(panel.getByText('현재 입력에 활용 가능한 분석',{exact:true})).toBeVisible({timeout:60000});
 const runs=await(await page.request.get('/api/company/improvements/'+version.id+'/analysis-runs')).json(),missing=runs.at(-1).candidates.find((c:{category:string})=>c.category==='MISSING_INFORMATION');expect(missing).toBeTruthy();
 await panel.locator('article[data-candidate-id="'+missing.id+'"]').getByRole('checkbox').check();await panel.getByLabel('운영자 검토 의견',{exact:true}).fill('TEST explicit reviewed source');await panel.getByRole('button',{name:'보완요청 작성',exact:true}).click();
 const title=page.getByLabel('보완자료 요청 제목',{exact:true});await expect(title).toBeVisible();const saved=await title.inputValue();await title.fill(saved+' TEST temporary edit');await expect(page.getByRole('button',{name:'요청 초안 저장',exact:true})).toBeEnabled();await title.fill(saved);await expect(page.getByRole('button',{name:'요청 초안 저장',exact:true})).toBeDisabled();
 const writes:string[]=[];page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);});await page.getByRole('button',{name:'로그아웃',exact:true}).click();await expect(page.getByRole('dialog',{name:'저장하지 않은 변경사항이 있습니다',exact:true})).toHaveCount(0);await expect(page).toHaveURL(url=>url.pathname==='/login');expect(writes).toEqual(['/api/notice/session/logout']);
});
