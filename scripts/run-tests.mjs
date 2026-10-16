import { readdir, readFile, writeFile, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import compiler from '../vendor/typescript.cjs';
import { compileLocalModules } from './local-modules.mjs';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const temp=await mkdtemp(path.join(tmpdir(),'flowchartcp-tests-'));
try{
  await mkdir(path.join(temp,'tests'),{recursive:true});
  await writeFile(path.join(temp,'package.json'),'{"type":"module"}');
  await compileLocalModules(site,path.join(temp,'src/lib'));
  const names=await readdir(path.join(site,'tests'));
  const tsFiles=[];
  for(const name of names.filter(name=>name.endsWith('.test.ts'))){
    let source=await readFile(path.join(site,'tests',name),'utf8');
    source=compiler.transpileModule(source,{compilerOptions:{target:compiler.ScriptTarget.ES2022,module:compiler.ModuleKind.ESNext},fileName:name}).outputText;
    source=source.replace(/(from\s+['"])([^'"]+)\.ts(['"])/g,'$1$2.js$3');
    const destination=path.join(temp,'tests',name.replace(/\.ts$/,'.js'));
    await writeFile(destination,source);tsFiles.push(destination);
  }
  const jsFiles=names.filter(name=>name.endsWith('.test.mjs')).map(name=>path.join(site,'tests',name));
  if(!tsFiles.length)throw new Error('Flowchart tests are missing.');
  const result=spawnSync(process.execPath,['--test',...tsFiles,...jsFiles],{cwd:site,stdio:'inherit'});
  process.exitCode=result.status??1;
}finally{await rm(temp,{recursive:true,force:true});}
