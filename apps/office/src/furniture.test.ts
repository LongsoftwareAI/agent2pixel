import {test,expect} from 'vitest';
import {layoutProjectRoom} from '../../../vendor/habblaud/client/src/world/layout/room';
import {roomTheme} from '../../../vendor/habblaud/client/src/art/theme';
import {withCustomFurniture,validateFurniture,type FurnishedRoom,type CustomFurniture} from './furniture';
test('native decoration validates collision and preserves unedited layout identity',()=>{
 const base=layoutProjectRoom({id:'room',slot:0,seed:1},roomTheme(1));
 expect(withCustomFurniture({} as FurnishedRoom,base)).toBe(base);
 const fixture=base.furniture[0];expect(()=>validateFurniture(base,[{id:'bad',kind:'floor_lamp',x:fixture.tx-base.rect.x,y:fixture.ty-base.rect.y}])).toThrow();
 expect(()=>validateFurniture(base,[{id:'outside',kind:'bookshelf',x:20,y:2}])).toThrow();
 let valid:CustomFurniture|undefined;for(let y=2;y<10&&!valid;y++)for(let x=1;x<15&&!valid;x++){const item:CustomFurniture={id:'ok',kind:'floor_lamp',x,y};try{validateFurniture(base,[item]);valid=item;}catch{}}
 expect(valid).toBeDefined();const updated=withCustomFurniture({customFurniture:[valid!]} as FurnishedRoom,base);expect(updated.furniture).toHaveLength(base.furniture.length+1);expect(updated.furniture.at(-1)?.id).toBe('agentverse:custom:ok');expect(()=>validateFurniture(base,[valid!,valid!])).toThrow();
});
