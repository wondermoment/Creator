let commerceData=null,commerceError='',commerceLoading=false,commerceGeneration=0,commerceCancel=null,commerceWriting=false;
const money=n=>'¥'+(n/100).toFixed(2);
const commerceStatus={pending:'待测试付款',paid:'测试已付款 · 佣金冻结',settled:'已模拟分账 · 未真实到账',refunded:'测试已退款',cancelled:'已取消',held:'冻结中',simulated:'模拟分账',reversed:'已冲回'};
function commerceReady(){return !!commerceData&&!commerceLoading&&!commerceError&&!commerceWriting}
function validCommerceSnapshot(d){
 const text=v=>typeof v==='string',num=v=>Number.isSafeInteger(v)&&v>=0;
 const rows=(key,check)=>Array.isArray(d?.[key])&&d[key].every(r=>r&&text(r.id)&&r.id&&check(r))&&new Set(d[key].map(r=>r.id)).size===d[key].length;
 return d?.mode==='sandbox'&&d.live_payment===false&&
  rows('products',r=>text(r.name)&&num(r.price)&&r.price>0&&num(r.stock))&&
  rows('agents',r=>text(r.name)&&(r.parent_id===null||text(r.parent_id)))&&
  rows('orders',r=>text(r.product_id)&&num(r.total)&&num(r.quantity)&&r.quantity>0&&['pending','paid','settled','refunded','cancelled'].includes(r.status))&&
  rows('ledger',r=>text(r.agent_id)&&text(r.order_id)&&[1,2].includes(r.level)&&num(r.amount)&&['held','simulated','reversed'].includes(r.status))&&
  rows('transfers',r=>text(r.created_at)&&['simulated_no_money_moved','simulated_reversed'].includes(r.status))&&
  rows('audit',r=>text(r.created_at)&&text(r.kind));
}
function commerceLoadStatus(){return commerceLoading?'正在刷新账本'+(commerceData?'，以下为上次读取的记录。':'…'):commerceError?commerceError+(commerceData?'；以下记录可能已过期，请刷新成功后再操作。':''):''}
async function commerceLoad(){
 const generation=++commerceGeneration;if(commerceCancel)commerceCancel();
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{
  commerceCancel=()=>{reject(Error('读取已被新请求替代'));controller.abort()};
  timer=setTimeout(()=>{reject(Error('账本读取超过15秒，请刷新重试'));controller.abort()},15000);
 });
 commerceLoading=true;commerceError='';if(state.page==='commerce')render();
 try{
  const data=await Promise.race([api('/commerce/snapshot',{signal:controller.signal}),deadline]);
  if(generation!==commerceGeneration)return null;
  if(!validCommerceSnapshot(data))throw Error('账本数据不完整，请刷新重试');
  commerceData=data;return data;
 }catch(e){if(generation===commerceGeneration)commerceError=e.message||'账本读取失败';return null}
 finally{clearTimeout(timer);if(generation===commerceGeneration){commerceLoading=false;commerceCancel=null;if(state.page==='commerce')render()}}
}

function invalidateCommerce(message){
 ++commerceGeneration;if(commerceCancel)commerceCancel();commerceCancel=null;commerceLoading=false;commerceError=message;
 if(state.page==='commerce')render();
}
async function commerceWrite(path,body,validate){
 if(commerceWriting)throw Error('上一项交易操作仍在等待，请稍候');
 commerceWriting=true;invalidateCommerce('交易操作处理中，请等待回执。');
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{reject(Error('提交等待超过30秒'));controller.abort()},30000)});
 try{
  const result=await Promise.race([api(path,{method:'POST',body:JSON.stringify(body),signal:controller.signal}),deadline]);
  if(!validate(result))throw Error('返回的交易结果不完整');
  return result;
 }catch(e){throw Error((e.message||'连接中断')+'；未能确认处理结果，服务端可能已完成。请刷新账本核对，勿重复新建。')}
 finally{clearTimeout(timer);commerceWriting=false;invalidateCommerce('交易后账本需要刷新核对。')}
}
async function commerceOrderAction(id,action){
 const targets={'simulate-pay':['paid','settled'],'simulate-settle':['settled'],refund:['refunded'],cancel:['cancelled']};
 if(!commerceReady()||!Object.hasOwn(targets,action))throw Error('请先刷新账本成功后再操作');
 await commerceWrite('/commerce/orders/'+encodeURIComponent(id)+'/'+action,{},r=>r?.mode==='sandbox'&&targets[action].includes(r.status));
 void commerceLoad();
}
function commerceAgentForm(){
 if(!commerceReady())throw Error('请先刷新账本成功后再操作');
 let attempted=false;
 showForm('新增测试代理',`<label>代理名称<input name="name" maxlength="40" required></label><label>上级代理<select name="parent"><option value="">无上级</option>${commerceData.agents.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('')}</select></label><p class="small muted">收款账户暂未绑定；当前仅测试代理关系。</p>`,'保存测试代理',async f=>{
  if(attempted)throw Error('请先关闭窗口并刷新代理列表核对上次结果，勿重复新增。');
  const name=String(f.get('name')||'').trim();if(!name)throw Error('请填写代理名称');
  attempted=true;await commerceWrite('/commerce/agents',{name,parent_id:f.get('parent')||null},r=>typeof r?.id==='string'&&/^agent-[a-f0-9]{12}$/.test(r.id));
  void commerceLoad();
 },{local:true,message:'测试代理已保存'});
}
function commercePage(){if(!commerceData)return `<section class="card"><h1>商城与代理后台</h1><p>${esc(commerceLoadStatus()||'请刷新读取交易沙盒')}</p><button class="secondary" data-commerce-refresh ${commerceLoading?'disabled':''}>刷新</button></section>`;const d=commerceData;const agentName=id=>d.agents.find(a=>a.id===id)?.name||'无';return `<a class="travel-back" href="#shop">← 返回商城</a><section class="travel-intro"><div class="eyebrow">COMMERCE / SANDBOX</div><h1>商城与代理后台</h1><p>支付宝接入准备中 · 一级 10% / 二级 5%</p></section><p class="notice">本机交易沙盒：所有金额、库存、佣金与分账均为测试数据，不产生真实扣款、转账或发货。正式商户认证与支付接口尚未接入。</p><p role="status">${esc(commerceLoadStatus())}</p><div class="actions"><button class="primary" data-commerce-agent ${commerceReady()?'':'disabled'}>新增测试代理</button><button class="secondary" data-commerce-refresh ${commerceLoading?'disabled':''}>刷新账本</button></div>${managedCatalog()}${inquiryAdmin()}<section class="card commerce-section"><h2>测试商品与库存</h2>${d.products.map(p=>`<div class="row"><div class="row-main"><strong>${esc(p.name)}</strong><small>${money(p.price)} · 测试库存 ${p.stock}</small></div></div>`).join('')}</section><section class="card commerce-section"><h2>代理关系</h2><p class="small muted">订单只计直接推荐人和其上一级；不按代理注册或入会计酬。关系在创建时确定。</p>${d.agents.map(a=>`<div class="row"><div class="row-main"><strong>${esc(a.name)}</strong><small>上级：${esc(agentName(a.parent_id))}</small><small class="file-name">推荐码：${esc(a.id)}</small></div><button class="secondary" data-commerce-link="${esc(a.id)}">邀请链接</button></div>`).join('')}</section><section class="card commerce-section"><h2>测试订单</h2><p class="small muted">模拟付款后生成两级冻结佣金；点击模拟结算测试分账。正式上线需由支付宝验签回调确认付款，并在售后期结束后发起分账。</p>${d.orders.map(o=>`<article class="commerce-order"><strong>${esc(d.products.find(p=>p.id===o.product_id)?.name||o.product_id)}</strong><small class="file-name">订单 ${esc(o.id)}</small><p>${money(o.total)} · ${o.quantity} 件</p><p class="chip">${commerceStatus[o.status]}</p><p class="small muted">一级：${esc(agentName(o.agent1))} / 二级：${esc(agentName(o.agent2))}</p><div class="actions">${o.status==='pending'?`<button class="primary" data-commerce-order="${o.id}" data-commerce-action="simulate-pay" ${commerceReady()?'':'disabled'}>模拟支付宝付款</button><button class="secondary" data-commerce-order="${o.id}" data-commerce-action="cancel" ${commerceReady()?'':'disabled'}>取消订单</button>`:''}${o.status==='paid'?`<button class="primary" data-commerce-order="${o.id}" data-commerce-action="simulate-settle" ${commerceReady()?'':'disabled'}>模拟售后期结束并分账</button>`:''}${['paid','settled'].includes(o.status)?`<button class="secondary" data-commerce-order="${o.id}" data-commerce-action="refund" ${commerceReady()?'':'disabled'}>模拟全额退款</button>`:''}</div></article>`).join('')||'<p class="muted">暂无订单，前往商城选择测试商品。</p>'}</section><section class="card commerce-section"><h2>两级佣金账本</h2>${d.ledger.map(l=>`<div class="row"><div class="row-main"><strong>${esc(agentName(l.agent_id))} · ${l.level} 级</strong><small>${money(l.amount)} · ${commerceStatus[l.status]}</small><small class="file-name">订单 ${esc(l.order_id)}</small></div></div>`).join('')||'<p class="muted">付款前不生成佣金。</p>'}</section><section class="card commerce-section"><h2>模拟分账记录</h2>${d.transfers.map(t=>`<div class="row"><div class="row-main"><strong>${t.status==='simulated_reversed'?'退款已冲回':'模拟成功 · 未真实转账'}</strong><small class="file-name">${esc(t.id)}</small><small>${date(t.created_at)}</small></div></div>`).join('')||'<p class="muted">暂无模拟分账。</p>'}</section><details class="card commerce-section"><summary>最近操作审计</summary>${d.audit.map(a=>`<p class="small file-name">${date(a.created_at)} · ${esc(a.kind)}</p>`).join('')}</details>`}
async function commerceBuy(id){const data=await commerceLoad();if(!data||data!==commerceData||!commerceReady())throw Error(commerceError||'商品状态尚未确认，请重试');const p=data.products.find(p=>p.id===id);if(!p){toast('该商品尚未配置可售规格、价格与供应商，暂不能下单。');return}const ref=new URLSearchParams(location.search).get('ref')||'';const requestKey=crypto.randomUUID();let submitted=null;showForm('购买 · 测试订单',`<p><strong>${esc(p.name)}</strong></p><p>测试单价 ${money(p.price)} · 库存 ${p.stock}</p><p class="notice">仅测试购买流程，不扣款、不发货。收货信息待正式支付接入后开放。</p><label>数量<input name="quantity" type="number" min="1" max="${Math.min(20,p.stock)}" value="1" required></label><label>推荐代理<select name="referral"><option value="">无推荐人</option>${commerceData.agents.map(a=>`<option value="${esc(a.id)}" ${ref===a.id?'selected':''}>${esc(a.name)}</option>`).join('')}</select></label>`,'创建测试订单',async f=>{
 const body={product_id:id,quantity:Number(f.get('quantity')),referral:f.get('referral')||null,request_key:requestKey};
 if(!Number.isInteger(body.quantity)||body.quantity<1||body.quantity>20)throw Error('数量请填写1至20的整数');
 if(submitted&&JSON.stringify(submitted)!==JSON.stringify(body))throw Error('上次提交结果待核对，请勿修改数量或推荐人重传。可保持原内容重试查询同一订单，或关闭后刷新账本。');
 submitted=body;
 await commerceWrite('/commerce/orders',submitted,r=>typeof r?.id==='string'&&/^[a-f0-9]{32}$/.test(r.id)&&r.request_key===requestKey&&r.product_id===id&&r.quantity===submitted.quantity&&r.agent1===submitted.referral&&Number.isSafeInteger(r.total)&&r.total>0&&['pending','paid','settled','refunded','cancelled'].includes(r.status));
 void commerceLoad();location.hash='commerce';
 }, {local:true,message:'测试订单已确认，请到后台核对当前状态'})}
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b||b.disabled)return;try{if((b.hasAttribute('data-commerce-agent')||b.dataset.commerceOrder)&&!commerceReady())throw Error('请先刷新账本成功后再操作');if(b.dataset.shopBuy){b.disabled=true;await commerceBuy(b.dataset.shopBuy)}if(b.hasAttribute('data-commerce-refresh'))await commerceLoad();if(b.hasAttribute('data-commerce-agent'))commerceAgentForm();if(b.dataset.commerceOrder){b.disabled=true;await commerceOrderAction(b.dataset.commerceOrder,b.dataset.commerceAction);toast('测试账本已更新 · 未发生真实资金交易')}if(b.dataset.commerceLink){const url=new URL(location.href);url.search='';url.searchParams.set('ref',b.dataset.commerceLink);url.hash='shop';await navigator.clipboard.writeText(url.href);toast('测试邀请链接已复制 · 当前仅本机可访问')}}catch(e){toast(e.message)}finally{b.disabled=false}});
window.addEventListener('hashchange',()=>{if(location.hash==='#commerce')commerceLoad()});
window.addEventListener('DOMContentLoaded',()=>{if(location.hash==='#commerce')commerceLoad()});
