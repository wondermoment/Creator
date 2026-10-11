const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map(),listeners={};
const node=k=>{if(!nodes.has(k))nodes.set(k,{innerHTML:'',value:'',open:true,classList:{add(){},remove(){}},addEventListener(){},close(){this.open=false},showModal(){this.open=true},querySelector:node});return nodes.get(k)};
const ctx=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector:node,addEventListener(t,f){(listeners[t]??=[]).push(f)}},window:{addEventListener(){}},location:{hash:'#content'},localStorage:{getItem(){return null}},setInterval(){},setTimeout(){},clearTimeout(){},fetch(){throw Error('Unexpected network')}});
vm.runInContext(fs.readFileSync('static/app.js','utf8'),ctx);
const setup=()=>vm.runInContext(`pid='p1';me={csrf:'test'};state={role:'owner',project:{name:'测试企业'},content:[{id:'c1',title:'<script>title</script>',revision:2,approved_revision:2,status:'approved',channels:['企业官网','微信公众号'],sources:[],approval_summary:{effective_approved:true}}],publication:[]};render=()=>{};refresh=async()=>{};previewId='c1';previewSnapshot={project:'p1',id:'c1',revision:2,ready:true};`,ctx);
const click=async a=>{const b={dataset:{action:a,id:'c1'},disabled:false};await listeners.click[0]({target:{closest:()=>b}});return b};
async function main(){
 setup();vm.runInContext(`openPublishTarget('p1','c1',2)`,ctx);
 let html=vm.runInContext('publishHandoffPanel()',ctx);assert(html.includes('matrix-create'));assert(html.includes('&lt;script&gt;'));assert(!html.includes('<script>'));
 assert.equal(vm.runInContext(`publishTargetRevision('c1')`,ctx),2);
 vm.runInContext(`state.publication=[{content_id:'c1',revision:2,channel:'企业官网'},{content_id:'c1',revision:2,channel:'微信公众号'}]`,ctx);assert(!vm.runInContext('publishHandoffPanel()',ctx).includes('matrix-create'));
 vm.runInContext(`state.role='reviewer'`,ctx);assert.throws(()=>vm.runInContext(`publishTargetRevision('c1')`,ctx),/管理员/);assert(!vm.runInContext('publishHandoffPanel()',ctx).includes('matrix-create'));
 vm.runInContext(`state.role='owner';state.content[0].revision=3`,ctx);assert.throws(()=>vm.runInContext(`publishTargetRevision('c1')`,ctx),/版本/);assert(!vm.runInContext('publishHandoffPanel()',ctx).includes('matrix-create'));
 vm.runInContext(`state.content[0].revision=2;state.content[0].approval_summary.effective_approved=false`,ctx);assert.throws(()=>vm.runInContext(`publishTargetRevision('c1')`,ctx),/审核/);
 vm.runInContext(`pid='p2'`,ctx);assert(!vm.runInContext('publishHandoffPanel()',ctx).includes('&lt;script&gt;'));assert.throws(()=>vm.runInContext(`publishTargetRevision('c1')`,ctx),/企业/);
 setup();const calls=[];ctx.record=(...args)=>calls.push(args);vm.runInContext(`api=async(...args)=>{record(...args);return {ok:true}}`,ctx);
 await click('approve-go-publish');assert.equal(calls.length,1);assert(calls[0][0].endsWith('/review'));assert.equal(calls[0][2].revision,2);assert.equal(calls[0][2].action,'approve');assert(ctx.location.hash.startsWith('publish?'));assert(!calls.some(c=>c[0].endsWith('/publish')));
 await click('matrix-create');assert.equal(calls.length,2);assert(calls[1][0].endsWith('/publish'));assert.equal(calls[1][2].revision,2);
 setup();ctx.location.hash='#content';calls.length=0;vm.runInContext(`api=async()=>{throw Error('知识未核准')}`,ctx);await click('approve-go-publish');assert.equal(ctx.location.hash,'#content');
 setup();ctx.location.hash='#content';vm.runInContext(`api=async()=>{pid='p2';return {ok:true}}`,ctx);await click('approve-go-publish');assert.equal(ctx.location.hash,'#content');
 setup();ctx.location.hash='#content';vm.runInContext(`previewSnapshot.ready=false;api=async(...args)=>record(...args)`,ctx);await click('approve-go-publish');assert.equal(calls.length,0);assert.equal(ctx.location.hash,'#content');
 console.log('PASS: approval navigation only, explicit task creation, tenant/version/role/effective approval guards, duplicate-task UI, failed approval and image-loading gates');
}
main().catch(e=>{console.error(e);process.exitCode=1});
