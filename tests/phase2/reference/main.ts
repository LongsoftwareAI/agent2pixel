// Independent reference imports unmodified pinned upstream, never app vendor code.
import { registerDictionary } from '@upstream/shared/i18n';
import { EN } from '@upstream/shared/locales/en';
registerDictionary('en', EN);
const [{createWorld},{createUI},{OfficeStore},{setAccess},{parityFixture,FIXTURE_TIME}] = await Promise.all([
 import('@upstream/client/src/world'), import('@upstream/client/src/ui'),
 import('@upstream/client/src/net/store'), import('@upstream/client/src/net/access'), import('@fixture'),
]);
setAccess({remote:false,local:false,permissions:false,messages:false,terminal:false,spawn:false,world:false});
const store=new OfficeStore({mock:false});
const world=createWorld(document.querySelector('#world') as HTMLCanvasElement,store);
createUI(document.querySelector('#ui') as HTMLElement,store,world);
world.setPlayback({clock:()=>FIXTURE_TIME,scale:()=>0});
world.setOptions({theme:'none',daylight:'day',liveliness:'calm'});
store.applySnapshot(parityFixture());store.connection='open';
Object.assign(window,{qaReference:{world,store}});
