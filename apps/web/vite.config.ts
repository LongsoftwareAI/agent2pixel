import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
const proxyTarget=process.env.AGENTVERSE_API_PROXY || 'http://127.0.0.1:8000';
export default defineConfig({base:process.env.AGENTVERSE_CONTROL_BASE || "/",plugins:[react()],server:{host:'127.0.0.1',port:3000,strictPort:true,proxy:{'/api':proxyTarget,'/health':proxyTarget,'/ws':{target:proxyTarget.replace(/^http/,'ws'),ws:true}}},test:{environment:'jsdom'}});
