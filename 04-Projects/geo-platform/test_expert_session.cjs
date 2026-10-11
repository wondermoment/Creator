const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map(),get=s=>{if(!nodes.has(s))nodes.set(s,{innerHTML:'',value:'typing',textContent:'',disabled:false,addEventListener(){},querySelector:get,classList:{add(){},remove(){}}});return nodes.get(s)};
const c=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector:get,addEventListener(){},hidden:false},window:{addEventListener(){}},location:{hash:'#skills?expert=content'},localStorage:{getItem(){return null}},setTimeout(){},setInterval(){},clearTimeout(){}});
for(const f of ['app','planning','knowledge','manager','leads','delivery','sample','experts'])vm.runInContext(fs.readFileSync(`static/${f}.js`,'utf8'),c);
const run=s=>vm.runInContext(s,c);
run("pid='a';me={identity:'alice'};activeExpert='content';state={marker:'initial',role:'owner',execution:[]};expertConversation=()=>state.marker;syncManager=()=>{};toast=x=>messages.push(x);editContent=id=>opened.push(id)");
c.messages=[];c.opened=[];c.releaseRefresh=null;
function pending(){let resolve,reject;c.api=()=>new Promise((a,b)=>{resolve=a;reject=b});return {promise:run('refresh()'),resolve:marker=>resolve({marker,role:'owner',execution:[]}),reject};}
function validJob(){run("state={role:'owner',execution:[{id:'j',job_type:'expert_chat',status:'succeeded',payload:{workflow:'chat',expert_id:'content'},result:{answer:'valid'}}]}");}
(async()=>{
 let p=pending();run("me.identity='bob'");p.resolve('private');await p.promise;assert.equal(run('state.marker'),'initial');
 run("me.identity='alice'");p=pending();run('++epoch');p.resolve('old-session');await p.promise;assert.equal(run('state.marker'),'initial');
 p=pending();run("pid='b'");p.reject(Error('old failure'));await p.promise;assert.equal(c.messages.length,0);run("pid='a'");
 const old=pending(),newer=pending();newer.resolve('newest');await newer.promise;old.resolve('older');await old.promise;assert.equal(run('state.marker'),'newest');assert.equal(get('#expert-message').value,'typing');
 p=pending();run("activeExpert='technical'");p.resolve('wrong-expert');await p.promise;assert.equal(run('state.marker'),'newest');run("activeExpert='content'");
 p=pending();p.reject(Error('current failure'));await assert.rejects(p.promise,/current failure/);
 validJob();c.button={disabled:false,isConnected:true};let finish;c.api=()=>new Promise(r=>finish=r);p=run("saveExpertDraft('j',button)");run("me.identity='bob'");finish({id:'draft'});await p;assert.equal(c.opened.length,0);
 run("me.identity='alice'");validJob();let finishRefresh;c.api=async()=>({id:'draft'});run('refresh=()=>new Promise(r=>releaseRefresh=r)');p=run("saveExpertDraft('j',button)");await new Promise(setImmediate);run('++epoch');c.releaseRefresh();await p;assert.equal(c.opened.length,0,'recheck after refresh');
 validJob();run('refresh=async()=>{}');await run("saveExpertDraft('j',button)");assert.deepEqual(c.opened,['draft']);assert.equal(c.button.disabled,false);
 validJob();let reject;c.api=()=>new Promise((_,r)=>reject=r);p=run("saveExpertDraft('j',button)");c.location.hash='#workspace';reject(Error('old save error'));await p;assert.equal(c.messages.length,0);
 console.log('PASS: expert read ordering, account/project/epoch isolation, expert switch, preserved input, current errors and save checks before/after refresh');
})().catch(e=>{console.error(e);process.exitCode=1});
