import {build} from 'esbuild';
import {mkdir} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
const base=import.meta.dirname,require=createRequire(import.meta.url);
for(const portal of ['company','operator','admin']){
 const out=path.join(base,'.role-portals',portal);await mkdir(out,{recursive:true});
 await build({entryPoints:[path.join(base,'src/portal/'+portal+'.tsx')],outfile:path.join(out,'portal.js'),bundle:true,platform:'browser',format:'iife',jsx:'automatic',minify:true,define:{'process.env.NODE_ENV':'"production"'}});
 if(portal==='company'){
  const cli=path.join(path.dirname(require.resolve('@tailwindcss/cli/package.json')),'dist/index.mjs');
  execFileSync(process.execPath,[cli,'-i',path.join(base,'src/ui-preview/company/preview.css'),'-o',path.join(out,'portal.css'),'--minify'],{cwd:base,stdio:'pipe'});
 }
}
