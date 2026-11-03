import {expect,type Page} from '@playwright/test';
import {randomInt} from 'node:crypto';
export const fixture=()=>JSON.parse(process.env.DATCO_HANDOFF_CONTEXT!);
export function isolated(){
 const origin=new URL(process.env.DATCO_E2E_BASE_URL!);
 const c=fixture();
 if(!['localhost','127.0.0.1'].includes(origin.hostname)||['18445','8443','8444','57425','57426','57427'].includes(origin.port)||c.nonce==='9ca49b473812'||!process.env.DATCO_TEST_NONCE)throw Error('SEPARATE_COMPANY_UX_TEST_ENVIRONMENT_REQUIRED');
 return c;
}
export async function login(page:Page,role='editor'){
 const c=isolated();await page.goto('/login');
 await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);
 await page.getByLabel('비밀번호',{exact:true}).fill(c.password);
 await page.getByRole('button',{name:'로그인',exact:true}).click();
 await expect(page).toHaveURL(/\/portal\/(company|operator)/);
}
function number(){
 const digits=Array.from({length:9},()=>randomInt(10));digits[0]=randomInt(1,10);
 const weights=[1,3,7,1,3,7,1,3,5],sum=digits.reduce((total,n,i)=>total+n*weights[i],0)+Math.floor(digits[8]*5/10);
 return digits.join('')+String((10-sum%10)%10);
}
export const headers=()=>({Origin:process.env.DATCO_E2E_BASE_URL!});
export async function company(page:Page,label:string,extra:Record<string,unknown>={}){
 await login(page);
 const profile={name:'TEST Company UX '+label+' '+randomInt(1000000),business_number:number(),industry:'TEST legacy industry',financials:[],history:[],...extra};
 const response=await page.request.post('/api/company',{headers:headers(),data:profile});expect(response.status()).toBe(200);
 const cid=(await response.json()).id;
 const siteResponse=await page.request.post('/api/company/'+cid+'/sites',{headers:headers(),data:{data:{name:'TEST 물류사업장',address:'TEST local site address'}}});expect(siteResponse.status()).toBe(200);
 const sid=(await siteResponse.json()).site.id;
 await goto(page,cid,'home');
 return {cid,sid,profile};
}
export async function goto(page:Page,cid:string,screen:string){await page.goto('/portal/company?company='+cid+'&screen='+screen);await expect(page.locator('aside')).toBeVisible();}
export async function menu(page:Page,name:string){await page.locator('aside').getByRole('button',{name,exact:true}).click();}
export async function detail(page:Page,cid:string){const r=await page.request.get('/api/company/'+cid);expect(r.status()).toBe(200);return r.json();}
export const financial=(year:number,revenue='1000')=>({year,revenue,unit:'원',currency:'KRW',period:String(year)});
export const history={name:'TEST public support project',period:'2023-01-01 ~ 2023-12-31',agency:'TEST support agency',role:''};
export async function optionalDetails(page:Page){const box=page.getByTestId('finance-optional-details');if(await box.count()&&await box.getAttribute('open')===null)await box.locator('summary').click();}
export function profileResponse(page:Page){return page.waitForResponse(r=>r.request().method()==='POST'&&/^\/api\/company\/[^/]+\/profile$/.test(new URL(r.url()).pathname));}
