// Bounded second-phase observations only. No production parser or binary storage.
const fs = require('node:fs');
const path = require('node:path');
const { readKey, items, sanitize, endpoint } = require('./probe.cjs');
async function run() {
  const key = readKey(); let requests = 0;
  const result = { requestBudget: 6, pagination: [], detail: null, files: [], changes: [] };
  const save = () => {
    result.requests = requests;
    const output = JSON.stringify(result, null, 2);
    if (output.includes(key) || output.includes(encodeURIComponent(key))) throw new Error('SECRET_CHECK');
    fs.writeFileSync(path.join(__dirname, 'phase2-observations.json'), output + '\n');
  };
  async function get(url, prefix = false) {
    const u = new URL(url);
    if (u.protocol !== 'https:' || !['bizinfo.go.kr', 'www.bizinfo.go.kr'].includes(u.hostname) || u.username || u.password) throw new Error('HOST_BLOCKED');
    if (requests >= 6) throw new Error('BUDGET');
    requests++;
    const response = await fetch(u, { redirect: 'manual', signal: AbortSignal.timeout(30000), headers: prefix ? { Range: 'bytes=0-63' } : { Accept: '*/*' } });
    const meta = { status: response.status, contentType: response.headers.get('content-type'), contentLength: response.headers.get('content-length'), contentRange: response.headers.get('content-range'), rateLimitHeaders: [...response.headers.keys()].filter(k => /ratelimit|retry-after/i.test(k)), redirect: response.status >= 300 && response.status < 400 };
    if (meta.redirect) { const loc = response.headers.get('location'); meta.sameOfficialDomain = loc ? ['www.bizinfo.go.kr', 'bizinfo.go.kr'].includes(new URL(loc, u).hostname) : false; }
    const reader = response.body.getReader(); const chunks = []; let size = 0;
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      if (prefix) { chunks.push(Buffer.from(value).subarray(0, 64)); size = chunks[0].length; await reader.cancel(); break; }
      size += value.length;
      if (size > 1000000) { await reader.cancel(); throw new Error('BODY_LIMIT'); }
      chunks.push(Buffer.from(value));
    }
    return { meta, body: Buffer.concat(chunks), disposition: response.headers.get('content-disposition') };
  }
  async function api(page) {
    const url = new URL(endpoint);
    for (const [k,v] of Object.entries({ crtfcKey:key, dataType:'json', searchCnt:'0', pageUnit:'2', pageIndex:String(page) })) url.searchParams.set(k,v);
    const { meta, body } = await get(url);
    let data; try { data = JSON.parse(body.toString('utf8')); } catch { data = null; }
    const list = items(data);
    const observation = { page, pageUnit:2, searchCnt:0, ...meta, json:data !== null, topKeys:data && typeof data === 'object' ? Object.keys(data) : [], count:list.length, total:list[0]?.totCnt ?? null, emptyShape:data && list.length === 0 ? sanitize(data,key) : null };
    result.pagination.push(observation);
    for (const item of list.slice(0,2)) result.changes.push({ page, pblancId:sanitize(item.pblancId,key,'pblancId'), creatPnttm:sanitize(item.creatPnttm,key,'creatPnttm'), updtPnttm:sanitize(item.updtPnttm,key,'updtPnttm'), different:item.creatPnttm !== item.updtPnttm, period:sanitize(item.reqstBeginEndDe,key,'reqstBeginEndDe'), contentPresent:!!item.bsnsSumryCn, attachmentPresent:!!item.flpthNm, printFilePresent:!!item.printFlpthNm });
    return { observation, list };
  }
  try {
    const first = await api(1); save();
    const total = Number(first.observation.total);
    if (first.observation.status === 200 && first.observation.json && first.list.length <= 2 && Number.isSafeInteger(total) && total > 2) {
      const last = Math.ceil(total / 2); result.lastCandidate = last;
      await api(last); save(); await api(last + 1); save();
    }
    const old = JSON.parse(fs.readFileSync(path.join(__dirname,'sample-page1.json'),'utf8')).jsonArray[0];
    const detail = await get(old.pblancUrl);
    const html = detail.body.toString('utf8');
    const ids = [...html.matchAll(/PBLN_\d+/g)].map(m=>m[0]);
    const hrefs = [...html.matchAll(/(?:href|src)\s*=\s*["']([^"']+)["']/gi)].map(m=>m[1].replace(/&amp;/g,'&'));
    const fileLinks = hrefs.filter(v=>/getImageFile|getFile|download|fileDown/i.test(v));
    result.detail = { ...detail.meta, pblancId:old.pblancId, idInHtml:ids.includes(old.pblancId), htmlBytes:detail.body.length, tableCount:(html.match(/<table\b/gi)||[]).length, fileLinkCount:fileLinks.length, sectionLabels:['사업개요','지원대상','지원내용','신청방법','첨부파일','공고문','신청서'].filter(s=>html.includes(s)), apiFileReferencesInHtml:[old.flpthNm,old.printFlpthNm].map(v=>{ const u=new URL(v); return { field:v===old.flpthNm?'flpthNm':'printFlpthNm', fileIdInHtml:html.includes(u.searchParams.get('atchFileId')) }; }) };
    save();
    for (const field of ['flpthNm','printFlpthNm']) {
      const file = await get(old[field], true);
      const b = file.body;
      const magic = b.subarray(0,5).toString('ascii') === '%PDF-' ? 'PDF' : b[0]===0x50 && b[1]===0x4b ? 'ZIP_CONTAINER' : b[0]===0xd0 && b[1]===0xcf && b[2]===0x11 && b[3]===0xe0 ? 'OLE_CONTAINER' : 'UNRECOGNIZED';
      let ext = null;
      if (file.disposition) { let decoded; try { decoded=decodeURIComponent(file.disposition); } catch { decoded=file.disposition; } ext=decoded.match(/\.(pdf|hwp|hwpx|zip|docx|xlsx)(?:["';\s]|$)/i)?.[1]?.toLowerCase() ?? null; }
      result.files.push({ field, ...file.meta, prefixBytes:b.length, magic, dispositionPresent:!!file.disposition, filenameExtension:ext, binarySaved:false }); save();
    }
  } catch { result.failure = 'REQUEST_OR_PARSE_FAILED_RAW_ERROR_SUPPRESSED'; save(); process.exitCode=1; }
  console.log('PHASE2 complete; sanitized observations saved; request attempts: ' + requests);
}
module.exports = { run };
