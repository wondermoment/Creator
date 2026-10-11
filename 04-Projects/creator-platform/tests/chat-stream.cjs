const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
async function run(events){
 const bytes=new TextEncoder().encode(events),updates=[];let offset=0,cancelled=false;
 const reader={async read(){if(offset>=bytes.length)return {done:true};const value=bytes.slice(offset,offset+2);offset+=2;return {done:false,value}},async cancel(){cancelled=true}};
 const c={AbortController,TextDecoder,Uint8Array,setTimeout,clearTimeout,requestErrorMessage:()=> 'failed',fetch:async()=>({ok:true,body:{getReader:()=>reader}})};
 vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/chat-stream.js','utf8'),c);
 let result,error;try{result=await c.coachStreamRequest('/coaches/research-learning/chat',{question:'合成'},text=>updates.push(text))}catch(e){error=e}
 return {result,error,updates,cancelled};
}
(async()=>{
 const lines=xs=>xs.map(x=>JSON.stringify(x)).join('\n')+'\n';
 const ok=await run(lines([{type:'delta',delta:'中文'},{type:'delta',delta:'重点'},{type:'done',answer:'中文重点'}]));
 assert.deepEqual(ok.updates,['中文','中文重点']);assert.equal(ok.result.answer,'中文重点');assert(ok.cancelled);
 const cut=await run(lines([{type:'delta',delta:'未完成'}]));assert(cut.error);assert(!cut.result);assert(cut.cancelled);
 const fail=await run(lines([{type:'delta',delta:'暂存'},{type:'error',message:'合成故障'}]));assert.match(fail.error.message,/合成故障/);assert(!fail.result);
 const tool=await run(lines([{type:'reasoning',delta:'不应显示'}]));assert(tool.error);assert.equal(tool.updates.length,0);
 console.log('PASS: UTF8 split chunks, incremental text, explicit completion, truncated/error streams and non-answer event rejection');
})().catch(e=>{console.error(e);process.exit(1)});
