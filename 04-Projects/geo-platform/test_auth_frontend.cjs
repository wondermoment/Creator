// Auth mode changes must never submit credentials or require a valid form.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const events={},fields={identity:{value:'fixture@example.com'},password:{value:'fixture-password'}};
const error={textContent:''},submit={disabled:false};
let submittedHandler;
const form={querySelector(s){return s==='[name="identity"]'?fields.identity:s==='[name="password"]'?fields.password:s==='.error'?error:submit;},addEventListener(type,handler){if(type==='submit')submittedHandler=handler;}};
const app={innerHTML:''},modal={addEventListener(){}};
const context=vm.createContext({console,URL,Intl,Date,document:{querySelector:s=>s==='#app'?app:s==='#modal'?modal:s==='#auth-form'?form:{},addEventListener:(type,fn)=>{events[type]=fn;}},window:{addEventListener(){}},setInterval(){},setTimeout(){},location:{hash:'#workspace'},FormData:class{constructor(){return new Map(Object.entries(fields).map(([k,v])=>[k,v.value]));}}});
vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
let requests=[],boots=0,fail=true;
context.testApi=async(url,method,body)=>{requests.push({url,method,body});if(fail)throw Error('账号或密码不正确');return {csrf:'fixture'};};
context.testBoot=async()=>{boots++;};
vm.runInContext('api=testApi;boot=testBoot;auth()',context);
async function click(action,id=''){const btn={dataset:{action,id}};await events.click({target:{closest:()=>btn}});}
(async()=>{
 assert(app.innerHTML.includes('>登录 <'));
 await click('auth-mode','register');
 assert(app.innerHTML.includes('注册并创建企业空间'));
 fields.password.value='';
 await click('direct-login');
 assert(app.innerHTML.includes('>登录 <'));
 assert(!app.innerHTML.includes('注册并创建企业空间'));
 assert.strictEqual(requests.length,0);
 assert.strictEqual(fields.identity.value,'fixture@example.com');
 fields.password.value='fixture-password';
 await click('auth-mode','register');await click('direct-login');
 assert.strictEqual(fields.password.value,'fixture-password');
 await submittedHandler({preventDefault(){},currentTarget:form});
 assert.strictEqual(requests[0].url,'/api/login');
 assert.strictEqual(error.textContent,'账号或密码不正确');
 assert.strictEqual(submit.disabled,false);
 fail=false;
 await submittedHandler({preventDefault(){},currentTarget:form});
 assert.strictEqual(boots,1);
 assert.strictEqual(error.textContent,'');
 assert.strictEqual(submit.disabled,false);
 console.log('PASS: login default, registration/login switch, no request on switch, preserved inputs, failed-login retry');
})().catch(e=>{console.error(e);process.exitCode=1;});
