import {test,expect,type Page} from '@playwright/test';
const context=()=>JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);
async function login(page:Page){const c=context();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts.admin);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(/\/portal\/admin/);}
test('asset detail result is immediately in the viewport, including source kinds and failure',async({page})=>{
 await login(page);
 // UI contract fixtures deliberately contain no customer source or credentials.
 const data={name:'TEST source',description:'TEST long source description '.repeat(35),role:'',business_areas:[],problems:[],conditions:[],exclusions:[],prerequisites:[],release:'',availability:'NEEDS_CONFIRMATION',availability_evidence:'',relations:[]};
 const make=(kind:string,id:string)=>({id,kind,name:'TEST '+kind+' '+id,parent_id:kind==='SYSTEM'?null:'source-system:0',version_id:null,asset_version_id:null,current_ordinal:0,data,availability:'NEEDS_CONFIRMATION',availability_evidence:'',mapping_status:'SOURCE_CLASSIFICATION',source:{},relations:[]});
 let selected='FEATURE',fail=false;
 await page.route('**/api/capability/assets**',async route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/api/capability/assets'){
   selected=url.searchParams.get('kind')??'FEATURE';const items=Array.from({length:20},(_,i)=>make(selected,selected==='SYSTEM'?'source-system:'+i:selected==='MODULE'?'source-module:'+i:'source-feature:'+i));
   await route.fulfill({json:{items,total:20,page:1,limit:20,systems:[make('SYSTEM','source-system:0')],modules:[make('MODULE','source-module:0')],digest:'TEST'}});return;
  }
  await new Promise(resolve=>setTimeout(resolve,250));
  if(fail){await route.fulfill({status:503,json:{reason:'STORAGE_UNAVAILABLE'}});return;}
  const item=make(selected,decodeURIComponent(url.pathname.split('/').at(-1)!));
  const source=selected==='FEATURE'?[{id:'TEST_RAW_REVISION',ordinal:1,digest:'b'.repeat(64),data:{name:'TEST feature',availability:'AVAILABLE',origin:'TEST.xlsx sheet source row 2'}}]:[];
  await route.fulfill({json:{root:{id:item.id,managed:false},current:item,versions:source,source_revisions:source}});
 });
 await page.getByRole('navigation',{name:'관리자 메뉴'}).getByRole('button',{name:'기준정보·버전',exact:true}).click();
 const assets=page.getByTestId('dmp-assets');
 for(const [kind,label] of [['SYSTEM','시스템'],['MODULE','모듈'],['FEATURE','기능']]){
  await assets.getByRole('button',{name:label+' 탐색',exact:true}).click();
  await expect(assets.locator('tr[data-asset-id]').first()).toHaveAttribute('data-asset-id',new RegExp(kind==='SYSTEM'?'source-system':kind==='MODULE'?'source-module':'source-feature'));
  await assets.getByRole('button',{name:'기술자산 상세·이력',exact:true}).first().click();
  const heading=assets.getByRole('heading',{name:/ · 기술자산 상세$/});
  await expect(heading).toBeInViewport();await expect(assets.getByTestId('asset-result')).toBeFocused();
  if(kind==='FEATURE'){await assets.getByText('원천과 변경 이력',{exact:true}).click();await expect(assets.getByRole('heading',{name:'보존된 원천 r1',exact:true})).toHaveCount(1);await expect(assets.getByText(/^관리 v/)).toHaveCount(0);}
 }
 fail=true;await assets.getByRole('button',{name:'기술자산 상세·이력',exact:true}).first().click();await expect(assets.getByRole('alert')).toBeInViewport();
 await page.screenshot({path:test.info().outputPath('asset-detail-result.png'),fullPage:true});
});