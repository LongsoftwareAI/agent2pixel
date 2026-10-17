import {useEffect,useRef,useState} from 'react';
import {Application,Container,Graphics,Text} from 'pixi.js';
import type {Agent,Room,RuntimeEvent} from '../types';
import {backendState,pathfind,validateLayout,type Point} from './model';
import {furniture,person,roomDecor,TILE} from './art';
interface Props {room:Room|null;agents:Agent[];events?:RuntimeEvent[];selectedAgentId?:string|null;onSelectAgent:(id:string)=>void;editMode?:boolean;onLayoutChange:(room:Room)=>void}
export function OfficeCanvas(props:Props){
 const host=useRef<HTMLDivElement>(null),latest=useRef(props);latest.current=props;
 const [zoom,setZoom]=useState(1),[grid,setGrid]=useState(false),[tool,setTool]=useState('select'),[notice,setNotice]=useState('');
 const controls=useRef({zoom,grid,tool});controls.current={zoom,grid,tool};
 useEffect(()=>{
 if(!host.current)return;let stopped=false,ready=false;const app=new Application();let tick=0;let offset={x:24,y:34};let viewport='';let drag:Point|null=null;let draggedId:string|null=null;let draggedFrom:Point|null=null;
 const positions=new Map<string,{point:Point;path:Point[];target:string}>();
 const world=new Container();const draw=new Graphics();world.addChild(draw);const labels=new Container();world.addChild(labels);
 const pointer=(e:PointerEvent)=>{const bounds=app.canvas.getBoundingClientRect();return {x:Math.floor(((e.clientX-bounds.left)*app.screen.width/bounds.width-offset.x)/controls.current.zoom/TILE),y:Math.floor(((e.clientY-bounds.top)*app.screen.height/bounds.height-offset.y)/controls.current.zoom/TILE)};};
 const save=(room:Room)=>{const error=validateLayout(room);if(error){setNotice(error);return;}latest.current.onLayoutChange(room);setNotice('Đã gửi layout để lưu.');};
 const down=(e:PointerEvent)=>{const room=latest.current.room;if(!room)return;const p=pointer(e);
 if(e.button===1||e.button===2||!latest.current.editMode&&e.shiftKey){drag={x:e.clientX,y:e.clientY};app.canvas.setPointerCapture(e.pointerId);return;}
 if(latest.current.editMode){const found=room.furniture.find(f=>f.x===p.x&&f.y===p.y);if(controls.current.tool==='remove'){if(found)save({...room,furniture:room.furniture.filter(f=>f.id!==found.id)});return;}
 if(controls.current.tool==='assign'){const id=latest.current.selectedAgentId;if(!id){setNotice('Chọn một agent trước khi gán vị trí.');return;}save({...room,assignments:{...room.assignments,[id]:p}});return;}
 if(controls.current.tool!=='select'){save({...room,furniture:[...room.furniture,{id:crypto.randomUUID(),asset_id:controls.current.tool,x:p.x,y:p.y,rotation:0}]});return;}
 if(found){draggedId=found.id;draggedFrom=p;app.canvas.setPointerCapture(e.pointerId);return;}}
 const agent=latest.current.agents.find(a=>{const q=positions.get(a.id)?.point??room.assignments[a.id]??a.workstation;return Math.abs(q.x-p.x)<1&&Math.abs(q.y-p.y)<1;});if(agent)latest.current.onSelectAgent(agent.id);
 };
 const move=(e:PointerEvent)=>{if(drag){offset={x:offset.x+(e.clientX-drag.x)*app.screen.width/app.canvas.getBoundingClientRect().width,y:offset.y+(e.clientY-drag.y)*app.screen.height/app.canvas.getBoundingClientRect().height};drag={x:e.clientX,y:e.clientY};}};
 const up=(e:PointerEvent)=>{drag=null;const room=latest.current.room;if(draggedId&&room){const p=pointer(e);if(!draggedFrom||p.x!==draggedFrom.x||p.y!==draggedFrom.y)save({...room,furniture:room.furniture.map(f=>f.id===draggedId?{...f,...p}:f)});}draggedId=null;draggedFrom=null;};
 const context=(e:Event)=>e.preventDefault();
 const wheel=(e:WheelEvent)=>{e.preventDefault();if(e.deltaY!==0)setZoom(current=>Math.min(3,Math.max(1,current+(e.deltaY<0?1:-1))));};
 void app.init({resizeTo:host.current,background:0xe8eee9,antialias:false,resolution:1,autoDensity:false,preference:'webgl'}).then(()=>{
 ready=true;if(stopped){app.destroy(true,{children:true});return;}host.current!.appendChild(app.canvas);app.canvas.style.imageRendering='pixelated';app.canvas.style.width='100%';app.canvas.style.height='100%';app.canvas.setAttribute('aria-label','Văn phòng pixel tương tác');app.canvas.setAttribute('role','img');app.stage.addChild(world);app.ticker.maxFPS=12;
 app.canvas.addEventListener('pointerdown',down);app.canvas.addEventListener('pointermove',move);app.canvas.addEventListener('pointerup',up);app.canvas.addEventListener('contextmenu',context);app.canvas.addEventListener('wheel',wheel,{passive:false});
 app.ticker.add(()=>{tick++;const {room,agents,selectedAgentId}=latest.current;if(!room)return;const z=controls.current.zoom;const viewKey=`${app.screen.width}:${app.screen.height}:${room.id}:${z}`;if(viewKey!==viewport){viewport=viewKey;offset={x:Math.max(12,Math.floor((app.screen.width-room.width*TILE*z)/2)),y:Math.max(58*z,Math.floor((app.screen.height-room.height*TILE*z)/2))};}offset.x=Math.min(app.screen.width-48,Math.max(48-room.width*TILE*z,offset.x));offset.y=Math.min(app.screen.height-48,Math.max(48-room.height*TILE*z,offset.y));world.scale.set(z);world.position.set(Math.round(offset.x),Math.round(offset.y));draw.clear();labels.removeChildren().forEach(x=>x.destroy());
 draw.rect(-6,-40,room.width*TILE+12,room.height*TILE+50).fill(0x718284);draw.rect(0,-20,room.width*TILE,20).fill(0xaebcc0);draw.rect(0,-3,room.width*TILE,5).fill(0x65777e);
 for(let y=0;y<room.height;y++)for(let x=0;x<room.width;x++){const warm=x<Math.floor(room.width*.6);draw.rect(x*TILE,y*TILE,TILE,TILE).fill(warm?((x+y)%2?0xdfc8a4:0xe5d0af):((x+y)%2?0xbacdd0:0xc4d5d7));if(warm)draw.rect(x*TILE,y*TILE+23,TILE,1).fill(0xc7ad89);if(controls.current.grid){draw.rect(x*TILE,y*TILE,TILE,TILE).stroke({color:0x83999d,width:1,alpha:.5});}}
 roomDecor(draw,room.width,room.height);
 const text=(s:string,x:number,y:number,color=0x53666a,size=10)=>{const t=new Text({text:s,style:{fontFamily:'monospace',fontSize:size,fill:color}});t.position.set(x,y);labels.addChild(t);};
 draw.rect(0,-55,145,17).fill(0xf9f7ee);draw.rect(Math.floor(room.width*.6)*TILE,-55,145,17).fill(0xf9f7ee);text('STUDIO · FOCUS',7,-53,0x3e555a,11);text('LOUNGE · IDEAS',Math.floor(room.width*.6)*TILE+7,-53,0x3e555a,11);
 const split=Math.floor(room.width*.6)*TILE;draw.rect(split-2,0,4,room.height*TILE).fill({color:0x839a9f,alpha:.3});draw.rect(split-6,Math.floor(room.height/2)*TILE-12,12,48).fill(0xe5d9bc);draw.rect(split-4,-22,8,26).fill(0x627d85);text('↔',split-5,Math.floor(room.height/2)*TILE+3,0x698680,10);
 // Shelves/windows/rugs are flat nonblocking decor; furniture below comes only from saved layout.
 const entities:{y:number;render:()=>void}[]=room.furniture.map(f=>({y:f.y,render:()=>furniture(draw,f.asset_id,f.x*TILE,f.y*TILE)}));
 for(const a of agents){const destination=room.assignments[a.id]??a.workstation??{x:1,y:1};let pos=positions.get(a.id);const target=`${room.id}:${destination.x},${destination.y}`;
 if(!pos){pos={point:{...destination},path:[],target};positions.set(a.id,pos);}else if(pos.target!==target){pos.path=pathfind(room,{x:Math.round(pos.point.x),y:Math.round(pos.point.y)},destination);pos.target=target;}
 if(pos.path.length&&tick%3===0)pos.point=pos.path.shift()!;const state=pos.path.length?'walk':backendState(a.status);const p={...pos.point};entities.push({y:p.y+.5,render:()=>{person(draw,p.x*TILE,p.y*TILE,a.skin,state,tick,selectedAgentId===a.id);text(a.name,p.x*TILE-6,p.y*TILE+25,selectedAgentId===a.id?0x14796f:0x4e5e66,9);}});}
 entities.sort((a,b)=>a.y-b.y).forEach(e=>e.render());
 });
 }).catch(error=>{if(!stopped)setNotice(`Không khởi tạo được canvas: ${String(error)}`);});
 return()=>{stopped=true;if(ready){app.canvas.removeEventListener('pointerdown',down);app.canvas.removeEventListener('pointermove',move);app.canvas.removeEventListener('pointerup',up);app.canvas.removeEventListener('contextmenu',context);app.canvas.removeEventListener('wheel',wheel);app.destroy(true,{children:true});}};
 },[]);
 return <section className="office-canvas" style={{height:'100%',minHeight:380,display:'flex',flexDirection:'column'}}>
 <div style={{display:'flex',gap:8,alignItems:'center',padding:'8px 12px',flexWrap:'wrap',fontSize:12}}><strong>Văn phòng · 01 tầng</strong><button aria-label="Thu nhỏ" onClick={()=>setZoom(Math.max(1,zoom-1))}>−</button><span>{zoom}×</span><button aria-label="Phóng to" onClick={()=>setZoom(Math.min(3,zoom+1))}>+</button><button aria-pressed={grid} onClick={()=>setGrid(!grid)}>Lưới</button>{props.editMode&&<select aria-label="Công cụ nội thất" value={tool} onChange={e=>setTool(e.target.value)}><option value="select">Chọn / kéo đồ</option><option value="assign">Gán vị trí agent đã chọn</option><option value="desk">Thêm bàn</option><option value="chair">Thêm ghế</option><option value="plant">Thêm cây</option><option value="bookshelf">Thêm kệ sách</option><option value="sofa">Thêm sofa</option><option value="remove">Xóa đồ</option></select>}<span style={{marginLeft:'auto',color:'#697c80'}}>Shift + kéo để pan · chọn agent</span></div>
 <div ref={host} style={{flex:1,minHeight:320,overflow:'hidden',borderRadius:8,touchAction:'none'}}/>{notice&&<div role="status" style={{padding:8,fontSize:12}}>{notice}</div>}
 </section>;
}
