import {FURNITURE} from '../../../vendor/habblaud/client/src/art/api';
import type {RoomInfo} from '../../../vendor/habblaud/shared/types';
import type {AreaLayout} from '../../../vendor/habblaud/client/src/world/layout/types';
import {buildWalkGrid} from '../../../vendor/habblaud/client/src/world/layout/building';
export const CUSTOM_KINDS = ['plant_tall','bookshelf','floor_lamp'] as const;
export type CustomKind = typeof CUSTOM_KINDS[number];
export type CustomFurniture = {id:string;kind:CustomKind;x:number;y:number;variant?:string};
export type FurnishedRoom = RoomInfo & {customFurniture?:CustomFurniture[];layoutVersion?:number};
export type FurnitureState = {items:CustomFurniture[];version:number;seed:number};
const customId = (id:string) => `agentverse:custom:${id}`;
export const layoutSignature=(info:RoomInfo)=>JSON.stringify([(info as FurnishedRoom).layoutVersion??0,(info as FurnishedRoom).customFurniture??[]]);
export function withCustomFurniture(info:RoomInfo,base:AreaLayout):AreaLayout {
 const items=(info as FurnishedRoom).customFurniture??[];
 if(!items.length)return base;
 return {...base,furniture:[...base.furniture,...items.map(item=>({id:customId(item.id),kind:item.kind,tx:base.rect.x+item.x,ty:base.rect.y+item.y,variant:item.variant,order:1}))]};
}
/** Uses upstream footprint/grid/BFS rules, not decorative hitboxes. Server repeats trusted checks. */
export function validateFurniture(baseWithExtras:AreaLayout,items:CustomFurniture[]):void {
 const base={...baseWithExtras,furniture:baseWithExtras.furniture.filter(f=>!f.id.startsWith('agentverse:custom:'))};
 const {x:ox,y:oy,w,h}=base.rect;
 const baseGrid=buildWalkGrid(Math.ceil((ox+w)/16),[base]);
 const occupied=new Set<string>();
 for(const f of base.furniture){const d=FURNITURE[f.kind];for(let y=f.ty;y<f.ty+d.footprint.h;y++)for(let x=f.tx;x<f.tx+d.footprint.w;x++)occupied.add(`${x},${y}`);}
 const protectedCells=new Set(base.spots.map(s=>`${s.tx},${s.ty}`));
 const ids=new Set<string>();
 for(const item of items){
  if(!CUSTOM_KINDS.includes(item.kind)||!item.id||ids.has(item.id))throw new Error('Invalid or duplicate furniture');ids.add(item.id);
  const d=FURNITURE[item.kind];
  if(!Number.isInteger(item.x)||!Number.isInteger(item.y)||item.x<1||item.y<2||item.x+d.footprint.w>w-1||item.y+d.footprint.h>h-1)throw new Error('Place furniture inside the room floor');
  if(item.variant && (item.kind!=='plant_tall'||!['palm','ficus','monstera','bonsai'].includes(item.variant)))throw new Error('Invalid furniture variant');
  for(let y=oy+item.y;y<oy+item.y+d.footprint.h;y++)for(let x=ox+item.x;x<ox+item.x+d.footprint.w;x++){
   const key=`${x},${y}`;if(occupied.has(key)||protectedCells.has(key)||!baseGrid.walkable(x,y))throw new Error('Furniture overlaps a fixture, doorway or agent access tile');occupied.add(key);
  }
 }
 const candidate=withCustomFurniture({...({} as RoomInfo),customFurniture:items} as FurnishedRoom,base);
 const grid=buildWalkGrid(Math.ceil((ox+w)/16),[candidate]);
 const entry=base.door?{x:base.door.x,y:base.side==='north'?base.door.y:base.door.y+base.door.h-1}:base.spots[0];
 if(!entry)throw new Error('Room entrance unavailable');
 const before=baseGrid.reachableFrom(entry.x,entry.y);const after=grid.reachableFrom(entry.x,entry.y);
 for(const s of base.spots){const index=s.ty*grid.w+s.tx;if(before[index]&&!after[index])throw new Error('Furniture blocks an agent path');}
}
