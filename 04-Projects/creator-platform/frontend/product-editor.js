let managedProducts=[],managedProductError='',managedProductLoading=false,managedProductLoaded=false,managedProductGeneration=0,managedProductCancel=null;
function renderManagedProducts(){if(state.overview&&['shop','commerce'].includes(state.page))render()}
function validManagedProducts(rows){
 const ids=new Set();
 return Array.isArray(rows)&&rows.every(p=>{
  if(!p||typeof p.id!=='string'||!p.id||ids.has(p.id))return false;ids.add(p.id);
  return ['name','category','description','ingredients','usage','cautions'].every(k=>typeof p[k]==='string')&&
   ['draft','published'].includes(p.status)&&Number.isSafeInteger(p.price)&&p.price>0&&Number.isSafeInteger(p.stock)&&p.stock>=0&&
   [0,1,false,true].includes(p.has_image)&&typeof p.revision==='string'&&/^[a-f0-9]{64}$/.test(p.revision);
 });
}
async function loadManagedProducts(){
 const generation=++managedProductGeneration;if(managedProductCancel)managedProductCancel();
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{
  managedProductCancel=()=>{reject(Error('读取已被新请求替代'));controller.abort()};
  timer=setTimeout(()=>{reject(Error('读取超过15秒，请刷新商品重试'));controller.abort()},15000);
 });
 managedProductLoading=true;managedProductError='';renderManagedProducts();
 try{
  const rows=await Promise.race([api('/commerce/catalog',{signal:controller.signal}),deadline]);
  if(generation!==managedProductGeneration)return;
  if(!validManagedProducts(rows))throw Error('商品数据不完整，请刷新商品重试');
  managedProducts=rows;managedProductLoaded=true;
 }catch(e){if(generation===managedProductGeneration)managedProductError=e.message||'商品读取失败，请重试'}
 finally{clearTimeout(timer);if(generation===managedProductGeneration){managedProductCancel=null;managedProductLoading=false;renderManagedProducts()}}
}
function managedProductStatus(){
 const text=managedProductLoading?'正在读取商品…':managedProductError;
 const note=(managedProductLoading||managedProductError)&&managedProductLoaded?' 以下为上次读取的商品，可能不是最新内容。':'';
 return `<div class="actions"><button class="secondary" data-product-refresh ${managedProductLoading?'disabled':''}>${managedProductLoading?'正在读取…':'刷新商品'}</button></div><p class="small muted" role="status">${esc(text+note)}</p>`;
}
function managedCatalog(){return `<section class="card portal-section"><div class="section-head"><h2>商品上架工作台</h2><button class="primary" data-product-new>新增商品</button></div><p class="small muted">本机发布到演示商城，支付仍为沙盒。草稿不展示；发布前由运营核对产品身份、宣传依据和供应信息。</p><ol class="small"><li>新增商品，填写名称、分类、价格和库存。</li><li>写好商品故事、规格来源、使用方式与购买须知。</li><li>先保存草稿，再上传主图并预览详情。</li><li>核对后编辑为「发布到演示商城」；切回草稿即可下架。</li></ol>${managedProductStatus()}${managedProductLoaded&&!managedProductLoading&&!managedProductError&&!managedProducts.length?'<p class="muted">还没有自建商品，点击「新增商品」开始。</p>':''}${managedProducts.map(p=>`<div class="row">${productPicture(p,true)}<div class="row-main"><strong>${esc(p.name)}</strong><small>${p.status==='published'?'已发布（演示）':'草稿'} · ${money(p.price)}</small></div><button class="secondary" data-product-edit="${esc(p.id)}" ${managedProductLoading||managedProductError?'disabled':''}>编辑 / 上下架</button></div><div class="actions"><button class="secondary" data-product-image="${esc(p.id)}" ${managedProductLoading||managedProductError?'disabled':''}>上传主图</button><button class="secondary" data-product-preview="${esc(p.id)}">预览详情</button></div>`).join('')}</section>`}
async function productContentWrite(id,body){
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{reject(Error('保存等待超过30秒'));controller.abort()},30000)});
 try{
  const result=await Promise.race([api('/commerce/products/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify(body),signal:controller.signal}),deadline]);
  if(result?.id!==id||result?.status!==body.status)throw Error('返回的商品保存结果不完整');
 }catch(e){throw Error((e.message||'连接中断')+'；本窗口未确认保存成功。请复制保留当前修改，关闭窗口并刷新商品列表核对，避免重复新增或覆盖。商品编号：'+id)}
 finally{clearTimeout(timer)}
}
function productEdit(id){let attempted=false;const p=managedProducts.find(p=>p.id===id)||{id:'custom-'+crypto.randomUUID(),category:'食物',price:100,stock:0,status:'draft'};showForm('编辑内容商品',`<label>商品名称<input name="name" maxlength="80" required value="${esc(p.name||'')}"></label><label>分类<select name="category">${['食物','有机蔬菜','饮品','调味料','基础营养素','长寿抗衰','智能硬件','精准检测'].map(x=>`<option ${p.category===x?'selected':''}>${x}</option>`).join('')}</select></label><label>测试售价（元）<input name="price" type="number" min="0.01" max="100000" step="0.01" required value="${p.price/100}"></label><label>可售库存（测试）<input name="stock" type="number" min="0" max="100000" step="1" required value="${p.stock}"></label>${[['description','分享理由与商品故事',10,3000],['ingredients','规格、成分与供应商',2,1000],['usage','使用方法',2,1000],['cautions','适用限制、过敏原与核验说明',2,1000]].map(([k,label,min,max])=>`<label>${label}<textarea name="${k}" required minlength="${min}" maxlength="${max}">${esc(p[k]||'')}</textarea></label>`).join('')}<label>发布状态<select name="status"><option value="draft" ${p.status==='draft'?'selected':''}>草稿 / 下架</option><option value="published" ${p.status==='published'?'selected':''}>发布到演示商城</option></select></label>`,'保存商品',async f=>{if(attempted)throw Error('请先复制保留修改，关闭窗口并刷新商品列表核对上次保存结果，再重新编辑。商品编号：'+p.id);const body=Object.fromEntries(f);body.price=Math.round(Number(body.price)*100);body.stock=Number(body.stock);if(id){if(!p.revision)throw Error('商品版本尚未加载，请复制保留修改，关闭编辑框后刷新页面再试');body.expected_revision=p.revision;}attempted=true;await productContentWrite(p.id,body);void loadManagedProducts();void commerceLoad()},{local:true,message:'商品内容已保存'})}
function managedShopCards(){const status=managedProductLoading||managedProductError?managedProductStatus():'';const list=managedProducts.filter(p=>p.status==='published'&&(shopFilter==='全部'||p.category===shopFilter));return status+(list.length?`<section class="stack portal-section"><h2>無龄岛 · 内容好物</h2>${list.map(p=>`<article class="card">${productPicture(p)}<span class="chip">${esc(p.category)}</span><h3>${esc(p.name)}</h3><p>${esc(p.description.slice(0,100))}</p><p>${money(p.price)} · 测试价格</p><a class="primary" href="#shop/${encodeURIComponent(p.id)}">阅读详情与购买 ↗</a></article>`).join('')}</section>`:'')}
function managedDetail(p){return `<a href="#shop" class="travel-back">← 返回商城</a><article class="card">${productPicture(p)}<span class="chip">${esc(p.category)}</span><h1>${esc(p.name)}</h1><p>${money(p.price)} · 库存 ${p.stock}（测试）</p>${[['description','为什么分享这件好物'],['ingredients','规格与来源'],['usage','使用方式'],['cautions','购买前须知']].map(([k,title])=>`<section class="portal-section"><h2>${title}</h2><p style="white-space:pre-wrap;overflow-wrap:anywhere">${esc(p[k])}</p></section>`).join('')}<button class="primary full" data-shop-buy="${esc(p.id)}" ${p.stock===0?'disabled':''}>${p.stock===0?'暂时缺货':'购买 · 测试下单'}</button><button class="secondary full" data-service-inquiry="${esc(p.name)}">咨询这件好物</button><p class="small muted">本机内容商城，未接通真实付款与发货。</p></article>`}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;if(b.hasAttribute('data-product-refresh')){void loadManagedProducts();return}if(b.hasAttribute('data-product-new'))productEdit();if(b.dataset.productEdit)productEdit(b.dataset.productEdit)});
window.addEventListener('DOMContentLoaded',loadManagedProducts);
window.addEventListener('hashchange',()=>{if(['#shop','#commerce'].includes(location.hash))loadManagedProducts()});

function productPicture(p,small=false){return p.has_image?`<img class="product-photo ${small?'product-thumb':''}" src="/api/commerce/products/${encodeURIComponent(p.id)}/image" alt="${esc(p.name)}" loading="lazy" width="600" height="450">`:''}
async function productImageWrite(id,body){
 const controller=new AbortController();let timeout;
 const deadline=new Promise((_,reject)=>{timeout=setTimeout(()=>{reject(Error('上传等待超过30秒'));controller.abort()},30000)});
 try{
  const result=await Promise.race([api('/commerce/products/'+encodeURIComponent(id)+'/image',{method:'POST',body,signal:controller.signal}),deadline]);
  if(result?.ok!==true)throw Error('返回的上传结果不完整');
 }catch(e){throw Error((e.message||'连接中断')+'；未能确认主图是否保存，服务端可能已处理。请关闭窗口并刷新商品列表核对主图，再决定是否重新上传。')}
 finally{clearTimeout(timeout)}
}
function productImageUpload(id){
 let attempted=false;
 showForm('上传商品主图','<p class="small muted">支持 JPG、PNG、WebP，最大 5 MB。请选择有权使用的商品实拍图，图片会自动压缩并移除位置等元数据。</p><label>选择图片<input name="file" type="file" accept="image/jpeg,image/png,image/webp" required></label><img id="product-image-preview" class="product-photo" hidden alt="上传图片预览">','保存图片',async f=>{
  if(attempted)throw Error('请先关闭窗口并刷新商品列表核对主图，再决定是否重新上传。');
  const file=f.get('file');if(!file?.size||file.size>5*1024*1024)throw Error('请选择不超过 5 MB 的图片');
  attempted=true;await productImageWrite(id,f);
  // A confirmed upload must not keep the form waiting for a separate catalog read.
  void loadManagedProducts();
 },{local:true,message:'商品主图已更新'});
 const input=document.querySelector('#fields input[type=file]'),img=document.querySelector('#product-image-preview'),modal=document.querySelector('#modal');
 let generation=0,reader=null,closed=false;
 const clearPreview=()=>{img.removeAttribute('src');img.hidden=true};
 const cancelReader=()=>{if(reader?.readyState===1)reader.abort();reader=null};
 const close=()=>{closed=true;generation++;cancelReader();clearPreview()};
 modal.addEventListener('close',close,{once:true});
 input.addEventListener('change',()=>{
  const current=++generation;cancelReader();clearPreview();
  const file=input.files[0];if(!file||file.size>5*1024*1024)return;
  const next=new FileReader();reader=next;
  const active=()=>!closed&&current===generation&&modal.open&&img.isConnected&&input.isConnected;
  next.onload=()=>{if(active()){img.src=next.result;img.hidden=false}};
  next.onerror=()=>{if(active())clearPreview()};
  next.readAsDataURL(file);
 });
}

document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.productImage)productImageUpload(b.dataset.productImage);if(b.dataset.productPreview){const p=managedProducts.find(x=>x.id===b.dataset.productPreview);if(p){showForm('商品详情预览',managedDetail(p),'关闭',()=>{},{local:true,message:'预览已关闭'});document.querySelectorAll('#fields [data-shop-buy],#fields [data-service-inquiry]').forEach(x=>{x.disabled=true});document.querySelector('#fields .travel-back')?.remove()}}});
