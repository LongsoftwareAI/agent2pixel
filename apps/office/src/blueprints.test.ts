import {test,expect} from 'vitest';
import {writeFileSync,readFileSync} from 'node:fs';
import {layoutProjectRoom} from '../../../vendor/habblaud/client/src/world/layout/room';
import {roomTheme} from '../../../vendor/habblaud/client/src/art/theme';
import {FURNITURE} from '../../../vendor/habblaud/client/src/art/api';
import {buildWalkGrid} from '../../../vendor/habblaud/client/src/world/layout/building';
import {CUSTOM_KINDS} from './furniture';
/** Run with OFFICE_BLUEPRINT_OUTPUT=/absolute/path npm test -- blueprints.test.ts */
test('generate authoritative native room collision blueprints',()=>{
 const rooms=[];for(let seed=1;seed<=8;seed++)for(let slot=0;slot<2;slot++){
 const r=layoutProjectRoom({id:'room',slot,seed},roomTheme(seed));const grid=buildWalkGrid(Math.ceil((r.rect.x+r.rect.w)/16),[r]);const ox=r.rect.x,oy=r.rect.y;
 rooms.push({seed,slot,width:r.rect.w,height:r.rect.h,door:r.door?{x:r.door.x-ox,y:r.door.y-oy,w:r.door.w,h:r.door.h}:null,furniture:r.furniture.map(f=>({id:f.id,kind:f.kind,x:f.tx-ox,y:f.ty-oy,w:FURNITURE[f.kind].footprint.w,h:FURNITURE[f.kind].footprint.h,blocks:FURNITURE[f.kind].blocks})),spots:r.spots.map(s=>({id:s.id,kind:s.kind,x:s.tx-ox,y:s.ty-oy})),grid:Array.from({length:r.rect.h},(_,y)=>Array.from({length:r.rect.w},(_,x)=>grid.get(ox+x,oy+y)))});
 }
 const result={schema_version:1,upstream:{repository:'https://github.com/marmottajr/habblaud',commit:'faa1a012b5fbf632c66dc6801c5383e53a542406',license:'MIT',copyright:'2026 Márcio Junior'},footprints:Object.fromEntries(CUSTOM_KINDS.map(k=>{const f=FURNITURE[k];return[k,{mount:f.mount,footprint:f.footprint,blocks:f.blocks,...(k==='plant_tall'?{variants:['palm','ficus','monstera','bonsai']}:{})}];})),rooms};
 expect(rooms).toHaveLength(16);
 if(process.env.OFFICE_BLUEPRINT_OUTPUT)writeFileSync(process.env.OFFICE_BLUEPRINT_OUTPUT,JSON.stringify(result,null,2)+'\n');
 if(process.env.OFFICE_BLUEPRINT_COMPARE)expect(result).toEqual(JSON.parse(readFileSync(process.env.OFFICE_BLUEPRINT_COMPARE,'utf8')));
});
