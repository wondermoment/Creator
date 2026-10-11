// Test-only JSON-lines transport to an isolated Python ASGI TestClient.
if(!process.argv.includes('--asgi-test-bridge')){console.log('SKIP: run via python -m unittest backend.test_inquiry_roundtrip (requires isolated ASGI bridge)');process.exit(0)}
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),readline=require('readline');
let seq=0,dropReply=false,writes=0;const waiting=new Map(),toasts=[],nodes={};
for(const id of ['modal','form','submit','form-error','modal-title','fields'])nodes[id]={};
nodes.modal.showModal=function(){this.open=true};nodes.modal.close=function(){this.open=false};
readline.createInterface({input:process.stdin}).on('line',line=>{const reply=JSON.parse(line),pending=waiting.get(reply.id);waiting.delete(reply.id);if(reply.lost)pending.reject(Error('合成回执丢失'));else if(reply.status>=400)pending.reject(Error(typeof reply.body.detail==='string'?reply.body.detail:'请求未通过校验'));else pending.resolve(reply.body)});
const c={AbortController,crypto:require('crypto').webcrypto,document:{addEventListener(){}},window:{addEventListener(){}},state:{overview:{},page:'account'},esc:String,date:String,render(){},reload:async()=>{},toast:m=>toasts.push(m),$:s=>nodes[s.slice(1)],FormData:class{constructor(target){return new Map(Object.entries(target))}},setTimeout,clearTimeout,api:(path,options={})=>new Promise((resolve,reject)=>{
 const id=++seq,method=options.method||'GET',lost=method!=='GET'&&dropReply;if(method!=='GET'){writes++;dropReply=false}
 waiting.set(id,{resolve,reject});process.stdout.write(JSON.stringify({id,path,method,body:options.body?JSON.parse(options.body):undefined,lost})+'\n');
})};
vm.createContext(c);const app=fs.readFileSync('frontend/app.js','utf8');vm.runInContext(app.slice(app.indexOf('let formGeneration='),app.indexOf('\nfunction record()')),c);vm.runInContext(fs.readFileSync('frontend/customer-service.js','utf8'),c);
const submit=target=>nodes.form.onsubmit({preventDefault(){},target});
(async()=>{
 const input={kind:'了解报价与日期',need:'合成接口联调需求'};
 c.serviceInquiry('合成接口联调项目');dropReply=true;await submit(input);
 assert(nodes.modal.open);assert.equal(toasts.length,0);assert(nodes['form-error'].textContent.includes('未能确认'));
 const before=writes;await submit({...input,need:'修改内容不应重发'});assert.equal(writes,before);
 await submit(input);assert(!nodes.modal.open);assert.equal(toasts.length,1);
 let rows=vm.runInContext('inquiryRows',c);assert.equal(rows.length,1);assert.equal(rows[0].timeline.length,1);const rid=rows[0].id;
 c.inquiryFollow(rid);dropReply=true;await submit({status:'following',note:'合成受理进度'});
 assert(nodes.modal.open);const count=writes;await submit({status:'following',note:'合成受理进度'});assert.equal(writes,count);
 nodes.modal.close();await c.loadInquiries();rows=vm.runInContext('inquiryRows',c);assert.equal(rows[0].timeline.length,2);assert.equal(rows[0].status,'following');
 c.inquiryFollow(rid);await submit({status:'closed',note:'合成完成进度'});assert(!nodes.modal.open);rows=vm.runInContext('inquiryRows',c);assert.equal(rows[0].timeline.length,3);assert.equal(rows[0].status,'closed');assert.equal(writes,4);
 process.stdout.write(JSON.stringify({done:true,writes,rows:rows.length,timeline:rows[0].timeline.length,status:rows[0].status})+'\n');process.exit(0);
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exit(1)});
