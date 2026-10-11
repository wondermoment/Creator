'use strict';
let collectionFilter='',assetPageIndex=0,assetSearchText='';
const sampleAssetRowsBase=assetRows;assetRows=function(){return sampleAssetRowsBase().map(a=>a.group==='media'&&a.mime&&!a.mime.startsWith('image/')&&!a.mime.startsWith('video/')?{...a,group:'document'}:a);};
function samplePanel(){const b=state.import_batch?.find(x=>x.batch==='hetuo-20261002')||state.import_batch?.[0];if(!b)return '';const drafts=state.content.filter(c=>c.origin==='customer_prepublication');return panel('企业资料归档与交付准备','真实资料样板 · 原文件、提炼稿、配图与待发内容分别留存',`<div class="knowledge-summary">${[['来源文档',state.knowledge.filter(k=>k.origin==='customer_source').length],['提炼文档',state.knowledge.filter(k=>k.derived).length],['图片资产',state.asset.filter(a=>a.category==='图片').length],['待发布稿',drafts.length]].map(([t,n])=>`<div class="kb-stat blue"><div><span>${t}</span><strong>${n}</strong></div></div>`).join('')}</div><p class="hint">资料已归档不等于技术事实已核准。当前 ${state.knowledge.filter(k=>k.status==='confirmed').length} 份知识已确认；本批 ${drafts.filter(c=>c.status==='approved').length} 篇审核通过。</p><div class="flex wrap">${action('查看 '+drafts.length+' 篇待发内容','sample-articles')}${action('下载客户审阅包','sample-download')}<a href="#assets">按分类查看企业资产 →</a></div>${b.quarantined?.length?`<p class="notice amber">已隔离 ${b.quarantined.length} 份归属异常资料：${b.quarantined.map(q=>esc(q.title)+"（"+esc(q.reason)+"）").join("；")}。不参与创作与问答。</p>`:""}<details style="margin-top:16px"><summary class="hint">来源记录与导入说明</summary>${b.links.map(l=>`<p><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.name)} ↗</a><br><span class="hint">${esc(l.note)}</span></p>`).join('')}</details>`);}
const sampleKnowledgeBase=knowledgePage;knowledgePage=function(){return samplePanel()+sampleKnowledgeBase();};

const sampleSkillsBase=skillsPage;skillsPage=function(){return sampleSkillsBase()+(state.import_batch?.length?panel('企业专属写作方法','学习外部文章结构，事实仍只来自本企业已核准资料。',`${action('查看写作方法与验收用例','sample-method')}<p class="hint">智能体 Soul 在专家配置中查看，3 套 Skill 已保存为本企业版本。提示词配置不代表真实模型已经接通。</p>`):'');};
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action="sample-method"]');if(!b)return;try{const d=await api(apiPath('/writing-reference'));openModal('写作参考 · 与企业事实分开',`<div class="notice">${esc(d.boundary)}</div><p class="hint">${esc(d.coverage||'归档进行中')}</p><div class="text-body" style="max-height:60vh">${esc(d.methodology)}</div>`,true);}catch(error){toast(error.message);}});
const samplePreviewBase=preview;preview=function(id){samplePreviewBase(id);const c=state.content.find(x=>x.id===id);if(c?.layout)$('.preview-side',modal).insertAdjacentHTML('afterbegin',`<section><h3>图文排版与客户审阅</h3><a class="file-link" href="${apiPath('/contents/'+id+'/proof?revision='+c.revision)}" target="_blank" rel="noopener">打开完整图文预览 ↗</a><p class="hint">保留原稿、表格与素材来源。参数核验提示在预览右侧，尚未发送。</p>${(c.review_notes||[]).map(n=>`<p class="hint">${esc(n)}</p>`).join('')}</section>`);};
function sampleArticles(){const rows=state.content.filter(c=>c.layout);const batches=[...new Set(rows.map(c=>c.import_batch||''))];openModal('待发布内容 · 分批预览与审核',`<div class="notice amber">共 ${rows.length} 篇原稿，当前交付版本尚未通过本系统发送。先核准来源事实、选择配图与渠道，再审核对应版本。</div>${batches.map(batch=>{const group=rows.filter(c=>(c.import_batch||'')===batch).sort((a,b)=>(parseInt(a.title)||0)-(parseInt(b.title)||0));return `<section><h2>${esc((state.import_batch?.find(b=>b.batch===batch)?.name||'内容批次').replace(/\s*·\s*新增\s*\d+\s*篇$/,' · 新增批次'))} · ${group.length} 篇</h2>${group.map(c=>`<div class="task"><div class="info"><h3>${esc(c.title)}</h3><p>${badge(c.status)} · v${c.revision} · ${esc(c.preparation_status||'图文已编排，待客户核准')}</p>${c.editorial_summary?`<p class="hint">${esc(c.editorial_summary.category)} · ${c.editorial_summary.tables} 张表格 · ${c.body.length} 字符</p>`:''}</div><div class="flex"><a href="${apiPath('/contents/'+c.id+'/proof?revision='+c.revision)}" target="_blank" rel="noopener">排版预览 ↗</a>${action('审核','preview',c.id,'class="small"')}</div></div>`).join('')}${action('下载本批审阅包','sample-download',batch)}</section>`;}).join('')}`,true);}
const sampleContentBase=contentPage;contentPage=function(){const imported=state.content.filter(c=>c.origin==='customer_prepublication');return (imported.length?panel('待发布内容批次',`${imported.length} 篇客户原稿 · 保留企业归属、原文与来源`,`${action('分批查看待发内容','sample-articles')}<p class="hint">新导入文章待选渠道与配图；历史刊发证据另行记录，不自动改变当前稿件状态。</p>`):'')+sampleContentBase();};

const sampleAssetsBase=assetsPage;assetsPage=function(){const markup=sampleAssetsBase();const collections=[...new Set(state.asset.map(a=>a.collection).filter(Boolean))].sort();return collections.length?markup.replace('<div id="asset-results">',`<div class="flex wrap" style="margin:16px 0">${action('全部分类','sample-collection','',`class="small ${!collectionFilter?'primary':''}"`)}${collections.map(c=>action(esc(c)+' · '+state.asset.filter(a=>a.collection===c).length,'sample-collection',c,`class="small ${collectionFilter===c?'primary':''}"`)).join('')}</div><div id="asset-results">`):markup;};
assetCards=function(query=''){assetSearchText=query;const rows=assetRows().filter(a=>(assetFilter==='all'||a.group===assetFilter)&&(!collectionFilter||a.collection===collectionFilter)&&[a.title,a.collection,...(a.tags||[])].join(' ').toLowerCase().includes(query.toLowerCase()));const pages=Math.max(1,Math.ceil(rows.length/24));assetPageIndex=Math.min(assetPageIndex,pages-1);const shown=rows.slice(assetPageIndex*24,(assetPageIndex+1)*24);return `<div class="between" style="margin:16px 0"><span class="hint">${rows.length} 项匹配资产 · 每页 24 项</span><div class="flex">${action('上一页','sample-page','-1',`class="small" ${assetPageIndex===0?'disabled':''}`)}<span class="hint">${assetPageIndex+1} / ${pages}</span>${action('下一页','sample-page','1',`class="small" ${assetPageIndex===pages-1?'disabled':''}`)}</div></div>`+(shown.length?`<div class="cards">${shown.map(a=>`<article class="panel resource-card">${a.mime?.startsWith('image/')?`<img class="asset-thumb" loading="lazy" src="${apiPath('/assets/'+a.id+'/file')}" alt="${esc(a.title)}" width="300" height="150">`:`<div class="asset-placeholder">${icon('file')}</div>`}<span class="eyebrow">${esc(a.collection||a.group)}</span><h2>${esc(a.title)}</h2><p class="desc">${esc(a.subtitle)}</p><footer>${action('查看资产',a.action,a.linkId||a.id,'class="small"')}</footer></article>`).join('')}</div>`:empty('此分类暂无匹配资产','可切换分类或修改搜索词。'));};
const sampleAssetPreviewBase=assetPreview;assetPreview=function(id){sampleAssetPreviewBase(id);const a=state.asset.find(x=>x.id===id);if(a.source_refs)$('.modal-body',modal).insertAdjacentHTML('beforeend',`<hr><h3>资产分类与来源</h3><p>${esc(a.collection||'未分类')}</p><p class="hint">${esc(a.description||'')}<br>${esc(a.rights_status||'')}</p>${(a.related_knowledge_ids||[]).map(kid=>{const k=state.knowledge.find(k=>k.id===kid);return k?action(esc(k.title),'view-knowledge',kid,'class="small"'):'';}).join('')}<details><summary class="hint">查看原始来源记录</summary><div class="text-body hint">${esc(JSON.stringify(a.source_refs,null,2))}</div></details>`);};
const sampleKnowledgePreviewBase=viewKnowledge;viewKnowledge=function(id){sampleKnowledgePreviewBase(id);const k=state.knowledge.find(x=>x.id===id);$('.modal-body',modal).insertAdjacentHTML('afterbegin',`${k.asset_id?`<p><a href="${apiPath('/assets/'+k.asset_id+'/file')}" target="_blank" rel="noopener">下载原始资料 ↗</a></p>`:''}${k.derived?`<div class="notice">提炼稿 · ${(k.source_ids||[]).length} 份来源；保留原文，不替代原始技术凭证。</div>${k.knowledge_outdated?'<p class="notice amber">来源待核对 · 停止复用。请先核准原资料；若来源已升版或缺少版本记录，需重新提炼并保留旧稿。</p>':''}${(k.source_ids||[]).map(rid=>{const source=state.knowledge.find(x=>x.id===rid),snapshot=(k.source_snapshots||[]).find(x=>x.id===rid);return action(esc(source?.title||'来源资料')+' · '+(snapshot?'引用 v'+esc(snapshot.version):'引用版本缺失')+' / '+(source?'当前 v'+esc(source.version):'来源不可用'),'view-knowledge',rid,`class="small" ${source?'':'disabled'}`);}).join('')}`:''}`);};
const rebuildKnowledgePreviewBase=viewKnowledge;
viewKnowledge=function(id){
  rebuildKnowledgePreviewBase(id);
  const k=state.knowledge.find(x=>x.id===id);
  if(k.derived&&canEdit())$('.modal-body',modal).insertAdjacentHTML('beforeend',`<hr>${action('基于最新来源重建提炼稿','knowledge-rebuild',id)}<p class="hint">新建待核准提炼稿，保留旧稿及关联内容；不会自动替换文章引用或恢复旧审批。</p>`);
  if(k.rebuild_from)$('.modal-body',modal).insertAdjacentHTML('afterbegin',`<p class="notice">重建自 ${esc(k.rebuild_from.title)} · v${esc(k.rebuild_from.version)}<br>重建人：${esc(k.rebuilt_by)} · ${esc(k.rebuilt_at)}<br>说明：${esc(k.rebuild_note)}</p>${action('查看旧提炼稿','view-knowledge',k.rebuild_from.id,'class="small"')}`);
};
function rebuildKnowledge(id){
  const projectId=pid;
  const old=JSON.parse(JSON.stringify(state.knowledge.find(k=>k.id===id)));
  const candidates=JSON.parse(JSON.stringify(state.knowledge.filter(k=>k.id!==id&&k.status==='confirmed'&&!k.knowledge_outdated)));
  if(!old?.derived||!canEdit())return;
  openModal('重建提炼稿 · 选择最新来源',`<form><p class="notice">${esc(old.title)} · v${esc(old.version)}。先选择来源，再阅读原文并编写新的提炼正文。未核准或失效来源不能使用。</p><div class="checklist">${candidates.map(k=>`<label class="check"><input name="source_ids" type="checkbox" value="${esc(k.id)}">${esc(k.title)} · v${esc(k.version)}</label>`).join('')||'<p class="hint">暂无有效来源，请先到企业知识库核准原始资料。</p>'}</div>${err()}<button type="submit" class="primary" ${candidates.length?'':'disabled'}>下一步：阅读来源并重新提炼</button></form>`,true,async f=>{
    if(pid!==projectId)throw new Error('企业空间已切换，请重新打开资料');
    const ids=f.getAll('source_ids');
    if(!ids.length||ids.length>20)throw new Error('请选择 1 至 20 份来源');
    const selected=ids.map(rid=>candidates.find(k=>k.id===rid));
    if(selected.some(k=>!k))throw new Error('来源选择已失效，请重新打开');
    openModal('重建提炼稿 · 阅读与编写',`<form><p class="notice">根据下方来源重新编写；新稿仍需客户核准。旧稿、旧确认记录和文章引用保留。</p><details><summary>查看旧稿 · ${esc(old.title)} · v${esc(old.version)}</summary><div class="text-body">${esc(old.body)}</div></details>${selected.map(k=>`<details open class="source"><summary>${esc(k.title)} · 本次引用 v${esc(k.version)}</summary><p class="hint">${esc(k.source)}</p><div class="text-body">${esc(k.body)}</div></details>`).join('')}<label>新提炼稿标题<input name="title" required maxlength="180" value="${esc((old.title+' · 重建稿').slice(0,180))}"></label><label>新提炼正文<textarea name="body" required rows="10" maxlength="80000" placeholder="重新提炼事实、适用条件与边界，说明各结论依据；不要直接沿用旧结论。"></textarea></label><label>重建说明<textarea name="note" required minlength="5" maxlength="2000" rows="3" placeholder="说明核对了什么、调整了哪些结论"></textarea></label><label class="check"><input type="checkbox" name="read_sources" required>我已阅读上述来源版本，并据此重新提炼；仍需客户审核。</label>${err()}<button type="submit" class="primary">保存新提炼稿，等待核准</button></form>`,true,async values=>{
      if(pid!==projectId)throw new Error('企业空间已切换，请重新打开资料');
      if(!values.get('read_sources'))throw new Error('请先阅读并确认所选来源');
      const r=await api(`/api/projects/${projectId}/knowledge/${old.id}/rebuild`,'POST',{version:old.version,title:values.get('title'),body:values.get('body'),note:values.get('note'),sources:selected.map(k=>({id:k.id,version:k.version}))});
      if(pid!==projectId)return;
      closeModal();await refresh();viewKnowledge(r.id);toast('新提炼稿已保存，等待客户核准；旧稿保留');
    });
  });
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-action="knowledge-rebuild"]');if(b)rebuildKnowledge(b.dataset.id);});
document.addEventListener('input',e=>{if(e.target.id==='asset-search'){assetPageIndex=0;$('#asset-results').innerHTML=assetCards(e.target.value);}});
document.addEventListener('change',e=>{if(e.target.id==='project-select'){collectionFilter='';assetPageIndex=0;assetSearchText='';}});
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;try{if(a==='sample-articles')sampleArticles();if(a==='sample-collection'){collectionFilter=id;assetPageIndex=0;render();}if(a==='sample-page'){assetPageIndex+=Number(id);$('#asset-results').innerHTML=assetCards(assetSearchText);}if(a==='asset-filter')assetPageIndex=0;if(a==='sample-download'){b.disabled=true;await downloadDelivery('/review-pack'+(id?'?batch='+encodeURIComponent(id):''),'和拓实业-客户审阅包.zip');toast('审阅包已下载；尚未批准或发送');}}catch(error){toast(error.message);}finally{b.disabled=false;}});

const formattedProofBase=preview;
preview=function(id){
  formattedProofBase(id);
  const project=pid,c=state.content.find(x=>x.id===id),target=$('.content-preview',modal),snapshot=previewSnapshot;
  if(!c?.layout||!target)return;
  const current=()=>project===pid&&previewId===id&&previewSnapshot===snapshot&&target.isConnected;
  const controls=Array.from(modal.querySelectorAll('[data-action="submit-content"],[data-action="approve-content"],[data-action="approve-go-publish"],[data-action="go-publish"],[data-action="reject-content"],[data-action="publish-content"]'));
  controls.forEach(b=>b.disabled=true);
  target.classList.add('article-proof');target.innerHTML='<p role="status">正在加载本次审核版本的图文排版…</p>';
  fetch(`/api/projects/${project}/contents/${id}/proof?revision=${snapshot.revision}`,{cache:'no-store'}).then(async r=>{
    if(!r.ok)throw Error(r.status===409?'内容版本已更新，请关闭预览并刷新后重新审阅':'图文稿读取失败，请关闭后重新打开');
    if(r.headers.get('X-Content-Revision')!==String(snapshot.revision))throw Error('预览版本未通过校验，请刷新页面后重新打开');
    const text=await r.text();if(!current())return;
    const doc=new DOMParser().parseFromString(text,'text/html'),article=doc.querySelector('article');
    if(!article)throw Error('图文预览不完整，请重试');
    target.innerHTML=article.innerHTML;
    await Promise.all(Array.from(target.querySelectorAll('img')).map(img=>{img.loading='eager';return img.decode();}));
    if(!current())return;
    if(r.headers.get('X-Layout-Status')!=='current'){
      target.insertAdjacentHTML('afterbegin','<p class="notice">图文排版已过期，旧配图已暂停展示。请根据最新标题和正文重新制作配图后再送审。</p>');
      return;
    }
    snapshot.ready=true;controls.forEach(b=>b.disabled=false);
  }).catch(e=>{if(current()){snapshot.ready=false;target.textContent=e.message.includes('版本')||e.message.includes('图文')?e.message:'配图加载失败，请关闭后重新打开；当前不能审批';}});
};
