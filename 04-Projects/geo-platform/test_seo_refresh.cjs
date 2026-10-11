const fs=require('fs'),vm=require('vm'),assert=require('assert');
let route='seo',syncs=0;const elements=new Map();
const ctx=vm.createContext({Map,Set,JSON,epoch:1,pid:'a',me:{identity:'alice'},state:{marker:'initial'},document:{addEventListener(){}},page:()=>route,$:s=>{if(!elements.has(s))elements.set(s,{innerHTML:''});return elements.get(s)},refresh:async()=>{},syncManager:()=>syncs++,websiteSeoChecks:()=>'',empty:()=>'',esc:s=>s});
vm.runInContext(fs.readFileSync('static/seo.js','utf8'),ctx);
function pending(){let resolve,reject;ctx.api=()=>new Promise((a,b)=>{resolve=a;reject=b});return {promise:vm.runInContext('refresh()',ctx),resolve:marker=>resolve({marker,seo_audit:[],seo_task:[],execution:[]}),reject};}
(async()=>{
 let p=pending();ctx.epoch++;p.resolve('old-login');await p.promise;assert.equal(ctx.state.marker,'initial','old login response must not replace state');
 p=pending();ctx.me.identity='bob';p.resolve('other-user');await p.promise;assert.equal(ctx.state.marker,'initial');
 p=pending();ctx.pid='b';p.resolve('other-project');await p.promise;assert.equal(ctx.state.marker,'initial');
 const old=pending(),latest=pending();latest.resolve('latest');await latest.promise;old.resolve('old');await old.promise;assert.equal(ctx.state.marker,'latest');assert.equal(syncs,1);
 p=pending();route='workspace';p.resolve('left-page');await p.promise;assert.equal(ctx.state.marker,'latest');route='seo';
 p=pending();ctx.epoch++;p.reject(Error('stale failure'));await p.promise;
 p=pending();p.reject(Error('current failure'));await assert.rejects(p.promise,/current failure/);
 p=pending();p.resolve('fresh');await p.promise;assert.equal(ctx.state.marker,'fresh');assert.equal(syncs,2);
 console.log('PASS: SEO refresh guards session, user, project, page, response ordering and stale errors; current errors surface');
})().catch(e=>{console.error(e);process.exitCode=1});
