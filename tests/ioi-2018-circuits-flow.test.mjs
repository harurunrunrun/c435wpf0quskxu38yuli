import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';
import { isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

const site = fileURLToPath(new URL('../', import.meta.url));
const json = async relative => JSON.parse(await readFile(path.join(site, relative), 'utf8'));
const cases = [
  { id: 'alternating-switch-bit-reversal-pruned-router', problemId: 'ioi2018_doll',
    domain: 'thinking', prefix: ['operation-goals', 'alternating-switches'],
    parent: 'thinking-operation-goals', parentNode: 'reason-task', graph: 'alternating-switch-circuit-conditions',
    guards: ['alternating-local-state', 'ordered-return-reset', 'bounds'],
    feature: 'data/alternating-switch-circuit-problem-features.json', group: 'construction',
    statement: 'https://www2.ioi-jp.org/ioi/2018/tasks/day2-doll.pdf',
    editorial: 'https://www2.ioi-jp.org/ioi/2018/tasks/day2-doll-review.pdf',
    terms: [/スイッチ/, /X/, /Y/, /原点|基点/, /200000|20万/, /2000万|20000000/],
    articleTerms: [/AlternatingTriggerCircuit/, /build_alternating_trigger_circuit/, /popcount/],
    cppSha256: 'ec7888a3cf046dd5d72d48429c83b1113d401c82558d0e36899cb1591be7a973' },
  { id: 'binary-weight-distance-oracle-edge-split-endpoint-search', problemId: 'ioi2018_highway',
    domain: 'interactive-oracles', prefix: ['binary-edge-distances'],
    parent: 'interactive-oracles', parentNode: 'response', graph: 'two-weight-hidden-endpoints-conditions',
    guards: ['fixed-known-graph', 'two-weight-shortest-distance', 'bounds'],
    feature: 'data/two-weight-hidden-endpoints-problem-features.json', group: 'construction',
    statement: 'https://www2.ioi-jp.org/ioi/2018/tasks/day2-highway.pdf',
    editorial: 'https://www2.ioi-jp.org/ioi/2018/tasks/day2-highway-review.pdf',
    terms: [/無向/, /連結/, /固定/, /最短距離/, /90000|9万/, /130000|13万/, /50/],
    articleTerms: [/BinaryWeightHiddenPair/, /find_binary_weight_hidden_pair/, /int64_t/],
    cppSha256: 'b7e618bcd9befb83f25499a950bde4c6feed4c0be5340bbbaa81f031731d9715' },
];
const candidates = value => value.current.techniques ?? [];
const matches = (row, current) => String(row.source).toLowerCase() === 'ioi' && row.problemId === current.problemId;
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const xml = value => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// This compact fixture contains only old graph/node IDs and original answer
// IDs, derived from the independent pre-batch raw freeze (455 graphs/3601 nodes).
// The hash below fixes every complete old graph/node field after projection,
// including labels and ordering, while future added branches remain possible.
const oldShape = JSON.parse(gunzipSync(Buffer.from('H4sIAAAAAAAAA+V9yZqjuNL2vXhdLP7rqacXMmBbnRjcDDnU1f8xaAQJgioP58vanFOdFiCFQqEY3/j589Cr9lwPhx8/fx6mW6VG+vdBnc99fYb/Ks6dauBPh/+muv8qRn3FAYehbupyrKsC/v9atyP/Dca0ZV2UF/POw9S+td1HC//S7Vj376op6ra6dfBfxXDpdft2+OfH2E/1P/DN8lKXb/jxL3q27YIX/PPjBNOgYRN8oh+Vhre2U9MEP9D0i76bxnr+2zCqUZfp32ZrTQ8Klp/5wpwiuWExkdKjctRKjP4Hx9MmFrxI2krdvgORtompmqZgugnGDkNXzmfa1+XUD/pd8Pyf7u+tr0/6c/7XSp9OdY8kXfzSTcdGt+f53+EfzVHhVOK/v+m2wul1JSyJ3uiY37PIqeuvxOzTFbkatoloFyzEsvP8NVvMR29e32C3Uz8PsL2D7tphm57EP/PPdqcTkOYZm4bzHMZ6OYVG/fqSb2Zu0/gYFXbv+LDAyZn85k2tRtqav9bwhZLkVaOvGg8s/90LLWDpEf7d4Lbe1DBGcuykj12rylIXqqqC3XYPFUKK+Qf6epiaBXkWK0nzT3Jx6aHJ9aaHRqtc58kPoHz3QTz5p7yS2+MPBeKwiq8lWoQ5iEXZtZUe+TgcTrUa9BHoyhIZ/po8nvNXZcR19PYMsRYfXKeYP3skf7sPXts60YZOIs77+tpJRPEEe7Y9ysgYgYhRPSykbh4vToaPur4t76Cur+p+8ecuzU55kXRUY3mBbVR9eVlIzJY3TcCytNfVjTa4gjur5Q0uL52Gy4COYaQv0a6xrLo1qiT1gVQNElLtG5zZM3DUDQec6xavHGSyCyyi678i8XTRVVW3BWzISCx7R/UKtYuMdlXCL2eYSjFbYmZUYuGZkXNyZIbNiJQZlSJdPHROvdw5rm6ka9V3kXrmTbNJg7QZe0U3909UM65euoR319iNzDhM01GDzhhJw6Xgm71s/a7g96+psrNPrpAM1tMOzJVIN6Ozoh61KdZo6FULRBEwFKl8m/J0Og61QKLCyt67ZhpFchAlhOpFd79RDQVa9+n0HEUtqV3DDk+JjT9fE9LzVz2q+d/acTHsqsZ++SFPkow+xHTI3MAZxcHd8YcfEb+ZxTJHHViDMf/BfEGiuO+qqRzNE4O6gpZZf5F+eKvVmDxb/r1SNZCvHOHgcNqJmyt56q4dLNvYhGxUbn/nrZ3GS3HsQE0QGBj2ZpSNcxPa4vv+LDvwxE7ANKr62h5N8gyn0I2dZM5MCeH2/OkRpI8tzaR+AA5JH4rhqj4WXF/pd12JzwhNrygVCHDn/fGSHVZwbLryLX2V0E8FTULM78EjiTVZrnVSDyYO5o1AnjfdrRYwK/pxtGRg1V2VhP/K7grHchC8cRR990+ZyPI2bMhSv9WtIi1taYxrNAg7sdU99e+ixdC4QkrL/yZV9caHJXtz+li496yxGN7s9SercCDpBLrArW5VMwqkjHv1XTjipuuy/tCDRMTejIYr2Rua5LNkm2p03S50czq1cpvq3KvbhX3VwwUM4nqgXftQzZvz9lS6Zz8s3N9nPpiHth4/uv4Nt7x1LoG+60jD7WvvKiILovDKd+zDRhukKlTfazJa7mdaZY+ZNV3CFWaGJNadGZmiRmZogkY542pJuXhkTLycmWC3FWwwvAp/kkJfs7aJNxsYS+Q87wbaG/tjcQVLkkzhq2q/gpXhoM+uJwJGewnj4LrDmdcVu/3qTwXa3hu9O9jb+Jtp/XM2jcyg2czSo+xkM4Y2M9rixeFS0k+Gq8sR307uXZOQm4sT5jA0i+1xMVEVmDI6Q38Y9xP+NzAgzAgdGOMF/n3pGvwdr6WrQtabZkcLLnm769a1F25B9OHVCA/PJT1kMb30MDfjwn14SfIeHQ5498OassGe5HYtl5rbDzp2FHii3RhBJWaTFfkRFzAUsPX0JvaEHukJ7xq91aU+aXT5gtzRZc3ykfk5Ij85g8FuLnhyoZt0+amcpzT8embMYkIZugFJ+05XInrO5r5KTOOUS76HBnTHf+kE1KwGW3/uoH8R8XDacGc6mWAPgjk51gcV/L2BSVV8oo+qWRDekpfZ4QZ3AHovgpslfMFK3NFNMj0oOe8M7VNLycSuUpPP0f/UoI2NZir7ZzK7cJv6W8eqzk3p3lGSPIHkBQwi0gpslPHLU5u9j2j/DKGYStjp7tXplc2/losJhxPIiYDEnLK3H5iy7ZkVHNivsRjVQHoFChrV64EUF/ihV1aL8WEr8oEX49Rn/H5/7Kecjjy/HN/YKeYuIDvrHKFW4lHB2tZpxxxGBLQOLec26evGXmZhcNZZhAdyUKK5Ccyv21t8R92PkL/Srjc/vwwNFlPOXF+LVWyQzG0sR6RuYOZwHJyIDuoknPKBfqbLQ7egSLAPjA5mxz7dwjnb4psd+OKKvzYN/Vn/h7FH+ts9eVNd0yzjZ58m1nxBGXGwXGP2EJjFZqO1fv0b23IDk6mt+u7KbhA7U6TS+HWDGYB8/kAl+QDMA3ttmYKM2cGLhgJ0uGHq43sHLICiq8hYQCcn/KWp2zNI8VPPwZmvO+5ODX+Gy3XBqMEqcmHo5cLWpYdZa+ZkxIvORD5mdMjt0tUaKO10PaJwMqIavaxn+G943Embo4Z5V/rMcT9aB+6wC974fQE2BCUG1B9FAeWJck1gnEbrwko0ikrTjdL19IxqMKhM8QzQB4hYA3we9vyJNmpi4ZmRETlykcQ5keaq/JxOmS2PSJeP8Rtq5uwGR+CcDhbQPG9dXdH/BvqSLgfvdnKpK6zIee2ddZDYF4FT9er91/Vaj7MAMNqPID9uTWRBsSo3+0K8Bh6S+GhqWDiP+Hdd1awT8bIE+nsw4xzp7BG71J2xhQI18VxWhXHgHZryaoPKSCDeDy/jWgxTvuuKxavukYoX1ZxIKlynZmS6gUQFTQX2CbY9NF+XqgB8W+Jou/UUvd4MZZgZbI+8TJIQSjD3x3udj3pauvd0/Z5UFFP+KXZOS8UO7XTyLOYOIfJRsP/JAcQMmRCj5YgMj6rmXB97ZbJ66N/BnVDVn+wvIBFgroWyq08nXZKAcqeaFRFyutlwuXFiJTkw9eqcbjL/Wk7aLSeQ9VVJApyDXor5PVH1dhxz4S+juW9JGXYe150Rlz/9f7gt4nQ7ayCTP7Atm441x/psdsEn7UXaLkVKMbISmhhAvve6CVJxIq1Y9yW85aIwikHX9tsXRUfh+/1TXcuLhWfGJciRcxoniZTTBRKkywxdEnQ2MKJpRjqEZM4d5TPG+uHWOKqjbqwvtP684bpkLIv+we5dELWsQd40XXd7vITm3BRazUw7z+lrvGLymcl4iugWedA+OKeiZFcwvzD2+8IlbI2vWPhpVo3ZBBg7MP0VhwE4Yeo0Nda4C04LfanAeQhoT2MzgmXq3zFOMeOCzQQHYBvQU6xGt5WBZL6RngJTIM3FROh+anJ2jqNW3lUeEjDrMr3o9s36BUAJRt+OlZcuNOC8bBjiRcajyyjIQGvRkcVuMNy8KxrH9ae6ksLnjNVE/nz8hVxQJfHRzOXv55EhS2pqq479TYY4DphxkxJW6XMakR23pzsZ4cMGrjRFaHucbt9BGihJ2NtkFEii8t4k2VaKJ0xHMtR+vPizFMycNkeOzO8mcyIjLcyqMz/HS80MyslU66swGc7b2x8Mz2Y/OA7zWawuI3brC3BdoNSqJZwjZweK7EsTQTHMKUmyxPz1J7BWMoG37XoQJ/pXQr3GDUpIBDV9wj2TMIHMQvYwDu3ypZ56dBpyRdh6xQ+qq2h6jokYFAjA27RM4+yqOuPl/FOCzqayEq5mge9yWEw22/an0T0+NUrA7eY2EJjk0gO0V/LZW2CT3dXC3wIyQC8N8LqdrqZsTcDI+A99WjAlzOq9XnxwahN/5826dB3wMOqgnLVDVSNWkd9enHX32fHW4zPcQDdDPRG4KZ/zLk1yIodcJnQN38m4Bsyncy7/DJdzJkZGQtsYALst4b9AZpAP/6evUzySkCdXIexzV0XHmYiLCiz/FORs8tXgo0kC3j5mr5MfP83HC846FbzMjF99GSinzW9KldxFmk98jyglTsWOn9rYR8r9uakRzn3Lvl/UaUmPDvfhoN4p6yEKn5F+e0jWlcJR6xslMB6DZzLZ9fjhgmMfgtxsGq3bCyx+lFSv8QMZ9ehB+2ooR0k6jUsh20j61XSSOUnWFsZvrY2s3YIMVfHoHL+QHlSclG7saZ9am9knoRE95wxQVpRM9kfayGql6tSx11VWfcbX2K8IqgoxF8VWtkvED+WMP5d7XDql3wtHrCLIoerGS532zEYjs64m2u8o3vIzrP7yhc3Gd4Oqy9GWqXEEIyyaTua64JPiHGwzPOOU+Oicp1qgY5mJajiAupTmJeM3BpUzxPxiw0Dj9rl2Tz2RjcITbXQEEvouDwBdEoKPkgsMPZaSerWvMmtjPnqRxPHofDIJC1KxVdVnSs4L+HhTL8dPlXj/KYnwcjN7OmVM6BJO9LmfzNp8TYstGDwMaOOpJlbhWLXg8rTQy8lPFaLgoxmbXrb5Ec5nN1AJ+4Iu/Uj3J5yzo8hLA+NxUzDZTzY6sx/wy8qsHqUJMsED+2j1E66QBI8cbSt7EMmnLQhr1fp8Ac26gNtNUpSH4RfpZf0aKYD5EVHKOP/JqrpAVFJHwogYl1tykkfE/Jhh4PCIOJnLQlews3l4C0JGQQTgonoPwiNwbuKkUNmT3I3m5ekcsZWi8R+23viP/CW7+Rk/KFRL3SZgCQMIrOGiBWYFPnWp1XvWMVqP1kZxFRqbporZ6iy14q3PJtHZnDEX9GaGdPzJcXnjIjw0HaY31p+3mAltLkEXpsSbpwq4xAUMZkdLbSs7PiOxu3MhKlzFgZSR1UtkC46WThDHpicH5Ct+1X0ncavddswOR0tnh2OfaykETJL3VPrUC+OhZ26k7A0fucLZcaIH2A3/Mm4Thh66q47Eo+dFTJ6S8SGOdImPGdWav1n0IgQFPzwXMaFp0/QkRp4d79K19j7x9Pvu1jVfZgrOKPKeHZ+nd9En2kjOhAnkC/0/GDvXWboeIzT1NVpsorAPP2Dyx4ypJX0qI7px0oXLehJsID8h3j0enuEdpJRP9JBwDz3hj4ps/HMFRbTb6xBRrqaJqtowhsO8xSiE1ifwxtnfLlP5mnHywLhCDPiGg6nwRRhxxPFpOsJ05J/FwTJUKhzp1yx1a+BTz5YPREaXhDkIwnDLqLvEM0cQIn19a5QEAQMn9Rr/gK1tZUr0NZZESVwa3hNrES4PFgkxwe2mENRaZVtiaMzhBJg7U7xhfBVLOPiTEs2ZiM+/tHxGk83/mV1cJUyN87TO9Aa4J0pKFLHOawNNBqIqrqnuFbkg8WfKyz9EdYyUe27gCiWhOH4gTR6cGPlWe30UZpHSI742XjR85eO6PWlQbJaVlkSrAu9trKMS2aDmmV25ZuaZzOWNvkKL1SuMSDgcx98OYPDt9WYLQQRRXRwtxN6gsUEO5pPvbmTtTLKd5fZs4SuXJQOrnpkq5CtAU8AUW2+LbH4UlAFJoqgdjfEv3U6SOgHzxPNvBaoluXHqwk8GuSxudSfKiwBLvi3OougnjrSpTpKxT5fJdX+dDF8PH+pmfGfwL6frqf6ox56ygyxoqAsAJWI+wQul8ZrwmYxYwQl5zAPB5YoPNLUSpK/Q0IHypcRvXZvmk73HgZYTAIa0nLhhEQ/dL+OHQEtAIV6I8WGDr2IOC6XVC7+Rv0NeQsWqLvUVTGrdlphzbPOPuQYXbh7zu2Bx6I1H0Vt/jnUrQ7K1H3+6KLT1KBgM8O5zr5IRVpOB8j4MmjJJ3X8yHmPsWwCz3eVLhXoYvUho25nRH8KgQzDJHFPZiTdfZ1Hel/oquEAPxPL2cNRhuEIlneM7omeVc7Vs3YnEIRs8hjXLOx95ctZL3y1L6wJekKwg5kgHgrO0Emz0Eq4OVHZ1OTX031i7gAVA6cvJPVmENe3b5gA/I9QX/QP58gqaYoFFgbXBBpYpS+ZB4SGyDzyZEaI9yaaf2E0GhVQhKtPBpJ8QMpzMgqZH5d4KGs4+80puKtBTTxfKtsyGOb8m4YJfaruCcdYP+nqtK43A2MdO9Zi6x6HXqlcfsTimPCF/CDg/PG1S0KsyoUIO7D4zishHI1v3ahZCtEKiMK0sDD2JWSzgUm9U/TMalRVYrWBMCHRIYNGUxzPABCDCPaKBLvuA1N1VmtqP7TK+7UNZLQgmDJs7jp0EhZSHZxh1GjmUuC28pnyMhnEKdi3RgRtkylOQ1PveaJ4RaplmdCbjF6GYSFUTmCg49rlidIP78TzqkrjfejUnSc0JygcSLQIdCAR0B6ZF9YKEDspnYXHkl8j/LdwyUISuuqUgne56kWvLiL8nr5V0NuPc6uAfjdvQAexd3lPGkAsB9PS1q2z47xDWh9v6BNNSwqGKe+nVqnd9NpE6l0bqAj90ZtxbfCm++5MpDdBtgN/kRSHN1JpMEh3FIg0Wx6k6S4DxGS6PCJWVnb1mly8RScLpcHZMexrpNNwWZBySXfdWoA3ZYP8AA2O1OQ98SDoBGpzPiq7qUy0LZo+FxU4ReKfJc4ZAqXlz51ES0fOttFbCydDMPJcsv4JsFpyCTCLW8mDkpLerkCuoms2qLhV3snGHGddGEIdAjubgs9HMWw8D0KEiWW4xCCgzdVVXCdo/pbPJcphYs4/PjpyZSQ4B5L3OQBy96Pr0GxASe56mBfuBnSWCYoWEVekJOtTYj0iUr+ofauqzkkVe/DM0r5zgcaPkJRb+GaFi5R8A0QFURitpz1NUIvOCxBm/7edeVx7r2foWzDmbbrdMbQWfRk3UlaSL83GymMSi0TiHrMpKb2vUpzDRxk/3qgQVMjScFv/CnZnJmfmZdNXVoDgNNYZtYussiMdzETi80mtO2yzKSZAgy8u6kpUErJdJk+lgSh/bRnDMGSIWgxJyccKkeLLTb7Zv/jKabxmpI5giwhES+GfaP+cuEVFwzY1ek4ZuEId5gvYi4tfTk68jq7nRQwdo0DLFXVGJe0lVehqKfVWC5qGy1hK1mQfnrHuukdk5AfcY5vMW5FQWqc7uuZf46oy2wdskAgFSbMBLjvYO98i5h+t7UTJPU1yiKRk3628Rah/s1/zuDahF6o+ECmVPhRWio7vjmAtrYOqhVJIADBgKlcRf96dkPtZL4GHVtrVK9R2+6GVRu5EbiywamP1uvA/nzKdKIQOyYP4t97TbB9ByksCSmeEvC5ieVA+mlVltpeGMjXDHXyaJc8oNH0DbEjVYdU+8bL0fujLaMv1LuFIeK14mD39dEPz/RTctKM36Sl34THOC5EXboVUzBggjW5k+PN5d4+Innutuuar2okb4MKjPV2kag38oCzRgac1ojqYPJ4MhK2lZremOLOp1ddXtW/cxvOnXsdUsTP1zHiTdk9oUPymrepqFZJ/tzEcftGm8q44DKzKIVXu7qKPE0xm23NrQquj1L10hXKwgp40J48BAJKovmkkiy+f8AoMk2kQCVXFFsj9dfx2BOotFWdzpanszn43dYuD1bVMrNMRtEthRc1GQyB3w36R7yYb7Tz1/kdS79Kr6szbpNfLk6XrQ1SRRml2H1GSRDv/4ikQ/35SI6whv+r1jmbQH8wZrskWmKb3+6Vsc+vm7t0IBkc/t1ZUji8vlwO5Rpcw/nQ9IPbDUCUMzDUH3cv7ffKE2NWRbLv0nS1l333v2Uk9dX+Iy6x4je8sd5b9LlvqBCBAyYCf+5isK2KrCNIu0/i8hVoLYs2KiUk/HqrBt09CCtWBbAVKR/EiK02D4Qy8os9CIjtzD/1F81W6ka+O+J51Vsp/mSy9Zp+qpgtafR2tEGjXChWZdz07yvw0H06yvYMCetGf8cRCEwdw2WozydHMB3mAF2UYV1b+q5GalBH3SGd+J/fv2+lq0wjEFQJJawl95iZ48YkG4Sxg26UwCdqc0DJE/Et7/1CpyLpDowJbuMJ7omgWCEiRxi7ZwOiQ1fuYLL0nBItR9zvMzfXwwCUuUKWfxULdVZ3rzawTUp+mXyRtnsoa3PoY1ENujPl8gdKmN1wLA0Apda4Sxe8mB9uZBE2ELDdL6M7NU3DSzafJcHVAVjR5CgUIZbgJtVWkJgkbzXEgK3xZ30c6YVsf52Zv212jcD5J8QWr+/PS74KYwL8ClmvDquHy7EGOQiqFFTI/kp8tOF59kADrbav1gcYbE0UthXQuXRL9E3LjzGsDuuL9dTYeSLafIIM/x5K+it/slx5NziD3r+kbgAoBfhq8QZqDZ0VIs3zoPCWy8Oy8hGCVQWTY2AKoShm4Fc1qDQn/wskxoy4hra4xbbBRVYfkR97g//LCLTrAEux0EMs9+7yWLtf3kMR132LONvoPtthDoXlBUYYoILLy071sQ5h4LeFBEC/v216ySMPFc5yLSl1wfg+3QokSRZ9S9V6ytUXAyPno9T46U6HlKFkZDbwB94VVSVPdhzqZX6+tPzBq22jzWCIWNE8F2pOtmWNX0ZaiFnOdvipo3XY5NIwRD3OfBQCeCbAamLCHdYqHJWZzXLNTQA5ViE8xlk2eOM7ejcgjvEpmVwO9/3UpNGRCwqrfghAJ3F7/YDzx9peT+gzulhQ9gH2feS1tKuz1tbOAi0Qr47S9b3hEtj6Ye9y2vr0+NxzHYktDcBF7o2LcTejpF8MNvtetuzp1OHNyMPLPDNw0Eg4oa0HhuT4juE8KyiBLidwBymqWkSUhZyK9EZeIeDCwWdypr/KiDrWgJJYGv0NULElQ8G8l4lfu8/hwRhNa6ELSsWZR4z83rn39s4JGBwAoCXx66g2Sc2n1KQUhc0FuB0UZxFrfvy/1mpUqOS2PemcXifkVhl25N819WHuPz4n6U6FHsCJYk+vhvviiw2hCc5wc6hht7JwWA3htZAIPEjgu/9IpFEldihDLugg2CAtGMRek3J+y+MshaxLnPPXuxBjIIOws1hW3QwXsqA4GVaiP0BcwdcJLECgYvKlZaS9H8np7KRNDUJ0JzKBvY+CG2fO/mWaaXPz8ZD4F8WiezvHN4n1tGcCvwh17B28XYq/e6KQh5OVwh/0G4TjDm2Jlco/+dcZg/Lh2VXqu+vCR5VglF/9jdilyMiF//fBHISPVljZcMKA/OHyKkF4kzidjjV79C28O0ma8iNHts0PanfP7S3uOvCKREbWVU+zaTXYLV0R/EaKqEVyxF4TRzeo2bz5rViMwecTf+QejyEhDEQ/Y/PWaoUJFQ5YVQmgfrOBAnKEo7F9E3XuEVIaD0jqoebFihrz9UX+2yU/kR6binr5MqFijeaLucRq7pXRFuqe9Z4qRfCYE+jhhvCL2jbhyco7sbtWXfW8H+a0tgi928z5dNTf2py44glRHVwDpxG3VcAPVsCR4EQpcoZvTu59++I0zw3KApQMWNcHpD7N4dkU/3Aomq6hFhM2i5riLkBUkeFifb4OorI8mwdYSS5FsZyFXB6R0GLlHPYgaTR/T5Ul3dNHbjUxVhUzoKiHm+rm0MbpNrzKde0h3n3+5YuFR8WiH82fgTqlpVZLRUkzUw+Rbo4QGFvTA/b5oA8dnFatNHh6T94d6WzCzk96Z+cUmpz8tI/Oef1OpndJLapEex081T6BVXe7ypD1+s+eaLEpzpOu2m3sbo7r8+z7ZP7y+ky6DrFTq4bjsjJtMgklv04hcwqzUljbU83Bo9jrZCtVFf3XQ35ZLe/fwKNx+xKkKWmzFgpRFwi7vSuzrGtYCWHZ/DbTRdHJ8rZ8PFBiuSc6swFhSs/oXbibWKGMh0Zaf7nJuyQtsXteM0WMxh2Jab6boIVPCTYMFyv7b7zKsCtehR4xuTEqANXIp8c+WG4Ct8d6r6dxpwZa50zef2Sl3WstIvX8z7fHWYUe+na1uEAJ22WFNYKHRsulJi+RMY5WsEkc/08C4q8zep80myQNCuWvWanWSvqjXmTZddlwQrK6uB/xR26Gmtx+/Z2BW/agaBLz7Ulyuj8T0673Qk7ctfE/iuVd+ia03tT9KWA3RQueVLIj/wXbwqCi4JKOi+26X7SHBy6K0vEjbc1dJCv4f1QtJ+l9KAzysaDLvA3QktLf56Iih/LjGlj3qr5LVzGCSNV3W9dCTNC9+cwTLEn1+Q0+KB4TkneCRE+dZ1k2Ua2mz39c+HWSJbEs99bOxe4XHjBA4/iw89ttwMd0dfamnxgnn5ixbJGTJ89VoMMPES5UgIr4AAO3KBNKwFvj0ZXuU/bn+PenwIRPb0fFPG9YFou9Yp+r/lBqyvNwlQUvid13AprGdqusIX8YmXeFHNu8gYN594ze3bTePN9JTjf2bhKG3fzaBlR31VGNTtd9GFljuRLL713Ka87Oy/0MQ6cVJ7/h6kwbn8o+l0yiKpUUGYrU9+cqy0vFKbiRAyQ7c3iR9SdsnhB55+SVOPQOuq4oTi3YU7J1DcO4EdZT72ioAAdt523nrUlUxbZ/kiwX4QQXI9u32ayU+5XkHX4C6uVVVc4ev61uwTd5xnKPLF0Yf+h6pImAMxwsywDNSMz1TP3J2N/cdeEPa5IprGB3DzSP/L9u+uZRpBve3b+XhBCb69okzYhxL2SI/fs0KZuH1JMqDDlXW2Y4GzjW0h1qtdr5foPxWc7rErBszUIYOzLKe+p1fapOoDd8gKMJO3s9zT4fqVH3Ee6dZZfkLJ33tKO39u+Al1Ekd5xDLFHNUPtT+3XsZZL+miEq3Rbl0A1Hf/A+T441VnCHiQqwjgQFCD6aiX/d23lVj+2b1xdFXVbUGY00BqPdbXgmBZTzt1dtkSj/n6+Uei9w6gl6ElE8gyLH7ey7bW/b/lWQsk1LP1NCuXSQoC2xpM+wdwa/+K8h5TQkfKqPXZeSNzz142+ipJH6YPPnuV9TscSbjBqvpsUwBNUvje8IVsK7fzSB+pclLV+03XZRgpdetDgcFj6MuNphjyR0fxQ/rVeRuGpAIiI8F5EqbNi7v5yKm26uMmX0VT3th0HqbrbP8xlI8lC/Dqq/osrCKm+qMGOd5/FcZZ+O0oQwoqMYKXBECnmDpNhz650ZEFqeX/TbTlRoLfjTzsujNWTlN/FkHPiZhEXGP+dqC+PKM+Tx163lijDyBBvx+JOOxdg4rnilCKo2qrmDyUYoqJkFQf6bDeGbs+sIi+GXFAW9BdRS0T26EuJyrNp8NmkeMDGs3H0OEK2O2g2q9A+fqGctq2LaWGNdp6yq4I+RiTKhpIjHTDNnNV35G/GhUZsi8CAc5Dvx/NhkYNF1urWOUFlB+BD8zllDUSDSjBdyOSlTheRJEF1XXjTA+oauyAYyCafa81boDbdEfVfD/iUI6WbR1IhEG8Ur3Ixw+H4JdmCJy+VImp9x2pxGizxbFrsY1tllL1Z9lMFdbXIlQ5dgoN/9PR6XvqTEQosjfw0CAO+zBPwHV/nPOMgaX7pso2yhuQQQyZWatTsoCzrck0M5CvLIuxDxCjc8N/njXatesFXv+nyWQ6twERzMqvw5iKdtr+SNSlrjtFtz0nln43ynhA52MDH1i0GvDm/ogMBmSjcYcfFlDL/JfBoya0g+9HJYPgbxbJLeuXaTNTG4xjEe7VhOBvFr31+xDpR9j3BmgwbL8o0xJvXnZRfbXqStbO4rBagFz0rlAqGvzbYid+04uQvGrcV6owREoQxo5gtRNHWbtvHCxhzJjhmxLqrVW3geUZorpxbgDpWDGpCNbjRv4UFlz4b4y1HGzDqrK7Yvbf93QmuMSYiw6SAYuh7PqZrYcDOvYZIIlsNdTBeHr9f34zCnFDVCQK6pWgdo9hlrs38uyPVij50P1wYO+mfez7UijMCk5kWXmSOCotyObUre9IJ+dOqntFrQrTbhX0yfnBjpf6qTWKaXkB9QOO2zdUtLobchKs9th1YLT0pt0plpvFRPJdhe0jaMcgnI2F8yDB5IZ9P1Ido8ZgBWg+2PohzifiPGhynR86f+xQHH36MpPDrbtZnLGDRaf7pOvQe66O01dhGnV1TqbhS2ylj5v+DzLGqfZJfQbUdpPJpA+Z+aV/jaacqXC3q0j/HCwsk9jEa808HS1/fY6mKupPUp2yanZA2lw7NU9n09cWOGVuzMGPBiNV0zwqfTrVfZ2JJqkBlnYTAvn97x6XDz3URRfGzlLa89hj/iwWQf8VdClV33+duCVQJBXmsWwrLL4/SaiHpBEmhlmmRJWMLYGsxstfQZZQgCJDJIEQTI7l519BEXtjgBr7rymiTiY8Bf1NbDbv9yeOLX5GKB7imVB7mCcSYb/Av+MeCuWtKS92tdLz7CG8oQejiX1/yrCqT44/7Lec1mjR89o0dYPQlZhxRYmVDfYLG9G9inqpuvq+o5wN0lBz2VvXfJ2JQLC0W01I8O/spEUWBLml8H3UJJzfegj8t/CiW/2r02kfRzytjOoXzTSjQvrJpwck1pPJtg+WmB7hVp3rdu4JkXnBgjYP0Hn/WZAXxK06k5F41VWAjOHOjoXbsVv6/Y/OUKoGQahiDoO/LlQW6spram3+CtKwVAEt7txz7YDBsUIkImWaJYZpQPoMbHztjL/3+9MnEChApPf6kzKkbo1qsZ/05+xWQvHEw/4K4rAQBdJQtjlBuHf90pwmsjCe+19AFOYNuj2wJVqPIL/APHUzzzsA+2CgcX+HZgdWwFthbs0aAyucUTEkqwNIA+RhfwVx9NAN2MVvCJSFo0baoGUAasNtRiCnXJzI9/sXkAiRverT1GDta9VdsTS/RIiXtGe3huE9O3OHiz5QSpgrgjuYV2A9ItGurD0opWlibXqWw8S7biANr6lHSme1vaFX8lvN53N+UJhRDu7ZTjJXI+rmnR4QLiWn+LrV5dTRaMG5NYQ0eJRea8lI8IPFSKXl8x5gQb4DVVfZff8LDgTxkUFWxcMB29A0tsozTNpC5HqsHBz/Emd2eIzqsuttRxI8GUd11M0CZBcLscqx+SoiMfH9KRUKlOHreq1HTOXDiulRjTPd/0Mj8EAdVKD+BQSKBCrDTIAE6tp6YVZzwp+/Rv4C2qizuUcY+Scvm60Mgif+Csq4yxMuU2Qgwn6BOxLuqHlqjKrUjbwxPPTvII+ROkaJsOyDaekDKrxwzrp+IaMtE4XVRt+fVtXNMhFVfjP3VPVJt9xph6sBOYmxVDdVMiS+zzaIANg9oN0hjdo9y6EkH3KcBkfJb57Gfxqxt5pLSoE0yyluU38DnZTCz4x5g5CD+Lk5fsuPg0GRPcwyY026Iuc4+tnja9IfZ7L5pL+cGowOedqZnMZO8LNJXT2cYc7J7CadScqY7dZGF5lLcpqWzxx+iDmQS17DhhARtX1ac91z1rb7i8H7Mphwifyuww/Xg9slyR1+WCcaLpxx0YLtIm+cFh5oab/XxzGwn2769ytWeed2npyNacbBW1Qmf7iFx5tmuFxWUdyJmMaCG4FwT1VcPQchm2iPXRaiyXuNMxXheb8/xAWZ9KOAHTJLnrDBmm1gYsTWRGGqExfwYFH4kJT07C+aMsfIrcAnYybHBQvbGJnIVky/cc7gK3GtkOdXTqnTv4uR8cqiI0rh5BMw6ywj21cPohdWHYeuoQ+4RlhIV5tVyPmEBpawKuD/2lH/Yr3uKZJfnU7ZZllrJyN3DOzaMy8cTEyVomNOgTfSJ6JWOfXvmSxls3H0NiFpwkfSeoXbnVzSnt+wDGcl9nCFuYCr38if7zyOAW95XjJBogB92lc722cJeMtlddNfi+EGxjWlVNY99svUDPrjqjBsF80ybMH1FI7LKnBf2fhuUAF+3Z6UGx1ku+x4KsMejsTpKYZUzwiyaCPS56PpMgLOco1JXSH8AD1wPnHMOoRM6xIO7FXvBgesZd6FICB6YE5xDXUwKBnpGLbhPfcvYTXZXm8oxmlz+nf9jqOewkdbVz4sak3hYwRf69LObllMkRwQYUSkzHRndMvf3SEpc6xACeYDBwI9eqPtnnr44ZtrHmyBpAkLBuaKubtICWGgE1ZNxgt89XwpbjAFo9D71sO2ffBh+GpLGNh2oDEzHik+63qr1uM92cC2hd0lUYg6QdDiYOuGFJu8EQRORJqJkNHMD1FyDRpJwtXQ54Vdw4x5k+GJPt9OzH8k13vB7XJGb0K3Uv5Wo/ejASvsTevGp2dDLJULl5DjmF6QvmCXDJc5+Z4HN86P66MNusi5tz0SwmPk0iXpekIGZ7wotIjZ6gnYJvCG2/J3W/Y/TCXG0EDttI+dup4WrN47XdFJvd95yZ0IC3YlfD9NVTo4plQOPN1MIP0rfy8Hu44ElU7GjM7Auye3JCNb5ru0wVFtDYK+f7N9oax/NmQp+9P73H803FRrvG2m9zku8UrkIlvkEIBKUM9kesgiCgRQAvxQR+jbcIfWoByA6gq3mW4Vc6X5VHCHjxcjR+yb8cby/T2HD41QRffj0ZAM++S6mzzJLqkFED2U8y1yx/m0C8Hvg/Sb+AgTVj7efiI9w0XL7JScjDgivxZkj8wb5hyT+1DIRLnLK+arvHI0Z7WNgxYCjqQ1IPZ4MyCrQW5ph4+ZyIbzjfJo7PX5TD+t4lAQzAn/yjpzSuKbvnDoYpja+5pV9GpCkMnpxJgpkMlYyB2nmAQr28gESV/eIV02My6sdM4uIaDeBhuw3TUHCwnZwPd6jDbe+4lMg7pDvNOLXSS9GLPl9a+64C6OpiefN9MR0P2e5s+pyZXvZWUjBSnYM5D16thl/vYO4KgMMTIfDeiT29Erso/tlIEOQp+t1k7XI8ojNRA1udFZ4CRxSbVkx5oYchA9PryDDk3ix4axzFDqMGAHuj9Q44FgG6mXg6j1l1Ddp0qKO8avfjgSZbacoSO6Xpe5IEzOK+PzlTOvNh0h8H9FBOLxtlJJ/kT6QkxsbK4oN9zqglho69OzZ4Tg3vOn0v4k7m2xchIwu7ew3pzlGeBiHPKgcx4wI48ZNBXSFI0jyJ+TuFLbenMQJ8eDBxI+uA6N9wSz2nffl4VzPGim7dr2ic6XJYXA85ft5BS8JjNiRtG8dpMk8ur+kyjB25ICsUkesMr7f1M3arPtWIwTbTr2wlN9AVeJQaYL/Bkwtu2uGj1A993KP5A4djFSpdmNz9iN4fLl/a9jqn1I+p9Gj+QaoJ3rjlO/uBzEcoTJqbU/2g0+qVhbvar2osZR0aXXdAM7IgLg98e7EMxnc3uauYGa/5fzwtqpZ/U8SxMQ7fBpzjQ8++adc5JdpiYOqtoiJFODZcuk+SUGU4KKz8qJNYCo+O+eJMWpZS3PjMPGVlDp662RsK0ZTyXSok6Rrgow7V5EauX8dZaAGa+4oWnuOo7JvLn9vlm6Op979DXlDg2ONPtK/3RgIx91fYtYw78TiyUaSlH3f7NqP7dtRj0/CEHyux6d8eBamcq4xWWfYHsIwc0Xj8+wgCcIV0JIErfsEwbrbc8jtkX1xlwsilzGkcjbSdVSAjenGZ1+F9tAWEIk2UgcawMKstEZR4/rFW6Q5bde5h+ophvYWuZ8iJ/avLCsSIGRTWCaLY4fWtuxdWYqd+3e+T+B1vSOGYemlYB5FTaVX4rhH1zWdANzXp3rg4s6ll3f1lHMMehVsk0Avi42VXrCStga5TxYAm/kc+RHqRp9ozZN4pvIdhj+3xNEhmkMH2qRtWkfQXsKn5M/szoHZlxxMKIrc9kgspvwx8+I+VdDx+Y8bN6nZglBPmDqMGMFU3SYqf4UHX1DdFfafEX6+ViPwN6txz5IHGYwmrhzGqaB0c+MgfB4BRaRylGf0o2SNIwNRmd4wpNEyhDBE5kIFSUTevKKYxyNHnflRc12MDsdhR0pzIx/n4kzm75qBnOehnvSpEpZt0hqeZxw7dqSwhr/m0xWxdX6RbitpwFmd72ofc/WIBFWLtT/lGPXmkqbbvD7rAf3QqSElCXih3J6mCEpb0S2hPItbx4sqE61YqusUH9SjTdK0hk/hI4M0fru7rtSzbk+9hkEk+T++HWhmynAcv3MdgCmclrC9ebRz/DkfKadGStcR0/g3ttkYJm/jh4RZpK78Tmt1SUMcYgYJCLTdmp9g6atj3ApUSvRvTFNfDM/Yk824jztZFPy61+CUXBiHX7cg2XZ8ZS72yxZc4aPOmdj3/++oaM1JyHrprmqnD3llr6HmWNWct5bH24O2em+x25jsXBO+EKwZfjzxiskh6i2FA9hGccB3ijLyqfrOfjfwMHhnkyLNPOKtQSsU49dmPJRjtFgj9l4YxPhU2B9wzb9sFWWrEblj1MQOUo8U3vw88NINo6Un3jZLkcj7rJj+g1t32E2uXMzpYTpeF/mfNf9OCWuGqBDT8Bku2hBaQPWqWctEfyjYHWGXvdd3qXZsQTObTkhGg/1SZ5pJo+yYoIPChuvugcyAtD9bmuYwuxnk/0Jq2XJM9a2dR1Img9MtKbUl3yTd7jWbRvwXHrIv5QNlrFuTVvfTH51sBNhoDCQ1Pvih7ZAX5q4K/G0rZks93T5hOvPmHMWfiB3QY8qaUnsyBnwU/AVcVSfdTDA3qj4m4hMnmlsTVemIuczLINfKZqgluWuysVkCJlCmE3/oMK+ZptZz0LPuOkO8xoT5Uo+ndnf6nqxrbZlSe7vtsfNjKkYxkLMIa5pLBx92B9cEdM6cjaZAiewfk0YJ9BQpiOuSOwbMcOz5nU2i9FXbF01pRz6ePz/iX1/+n5aqthlYwqPjmr52EXDPZIMRoyHuItzFAzYsyCNw6BCZxM1TCcnUUIIlQ6sOWLskrbflfPbxLXgIyIuZbxcad+6QHbZoq/78pNz1mdul99nHJeydOvrd83dW330Na60sESI/VVo0qDJUkdo6QFcGOM2iX1hLjwm9adaXKhMNO9pHrolFXKSzXRpsEH10Lq9VTaKWF5MHjXZhRigS3TbcIwxDTQUllNN5L2mh+/n2ueJZQqWVnpe8ORXquZzbBquTLpL0TOZo2IpRPX+6xvEWd+jtrA2wea44BwsYoiznLnfmPdhP2cPzIR+ZxMGeZqls73XKrp9VcEqdR08C/z/1SFOBTQ2aPnXutKqnXG9y2uPW5ob/D/0U6JY0tYhRgKOkA8seiABqTxnazaPgDCDmcYO6BkTXM2InGkgbrb9FUxg0fdzluyU+4nfnqtNXJMA5P6h1EstuHnD0TmHJLqvd/mEjcPb4Hpkkh0dk61sccR3W+fCANWwDF8cizCXylQLGpwTYI0i8CDAn9QN699dSrOtCdCtd+Id3Pe6m6lzJx3A4PcEh4uTPLByk/q7/Y8cnhz3vNW3URrbsIQEHeikP+XjM0wdOHHSiQUMwb5atuG2KJcJyDNwe2YzB0y+LYMNIfAh9ilR1b9TdEsFKGL0E2zqSkGm4xDUU9bhnjzKUvKSijho/RhwsJobCnr9SFUC2aeGoSufEG9ZumdcAvzcOf9rYRJk1XM69d4jSGSgZfuIf3QZ8sZFYQeHn8x5Y++xIgjvp5tzI9yweIm4CH/xYOacuAQGG1FxGjG9vbUgD0nGDX5fZySLrMesVJ9OoHUYZjKBufvaan+w2cYuoM1mlKBopxlZkP/B4xYeGqx7oAIJ2SIMFJFwtHn5Ig5v8Ixydy6iIbKIF124fnjOHdB0pQlbS2fOj3jF9Dcfy7kUeD+ss4oZLby9j7UC7QB0gE7g2PxjsUQfy1X0/zZvluo2Z0b49QpqTdOxuxCdLmCE3NhkRSfTL7TLA9GD6cGJo37Cgue1Hrllo66ZClueQCYHBCaDrVOzmoWd44ZCxipIV5ZT39dxNNpcNfeVIFYNke2T3SCf+hHsEvdr415TOJc3KsQ49XxNfxUOBsz/iTtPhXEkCzDnjF5JrJSeyNd4XbHTrZBQbnze+wX7A0srrvCzxlRsxlfdMhn8g8B8krT14ImMIeTIKCaWf6SqGwwDyR+wcHpbZEGELCVJug6ecQ6FdDJEfBjwzeMXp5ky1MdIGihjDp4j0RGEE+zITPwx1wdgzqui4+u9bagNmNPbNOKb6Ykn3dfV7pUBV91S354DHQTWFMEGbNItkP2gTReBGZm9AY0L0BM5SK7jkKIoV4pznx99QwLzJIIvIAASbuSMRp/biA/VGveMDd/z6qdrYcF9Q0/hJ+VzOrntxh6/PETWyWsebK5jyMJhGs8jt9h0UUYeNz4jyaLJifPuadbF3rnMPpZRXmbvXpt3Ss2Aw1FcqXlVPvx9zYJvpv2ZxCHhhuRkkTkgAzXFvGu6CssQ60Tcy6au1+SBA4RLhK1rrVrXANhG/MxecDb3oo0w/G3sbsVbYSOJQdYsz1bomAlHZ/2LSpyQY2efzZBeNkROV5eHi9vYcY64NnUIT07A720HN58W+Cma+oRZ++LxjD0oCruKlZQ/ZtKO+2HtYd7VkMY2Z4Pd/x9FJy1exYyryS19nKoz3ZKmNgfT4sek8isOFFppnnSD8/ey6Jo4BWaufE6E6xAQwZH6fz86KXNPrLnB4JLXFQW8rtJIdXbxHId1cT5aTBy5l8YIXxbLT+Z17Q7wBwquMdSxH5/z/Qberf8ZGZByPuxUdZerPsN/IbqvbahxkyHc3NOPTA4X4TCpE+gxrkm5x/ouTqSlEWYxShyPyigsDuOAoBlEgb3HGG4ZYtpOmYkdrbrpmMpeydOTK7iGMPAdgvEFf3VrdFm6Pj2HbQ3mMspz4GQxG+p0zsvgxjQt6LJ5Pn98sbjqtEwh43wRGXDdxbpyEbRoqVkUr+Wac3ezmT0laZvckarGcDRvzU2NIOMFAtltxyYTY+bTIBLyTS0Ia/7pDv5a/KFwi45/uKjhstz/k9TrGZI7YBsqgAsoLlq0104EFI/Rq+W64MOVMnWVkRMGppXt1I5s2OM5pY/2wUJpzTzTEbVX7PComFGcCRg9tJIDEngv97w6eCxbBMmsGHRQWQqCR5xvUyr1aD6r4c8EjSI4ztR0MqfnSnmJqRdkv2xMnOOGOB/KhNGDjHzmOdMvXkik4FtpXmND3EzemZoy890+tc5oA2n9oP0OUeXNCJegw5Owqoq/gA5gi4YZinjvY7aJ63i7qAqw7WcD7WKB1P/ntRJpBOJt1SBeTu665xXi0lbv+uUa1+/7oQg0jswWuPlzHqKVDYcfhzh9kRayAJG8H4kDsfQ7dM4d0oTSObtImK2kJno0fPsEGEMww/0KGyhe6oG+OM+HO8LGvdWjS/yahbH9ATg33ZGscwsKf9JN47WbkLKYdYXvph6ZfdFPDAmP7KXQ/Lup892bTf3evgW0kQq98JFMyfhacpulN0otoE9WiQ+2IRMbjPYjs+xgi3IJhPGuZUqrg43Mi45ob7dEBju0x6lvEywLtgZCibUctejraSC03Q9s9XxW1/ohouE3WSiYq5SFwkcyCIi40lxvqqWpZXzIXgDM0ziPJrsT1K6O8uj4gZuuWQ3lnGomcFOmY9V3t43MJBTqlKokxy3d/DQ/08h74LqP5WxYwUn6II4riZzRwjNXQEwL0QYkM2P8JhCtKH/DHEa6BWkzyCXUDnU5cT52YqkZC/Lu+8EJJkmqJaYqogu1y8JsAyCobm/TOKfMh26qkls7ITJ3ACHqPwr2DMi4dAD/7kTI3vA1CH6EFhaXfroHgC26SgKn4p7IwaIyrcRZqHa8OVXi8dkuILgNWP6s2i3fcdo/wQczyB0jZWT2qr5zyfvL/SaHxn3PQcJzkLXrzdTkhXk2CX7dWA5hqYztniKS79Rq6+Fs+SopW6Sp4xgPOfCIa1JOLjdfFKM7o4csejOoOrhoj5677RSn8aspFXE8TZzlEVJbvsmpske/yz4nzObLWIUyxCwjywn9W0QozkJ4ymbPppcDjlxFV/vxczb5jcsk0FIxxw47jXyQ+1HgYXRlHilZs+Z7vq+USfmNMkt0kaLJlgSGi7TlQDY8gRl8sU/RBYGKqj7TNx/AGRk/WN4jWmlscm4Cl0KPY/BMzpdJQ0xkZNdr19oXegrKkDj8eEQ2PfywMb/RQOXTNjCqW2BR487xT1G6BQ82AkYY94sfkrtmF56DkNPYF+g8jwfshF0T1I0+T1wn/3K++ivcnT+EDcmz0dFU+DMXKuW52jDPp8/CVDA4U4n0ItM7nH8mayQYEWafUUP5w7zEKh+MMQlxM4oKomWMMpeXNEzUnPfG7sGOrU4FtXNbTQZfGPo2WCjoi0H9okFOty2q/5c2vkVn0f4Q1vyxVfWSBosBjf0j24zIER0n2ccOpAQzXtc2ccWbp/SH0uMODBE7PDObaGf3sNciPSLHW8aDzYUP1Mc0uEkyKtqLuClbZRFOex1P0ooWak3HVOFWkYI8JwTFh7GCqEAy8TAZbuAulLti1vVn2UxVLcOe7WvqvWgAJRdFIfT57miw9fB1rPvYpiheBzKKS6luiiqWorbXKBkZStf+vDkxOxJ2DdQBm7QtVJ/cwzkFitaF2JkgkxPArDu2kgEENoftzWkVc8Eu1MyHcwe3wjQ0mWvIvlkV/TdBHmCGfZyhzDC04UtdETYbxyfQzC+sj4+qxxTkY9dmlFj3qHtzOupaEhl1mbVywy9lZEywpFUZ43tdcvdRz3ZC1NpXs1wSy3YvHy55h4EwA6ZBlGdqfEfpwLYXpycfFyf3M3QoBnUNnsk2E7AdR9ksTe+Yb//KmxtCgg4CvfGouUXG4vugsAa//dYWXcG+o0kkkg/w7jzXLZgY4vyU29TfuqE+eA7D6M2JGnOcur6cYaiZtxd2LBUNEQodXw2+N4R5S3gjIIyM/xw9ShDkqMlWitl2RYvnN4avqBWhyTq4v+2Hp1ZLgIp48H+TAmNZcm+ZBzIFPnZ1ucKsPq3FoW4TkjtTPx7uQC51JN4UCdtTVJrQsDzzZ9k6yaghZ5m0fopVGvyyiK1uvWar7BY3JLQPhpse9oSiAFVjXOgryXiOALm6FX5LxtdpEddyab23fLw8IKnlpoCgDfUM3pYDfyZ0krvTcC/ZNMOmRUx0dvuzpu0kzAiW0MNMkgPVa3SqGUPl4GqWetNVifA4hm4C/i+u+nOc+likw92cKWY869No35s5FuGnMtu++LpgF8tLh6zKHvIYLXoSbNKdLoDpEfIfW2VOhKVgQpkcg8ofK/PAqt5j7ABQ4q6YEEOdftjsHEVV6/9HtKMcXu6fa02BCjkBHTVo8brFmLwvQnkUXjwZb8J9orE5wys4P7ZXe19jRUnQc+8e+ZefpwbhRVc+D9/kEz9xR8D4VpOap4KRzxIG9tjnVI8lSe4rQpg94bE3CpIiu3OqSFG309Vju+El7ArlNksajkPdS6qgeKBKlZpdu6q+b2Oj2VJHShkLYOuNOcffFTmDVgqFRGloW6D9Jmf4N6mwQlwJgWzCMt+YxqtmJ7Ttg+CHc93z6rqSqeVdJllat1RVnah1ewpx3OcHRu7xxySY2HYlsBmaA7OtJXojsRuczE+FKa073Y7PoZYDiQzULcTPxSwGn3PK0bHDD89lwCjqdimOk6YigTRQqFdYETsD4aYYUirIWqIi8BCo8vdqwH9EQvA5hMxLgYA2v42aGVEsqwfabcSyf5wgOWoiCJHZZgZnwFd/LPXP7Bk2aaL2spcIiuiB/5XNi8lnQlooTVNEM4qaE46g7FJrHuyUkSTfyhW0IjiDt2aur6cQgzUNI7SGMNtmRhanSyzCF6F/ILex/6evYttfcuAqYnJzBIduWKviA7vPCbwgkH5bZFb5twqMOTLpE+4pB68h8FyY1fg7IWe02+6a7vULwyn8coYKJ9UXcDuGOFUY5MU2wPN9oEeAE+uTIOdosLetHFpkWLugDSyDgH65qzyg06mXYm8EDxmE8F3PELF0qTOA/NE+EqD06PIn5QZjgmkFh0a3Vf3JIQWL+GDDhDwg0Dzeu8Zm7CJG162Z2CPmF2eIk0m6Ct+waTSO2SSFtczHhQFIs5TmI7jxO7XDJQW2Tmv4SADBNye6XSu3CxqK4aJPadmepkqNz60gnC+pNpMpNtdmJlPn8zROzBs7eg8sIsJDf+C4QfAHGptNCX6+uH2GoHJrFpfxuQf2tmY1IUD9jq74Svf1vPA1NA4wON1TwPBg2wcUHO32N4TxCuL1Tq9AAmtYZYlBGeNSDYPd/L4oEjZxZ0xUXcoL1cpZfQZdThrztFXl9OUUk5dlVu+IXplDjeOPCI/CDwuE720yVkD7DvES4HCBggivcvnLeRdy+J50kJ7etTUqJ4DivclGx2bblW8WGbCOBVXuGe58wTiuyIPR0D2/cOkow+x452OwweHF4EPg8aSrYRLtk/9Yrk518X3R6k2fGi52Gru+Th0dyiGjO5GRREEwthhLK0xniCRHmMwzbkksdBMtglv6VJuuRxJeFqNCc4+I+fO2zwUnPm+9xHXFyKg7EZm9kmvzDeVaTy7lOq/6RJ8mh35AyJ8RWbdLp3Jfr7rfn3vmVo7mzck/Hk2Bp+7BFZzIx2mQbxxM2vMlfdnuxdtfRdrftbDoZTjB/VOgp/JsNlHviibIqrEpLviLBWQG3be7at80j5I+GMrTYyQfLHRfXQTjvcgz/iFnIRhY7aM621cEJiaYHiDv5bVc6Y6Hizlu2/B2CdeuKvbB0cw32a5gHxMcu89sAYGfnVNc9yzJ7krOcoj2J3MRz7ZsvaMy5Y9wwHwGFhxxl66wi2VJ7OKaSR8SsBb89RbP9rGbpRkGzaDipMJFP2FWqvHmSqtR837Ws/0xk1ohj53gDk2Kd12cqR6XLGZ6HGfZKMd6noTr22rQn2chr3hPw3ZhJBrCJtq+93UqRytsNCYHY5jv84y37QcFexF3OtttWCAVgA80HBAyFHrXvpzpxNwOd5Rrl+NrpYHRXX3Lir4M99xbHjAEORTVp4w/X9ygPG0IrncAT9E54hz82dXORjVMkozrbINxwc4G07DpBw7JR467u6+d+dokjO96Fh9/nF5HVhAlYSM6wU2NlxBsiHKc8bt2xIGQti6+TJ3+y3VzPTJmCfwtFsMNmVDIeeifb9Sxjpqw+LdvEjoDKQq8IlOxzcBsLd64wHpLM7zpJZIQKkyMKn1NOPpk0HgSdFovTzHLmbeS8zvnKIOIe/H1GPU+p9ck10OPZZaa5GR6lcm6NiUVqZnxCNyrWqGlWLg/mGejVLPlpO3weE7hy3JZsbO373Lz0eJM81wuAbCH8+HH1O6St/xC5MV4D9FYvuHRtMnXWLbhzilFoT96yi1a3CgIOKFOy1P67DNmak3SzRaBr2j+OVQrt4DV48N1mHQe+QRFBA3PuFUQucfUWi45Y/4LXZUutvwnhHrLw/hxcqDtiphZaCyx4r4izifJBsOCeVKaWmLaHr79t/Zz7SxabiM5Fa8rlFwRUuuVUHtWW6VQauncbqz2zQ9s7R4TbaiJrc0nDqp7YNXs68N8v/5Kpg5V7gLr9aQI2xoi/DfDc2DhUj5a3fUVo8ux43V2adEEBOoMdUQqbILEH7gp+tq4XAjwbKmjDTnHc0w+xzuclpCm4PChRyr5QOQ50prtAlIXHg0WAz7x6Hv4bWBuYm8Njs157g0zUYr9CuWGC9yGla0wi4MZIfHA+sCMOq694PondPIR2/Er4s6soU+2lfewN5/JrKmaxJHlyqKV//mW+NUWqcqGYYLbtsWTv/g1JrV7Q4EZxfu1gkr/+wb2u8qsaUU5cFNwbMHnJJSFc47ZJrEZv6+l+HqS1E6LyK3LQzh5Po4WN9/CbaAY90Dk8xU/dd/1WQIXTtzP9i6Wotu7YMbfuhG9CpJ+MO6Z+67MC4+Zrhofqm2N0o7/BUqhrFTZP3OXJTXYSrpeAK3AzXXjfP4A6tgBqyTLzUAXguuOCugE+aKM+yMbfAHOKS9H0F0WQg7R1pdm8+MMllvXfBm/Mic2cOB/mBEtSOnACTinfPqqsQByJ103gtr/EyqqPrtmO2UapAzMO5lKZ3AE/Co2v20d/cLJRlChz9qlc6+5Xz3hj6ASTvtjo/bOZW1V0LBYsnvj6E4P70DsTH76UMGmtx0wbGMgwTO+3NAPsLPYd7OwZbWmFmeeK64wa/mT3NV9u4CcxQRLlyFq7K1n6uLMSLQKqF2w2YphlVZ+x+hdGU2b+MDqg3zNDBEn9HQ3VDZLoUF/dAF0Bu5u9RCKOmenmMsKbs2vwoZV+u6j+G/q0F17+G9SVU8WNn59ZkC6xBHqUp4s4aX+z/C/tQI1+Vifur6m7wRvOtedcUs/c0OznRUt3dJBIlhGFt8mJGmGqy2Vc0xvCJ/+Od6LVS5hM7udrkfqeBjwiN0gHhE576gKn/Ax+1qRx88IFtdi3e/qhfWQQTeXbkJ08kjuRMgPSOkb6BeI+Dywc9o6VNzh2I1BtHu/PVkyxHerP3aZmuUZPTLZ9XPCbFX0byFezMi3CqvtKZrt3sgZMNiBmmx252tiLuE/b5M/cD6R3+g6jcb44E5pG+X8nJIr0JWOncVgFNzm7LFPR98feznHwpScWu8SXIAPXUm6ONVUbL+pmzTdYNodbQxkAfVkQl2t9Q1a7uzeKhss8AUN00oi7txTcF/jNAfxI4sugOmePxlrwU0pnsAy48FgzmzThaCBRKhj7UAJxTJDLSRHcR0WORl21QL1VbqSWDLcdTWuiI/QyH1npeCSol84g/CgwPZoa5NPveiCkmANSnP2/sjt6U+txrISAdvrFj4uy2zkNaQpY5aU/tF2FNlFVNfjEqsrfuE1FtLVdILflrYGhme77r3AtGSQ+MJEpl1rabTNfgn8oJY1rjXpNBfqjpN3sZsjw6MFBrz6El0x5rXCqjKqQCnkPfh4trmNJyf8LkJyZjBKNO5YrxL0dMkyFs8arBfqIg9zy9ze2d7lYCPuirws55doTs8eL8nZ5GKf0FVxV7b0s7UkGko0Z2bzven3bhcyrSDGIOrVt09eWBxRBdY00M33/fhJ5R8mUicQc9NIkCbCpeyjeN2zYgk0tzDB5Le3eT/i5pauRd0glN5S7Oh9N591uHrnB6ofzDZ0W0nc98zooBMSeLbIZVbViL1f332DuAI9KFEIDT90IV71KNI2ppba3j9EczI9CrGzHqcEc86hxVDfFPl2045KgnvxW9NDIKuuqoIKTKCdpD84HIF/he3G98xrifFzZItBV9ZS3BVxIoNZQuxdsxy70RQmkvGLnhPtWO8yneti3oZrRS+W128+RDRwKg5m0pDijSrQ7F7hY49DpGqKIJ7kijzuvxiQzFjIH6TIzS9KBhaTyeM90L49gh4yvuiDLBdEzTAp9ykNFX7sekJwt7AaXVpLvSax5X/8PGTxOPKTs5+dk5laMiB2hxbwNjOZ9/o/6DI3y5vN9KgDWNkNjehDS+pYd03wNLUUMUQLj2y32fQ6MkJL68XctpF2CEjSBoW9RnYtalkeuPAdaLy976xFYABVpD7u1MBdEw4TcQW60ZH8WnpEOPV5U32VNrFSze0CYuxhKqHRUKZWw4LmqyGgS9u+d9NbiO1Mmi8QrKIj8ph1jd2teCuMQwGz/7CWYrFL0jb24l3ixPx732dxVQmKsHVDGl5xODVd17sOYqkU1JVSLX54VxIjWEU1R4l9Ac78vhUhbPL870o/Krwg255QV7ulaMXUg0nggOP9fcTdTpQzdKcdnlNPbJ/xHMWuU587etf1XNXwFvTFWPKrNR1cKgcGiilxZ63C60OPLVyAK7iHu9jWTYKmm9J4pfQ+bg/knGqzgjuTe0a8+VJwhuJKKfGCAlTu+y7G+lo4SJzgHS7xP3lYAC72nDWQWGACrHbk3sM3PDFqijEkdBpWY+mjMvJQtrxQZXnMHeP7kjdL+Ui5NJKzgDoqvUHkxffFuHddCvdTewtybWfLEfbDZYwe6YbcOwoBoukNOHpAmOFUvE2gjUgddGM3lQItaJ9iaVUuGzXE/K2ld53RfjlxVyKaTER20y813RqMpt7db+0VfqrXHkyhzO/dHPI7Hcnk27nd14WKqTzqi/0+s3W4tGfBVz9gjoJhfEebVK+HGfiuHN23PoyUKT9UYng6dIAXyeZT139gX25TJkltyRSj38Vsx+PubEvLOp78prfRQistLE5RDSHc2LsXXJg+E/eVdjH+RVoJ26HC71PVyON47yVh3hcFGtWndQ6klOTgJ4Efni8BCc9hHhg6ke8eksEkx5su30ym41zTMagvEt/1R7HrHHU3490TQsPsWtWHbqoSZYRxVRS8bQsHIkh5uGxFUm/H0gZKzL6vzNPHwvm7VbUAfBai5LMmLrLtSQ1pavV+d5YL/IY+jPwBmzRXhlwrWpG/Vuomd9DG9w0d1rqtGdqWspJma8Fk1l6Y6+XqDyWpn6f6w3307ou6qZbyq0fft/dP1hW+TjBXE6YsHnCcwj5gOV2cfjMFnZs8paiGuBH2MjlKfOH7krTKoTjq0Tri5waSb0kruWxcv0epQ/ijA1H7kECs7cYWIMel2ND9LLx0JdV98nyWfYfqqy0vPdyrwNlWQXJ9Nf/kdGmsQFdtLUujuP+Z6msM1Z1OqOpZ3S6n84VtTIXikN8s2LYO2yJgrkGph/tnQ7qzYZMyuA3dr2SqskNHojlJXECMw2I6Zgj1Xenb97Gpr5jgEwNaw+2WCGjj0auLd11/CPYSeMSDeO2zU3gW9xabuMA+VFzBBGNMjXlsjFGGJlEhY/i+HV7hx7g0Ft0qMdNjXERUMKhZ6ZNp3CCYhNx+Y01b3zv+fNFwh/flBfEOOaml+FDNwiTDlKlRGs3fkcfnoqmmx/l9U1uoJ0OQsLKwXqpKWiWL5MfyM2kFOJ7yHZf/auXKwtUBXGZaPqYvcky9uwnPi6ltkia7PmRBpn0LxwlIZUyokbWtdZNYJ/giwsoSsKBQ5dq3RR4YyOJ3/5Y36gP0MXnechu09L6X+rJr2eT5xUBCQ6Gz8o3Lu+eBBuXQkCUA1zaeWtYibzDvJ2E/oGC78woTwOxz75XFa59kKUggpqQZgw/YMTd5NOSYzAheqsrQLWLKsy2e1Yj9rbjXcRBnSYRI7UBPIomm2uv2TUgQ+gO8ndGnRKGZB9DQSCdbJjv17/p9GfCMRokm6m2RoqpLJZFlLjmJ5yDSJnestAXFmuRw3y6TCc1fhV60RqG7pbdVGiKV7QF7hy5ph/LDkmuR1et+n1oRC+NOf+hBDHn0KEGcLMhOJhUyEoJgCvaFL5NXM8AA0sabhQw2sBIiRnSg7MIA4tE0Cr/rstwlZ1QhX5g1WxlLPEzNuRhc8s2DtsfoesCODW9fDRW7jqpPRoTtgBBYZFMvsh4EmxDzkqXF8MUZfScaJFiaicjKy2AeoRXovmwYKapCyHBED1+KDiypG241Xgg0fp9Nb1/7ohPHawsS5HPL3JkjHy5RjHv5kBXC+kD9gk20qWjtIuLFFkov/Lp5YVW/a2Gew2N2Dm2rBGB1ysKiMrTbRQ2SXeB3UkfTSyfIhXrI6rh2wQpKSmzhdm3JGoeCyhUFLhnKX/MvfZGiTA3ScEt8446Fc9sOQSeKRMlw4Gz8TmmSsleVZZ/Z7aExgJRX/TmmzH8/woYqFVwgotgXoeRyMhqGAbqjuMboAXvKbdBsnj6GoJcS1A7hHZKmhtuwtrC6WTV401akGz1G7sCWEbj7VbUXNYKuQvfepJMOOPM1ekJy2ii0iJCZxfllhiyHIfDFdAKdLymLHlPsCa65uJX/jGCZ8UTqtpvO9/bpoA1orAmPSbWwARFwbqwLO1jmjqv7HiHJxlpS6PMA3XvsSrj80FxCfWc0PRdnKwsUFkzJBkuBnXgSJmTwEGoAeiJ8m7pQoxA19GGnFJTSMm4unXeU27HYBVDUCMReN/OXv8jTzGkDBuqCsuoWCWg0hBAtpFYgimsMpe9xzjxkN03tIB49FI2mLL7rVblk5OjH7XnEr94ez603HrKHiF4GR/QDjmL3Yf2IyYJdgwgTjhfcpA3pxid9noJOmC/YTStkI1y/lURqMdgBqx1CReFRUsen11iQ/1wiyr4oDYOozl7+inX+8/8BRl/WIn5BAgA=', 'base64')));
let temporary;
const implementation = (async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-circuits-flow-'));
  await compileLocalModules(site, temporary);
  return {
    flow: await import(pathToFileURL(path.join(temporary, 'flow.js')).href),
    viewer: await import(pathToFileURL(path.join(temporary, 'diagram-viewer.js')).href),
  };
})();
after(async () => { await implementation; await rm(temporary, { recursive: true, force: true }); });

async function collections(expression) {
  return (await Promise.all((await readdir(path.join(site, 'data')))
    .filter(name => expression.test(name)).map(name => json('data/' + name)))).flat();
}
function walk(flow, choices, domain) {
  const value = flow.walkFromRoot(choices, domain);
  assert.equal(value.consumed, choices.length, choices.join('/') + ': consume every fixed answer');
  return value;
}
function enterRoutes(flow, state) {
  for (let limit = 0; flow.evaluateState(state).current.type === 'route'; ++limit) {
    assert(limit < 100, 'route entry terminates');
    state = flow.enterFlowRoute(state);
  }
  return state;
}
function replay(flow, choices, domain) {
  let state = flow.initialState(domain);
  for (const answer of choices) state = flow.answerState(enterRoutes(flow, state), answer);
  return enterRoutes(flow, state);
}
function weight(state) {
  return state.answers.length + (state.trail ?? []).reduce((sum, context) => sum + context.answers.length + 1, 0);
}
function checkSvg(flow, graph) {
  const svg = flow.renderFlowSvg(graph);
  let edges = 0;
  for (const node of graph.nodes) {
    assert(svg.includes(`data-node="${node.id}"`), `${graph.id}/${node.id}: visible node`);
    if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
      ++edges;
      assert(svg.includes(`data-edge="${node.id}:${option.id}:${node.answers[option.id]}"`));
      assert(svg.includes(`<title>${xml(option.label)}</title>`), 'the complete answer label is readable');
    }
    if (node.type === 'result') for (const technique of node.techniques ?? [])
      assert(svg.includes(`href="/flowchartcp/techniques/${technique}/"`));
  }
  assert.equal((svg.match(/class="flow-edge /g) ?? []).length, edges);
  return svg;
}


let html;
const svgCache = new Map();
for (const current of cases) {
  test(current.problemId + ': all premises gate the sole concrete result and no/unknown stays unresolved', async () => {
    const { flow } = await implementation;
    assert.deepEqual(flow.validateGraphs(), []);
    assert.equal(flow.getGraph(current.domain).entry, true);
    assert.equal(flow.getFlowDomainId(flow.initialState(current.graph)), current.domain);
    const parent = walk(flow, current.prefix.slice(0, -1), current.domain);
    assert.equal(parent.graph.id, current.parent);
    assert.equal(parent.current.id, current.parentNode);
    assert.equal(flow.getNodeOptions(parent.current).filter(option => option.id === current.prefix.at(-1)).length, 1);
    for (let index = 0; index < 3; ++index) {
      const result = walk(flow, [...current.prefix, ...Array(index).fill('yes')], current.domain);
      assert.equal(result.graph.id, current.graph);
      assert.equal(result.current.id, current.guards[index]);
      assert.equal(result.current.type, 'question');
      assert.notEqual(result.graph.entry, true);
      assert(!candidates(result).includes(current.id));
      assert.deepEqual(flow.getNodeOptions(result.current).map(option => option.id).sort(), ['no', 'unknown', 'yes']);
      for (const answer of ['no', 'unknown']) {
        const fallback = walk(flow, [...current.prefix, ...Array(index).fill('yes'), answer], current.domain);
        assert.equal(fallback.graph.id, 'condition-check');
        assert.equal(fallback.current.type, 'question');
        assert(!candidates(fallback).includes(current.id));
      }
    }
    const result = walk(flow, [...current.prefix, 'yes', 'yes', 'yes'], current.domain);
    assert.equal(result.current.type, 'result');
    assert.deepEqual(candidates(result), [current.id]);
    for (const term of current.terms) assert.match(JSON.stringify(result.graph), term);
    const occurrences = flow.graphs.flatMap(graph => graph.nodes.filter(node => (node.techniques ?? []).includes(current.id))
      .map(node => ({ graph: graph.id, node: node.id, type: node.type })));
    assert.deepEqual(occurrences, [{ graph: current.graph, node: 'result', type: 'result' }],
      'new techniques occur only inside their premise graph result');
  });

  test(current.problemId + ': both displays, complete SVG labels, shared URLs and Back retain all premise histories', async () => {
    const { flow, viewer } = await implementation;
    html ??= flow.renderFlowHtml('/flowchartcp/');
    assert(html.includes('data-view="questions"') && html.includes('data-view="diagram"'));
    for (const graphId of [current.domain, current.parent, current.graph]) {
      const graph = flow.getGraph(graphId);
      assert(html.includes(`data-graph-panel="${graphId}"`));
      if (!svgCache.has(graphId)) svgCache.set(graphId, checkSvg(flow, graph));
      for (const node of graph.nodes) {
        assert(html.includes(`id="flow-text-${graphId}-${node.id}"`));
        assert(html.includes(xml(node.title)));
        if (node.type === 'question') for (const option of flow.getNodeOptions(node)) {
          assert(html.includes(xml(option.label)));
          assert(html.includes(`#flow-text-${graphId}-${node.answers[option.id]}`));
        }
      }
    }
    assert(html.includes(`/flowchartcp/techniques/${current.id}/`));
    const histories = [[...current.prefix, 'yes', 'yes', 'yes']];
    for (let index = 0; index < 3; ++index) for (const answer of ['no', 'unknown'])
      histories.push([...current.prefix, ...Array(index).fill('yes'), answer]);
    for (const choices of histories) {
      let state = replay(flow, choices, current.domain);
      assert.deepEqual(flow.evaluateState(state).current, walk(flow, choices, current.domain).current);
      for (let limit = weight(state) + 1; ; --limit) {
        assert(limit > 0);
        assert.equal(flow.getFlowDomainId(state), current.domain);
        assert.deepEqual(flow.sanitizeState(state), state);
        const evaluated = flow.evaluateState(state);
        if (!svgCache.has(state.graph)) svgCache.set(state.graph, checkSvg(flow, evaluated.graph));
        const svg = svgCache.get(state.graph);
        for (const node of evaluated.path) assert(svg.includes(`data-node="${node.id}"`));
        for (const edge of evaluated.edges) assert(svg.includes(`data-edge="${edge.from}:${edge.answer}:${edge.to}"`));
        const hash = flow.serializeFlowHash(state);
        assert.deepEqual(flow.parseFlowHash(hash), state);
        assert.deepEqual(viewer.diagramState(state.graph, hash), state);
        const url = new URL(viewer.diagramViewerUrl(state.graph, '/flowchartcp/', state), 'https://flowchartcp.test');
        assert.equal(url.pathname, `/flowchartcp/diagrams/${state.graph}/`);
        assert.equal(url.hash, hash);
        assert.deepEqual(viewer.diagramState(state.graph, url.hash), state);
        if (!weight(state)) break;
        const previous = flow.backFlowState(state);
        assert(weight(previous) < weight(state));
        state = previous;
      }
      assert.deepEqual(state, flow.initialState(current.domain));
      assert.deepEqual(flow.backFlowState(state), state);
    }
  });

  test(current.problemId + ': dated original, complete article, grouped metadata and one canonical example agree', async () => {
    const { flow } = await implementation;
    const [metadata, refs, features, walks] = await Promise.all([
      collections(/^techniques-.*\.json$/), collections(/^references-.*\.json$/), json(current.feature), json('data/problem-walks.json'),
    ]);
    const registered = metadata.filter(row => row.id === current.id);
    assert.equal(registered.length, 1);
    assert.equal(registered[0].kind, 'technique');
    assert.equal(registered[0].status, 'reviewed');
    assert(registered[0].aliases.some(alias => /[A-Za-z]/.test(alias)));
    assert((await json('data/techniques-specific-' + current.group + '.json')).some(row => row.id === current.id));
    assert((await json('data/references-specific-' + current.group + '.json')).some(row => row.techniqueId === current.id && matches(row, current)));
    assert(registered[0].sources.includes(current.statement));
    assert(registered[0].sources.includes(current.editorial));
    const article = await readFile(path.join(site, 'src/content/docs/techniques', current.id + '.mdx'), 'utf8');
    assert.deepEqual([...article.matchAll(/^## (.+)$/gm)].map(match => match[1]),
      ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料']);
    assert.equal((article.match(/^```cpp\s*$/gm) ?? []).length, 1);
    const cpp = [...article.matchAll(/^```cpp\s*\n(.*?)^```\s*$/gms)][0][1];
    assert.equal(createHash('sha256').update(cpp).digest('hex'), current.cppSha256);
    assert(!/<(?:details|summary)\b/i.test(article));
    for (const term of current.articleTerms) assert.match(article, term);
    assert(article.includes(current.statement) && article.includes(current.editorial));
    assert(article.includes(`techniqueId="${current.id}"`));
    const originals = refs.filter(row => row.techniqueId === current.id && matches(row, current));
    assert.equal(originals.length, 1);
    const ref = originals[0];
    assert.equal(ref.url, current.statement);
    assert.equal(ref.editorialUrl, current.editorial);
    assert.equal(ref.verification, 'independent-analysis');
    assert.equal(ref.sourceDate, '2018-09-05');
    assert.equal(ref.difficulty, null);
    assert.equal(ref.cutoffVerification, 'contest-before-cutoff');
    assert(ref.evidence.trim().length > 0);
    assert.equal(features.length, 1);
    const feature = features[0];
    assert(matches(feature, current));
    assert.deepEqual(feature.techniqueIds, [current.id]);
    assert.equal(feature.url, current.statement);
    assert.equal(feature.evidenceUrl, current.editorial);
    assert.equal(feature.reviewStatus, 'verified');
    assert.equal(feature.verification, 'independent-analysis');
    assert.equal(feature.publicationDate, '2018-09-05');
    assert.equal(feature.exactDateVerified, true);
    assert.equal(feature.originalNumericBoundsVerified, true);
    assert.equal(feature.difficulty, null);
    assert.equal(feature.cutoff, '2026-10-14');
    const examples = walks.filter(row => matches(row, current) && row.expectedTechniqueIds.includes(current.id));
    assert.equal(examples.length, 1);
    const example = examples[0];
    assert.equal(example.entryGraphId, current.domain);
    assert.deepEqual(example.choices, [...current.prefix, 'yes', 'yes', 'yes']);
    assert.deepEqual(example.expectedTechniqueIds, [current.id]);
    assert.equal(example.statementUrl, current.statement);
    assert.equal(example.verificationKind, 'independent-analysis');
    assert.equal(example.reviewStatus, 'verified');
    assert.deepEqual(example.features, feature.features);
    const reached = walk(flow, example.choices, current.domain);
    assert.deepEqual(reached.steps.map(({graph,node,answer}) => ({graph,node,answer})), example.steps);
  });
}

test('all 509 pre-batch walkthrough records, every target/result and full text/answer labels stay unchanged', async () => {
  const { flow } = await implementation;
  const walks = await json('data/problem-walks.json');
  assert(walks.length >= 511);
  const previous = walks.slice(0, 509);
  assert.equal(digest(previous), '79504ea3eae67573533d884f90f31cf63c3501cc0ed3382f8704590e09e9e729');
  // Both expected hashes were computed solely from frozen raw JSON, before
  // either article was registered, by an interpreter independent of flow.ts.
  const observed = previous.map(row => {
    const value = flow.walkFromRoot(row.choices, row.entryGraphId);
    assert.equal(value.consumed, row.choices.length);
    for (const expected of row.expectedTechniqueIds) assert(candidates(value).includes(expected));
    return { graph: value.graph.id, node: value.current.id, type: value.current.type,
      techniques: candidates(value), steps: value.steps };
  });
  assert.equal(digest(observed), '805b403bedb97629e957cf3629eaaca13242010bb8ed11f79be7ecfecef8862f');
  const text = observed.map(value => ({ graph: value.graph, node: value.node, type: value.type,
    title: flow.getNode(flow.getGraph(value.graph), value.node).title, techniques: value.techniques,
    steps: value.steps.map(step => {
      const node = flow.getNode(flow.getGraph(step.graph), step.node);
      return { graph: step.graph, node: step.node, question: node.title, answer: step.answer,
        answerLabel: flow.getNodeOptions(node).find(option => option.id === step.answer).label, target: step.target };
    }) }));
  assert.equal(digest(text), '07f242096ded4cd8f6e89fc96922a59caa4b721263d0fe3fbcb126c9d248f5e6');
});

test('every field of all 455 old graphs and 3601 nodes survives, including every old option order and result', async () => {
  const { flow } = await implementation;
  assert.equal(digest(oldShape), '3d877e9b0c1a10798909ddb058386d421b188aea744fe02bbbb8063a5fe8c835');
  assert.equal(oldShape.length, 455);
  assert.equal(oldShape.reduce((sum, [,nodes]) => sum + nodes.length, 0), 3601);
  const shapeMap = new Map(oldShape);
  const oldIds = oldShape.map(([id]) => id);
  const projection = structuredClone(flow.graphs.filter(graph => shapeMap.has(graph.id)));
  assert.deepEqual(projection.map(graph => graph.id), oldIds);
  for (const graph of projection) {
    const shape = new Map(shapeMap.get(graph.id).map(([id,answers,explicitOptions]) => [id,{answers,explicitOptions}]));
    const nodeIds = shapeMap.get(graph.id).map(([id]) => id);
    graph.nodes = graph.nodes.filter(node => shape.has(node.id));
    assert.deepEqual(graph.nodes.map(node => node.id), nodeIds);
    for (const node of graph.nodes) {
      const { answers, explicitOptions } = shape.get(node.id);
      if (!answers) continue;
      assert.equal(node.type, 'question');
      for (const answer of answers) assert(Object.hasOwn(node.answers, answer));
      if (explicitOptions) {
        assert(Array.isArray(node.options));
        node.options = node.options.filter(option => answers.includes(option.id));
      } else if (node.options !== undefined) {
        assert.deepEqual(node.options.filter(option => answers.includes(option.id)),
          answers.map(id => ({id,label:({yes:'はい',no:'いいえ',unknown:'わからない'})[id] ?? id})));
        delete node.options;
      }
      node.answers = Object.fromEntries(answers.map(answer => [answer,node.answers[answer]]));
    }
  }
  assert.equal(digest(stable(projection)), 'e89b7787b616a699483b24d6f1e660d3ad6d4b3d9c6c94ea769c2a389eb09ad6');
});

test('initial IOI2018 six rows/status/snapshot and all three existing resolutions stay fixed while the two new resolutions are appended', async () => {
  const [audit,plan] = await Promise.all([json('data/corpus-audits/ioi-2018.json'),json('data/coverage-plan.json')]);
  assert.equal(audit.snapshot.articleCount, 482);
  assert.equal(audit.snapshot.specificTechniqueCount, 404);
  assert.equal(audit.snapshot.flowGraphCount, 449);
  assert.equal(audit.snapshot.walkCount, 503);
  for (const [kind,hash] of Object.entries({ flow:'51b48b37676eb0d9d19a5306bd736b83950c8573ff4790bddb6853b4e7b0ea2e',
    technique:'74d4857883b0cb6e5e3a8a4518d64143ddc334a534aee4b26797370ba02341be' })) {
    const raw=gunzipSync(await readFile(path.join(site,audit.snapshot[kind+'SnapshotFile'])));
    assert.equal(createHash('sha256').update(raw).digest('hex'),hash);
    assert.equal(audit.snapshot[kind+'Sha256'],hash);
  }
  assert.equal(digest(audit.status),'8004bbe3f1d6107d67f6b75a76ae60175a1c7b7ee6e86277bc8d864b027f7ff3');
  assert.equal(digest(audit.selection),'1a1ad95f82fcff524f555c339050ba4c05c86b9d7309e80023486479570da71b');
  const initial=audit.records.map(({resolution,...row})=>row);
  assert.equal(digest(initial),'ee06a9394e994d941e27a5b820bdd7f6eafbe0d54561f1b3216d2a7a950a0523');
  assert(initial.every(isCorpusSolutionReviewed));
  assert.equal(audit.status.solutionReviewedCount,6);
  assert.equal(audit.status.coveredCount,0);
  assert.equal(audit.status.fullImplementationValidatedCount,0);
  assert.equal(audit.status.fixedCorpusResearchComplete,true);
  assert.equal(audit.status.fixedCorpusCoverageComplete,false);
  assert.equal(audit.status.globalCoverageComplete,false);
  for (const [problemId,hash] of Object.entries({"ioi2018_combo":"b95a8da558f4c0bae5119cf7ddc425d61a331bfd0c41140ae545143dbccd43b1","ioi2018_seats":"b3a80c33e0994f177dbc985b9e7b84e747ac594bab2526012ea543236d190a19","ioi2018_werewolf":"11fe9b7f4ac8041b0c12cd7fc2aee1735b81206790dd55e8a5ac06d5d19ec4e7"}))
    assert.equal(digest(audit.records.find(row=>row.problemId===problemId)),hash);
  const corpus=plan.corpora.find(row=>row.id==='ioi-2018');
  assert.equal(corpus.expectedProblems,6);
  assert.equal(corpus.state,'audited');
  assert.deepEqual(corpus.fixedProblems.map(row=>row.problemId),initial.map(row=>row.problemId));
  for (const current of cases) {
    const row=audit.records.find(row=>matches(row,current));
    const first=initial.find(row=>matches(row,current));
    assert.equal(first.classification,'missing-technique');
    assert.equal(first.technicalFindings.fullImplementationValidated,false);
    assert.deepEqual(first.expectedTechniqueIds,[]);
    assert.equal(row.resolution.status,'verified');
    assert.deepEqual(row.resolution.techniqueIds,[current.id]);
    assert.equal(row.resolution.rootWalkFile,'data/problem-walks.json');
    assert.match(row.resolution.reviewedAt,/^\d{4}-\d{2}-\d{2}$/);
    assert(row.resolution.notes.trim().length>0);
    const gap=plan.knownGaps.find(gap=>gap.id===first.gap.id);
    assert.equal(gap.state,'resolved');
    assert.equal(gap.problemId,current.problemId);
    assert.deepEqual(gap.techniqueIds,[current.id]);
    const record=await json('research/technique-verifications/'+current.id+'.json');
    assert.equal(record.sourceVerification.numericBoundsVerified,true);
    assert.equal(record.cppSha256,current.cppSha256);
    assert.equal(record.reference.verification,'independent-analysis');
    assert.equal(record.sourceVerification.date,'2018-09-05');
    if (current.problemId==='ioi2018_doll') {
      assert.equal(record.sourceVerification.apiContainsEntireSourceRange,true);
      assert.equal(record.sourceVerification.editorialFullFormulaTranscriptionVerified,false);
      assert.equal(record.complexity.allInputBudgets.hardSwitchBudget,400000);
      assert.equal(record.complexity.allInputBudgets.hardStateChangeBudget,20000000);
      assert.equal(record.verification.checks,117243125);
    } else {
      assert.deepEqual(record.sourceVerification.unconfirmedOriginalNumericBounds,[]);
      assert.equal(record.sourceVerification.officialReviewFullFormulaTranscriptionVerified,false);
      assert.equal(record.sourceVerification.sourceBounds.fullScoreQueries,50);
      assert.equal(record.sourceVerification.sourceBounds.hardQueryLimit,100);
    }
    assert.equal(record.reference.difficulty,null);
    assert.equal(record.reference.sourceDate,'2018-09-05');
  }
  assert.equal(initial.find(row=>row.problemId==='ioi2018_doll').gap.firstMissingGraphId,'thinking-operation-goals');
  assert.equal(initial.find(row=>row.problemId==='ioi2018_highway').gap.firstMissingNodeId,'general-result');
});
