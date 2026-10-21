import {syntheticBusinessNumber} from './company-number';
import {test,expect,Page} from "@playwright/test";
const config=()=>JSON.parse(process.env.DATCO_COMPANY_CONTEXT??'null');
async function login(page:Page,role:string){const c=config();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(new RegExp(role==='admin'?'/portal/admin':role==='operator'?'/portal/operator':role==='approver'?'/':'/portal/company'));await page.goto('/');await expect(page.getByRole('button',{name:'로그아웃',exact:true})).toBeVisible();}
test('W0 company home, persisted context, real logout, back and another company account',async({page})=>{
 test.setTimeout(180000);const name='TEST W0 Company '+Date.now();await login(page,'editor');await expect(page.getByRole('heading',{name:'내 기업 홈',exact:true})).toBeVisible();await page.getByRole('navigation',{name:'전체 업무 메뉴'}).getByRole('link',{name:'기업정보',exact:true}).click();await page.getByRole('button',{name:'신규 기업 등록'}).click();await page.getByLabel('기업명',{exact:true}).fill(name);await page.getByLabel('사업자번호 10자리').fill(syntheticBusinessNumber());await page.getByLabel('담당자·연락처').fill('TEST W0 private contact');await page.getByRole('button',{name:'기업정보 저장',exact:true}).click();await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();await expect(page.getByLabel('업무 기업',{exact:true})).toHaveValue(/.+/);
 await page.getByRole('navigation',{name:'전체 업무 메뉴'}).getByRole('link',{name:'사업장·재무·정부사업이력'}).click();await page.getByLabel('사업장명',{exact:true}).fill('TEST W0 Site');await page.getByLabel('소재지',{exact:true}).fill('TEST W0 address');await page.getByRole('button',{name:'사업장 저장'}).click();await expect(page.getByText('TEST W0 Site',{exact:true}).last()).toBeVisible();
 await page.getByRole('navigation',{name:'전체 업무 메뉴'}).getByRole('link',{name:'개선요구',exact:true}).click();await page.getByLabel('개선 대상 사업장').selectOption({label:'TEST W0 Site'});await page.getByLabel('개선과제명',{exact:true}).fill('TEST W0 stock problem');await page.getByLabel('기업 개선요구 원문').fill('TEST W0 private inventory problem');await page.getByLabel('To-Be',{exact:true}).fill('TEST W0 target');await page.getByRole('button',{name:'개선과제 초안 저장·새 Version'}).click();await expect(page.getByLabel('개선과제 선택')).toContainText('TEST W0 stock problem');await page.reload();await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();await page.getByLabel('개선과제 선택').selectOption({label:'TEST W0 stock problem · DRAFT'});await expect(page.getByLabel('기업 개선요구 원문')).toHaveValue('TEST W0 private inventory problem');
 await expect(page.getByRole('navigation',{name:'전체 업무 메뉴'}).getByText('지원사업 진행현황')).toHaveAttribute('aria-disabled','true');const listing=await(await page.request.get('/api/company')).json();const company=listing.find((c:{name:string})=>c.name===name);const token=(await page.context().cookies()).find(c=>c.name==='datco_session')!.value;
 await page.getByRole('button',{name:'로그아웃',exact:true}).click();await expect(page).toHaveURL(/\/login$/);expect((await page.request.get('/api/company')).status()).toBe(401);const old=await page.request.get('/api/company',{headers:{Cookie:'datco_session='+token}});expect(old.status()).toBe(401);await page.goBack();await expect(page.getByText('TEST W0 private inventory problem',{exact:true})).toHaveCount(0);await login(page,'other');await expect(page.getByText(name,{exact:true})).toHaveCount(0);expect((await page.request.get('/api/company/'+company.id)).status()).toBe(404);await page.goto('/capability?view=catalog');await expect(page.getByRole('heading',{name:'접근 권한 없음'})).toBeVisible();
});
test('W0 operator and admin homes, real module links, membership and unavailable features',async({page,browser})=>{
 test.setTimeout(180000);const c=config();await login(page,'admin');await expect(page.getByRole('heading',{name:'운영 대시보드'})).toBeVisible();const nav=page.getByRole('navigation',{name:'전체 업무 메뉴'});await expect(nav.getByText('시스템 설정')).toHaveAttribute('aria-disabled','true');await nav.getByRole('link',{name:'DMP 기능 목록',exact:true}).click();await expect(page).toHaveURL(/view=features/);await expect(page.getByRole('button',{name:'검색·조회',exact:true})).toBeVisible();await page.goto('/capability?view=composer');await expect(page.getByRole('heading',{name:'접근 권한 없음'})).toBeVisible();expect((await page.request.post('/api/capability/compositions',{headers:{Origin:process.env.DATCO_E2E_BASE_URL!},data:{data:{},idempotency_key:'TEST_W0_forbidden'}})).status()).not.toBe(200);
 await page.goto('/company');const access=await(await page.request.get('/api/company/access')).json();expect(access.length).toBeGreaterThan(0);const first=access[0];{await page.getByLabel('선택 기업').selectOption(first.id);await page.getByLabel('접근 허용할 기존 계정 아이디').fill(c.accounts.operator);await page.getByRole('button',{name:'기업 접근권한 부여'}).click();await expect(page.getByRole('status')).toContainText('완료');}
 const context=await browser.newContext(),operator=await context.newPage();await login(operator,'operator');await expect(operator.getByRole('heading',{name:'업무 대시보드'})).toBeVisible();const menu=operator.getByRole('navigation',{name:'전체 업무 메뉴'});await expect(menu.getByText('DATCO 솔루션 추천')).toHaveAttribute('aria-disabled','true');await menu.getByRole('link',{name:'기업자료·Fact 검토',exact:true}).click();await expect(operator).toHaveURL(/tab=facts/);await menu.getByRole('link',{name:'서비스 조합',exact:true}).click();await expect(operator.getByRole('heading',{name:'기업 개선 요구사항',exact:true})).toBeVisible();await expect(operator.getByLabel('ImprovementVersion',{exact:true})).not.toBeVisible();await menu.getByRole('link',{name:'매칭 검토',exact:true}).click();await expect(operator.getByLabel('검토할 정부지원사업')).toBeVisible();await menu.getByRole('link',{name:'제안서 작성',exact:true}).click();await expect(operator.getByRole('heading',{name:'시스템 파악 결과와 항목별 검토',exact:true})).toBeVisible();await expect(operator.getByLabel('매칭 후보 ID',{exact:true})).not.toBeVisible();await expect(operator.getByRole('banner').getByText('DATCO 운영자',{exact:true})).toBeVisible();await operator.screenshot({path:test.info().outputPath('w0-operator-workspace.png'),fullPage:true});await operator.getByRole('button',{name:'로그아웃',exact:true}).click();await expect(operator).toHaveURL(/\/login$/);await context.close();
});


test('UI1 CASE-01 company entry, password visibility, failed login and permission gates',async({page})=>{
  const c=config();
  await page.goto('/company');
  expect((await page.request.get('/api/company')).status()).toBe(401);
  await page.goto('/login');
  await expect(page.getByRole('heading',{name:'DATCO 정부지원사업 운영관리 시스템'})).toBeVisible();
  await page.screenshot({path:test.info().outputPath('ui1-login.png'),fullPage:true});
  await page.getByLabel('아이디',{exact:true}).fill(c.accounts.editor);
  const password=page.getByLabel('비밀번호',{exact:true});
  await password.fill('TEST_INVALID_PASSWORD_UI1');
  await expect(password).toHaveAttribute('type','password');
  await page.getByRole('button',{name:'비밀번호 표시',exact:true}).click();
  await expect(password).toHaveAttribute('type','text');
  await page.getByRole('button',{name:'비밀번호 숨기기',exact:true}).click();
  await expect(password).toHaveAttribute('type','password');
  await page.getByRole('button',{name:'로그인',exact:true}).click();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('아이디 또는 비밀번호가 올바르지 않습니다.');
  await expect(page).toHaveURL(/\/login$/);
  await login(page,'editor');
  const companies=page.getByLabel('업무 기업',{exact:true});
  const own=await companies.locator('option').evaluateAll(nodes=>nodes.map(n=>(n as HTMLOptionElement).value).filter(Boolean));
  expect(own.length).toBeGreaterThan(0);await companies.selectOption(own[0]);
  await expect(page.getByLabel('업무 기업',{exact:true})).toHaveValue(own[0]);
  await page.screenshot({path:test.info().outputPath('ui1-company-home.png'),fullPage:true});
  const home=page.getByRole('region',{name:'업무 시작'});
  await home.getByRole('link',{name:'기업 증빙자료 제출하기',exact:true}).click();
  await expect(page).toHaveURL(/tab=onboarding/);
  await expect(page.getByRole('heading',{name:'기업 증빙자료 제출',exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:'전체 업무 메뉴'});
  await nav.getByRole('link',{name:'기업정보',exact:true}).click();
  await expect(page).toHaveURL(/tab=profile/);
  await nav.getByRole('link',{name:'개선요구',exact:true}).click();
  await expect(page).toHaveURL(/tab=improvement/);
  expect((await page.request.get('/api/company/access')).status()).toBe(403);
  await page.getByRole('button',{name:'로그아웃',exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get('/api/workspace')).status()).toBe(401);
});

test('UI1 CASE-02 operator selected company and existing module journey',async({page})=>{
  await login(page,'operator');
  await expect(page.getByRole('heading',{name:'업무 대시보드',exact:true})).toBeVisible();
  const select=page.getByLabel('업무 기업',{exact:true});
  const options=await select.locator('option').evaluateAll(nodes=>nodes.map(n=>(n as HTMLOptionElement).value).filter(Boolean));
  expect(options.length).toBeGreaterThan(0);
  await select.selectOption(options[0]);
  await expect(page.getByLabel('업무 기업',{exact:true})).toHaveValue(options[0]);
  await page.screenshot({path:test.info().outputPath('ui1-operator-home.png'),fullPage:true});
  await page.getByRole('region',{name:'업무 시작'}).getByRole('link',{name:'기업자료·Fact 검토하기'}).click();
  await expect(page).toHaveURL(new RegExp('company='+options[0]));
  await expect(page).toHaveURL(/tab=facts/);
  const nav=page.getByRole('navigation',{name:'전체 업무 메뉴'});
  for(const label of ['서비스 조합','매칭 검토','제안서 작성']){
    await nav.getByRole('link',{name:label,exact:true}).click();
    await expect(page).toHaveURL(new RegExp('company='+options[0]));
  }
  await page.getByRole('button',{name:'로그아웃',exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
});

test('UI1 CASE-03 admin catalog, access management and no operator inheritance',async({page})=>{
  await login(page,'admin');
  await expect(page.getByRole('heading',{name:'운영 대시보드',exact:true})).toBeVisible();
  await expect(page.getByText('공고 운영은 DATCO 운영자 권한이 필요합니다.',{exact:false})).toBeVisible();
  await page.screenshot({path:test.info().outputPath('ui1-admin-home.png'),fullPage:true});
  await page.getByRole('region',{name:'업무 시작'}).getByRole('link',{name:'Catalog·Version 관리'}).click();
  await expect(page).toHaveURL(/view=catalog/);
  await page.getByRole('navigation',{name:'전체 업무 메뉴'}).getByRole('link',{name:'사용자·기업 접근권한',exact:true}).click();
  await expect(page.getByRole('button',{name:'기업 접근권한 부여',exact:true})).toBeVisible();
  await page.goto('/notice');
  await expect(page.getByRole('heading',{name:'접근 권한 없음',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'로그아웃',exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
});
