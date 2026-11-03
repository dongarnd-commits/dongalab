import {test,expect,type Page} from '@playwright/test';
const context=()=>JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);
const esc=(s:string)=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
// Bounded synthetic OOXML ZIP, using stored entries and real CRC; no customer source.
function xlsx(rows:string[][]){
 const sheet='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+rows.map((row,i)=>'<row r="'+(i+1)+'">'+row.map((value,j)=>'<c r="'+String.fromCharCode(65+j)+(i+1)+'" t="inlineStr"><is><t>'+esc(value)+'</t></is></c>').join('')+'</row>').join('')+'</sheetData></worksheet>';
 const files:Record<string,string>={'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="TEST source" r:id="r1"/></sheets></workbook>','xl/_rels/workbook.xml.rels':'<Relationships><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>','xl/worksheets/sheet1.xml':sheet};
 let offset=0;const local:Buffer[]=[],central:Buffer[]=[];
 for(const [path,text] of Object.entries(files)){
  const name=Buffer.from(path),data=Buffer.from(text);let crc=0xffffffff;for(const byte of data){crc^=byte;for(let i=0;i<8;i++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}crc=(crc^0xffffffff)>>>0;
  const head=Buffer.alloc(30);head.writeUInt32LE(0x04034b50);head.writeUInt16LE(20,4);head.writeUInt32LE(crc,14);head.writeUInt32LE(data.length,18);head.writeUInt32LE(data.length,22);head.writeUInt16LE(name.length,26);
  local.push(head,name,data);const index=Buffer.alloc(46);index.writeUInt32LE(0x02014b50);index.writeUInt16LE(20,4);index.writeUInt16LE(20,6);index.writeUInt32LE(crc,16);index.writeUInt32LE(data.length,20);index.writeUInt32LE(data.length,24);index.writeUInt16LE(name.length,28);index.writeUInt32LE(offset,42);central.push(index,name);offset+=head.length+name.length+data.length;
 }
 const directory=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(central.length/2,8);end.writeUInt16LE(central.length/2,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);return Buffer.concat([...local,directory,end]);
}
async function login(page:Page){const c=context();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts.admin);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(/\/portal\/admin/);await page.getByRole('navigation',{name:'관리자 메뉴'}).getByRole('button',{name:'기준정보·버전',exact:true}).click();}

test('Excel selected source update preserves original, retries uncertain apply, and reupload creates no duplicate',async({page})=>{
 test.setTimeout(120000);page.on('dialog',dialog=>dialog.accept());await login(page);const nonce=context().nonce??Date.now().toString();
 const header=['system','feature_group','name','description','feature_id'],first=['TEST workbook '+nonce,'TEST group','TEST receive '+nonce,'TEST received records '+nonce,''],second=['TEST workbook '+nonce,'TEST group','TEST dispatch '+nonce,'TEST dispatched records '+nonce,''];
 const content=xlsx([header,first,second]);const box=page.getByTestId('asset-workbook-import');
 async function inspect(bytes:Buffer){await box.getByLabel('Excel 개발자료',{exact:true}).setInputFiles({name:'TEST-workbook.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:bytes});const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/capability/asset-imports/preview');await box.getByRole('button',{name:'원본 보관·기존 자료와 비교',exact:true}).click();const result=await response;expect(result.status(),await result.text()).toBe(200);return result.json();}
 async function confirm(){await box.getByLabel('선택한 범위와 예외 연결을 검토했으며 자료 등록을 확정합니다.',{exact:true}).check();await box.getByRole('button',{name:'선택한 자료 등록 확정',exact:true}).click();}
 const preview=await inspect(content);expect(preview.rows.map((r:{status:string})=>r.status)).toEqual(['NEW','NEW']);
 await box.getByLabel(second[2]+' 등록 선택 0:3',{exact:true}).uncheck();
 // Persist through the actual backend, then lose only the HTTP response.
 await page.route('**/api/capability/asset-imports/apply',async route=>{const response=await route.fetch();expect(response.status()).toBe(200);await route.abort('failed');});
 await confirm();await expect(box.getByRole('alert').filter({hasText:'등록 응답을 확인하지 못했습니다'})).toBeVisible();await expect(box.getByLabel('Excel 개발자료',{exact:true})).toBeDisabled();
 await page.unroute('**/api/capability/asset-imports/apply');await box.getByRole('button',{name:'같은 등록 요청 결과 다시 확인',exact:true}).click();await expect(box.getByRole('status').filter({hasText:'1개 신규·변경 항목을 반영'})).toBeVisible();
 const next=await inspect(content);expect(next.rows.map((r:{status:string})=>r.status)).toEqual(['SAME','NEW']);await confirm();await expect(box.getByRole('status').filter({hasText:'1개 신규·변경 항목을 반영'})).toBeVisible();
 const download=await page.request.get('/api/capability/asset-imports/'+preview.file_sha256+'/original');expect(download.ok()).toBe(true);expect(await download.body()).toEqual(content);
 const before=await(await page.request.get('/api/capability/features?q='+encodeURIComponent(nonce))).json();expect(before.total).toBe(2);expect(before.scope).toBe('CURRENT_CATALOG');
 const moved=await inspect(xlsx([header,second,[],first]));expect(moved.rows.map((r:{status:string})=>r.status)).toEqual(['SAME','SAME']);
 await box.getByLabel(second[2]+' 등록 선택 0:2',{exact:true}).check();await box.getByLabel(first[2]+' 등록 선택 0:4',{exact:true}).check();await confirm();await expect(box.getByRole('status').filter({hasText:'0개 신규·변경 항목을 반영'})).toBeVisible();
 const after=await(await page.request.get('/api/capability/features?q='+encodeURIComponent(nonce))).json();expect(after.items).toEqual(before.items);expect(after.import).toEqual(before.import);
 const target=before.items.find((r:{data:{name:string}})=>r.data.name===first[2]).data.feature_id;
 const renamed=[first[0],first[1],'TEST renamed '+nonce,first[3],''];const exception=await inspect(xlsx([header,renamed]));expect(exception.rows[0].status).toBe('DUPLICATE_SUSPECT');await box.getByLabel('예외 연결 0:2',{exact:true}).selectOption(target);await box.getByLabel(renamed[2]+' 등록 선택 0:2',{exact:true}).check();await confirm();await expect(box.getByRole('status').filter({hasText:'1개 신규·변경 항목을 반영'})).toBeVisible();
 const history=await(await page.request.get('/api/capability/features/'+target)).json();expect(history.revisions).toHaveLength(2);expect(history.revisions[0].data.name).toBe(first[2]);expect(history.revisions[1].data.name).toBe(renamed[2]);
 const retained=await(await page.request.get('/api/capability/features?q='+encodeURIComponent(nonce))).json();expect(retained.total).toBe(2);
 // Actual source SYSTEM/MODULE/FEATURE details through the running backend,
 // distinct from the UI-contract fault/latency fixture in quality-portals.
 await page.getByLabel('기술자산 검색',{exact:true}).fill('');
 await page.getByLabel('기술자산 시스템',{exact:true}).selectOption({label:first[0]+' · 원천 분류'});
 const assets=page.getByTestId('dmp-assets');
 for(const label of ['시스템','모듈','기능']){
  await assets.getByRole('button',{name:label+' 탐색',exact:true}).click();
  await expect(assets.locator('tr[data-asset-id]').first()).toBeVisible();
  const response=page.waitForResponse(r=>r.request().method()==='GET'&&new URL(r.url()).pathname.startsWith('/api/capability/assets/'));
  await assets.getByRole('button',{name:'기술자산 상세·이력',exact:true}).first().click();const actual=await response;expect(actual.status()).toBe(200);const body=await actual.json();expect(body.root.managed).toBe(false);expect(body.current.kind).toBe(({시스템:'SYSTEM',모듈:'MODULE',기능:'FEATURE'} as Record<string,string>)[label]);
  await expect(assets.getByRole('heading',{name:/ · 기술자산 상세$/})).toBeInViewport();await expect(assets.getByTestId('asset-result')).toBeFocused();
  if(label==='기능'){expect(body.current.source.kind).toBe('ADMIN_WORKBOOK');expect(body.current.availability).toBe('NEEDS_CONFIRMATION');expect(body.current.source.workbook.location.row).toBe(body.current.external_id===target?2:3);}
 }
 expect((await page.request.get('/api/capability/assets/source-system%3Anot-a-digest')).status()).toBe(400);
 expect((await page.request.post('/api/capability/assets/source-system%3A'+'a'.repeat(24),{headers:{Origin:process.env.DATCO_E2E_BASE_URL!},data:{}})).status()).toBe(400);
 expect((await page.request.get('/api/capability/catalog/source-system%3A'+'a'.repeat(24))).status()).toBe(400);
 await page.screenshot({path:test.info().outputPath('workbook-selected-registration.png'),fullPage:true});
});
