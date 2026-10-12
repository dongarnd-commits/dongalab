// Independent zero-dependency probe; not a production collector.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const endpoint = 'https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do';
const readKey = () => {
  const match = fs.readFileSync(path.join(root, '.env'), 'utf8').match(/^\s*(?:export\s+)?BIZINFO_API_KEY\s*=\s*(.*)$/m);
  let value = match ? match[1].trim() : '';
  if (/^(['"]).*\1$/.test(value)) value = value.slice(1, -1);
  if (!value || /[\r\n]/.test(value)) throw new Error('KEY_NOT_READY');
  return value;
};
function items(data) {
  const candidate = data?.jsonArray?.item ?? (Array.isArray(data?.jsonArray) ? data.jsonArray : null) ?? data?.items ?? data?.item;
  return Array.isArray(candidate) ? candidate : candidate && typeof candidate === 'object' ? [candidate] : [];
}
function sanitize(value, key, name = '') {
  if (Array.isArray(value)) return value.map(v => sanitize(v, key, name));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, /key|token|password|authorization|cookie|secret/i.test(k) ? '[REDACTED]' : sanitize(v, key, k)]));
  if (typeof value !== 'string') return value;
  if (!value) return value;
  if (value.includes(key) || value.includes(encodeURIComponent(key))) return '[REDACTED]';
  if (['pblancId', 'seq'].includes(name) && /^PBLN_[A-Za-z0-9_]+$/.test(value)) return value;
  if (['totCnt', 'inqireCo'].includes(name) && /^\d+$/.test(value)) return value;
  if (['pubDate', 'creatPnttm', 'updtPnttm', 'reqstDt', 'reqstBeginEndDe'].includes(name) && /^[\d\s:~./-]+$/.test(value)) return value;
  if (/^https?:\/\//i.test(value)) {
    try {
      const url = new URL(value);
      if (!['www.bizinfo.go.kr', 'bizinfo.go.kr'].includes(url.hostname)) return '[REDACTED_URL]';
      url.username = ''; url.password = ''; url.hash = '';
      for (const p of [...url.searchParams.keys()]) if (!['pblancId', 'atchFileId', 'fileSn'].includes(p)) url.searchParams.delete(p);
      return url.toString();
    } catch { return '[REDACTED_URL]'; }
  }
  // Conservatively redact all free text, HTML, contacts and filenames.
  return '[REDACTED_TEXT]';
}
async function request(key, page) {
  const url = new URL(endpoint);
  for (const [k, v] of Object.entries({ crtfcKey: key, dataType: 'json', searchCnt: '2', pageUnit: '1', pageIndex: String(page) })) url.searchParams.set(k, v);
  const response = await fetch(url, { redirect: 'manual', signal: AbortSignal.timeout(30000), headers: { Accept: 'application/json' } });
  const reader = response.body.getReader();
  const chunks = []; let bytes = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    bytes += value.length;
    if (bytes > 1000000) { await reader.cancel(); throw new Error('RESPONSE_LIMIT'); }
    chunks.push(Buffer.from(value));
  }
  const body = Buffer.concat(chunks).toString('utf8');
  let data; try { data = JSON.parse(body); } catch { data = null; }
  const list = items(data);
  const meta = {
    page, status: response.status, contentType: response.headers.get('content-type'), bytes,
    json: data !== null, topLevelKeys: data && typeof data === 'object' ? Object.keys(data) : [],
    count: list.length,
    fields: list[0] ? Object.fromEntries(Object.entries(list[0]).map(([k, v]) => [k, { type: Array.isArray(v) ? 'array' : v === null ? 'null' : typeof v, nonempty: v !== null && v !== '' }])) : {},
    externalId: /^PBLN_\w+$/.test(list[0]?.pblancId ?? list[0]?.seq ?? '') ? list[0]?.pblancId ?? list[0]?.seq : null,
    total: list[0]?.totCnt ?? null,
    rateLimitHeaders: [...response.headers.keys()].filter(k => /ratelimit|retry-after/i.test(k))
  };
  if (response.ok && data && list.length === 1) {
    const sample = JSON.stringify(sanitize(data, key), null, 2) + '\n';
    if (sample.includes(key) || sample.includes(encodeURIComponent(key))) throw new Error('SANITIZE_FAILED');
    fs.writeFileSync(path.join(__dirname, `sample-page${page}.json`), sample);
  }
  return meta;
}
module.exports = { readKey, items, sanitize, endpoint };
if (require.main === module) (async () => {
  if (process.argv.includes('--check')) { readKey(); console.log('KEY_READY (value hidden)'); return; }
  if (process.argv.includes('--phase2')) { await require('./phase2.cjs').run(); return; }
  const key = readKey();
  const results = [];
  for (const page of [1, 2]) {
    const result = await request(key, page); results.push(result);
    if (result.status !== 200 || !result.json || result.count !== 1) break;
  }
  const summary = { endpoint, method: 'GET', authParameter: 'crtfcKey', request: { dataType: 'json', searchCnt: 2, pageUnit: 1 }, results };
  const output = JSON.stringify(summary, null, 2);
  if (output.includes(key)) throw new Error('OUTPUT_CHECK_FAILED');
  fs.writeFileSync(path.join(__dirname, 'observations.json'), output + '\n');
  console.log(output);
})().catch(() => { console.error('PROBE_FAILED: raw URL/body/error suppressed; check network/runtime and local configuration.'); process.exitCode = 1; });
