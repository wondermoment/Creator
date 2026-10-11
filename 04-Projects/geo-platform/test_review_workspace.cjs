const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map(),listeners={};
const node=k=>{if(!nodes.has(k))nodes.set(k,{innerHTML:'',value:'',open:false,classList:{add(){},remove(){}},addEventListener(){},querySelector:node});return nodes.get(k)};
const c=vm.createContext({console,Intl,Date,URLSearchParams,Map,Set,document:{querySelector:node,addEventListener(t,f){(listeners[t]??=[]).push(f)}},window:{addEventListener(){}},location:{hash:'#workspace'},localStorage:{getItem(){}},setInterval(){},setTimeout(){},clearTimeout(){}});
for(const f of ['app','workspace'])vm.runInContext(fs.readFileSync(`static/${f}.js`,'utf8'),c);
vm.runInContext(`pid='p1';state={role:'owner',project:{name:'测试企业'},content:[],knowledge:[],publication:[],execution:[]};deliveryStrip=()=>'<div>执行工具</div>';render=()=>{};for(let i=1;i<=8;i++)state.content.push({id:'c'+i,title:i+'、测试文章',revision:1,status:'pending',channels:[],sources:[],layout:{cover_id:'a'+i,blocks:[{text:'正文'}],figures:[]}});state.content.push({id:'raw',title:'待排版',revision:1,status:'pending',channels:[],sources:[]},{id:'old',title:'过期排版',revision:1,status:'pending',channels:[],sources:[],layout:{outdated:true}},{id:'approved',title:'待发稿',revision:2,approved_revision:2,status:'approved',channels:['官网'],sources:[]},{id:'invalid',title:'审批失效',revision:2,approved_revision:2,status:'approved',channels:['官网'],sources:[],approval_summary:{effective_approved:false}});`,c);
assert.equal(vm.runInContext('workQueueGroups().review.length',c),8);
assert.equal(vm.runInContext('workQueueGroups().preparation.length',c),3);
assert.equal(vm.runInContext('workQueueGroups().approved.length',c),1);
let html=vm.runInContext('workspace()',c);assert.equal((html.match(/class="review-card"/g)||[]).length,6);assert(html.indexOf('图文审核工作台')<html.indexOf('执行工具'));assert(!html.includes('AI 平台表现'));assert(!html.includes('企业交付进度'));
vm.runInContext(`workQueuePage=1`,c);html=vm.runInContext('workQueueCards()',c);assert.equal((html.match(/class="review-card"/g)||[]).length,2);assert(html.includes('8、测试文章'));
vm.runInContext(`workQueueSearch='3、';workQueuePage=0`,c);html=vm.runInContext('workQueueCards()',c);assert(html.includes('3、测试文章'));assert(!html.includes('4、测试文章'));
vm.runInContext(`pid='p2';state.content=[]`,c);html=vm.runInContext('workspace()',c);assert(!html.includes('测试文章'));assert.equal(vm.runInContext('workQueueSearch',c),'');assert.equal(vm.runInContext('workQueuePage',c),0);
vm.runInContext(`state.content=[{id:'a',title:'<script>x</script>',revision:1,approved_revision:1,status:'approved',channels:['官网'],sources:[]}];state.publication=[{content_id:'a',revision:1,channel:'官网',status:'wp_draft'}]`,c);assert.equal(vm.runInContext('workQueueGroups().approved.length',c),1);
vm.runInContext(`state.publication[0].status='recorded'`,c);assert.equal(vm.runInContext('workQueueGroups().approved.length',c),0);
vm.runInContext(`state.publication[0].revision=0;workQueueTab='approved'`,c);html=vm.runInContext('workQueueCards()',c);assert(html.includes('安排发布'));assert(!html.includes('<script>'));
html=vm.runInContext('scheduleActionQueue()',c);assert(html.includes('现在需要审核与发送'));assert(html.includes('待发送'));
html=vm.runInContext('coreNavigation()',c);assert(html.includes('更多工具'));assert(html.indexOf('#workspace')<html.indexOf('#schedule'));assert(html.indexOf('更多工具')<html.indexOf('#diagnosis'));
assert(!fs.readFileSync('static/delivery.js','utf8').includes("publishHandoffPanel()+deliveryStrip('publish')"));
console.log('PASS: review-first workbench, 6-card paging/search, tenant reset, stale layout/approval grouping, draft versus confirmed receipts, schedule shared queue and collapsed tools');

html=vm.runInContext('coreNavigation()',c);assert(html.indexOf('#screen')<html.indexOf('#workspace'));assert.equal((html.match(/href="#screen"/g)||[]).length,1);assert(html.includes('monitor-entry'));

assert(!html.includes('href="#content"'));
assert(html.indexOf('企业资料')<html.indexOf('href="#brand"'));
assert(html.indexOf('href="#qa"')<html.indexOf('更多工具'));
assert(html.indexOf('更多工具')<html.indexOf('href="#seo"'));
// All statuses remain discoverable after publishing or while generating.
vm.runInContext(`state.content.push({id:'generating',title:'生成中稿件',status:'generating',revision:1,channels:[],sources:[]});workQueueTab='all';workQueueSearch='';workQueuePage=0`,c);
assert.equal(vm.runInContext('workQueueGroups().all.length',c),2);
html=vm.runInContext('workQueueCards()',c);assert(html.includes('生成中稿件'));assert(html.includes('&lt;script&gt;'));
assert(vm.runInContext('workspace()',c).includes('全部稿件'));
console.log('PASS: all-content view includes delivered and generating records without changing review groups');
