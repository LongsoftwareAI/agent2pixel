export async function api<T>(path:string, method='GET', data?:unknown):Promise<T>{
 const response=await fetch(path,{method,headers:{'Content-Type':'application/json'},...(data!==undefined?{body:JSON.stringify(data)}:{})});
 if(!response.ok){let detail:unknown;try{detail=(await response.json()).detail}catch{detail=response.statusText}throw new Error(typeof detail==='string'?detail:JSON.stringify(detail));}
 return response.json();
}
export function pretty(value:unknown):string {return typeof value==='string'?value:JSON.stringify(value,null,2)??''}
