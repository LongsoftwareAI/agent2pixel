// Console is published on3000; office stays internal on3002 behind /office/.
import {spawn} from 'node:child_process';
const children=[];
let stopping=false;
function stop(code=0){
 if(stopping)return;stopping=true;
 for(const child of children){try{process.kill(-child.pid,'SIGTERM')}catch{}}
 setTimeout(()=>{for(const child of children){try{process.kill(-child.pid,'SIGKILL')}catch{}}process.exit(code)},1500);
}
for(const sig of ['SIGTERM','SIGINT'])process.on(sig,()=>stop(0));
for(const [app,port,extra] of [['web','3000',{AGENTVERSE_CONTROL_BASE:'/',AGENTVERSE_OFFICE_PROXY:'http://127.0.0.1:3002'}],['office','3002',{AGENTVERSE_OFFICE_BASE:'/office/',AGENTVERSE_CONTROL_PROXY:'http://127.0.0.1:3000'}]]){
 const child=spawn('npm',['--prefix',`apps/${app}`,'run','dev','--','--host','0.0.0.0','--port',port,'--strictPort'],{stdio:'inherit',env:{...process.env,...extra},detached:true});
 children.push(child);child.on('error',()=>stop(1));child.on('exit',code=>{if(!stopping)stop(code??1)});
}
