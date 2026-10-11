const fs=require('fs'),vm=require('vm'),assert=require('assert');
let route='repurpose',timer=0,calls=0,toasts=0;const timers=new Map(),els={'#vc-library':{innerHTML:'initial'},'#vc-error':{textContent:''},'#vc-editor':{innerHTML:''}};
const ctx=vm.createContext({console,Map,JSON,Number,String,epoch:1,pid:'p',me:{identity:'u'},state:{asset:[],content:[]},document:{addEventListener(){}},setTimeout:f=>{timers.set(++timer,f);return timer},clearTimeout:id=>timers.delete(id),page:()=>route,$:s=>els[s],esc:s=>String(s??''),action:()=>'',fmt:()=>'',canEdit:()=>true,toast:()=>toasts++});
vm.runInContext(fs.readFileSync('static/video-composer.js','utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
const data=(label,status)=>({capabilities:{message:label},plans:[],renders:status?[{id:'j',status,plan_snapshot:{title:'test'},created:'',source_revision:1,plan_revision:1}]:[]});
function pending(){let yes,no;ctx.api=()=>{calls++;return new Promise((a,b)=>{yes=a;no=b})};return {promise:run('videoLoad()'),resolve:yes,reject:no};}
(async()=>{
 const first=pending(),second=pending();second.resolve(data('latest'));await second.promise;first.resolve(data('stale'));await first.promise;assert.equal(run('videoDraft().data.capabilities.message'),'latest');
 let p=pending();ctx.epoch++;p.resolve(data('old-session'));await p.promise;assert.equal(run('videoDraft().data.capabilities.message'),'latest');
 p=pending();run('clearVideoSession()');p.resolve(data('before-logout'));await p.promise;assert.equal(run('videoDraft().data'),null);assert.equal(timers.size,0);
 p=pending();ctx.me.identity='other';p.reject(Error('private failure'));await p.promise;assert.equal(run('videoDraft().error'),'');ctx.me.identity='u';
 p=pending();p.resolve(data('working','running'));await p.promise;assert.equal(timers.size,1);
 const scheduled=[...timers.values()][0],before=calls;route='workspace';scheduled();assert.equal(calls,before,'leaving page stops polling');
 route='repurpose';run('videoComposerPanel()');assert.equal(run('videoDraft().loading'),true,'returning resumes pending jobs');
 const callback=[...timers.values()][0];run('clearVideoSession()');callback();assert.equal(calls,before,'old timer cannot read next session');
 run("videoDraft().plan={title:'unsaved',source_id:'s',source_revision:1,revision:0,aspect:'landscape',scenes:[{text:'caption',asset_id:'a',seconds:3,start:0}]}");
 let saveResolve;ctx.api=()=>{calls++;return new Promise(r=>saveResolve=r)};const save=run('videoSave(true)');run('clearVideoSession()');saveResolve({id:'saved',title:'old',revision:1,scenes:[]});await save;
 assert.equal(calls,before+1,'old save must not enqueue a render after logout');assert.equal(run('videoDraft().plan'),null);assert.equal(toasts,0);
 assert(fs.readFileSync('static/repurpose.js','utf8').includes("if(typeof clearVideoSession==='function')clearVideoSession()"));
 console.log('PASS: video request ordering, epoch/logout isolation, stale errors, scoped timers, polling resume and no render continuation after logout');
})().catch(e=>{console.error(e);process.exitCode=1});
