import { registerDictionary, getLocale } from '../../../vendor/habblaud/shared/i18n';
import { EN } from '../../../vendor/habblaud/shared/locales/en';
import './style.css';
registerDictionary('en', EN);
// Upstream UI modules read translations at module evaluation; import after dictionary registration.
const [{createWorld},{createUI},{setAccess,loadAccess},{AgentVerseStore},{OfficeStore}] = await Promise.all([
 import('../../../vendor/habblaud/client/src/world'),import('../../../vendor/habblaud/client/src/ui'),
 import('../../../vendor/habblaud/client/src/net/access'),import('./adapter'),import('../../../vendor/habblaud/client/src/net/store'),
]);
document.documentElement.lang = getLocale();
setAccess({remote:false,local:false,permissions:false,messages:false,terminal:false,spawn:false,world:false});
const fixtureMode = import.meta.env.DEV && new URLSearchParams(location.search).get('fixture') === 'parity';
const store = fixtureMode ? new OfficeStore({mock:false}) : new AgentVerseStore();
// Fixture selection/history remains entirely local and never calls domain agent detail.
if (fixtureMode) store.agentHistory = async id => store.agent(id)?.recent ?? [];
const root = document.getElementById('ui')!;
const {withCustomFurniture,layoutSignature}=await import('./furniture');
const world = createWorld(document.getElementById('world') as HTMLCanvasElement,store,fixtureMode?{}:{roomLayoutTransform:withCustomFurniture,roomLayoutSignature:layoutSignature});
createUI(root,store,world,undefined,{agentverse:true});
world.setOptions({theme:'none',ambientSocial:fixtureMode});
const name = root.querySelector('.ui-brand__name');
if (name) {name.textContent='AgentVerse';name.setAttribute('aria-label','AgentVerse');}
const links = document.createElement('nav'); links.className='av-controls';links.setAttribute('aria-label','AgentVerse controls');
for(const [label,hash] of [['Agents','agents'],['Workflows','workflows'],['Runs','runs'],['Settings','settings']]) {
 const a=document.createElement('a');a.href=`/control/#${hash}`;a.textContent=label;links.append(a);
}
root.querySelector('.ui-topbar__right')?.prepend(links);
const attribution=document.createElement('a');attribution.className='av-attribution';attribution.href='https://github.com/marmottajr/habblaud';attribution.textContent='Office art & renderer: Habblaud · MIT';attribution.target='_blank';attribution.rel='noopener noreferrer';root.append(attribution);
if(fixtureMode){
 const {parityFixture,FIXTURE_TIME}=await import('./fixture');
 world.setPlayback?.({clock:()=>FIXTURE_TIME,scale:()=>0});
 world.setOptions({theme:'none',daylight:'day',liveliness:'calm'});
 store.applySnapshot(parityFixture());store.connection='open';
 const badge=document.createElement('div');badge.className='av-fixture';badge.textContent='TEST FIXTURE — no live execution';root.append(badge);
} else {
 const {mountFurnitureEditor}=await import('./furniture-editor');mountFurnitureEditor(root,store,world);
 await loadAccess();
 void (store as InstanceType<typeof AgentVerseStore>).bootstrap().catch(error=>{
  console.error('[AgentVerse office]',error);
  const alert=document.createElement('div');alert.className='av-error';alert.role='alert';alert.textContent='Office data unavailable. Reconnecting to local backend…';root.append(alert);
  store.on('snapshot',()=>alert.remove());
 });
}
Object.assign(window,{agentverseOffice:{store,world,fixture:fixtureMode}});
window.addEventListener('pagehide',()=>{store.disconnect();world.destroy();},{once:true});
