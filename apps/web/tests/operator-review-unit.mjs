import test from 'node:test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const bundle=await build({entryPoints:[fileURLToPath(new URL('../src/portal/operator-review-flow.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',write:false});
const {ReviewCommands,readOrigin,writeOrigin,usableReview,sameReviews}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));

test('return context is actor-bound and uses a closed list of destinations',()=>{
 const q=new URLSearchParams({context_actor:'A',company:'C',version:'V'}),origin={page:'dashboard',view:{search:'TEST query',filter:'NEEDS_REVIEW',page:6,scroll:120,inbox:80}};
 writeOrigin(q,origin);assert.deepEqual(readOrigin(q,'A'),origin);assert.equal(readOrigin(q,'B'),undefined);
 q.set('review_from','https://untrusted.invalid');assert.equal(readOrigin(q,'A'),undefined);
 q.set('review_from','improvement');q.set('review_page','-40');q.set('review_scroll','Infinity');
 assert.equal(readOrigin(q,'A').view.page,1);assert.equal(readOrigin(q,'A').view.scroll,10000000);
 q.delete('version');assert.equal(readOrigin(q,'A'),undefined);writeOrigin(q);assert.equal(q.has('review_from'),false);
});
test('a confirmed POST is retained until UI completion, even after later GET failure',async()=>{
 const commands=new ReviewCommands(()=> 'KEY');let calls=0;
 const post=async body=>{calls++;assert.equal(body.expected_ordinal,0);return {id:'SAVED'};};
 const body={expected_ordinal:0,decision:'NEEDS_CHECK',note:'TEST checked'};
 assert.deepEqual(await commands.execute('judge',body,post,async()=>undefined),{id:'SAVED'});
 assert.deepEqual(await commands.execute('judge',{...body,expected_ordinal:1},post,async()=>undefined),{id:'SAVED'});
 assert.equal(calls,1);commands.clear('judge');assert.equal(commands.key('judge'),undefined);
});
test('lost response requires explicit reconciliation and never automatic POST retry',async()=>{
 const commands=new ReviewCommands(()=> 'KEY');let posts=0,reads=0;const body={expected_review_ordinal:0,decision:'USE_FOR_REQUEST',note:'TEST checked',question:'TEST question'};
 await assert.rejects(commands.execute('candidate',body,async()=>{posts++;throw Error('connection lost after commit');},async()=>{reads++;return {id:'REVIEW'};}));
 assert.equal(posts,1);assert.equal(reads,0);assert.equal(commands.key('candidate'),'KEY');
 const row=await commands.execute('candidate',{...body,expected_review_ordinal:1},async()=>{posts++;},async key=>{reads++;assert.equal(key,'KEY');return {id:'REVIEW'};});
 assert.deepEqual(row,{id:'REVIEW'});assert.equal(posts,1);assert.equal(reads,1);
});
test('failed reconciliation blocks writes and an uncommitted retry uses the identical key/body',async()=>{
 const commands=new ReviewCommands(()=> 'KEY');let posts=0;const received=[];const body={expected_review_ordinal:0,note:'TEST checked'};
 const post=async value=>{posts++;received.push(value);if(posts===1)throw Error('offline');return {id:'REVIEW'};};
 await assert.rejects(commands.execute('candidate',body,post,async()=>undefined));
 await assert.rejects(commands.execute('candidate',body,post,async()=>{throw Error('GET failed');}));assert.equal(posts,1);
 await commands.execute('candidate',{...body,expected_review_ordinal:4},post,async()=>undefined);
 assert.equal(posts,2);assert.deepEqual(received[0],received[1]);
});
test('ambiguous intent cannot be changed; a definitive 409 permits a fresh explicit command',async()=>{
 let sequence=0;const commands=new ReviewCommands(()=> 'KEY-'+(++sequence));const body={expected_ordinal:0,note:'TEST first'};
 await assert.rejects(commands.execute('judge',body,async()=>{throw Error('offline');},async()=>undefined));
 await assert.rejects(commands.execute('judge',{...body,note:'TEST changed'},async()=>assert.fail('must not post'),async()=>undefined));
 await assert.rejects(commands.execute('judge',body,async()=>{throw Object.assign(Error('STALE_REVIEW'),{status:409});},async()=>undefined));
 assert.equal(commands.key('judge'),undefined);
 const key=await commands.execute('judge',{...body,expected_ordinal:1,note:'TEST changed'},async value=>value.idempotency_key,async()=>undefined);
 assert.equal(key,'KEY-2');
});
test('reuse requires the latest USE review and exact explicit edits, not a checkbox inference',()=>{
 const r={id:'R',decision:'USE_FOR_REQUEST',note:'TEST earlier human review',question:'TEST saved question'};
 assert.equal(usableReview(r,{}),true);assert.equal(usableReview({...r,decision:'EXCLUDE'},{}),false);
 assert.equal(usableReview(r,{question:'TEST edited question'}),false);assert.equal(usableReview(r,{note:'TEST changed opinion'}),false);
 assert.equal(usableReview(undefined,{}),false);assert.equal(r.decision,'USE_FOR_REQUEST');
 assert.equal(sameReviews(['R2','R1'],['R1','R2']),true);assert.equal(sameReviews(['R1'],['R1','R2']),false);
});
