export interface Workspace {id:string;name:string;root_path:string;created_at:string}
export interface Agent {id:string;workspace_id:string;name:string;role:string;system_prompt:string;brain:{provider:string;model:string;endpoint?:string;secret_ref?:string};skin:string;status:string;skills:string[];tools:string[];memory_policy:string;workstation:{x:number;y:number};enabled:boolean;execution?:{engine:string;profile?:string;version?:string};role_config?:{id:string;version:number;instructions:string;responsibilities:string[];output_schema?:unknown};skill_bindings?:{id:string;version:number}[];tool_grants?:{id:string;allow:boolean;approval_required?:boolean}[];memory_config?:{scope:'agent'|'workspace'|'none';retention?:number};appearance?:{seed:string;parts?:Record<string,unknown>}}
export interface GraphNode {id:string;type:'start'|'agent'|'condition'|'end';agent_id?:string;instructions?:string;deliverable?:{filename:string};position?:{x:number;y:number};condition?:{field:string;equals:string}}
export interface Graph {nodes:GraphNode[];edges:{source:string;target:string;label?:'true'|'false'}[]}
export interface Workflow {id:string;workspace_id:string;name:string;version:number;graph:Graph}
export interface Task {id:string;node_id:string;agent_id:string;state:string;input:string;output:string;error:string;retry_count:number}
export interface Run {id:string;workflow_id:string;workspace_id:string;state:string;input:string;output:string;error:string;started_at:string;ended_at:string;tasks:Task[];engine_version?:string;checkpoint?:Record<string,unknown>;artifacts?:Record<string,unknown>[]}
export interface RuntimeEvent {id:string;seq:number;schema_version:1;workspace_id:string;run_id:string|null;agent_id:string|null;event_type:string;payload:Record<string,unknown>;created_at:string}
export interface Furniture {id:string;asset_id:string;x:number;y:number;rotation:number}
export interface Room {id:string;workspace_id:string;width:number;height:number;furniture:Furniture[];assignments:Record<string,{x:number;y:number}>}
export interface Asset {id:string;name:string;kind:string;license:string;author:string}
export interface Bootstrap {workspaces:Workspace[];agents:Agent[];workflows:Workflow[];room:Room;assets:Asset[];runs:Run[]}
export interface Message {id:string;run_id:string;sender:string;recipient:string;payload:unknown;timestamp:string;correlation_id:string}

export interface RegistryRole {id:string;name:string;version:number;instructions:string;responsibilities?:string[]}
export interface RegistrySkill {id:string;name:string;version:number;instructions:string;allowed_tools:string[]}
export interface RegistryTool {id:string;name?:string;description?:string;approval_required?:boolean}
export interface Engine {id:string;available:boolean;reason?:string;version?:string;capabilities:Record<string,unknown>}
export interface Catalog {roles:RegistryRole[];skills:RegistrySkill[];tools:RegistryTool[];engines:Engine[]}

export interface WorkflowTemplate {id:string;name:string;description:string;roles:string[];steps:{role:string;instructions:string;deliverable?:{filename:string}}[]}
export interface WorkItem {id:string;workspace_id:string;title:string;description:string;workflow_id:string;acceptance_criteria:string[];status:string;run_ids:string[];latest_run_id:string|null;brief_revision?:number;reviews:{decision:string;comment:string;run_id?:string;reviewed_at?:string}[]}
