export type Point = {x:number;y:number};
export type Furniture = Point & {id:string;asset_id:string;rotation:number};
export type OfficeRoom = {id:string;workspace_id:string;width:number;height:number;furniture:Furniture[];assignments:Record<string,Point>};
export type OfficeAgent = {id:string;name:string;skin:string;status:string;workstation:Point};
export function pathfind(room:OfficeRoom, start:Point, end:Point):Point[] {
  const blocked=new Set(room.furniture.map(f=>`${f.x},${f.y}`));
  const key=(p:Point)=>`${p.x},${p.y}`;
  if (!inside(room,start)||!inside(room,end)||blocked.has(key(end))) return [];
  const queue:Point[]=[start], seen=new Set([key(start)]), parents=new Map<string,Point>();
  for(let i=0;i<queue.length;i++) {const p=queue[i];if(key(p)===key(end)){const out:Point[]=[];let q=p;while(key(q)!==key(start)){out.unshift(q);q=parents.get(key(q))!;}return out;}
    for(const d of [{x:0,y:1},{x:1,y:0},{x:0,y:-1},{x:-1,y:0}]){const q={x:p.x+d.x,y:p.y+d.y};if(inside(room,q)&&!blocked.has(key(q))&&!seen.has(key(q))){seen.add(key(q));parents.set(key(q),p);queue.push(q);}}
  } return [];
}
export function inside(room:OfficeRoom,p:Point){return Number.isInteger(p.x)&&Number.isInteger(p.y)&&p.x>=0&&p.y>=0&&p.x<room.width&&p.y<room.height;}
export function validateLayout(room:OfficeRoom):string|null {
 const tiles=new Set<string>();const ids=new Set<string>();
 for(const f of room.furniture){const k=`${f.x},${f.y}`;if(!inside(room,f))return 'Nội thất nằm ngoài phòng.';if(tiles.has(k)||ids.has(f.id))return 'Nội thất bị chồng lấn.';tiles.add(k);ids.add(f.id);}
 const spawn={x:0,y:Math.floor(room.height/2)};
 if(tiles.has(`${spawn.x},${spawn.y}`))return 'Lối vào phải thông thoáng.';
 for(const p of Object.values(room.assignments)){if(!inside(room,p)||tiles.has(`${p.x},${p.y}`))return 'Vị trí agent bị chặn.';if((p.x!==spawn.x||p.y!==spawn.y)&&!pathfind(room,spawn,p).length)return 'Không có đường đến vị trí agent.';}
 return null;
}
export function backendState(status:string):'idle'|'walk'|'working'|'waiting'|'error'|'completed' {
 if(status==='working'||status==='running')return 'working';if(status==='queued'||status==='waiting')return 'waiting';if(status==='failed'||status==='error')return 'error';if(status==='completed')return 'completed';if(status==='walk')return 'walk';return 'idle';
}
