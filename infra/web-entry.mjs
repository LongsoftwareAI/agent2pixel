// Two localhost frontends in one container; only office3000 is published.
import {spawn} from 'node:child_process';
const children=[];
let stopping=false;
function stop(code=0){
 if(stopping)return;stopping=true;
 for(const child of children){try{process.kill(-child.pid,'SIGTERM')}catch{}}
 setTimeout(()=>{for(const child of children){try{process.kill(-child.pid,'SIGKILL')}catch{}}process.exit(code)},1500);
}
for(const sig of ['SIGTERM','SIGINT'])process.on(sig,()=>stop(0));
for(const [app,port,extra] of [['web','3001',{AGENTVERSE_CONTROL_BASE:'/control/'}],['office','3000',{}]]){
 const child=spawn('npm',['--prefix',`apps/${app}`,'run','dev','--','--host','0.0.0.0','--port',port,'--strictPort'],{stdio:'inherit',env:{...process.env,...extra},detached:true});
 children.push(child);child.on('error',()=>stop(1));child.on('exit',code=>{if(!stopping)stop(code??1)});
}
