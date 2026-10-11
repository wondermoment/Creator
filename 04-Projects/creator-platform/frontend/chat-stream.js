// Render only answer deltas, never reasoning/tool events. Commit on explicit done.
async function coachStreamRequest(path,body,onText,signal){
 if(signal?.aborted)throw Error('本次对话已关闭');
 const controller=new AbortController();let timer,reader,stopped=false,rejectClosed;
 const closed=new Promise((_,reject)=>{rejectClosed=reject});
 const onClose=()=>{stopped=true;controller.abort();rejectClosed(Error('本次对话已关闭'));if(reader)reader.cancel().catch(()=>{})};
 signal?.addEventListener('abort',onClose,{once:true});
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error('等待回复超时，请稍后重试'))},270000)});
 const request=(async()=>{
  const response=await fetch('/api'+path+'/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal});
  if(stopped)throw Error('回复请求已结束');
  if(!response.ok){let data;try{data=await response.json()}catch{}throw Error(requestErrorMessage(data,response.status))}
  if(!response.body?.getReader)throw Error('当前浏览器无法读取连续回复，请更新浏览器');
  reader=response.body.getReader();const decoder=new TextDecoder('utf-8',{fatal:true});let buffer='',text='',done=null;
  function line(raw){
   if(stopped)return;
   if(!raw.trim())return;
   const event=JSON.parse(raw);
   if(event.type==='error')throw Error(event.message||'回复未完成');
   if(event.type==='delta'){
    if(done||typeof event.delta!=='string'||event.delta.includes('\ufffd'))throw Error('回复格式异常');
    text+=event.delta;if(text.length>150000)throw Error('回复过长');onText(text);
   }else if(event.type==='done'){
    if(done||typeof event.answer!=='string'||!event.answer.trim()||event.answer.includes('\ufffd'))throw Error('未收到完整回复');
    done=event;
   }else throw Error('回复事件异常');
  }
  while(true){
   const chunk=await reader.read();buffer+=decoder.decode(chunk.value||new Uint8Array(),{stream:!chunk.done});
   if(stopped)throw Error('回复请求已结束');
   if(buffer.length>1000000)throw Error('回复数据过大');
   let newline;while((newline=buffer.indexOf('\n'))>=0){line(buffer.slice(0,newline));buffer=buffer.slice(newline+1)}
   if(done)return done;
   if(chunk.done){line(buffer);if(!done)throw Error('回复连接中断，内容尚未完整生成');return done}
  }
 })();
 try{return await Promise.race([request,deadline,closed])}
 finally{stopped=true;clearTimeout(timer);signal?.removeEventListener('abort',onClose);controller.abort();if(reader)reader.cancel().catch(()=>{})}
}
