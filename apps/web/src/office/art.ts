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
