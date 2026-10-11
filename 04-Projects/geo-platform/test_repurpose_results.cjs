const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={};
const ctx=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector(){return{addEventListener(){}}},addEventListener(t,f){(listeners[t]??=[]).push(f)},hidden:false},window:{addEventListener(){}},location:{hash:'#repurpose'},localStorage:{getItem(){return null}},setInterval(){},setTimeout(){},clearTimeout(){},fetch(){throw Error('No network')}});
for(const f of ['app','planning','knowledge','manager','leads','delivery','sample','experts','repurpose'])vm.runInContext(fs.readFileSync(`static/${f}.js`,'utf8'),ctx);
vm.runInContext(`pid='p';state={role:'owner',content:[],execution:[{id:'j',status:'succeeded',created:'2026-10-03',payload:{workflow:'repurpose',repurpose_channel:'moments',repurpose_source:{title:'原稿',revision:1}},result:{answer:'## 采购先问条件\\n\\n- **限定基材**：[1]\\n- 未做盐雾。\\n\\n<img src=x onerror=alert(1)>'}}]};`,ctx);
let html=vm.runInContext('repurposeResults()',ctx);assert(html.includes('<h4>'));assert(html.includes('<strong>限定基材</strong>'));assert(html.includes('<ul>'));assert(html.includes('[1]'));assert(!html.includes('<img'));assert(html.includes('repurpose-save'));
for(const status of ['failed','running','cancelled']){ctx.status=status;vm.runInContext('state.execution[0].status=status',ctx);html=vm.runInContext('repurposeResults()',ctx);assert(!html.includes('限定基材'));assert(!html.includes('repurpose-save'));assert(html.includes('role="status"'));}
vm.runInContext("state.execution[0].status='succeeded';state.execution[0].result.discarded=true;state.execution[0].result.reason='来源变更';",ctx);html=vm.runInContext('repurposeResults()',ctx);assert(html.includes('来源变更'));assert(!html.includes('限定基材'));
vm.runInContext("state.execution[0].result.discarded=false;state.execution[0].result.answer='   '",ctx);assert(!vm.runInContext('repurposeResults()',ctx).includes('repurpose-save'));
vm.runInContext("state.execution[0].result.answer='有效正文';state.role='viewer'",ctx);assert(!vm.runInContext('repurposeResults()',ctx).includes('repurpose-save'));
const click=listeners.click.find(f=>f.toString().includes('repurpose-save'));vm.runInContext('toast=()=>{};api=async()=>{throw Error("unexpected network")}',ctx);
(async()=>{await click({target:{closest:s=>s.includes('repurpose-save')?({dataset:{id:'j'}}):null}});console.log('PASS: repurpose safe formatting, no stale answers, blank/discarded/readonly save gates');})().catch(e=>{console.error(e);process.exitCode=1});

vm.runInContext(`openModal=(_title,html)=>{globalThis.previewHtml=html};state.project={name:'测试'};state.content=[{id:'draft',title:'改编稿',status:'draft',revision:2,generator:'test',channels:[],sources:[],repurpose_job_id:'j',body:'**保留条件**\\n\\n<img src=x>',skill_name:'test',skill_version:1}];originalPreview('draft');`,ctx);
assert(ctx.previewHtml.includes('尚未选择发布渠道'));assert(ctx.previewHtml.includes('<strong>保留条件</strong>'));assert(!ctx.previewHtml.includes('<img'));assert(ctx.previewHtml.includes('&lt;img'));
vm.runInContext(`delete state.content[0].repurpose_job_id;originalPreview('draft')`,ctx);assert(ctx.previewHtml.includes('class="text-body"'));assert(!ctx.previewHtml.includes('<strong>保留条件</strong>'));
console.log('PASS: saved repurpose preview uses safe formatting and explicit empty-channel label; ordinary preview unchanged');
