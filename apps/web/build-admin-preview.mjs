import {build} from "esbuild";
import {mkdir} from "node:fs/promises";
import path from "node:path";
const out=process.argv[2];if(!out)throw Error("Output directory required");
await mkdir(out,{recursive:true});
await build({entryPoints:[path.join(import.meta.dirname,"src/ui-preview/admin/entry.tsx")],outfile:path.join(out,"preview.js"),bundle:true,platform:"browser",format:"iife",jsx:"automatic",minify:true,define:{"process.env.NODE_ENV":'"production"'}});
