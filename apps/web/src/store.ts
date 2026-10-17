import {create} from 'zustand';
import type {RuntimeEvent} from './types';
interface State {workspaceId:string;connected:boolean;events:RuntimeEvent[];setWorkspace:(id:string)=>void;setConnected:(connected:boolean)=>void;receive:(event:RuntimeEvent)=>void}
export const useStore=create<State>((set)=>({workspaceId:localStorage.getItem('agentverse.workspace')??'',connected:false,events:[],setWorkspace:(workspaceId)=>{localStorage.setItem('agentverse.workspace',workspaceId);set({workspaceId,events:[],connected:false})},setConnected:(connected)=>set({connected}),receive:(event)=>set(state=>({events:state.events.some(e=>e.seq===event.seq)?state.events:[...state.events,event].sort((a,b)=>a.seq-b.seq).slice(-500)}))}));
