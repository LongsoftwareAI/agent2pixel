import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
const r = (path: string) => fileURLToPath(new URL(path, import.meta.url));
export default defineConfig({
 publicDir:r('../../vendor/habblaud/client/public'),
 resolve:{alias:[{find:/^\.\/locales\/all$/,replacement:r('../../vendor/habblaud/shared/locales/none.ts')},{find:'@fontsource/pixelify-sans',replacement:r('node_modules/@fontsource/pixelify-sans')},{find:'@xterm/xterm',replacement:r('node_modules/@xterm/xterm')},{find:'@xterm/addon-fit',replacement:r('node_modules/@xterm/addon-fit')}]},
 server:{host:'127.0.0.1',port:3000,strictPort:true,fs:{allow:[r('../..')]},proxy:{'/api':{target:'http://127.0.0.1:8000'},'/health':{target:'http://127.0.0.1:8000'},'/ws':{target:'ws://127.0.0.1:8000',ws:true},'/control':{target:'http://127.0.0.1:3001',ws:true}}},
 build:{assetsDir:'bundle',outDir:'dist',emptyOutDir:true}
});
