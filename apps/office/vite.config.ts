import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { officeBase,officeAssetPaths } from './host-config.ts';
const base=officeBase(process.env.AGENTVERSE_OFFICE_BASE);
const r = (path: string) => fileURLToPath(new URL(path, import.meta.url));
const api = process.env.AGENTVERSE_API_PROXY ?? 'http://127.0.0.1:8000';
const control = process.env.AGENTVERSE_CONTROL_PROXY ?? 'http://127.0.0.1:3000';
export default defineConfig({
 base,
 plugins:[{name:'agentverse-office-public-assets',enforce:'pre',transform(code,id){if(id.includes('/vendor/habblaud/client/src/') && /\.[jt]s$/.test(id))return {code:officeAssetPaths(code,base),map:null};}}],
 publicDir:r('../../vendor/habblaud/client/public'),
 resolve:{alias:[{find:/^\.\/locales\/all$/,replacement:r('../../vendor/habblaud/shared/locales/none.ts')},{find:'@fontsource/pixelify-sans',replacement:r('node_modules/@fontsource/pixelify-sans')},{find:'@xterm/xterm',replacement:r('node_modules/@xterm/xterm')},{find:'@xterm/addon-fit',replacement:r('node_modules/@xterm/addon-fit')}]},
 server:{host:'127.0.0.1',port:3002,strictPort:true,fs:{allow:[r('../..')]},proxy:{'/api':{target:api},'/health':{target:api},'/ws':{target:api.replace(/^http/, 'ws'),ws:true},'/control':{target:control,ws:true}}},
 build:{assetsDir:'bundle',outDir:'dist',emptyOutDir:true}
});
