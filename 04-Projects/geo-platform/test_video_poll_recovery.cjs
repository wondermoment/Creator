const fs=require('fs'),vm=require('vm'),assert=require('assert');
let serial=0;const timers=new Map(),els={'#vc-library':{innerHTML:''},'#vc-error':{textContent:''}};
const ctx=vm.createContext({console,Map,JSON,Number,String,epoch:1,pid:'p',me:{identity:'u'},state:{asset:[],content:[]},document:{addEventListener(){}},setTimeout:(fn,delay)=>{timers.set(++serial,{fn,delay});return serial},clearTimeout:id=>timers.delete(id),page:()=> 'repurpose',$:s=>els[s],esc:s=>String(s??''),action:()=>'',fmt:()=>'',canEdit:()=>true});
vm.runInContext(fs.readFileSync('static/video-composer.js','utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
const working={capabilities:{message:'available'},plans:[],renders:[{id:'j',status:'running',plan_snapshot:{title:'sample'}}]};
async function fire(){assert.equal(timers.size,1);const [id,t]=[...timers][0];timers.delete(id);t.fn();await Promise.resolve();await Promise.resolve();}
(async()=>{
 ctx.api=async()=>working;await run('videoLoad()');assert.equal([...timers.values()][0].delay,3000);
 ctx.api=async()=>{throw Error('network disconnected')};await fire();
 assert.equal([...timers.values()][0].delay,6000,'first failure backs off');await fire();
 assert.equal([...timers.values()][0].delay,12000,'second failure backs off');await fire();
 assert.equal(timers.size,0,'third failure stops automatic reads');assert(els['#vc-error'].textContent.includes('刷新制作记录'));
 run('videoComposerPanel()');assert.equal(timers.size,0,'rerender cannot bypass paused retries');
 assert.equal(run('videoDraft().data.renders[0].status'),'running','read failure must not invent a failed render');
 ctx.api=async()=>({...working,renders:[]});await run('videoLoad()');assert.equal(timers.size,0);assert.equal(run('videoDraft().error'),'');
 ctx.api=async()=>working;await run('videoLoad()');assert.equal([...timers.values()][0].delay,3000,'manual refresh resumes normal cadence');
 ctx.api=async()=>{const e=Error('access denied');e.status=403;throw e};await fire();assert.equal(timers.size,0,'permission errors never auto retry');
 run('clearVideoSession()');ctx.api=async()=>{throw Error('initial read failed')};await run('videoLoad()');assert.equal([...timers.values()][0].delay,6000,'first read also has bounded recovery');
 console.log('PASS: bounded network recovery, increasing delay, paused rerender, manual resume, permission stop and first-read recovery');
})().catch(e=>{console.error(e);process.exitCode=1});
