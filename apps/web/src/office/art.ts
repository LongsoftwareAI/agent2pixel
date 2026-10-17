/** Original procedural AgentVerse pixel artwork. CC0-1.0; no upstream art/code. */
import {Graphics} from 'pixi.js';
export const TILE=24;
function rect(g:Graphics,x:number,y:number,w:number,h:number,c:number){g.rect(x,y,w,h).fill(c);}
export function furniture(g:Graphics,kind:string,x:number,y:number){
 rect(g,x+2,y+18,21,5,0x000000);g.alpha=0.95;
 if(kind.includes('plant')){rect(g,x+8,y+13,9,8,0xb97759);rect(g,x+6,y+12,13,3,0xd89c70);rect(g,x+10,y+3,4,12,0x3f7959);rect(g,x+4,y+5,9,6,0x599768);rect(g,x+13,y,7,10,0x79b275);rect(g,x+7,y,6,8,0x82bc7a);}
 else if(kind.includes('chair')){rect(g,x+7,y+7,12,10,0x38586d);rect(g,x+6,y+5,14,8,0x60889b);rect(g,x+6,y+15,14,5,0x77a3b2);rect(g,x+8,y+20,2,3,0x3a4459);rect(g,x+17,y+20,2,3,0x3a4459);}
 else if(kind.includes('shelf')||kind.includes('book')){rect(g,x+2,y-10,21,31,0x825f4d);rect(g,x+3,y-9,19,27,0xc19971);for(let row=0;row<3;row++){for(let i=0;i<5;i++)rect(g,x+5+i*3,y-7+row*8,2,6,[0x7695ab,0xc8827f,0xe5c884,0x8cad8d,0xc5b0cf][i]);rect(g,x+3,y+row*8,19,2,0x725a4d);}}
 else if(kind.includes('sofa')){rect(g,x+2,y+4,21,17,0x7c6b98);rect(g,x+4,y+1,17,12,0xab96c0);rect(g,x+4,y+13,8,5,0xc4add4);rect(g,x+13,y+13,8,5,0xc4add4);}
 else {rect(g,x+3,y+14,3,9,0x775b51);rect(g,x+19,y+14,3,9,0x775b51);rect(g,x+1,y+4,23,12,0x997455);rect(g,x,y+3,24,10,0xd5ac78);rect(g,x+5,y-5,14,11,0x303c51);rect(g,x+6,y-4,12,8,0x91c9c6);rect(g,x+8,y-2,7,1,0xc8f1df);rect(g,x+10,y+6,4,2,0x536075);rect(g,x+6,y+9,11,2,0xf2e2c6);rect(g,x+20,y+6,2,4,0xe8cfac);}
}
export function person(g:Graphics,x:number,y:number,skin:string,state:string,frame:number,selected:boolean){
 const hash=[...skin].reduce((a,c)=>a+c.charCodeAt(0),0),skinTone=[0xf4c99d,0xb87956,0xe1a57b,0x875a46][hash%4],shirt=[0x5c8cbd,0xa177b0,0x6c9e8d,0xc88b69][hash%4];
 rect(g,x+5,y+18,15,4,0x99a9a2);if(selected){g.rect(x+1,y+21,23,2).fill(0x2bbdaf);g.rect(x,y+2,2,20).fill(0x2bbdaf);g.rect(x+23,y+2,2,20).fill(0x2bbdaf);}
 const step=state==='walk'?frame%2:0;rect(g,x+8,y+15,4,6+step,0x34435b);rect(g,x+14,y+15,4,7-step,0x34435b);rect(g,x+6,y+8,14,9,shirt);rect(g,x+8,y-2,11,12,skinTone);rect(g,x+7,y-4,12,5,0x493b40);rect(g,x+6,y-1,3,6,0x493b40);rect(g,x+15,y+3,2,2,0x303744);rect(g,x+13,y+7,4,1,0xa26d5c);
 rect(g,x+4,y+10+(state==='working'?frame%2:0),3,6,skinTone);rect(g,x+20,y+10,3,6,skinTone);
 const c=state==='error'?0xe06c75:state==='completed'?0x49a48e:state==='working'?0x64bcb3:0x9b9bb7;rect(g,x+17,y-10,8,7,0xfaf5e8);rect(g,x+19,y-8,4,3,c);
}
/** Flat floor textiles and wall fittings are decorative only, never collision objects. */
export function roomDecor(g:Graphics,width:number,height:number){
 const split=Math.floor(width*.6)*TILE;
 const rug=(x:number,y:number,w:number,h:number,color:number)=>{rect(g,x-2,y-2,w+4,h+4,0x9bafad);rect(g,x,y,w,h,color);g.rect(x+4,y+4,w-8,h-8).stroke({width:1,color:0xd9e5d9});for(let i=3;i<w;i+=6){rect(g,x+i,y-4,2,3,0xe8e1c9);rect(g,x+i,y+h+1,2,3,0xe8e1c9);}for(let i=10;i<w-8;i+=12)for(let j=10;j<h-8;j+=12)rect(g,x+i,y+j,2,2,0xc8d9ce);};
 rug(30,42,Math.max(72,split-60),60,0xa9bfb4);rug(30,Math.max(150,height*TILE-96),Math.max(72,split-60),60,0xb8b3c5);
 rug(split+24,Math.min(100,height*TILE-130),Math.max(48,(width*TILE-split)-48),96,0x8faeb2);
 // Wall paneling, skirting and shelf-mounted book spines; nothing placed on floor.
 rect(g,0,-36,width*TILE,32,0xb9c7c7);rect(g,0,-8,width*TILE,5,0x889b9e);
 for(let x=12;x<split-24;x+=72){rect(g,x,-32,54,22,0xd8c1a1);rect(g,x+2,-30,50,17,0x867260);for(let i=0;i<11;i++)rect(g,x+4+i*4,-28+(i%3),3,13-(i%3),[0x7c9d9b,0xc68f85,0xd8c390,0xa59bb5][i%4]);rect(g,x-1,-12,56,3,0xead4b6);}
 const windowX=split+16, windowW=Math.max(28,width*TILE-split-72);rect(g,windowX,-33,windowW,27,0x647f8c);rect(g,windowX+3,-30,windowW-6,20,0xb6d9dc);rect(g,windowX+6,-27,windowW-12,5,0xd6e9dc);rect(g,windowX+Math.floor(windowW/2),-30,2,20,0x78929a);rect(g,windowX-2,-7,windowW+4,3,0xe3ddd0);
 const boardX=width*TILE-48;rect(g,boardX,-32,36,25,0x93775e);rect(g,boardX+2,-30,32,21,0xccad82);rect(g,boardX+5,-27,11,13,0xf5ead5);rect(g,boardX+20,-25,10,10,0xbccdc1);rect(g,boardX+9,-28,2,2,0xc77971);rect(g,boardX+23,-26,2,2,0x668ba3);
 // Small floor inlay at open threshold; flat, passable material.
 rect(g,split-6,Math.floor(height/2)*TILE-12,12,48,0xe5d9bc);for(let y=0;y<48;y+=8)rect(g,split-5,Math.floor(height/2)*TILE-12+y,10,1,0xcbbca0);
}
