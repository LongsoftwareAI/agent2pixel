// Run using the already installed office Vite binary; no dependency download.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const upstream=process.env.QA_UPSTREAM || '/workspace/reference-checkouts/marmottajr--habblaud';
const app=process.env.QA_APP || '/workspace/worktrees/p2-pixel';
export default {
 root,
 publicDir:path.join(upstream,'client/public'),
 resolve:{alias:[
  {find:'@upstream',replacement:upstream},
  {find:'@fixture',replacement:path.join(app,'apps/office/src/fixture.ts')},
  {find:/^\.\/locales\/all$/,replacement:path.join(upstream,'shared/locales/none.ts')},
  ...['@fontsource/pixelify-sans','@xterm/xterm','@xterm/addon-fit'].map(find=>({find,replacement:path.join(app,'apps/office/node_modules',find)})),
 ]},
 server:{host:'127.0.0.1',port:3102,strictPort:true,fs:{allow:['/workspace','/tmp']}},
};
