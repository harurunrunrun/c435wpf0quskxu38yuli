import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import compiler from '../vendor/typescript.cjs';
import path from 'node:path';

// Local preview is dependency-free. The same flow source drives both builds.
export async function compileLocalModules(site, output, base = '/flowchartcp/') {
  await mkdir(output, { recursive: true });
  await writeFile(path.join(output,'package.json'), '{"type":"module"}\n');
  for (const name of (await readdir(path.join(site,'src/lib'))).filter(name => name.endsWith('.ts'))) {
    const sourcePath = path.join(site,'src/lib',name);
    let source = await readFile(sourcePath,'utf8');
    source = source.replace(/import\s+(\w+)\s+from\s+['"]([^'"]+\.json)['"](?:\s+with\s*\{[^}]+\})?\s*;/g, (_, binding, specifier) => {
      // Only checked-in JSON imports are inlined. No runtime network fetch.
      return `const ${binding} = ${JSON.stringify(JSON.parse(readJsonSync(path.resolve(path.dirname(sourcePath),specifier))))};`;
    });
    source = compiler.transpileModule(source, { compilerOptions: { target: compiler.ScriptTarget.ES2022, module: compiler.ModuleKind.ESNext }, fileName: sourcePath }).outputText;
    source = source.replace(/(from\s+['"])(\.\/?[^'"]+)(['"])/g, (_,prefix,specifier,suffix) => `${prefix}${specifier.replace(/\.ts$/, '').replace(/(?<!\.js)$/, '.js')}${suffix}`);
    source = source.replace(/import\.meta\.env/g, `({ BASE_URL: ${JSON.stringify(base)} })`);
    await writeFile(path.join(output,name.replace(/\.ts$/,'.js')),source);
  }
}
import { readFileSync } from 'node:fs';
function readJsonSync(file) { return readFileSync(file,'utf8'); }
