'use strict';
// The first screen is the actual review queue; drafts stay scoped to the enterprise.
let workQueueProject='',workQueueTab='review',workQueueSearch='',workQueuePage=0;
function resetWorkQueue(){if(workQueueProject!==pid){workQueueProject=pid;workQueueTab='review';workQueueSearch='';workQueuePage=0;}}
function hasReviewLayout(c){return !!(c.layout&&!c.layout.outdated&&c.layout.cover_id&&c.layout.blocks?.length);}
function deliveredContent(c){return c.channels.length>0&&c.channels.every(ch=>(state.publication||[]).some(p=>p.content_id===c.id&&p.revision===c.revision&&p.channel===ch&&['published','recorded'].includes(p.status)));}
function workApprovalValid(c){return c.status==='approved'&&c.approved_revision===c.revision&&c.approval_summary?.effective_approved!==false;}
function workQueueGroups(){
 const rows=[...(state.content||[])].sort((a,b)=>String(a.import_batch||'').localeCompare(String(b.import_batch||''))||a.title.localeCompare(b.title,'zh-CN',{numeric:true})||a.id.localeCompare(b.id));
 return {
  all:rows,
  review:rows.filter(c=>c.status==='pending'&&hasReviewLayout(c)),
  preparation:rows.filter(c=>['draft','rejected'].includes(c.status)||(c.status==='pending'&&!hasReviewLayout(c))||(c.status==='approved'&&!workApprovalValid(c))),
  approved:rows.filter(c=>workApprovalValid(c)&&!deliveredContent(c)),
 };
}
function workQueueCards(){
 resetWorkQueue();const groups=workQueueGroups();
 const rows=groups[workQueueTab].filter(c=>c.title.toLocaleLowerCase().includes(workQueueSearch.toLocaleLowerCase().trim()))
  .sort((a,b)=>String(a.import_batch||'').localeCompare(String(b.import_batch||''))||a.title.localeCompare(b.title,'zh-CN',{numeric:true})||a.id.localeCompare(b.id));
 const pages=Math.max(1,Math.ceil(rows.length/6));workQueuePage=Math.min(Math.max(0,workQueuePage),pages-1);
 const cards=rows.slice(workQueuePage*6,workQueuePage*6+6).map(c=>{
  const layout=hasReviewLayout(c),cover=layout?c.layout.cover_id:null;
  const factsPending=c.approval_summary?.sources_outdated||c.sources?.some(source=>{const k=state.knowledge.find(k=>k.id===source.id);return !k||k.status!=='confirmed'||k.version!==source.version||k.knowledge_outdated;});
  return `<article class="review-card"><button class="review-cover" data-action="preview" data-id="${esc(c.id)}" aria-label="预览：${esc(c.title)}">${cover?`<img src="${apiPath('/assets/'+encodeURIComponent(cover)+'/file')}" alt="${esc(c.title)}封面" loading="lazy">`:'<span>待完善图文排版</span>'}</button><div class="review-card-body"><div class="between"><span class="pill ${workQueueTab==='approved'?'green':'amber'}">${layout&&c.status==='pending'?'已排版 · 待审核':esc(c.status==='approved'&&!workApprovalValid(c)?'审批需复核':statuses[c.status]?.[0]||c.status)}</span><span class="hint">v${c.revision}</span></div><h3>${esc(c.title)}</h3><p class="hint">${c.channels.length?c.channels.map(esc).join(' / '):'发布渠道待选择'}${layout?' · '+(1+(c.layout.figures||[]).length)+' 张配图':''}</p>${factsPending?'<p class="review-warning">引用资料待核准</p>':''}<div class="review-card-actions">${workQueueTab==='approved'?primary('安排发布','work-queue-publish',c.id):primary(workQueueTab==='preparation'?'查看并完善':'预览审核','preview',c.id)}${layout?`<a href="${apiPath('/contents/'+encodeURIComponent(c.id)+'/client-preview?revision='+c.revision+'&format=png')}">下载长图</a>`:''}</div></div></article>`;
 }).join('');
 return `<div class="review-grid">${cards||`<div class="review-empty"><h3>${workQueueSearch?'没有匹配的文章':workQueueTab==='all'?'暂无稿件':workQueueTab==='review'?'暂无已排版待审稿':workQueueTab==='approved'?'暂无审核通过的文章':'暂无需要完善的稿件'}</h3><p>${workQueueSearch?'换个标题关键词试试。':'可以从内容创作开始，或切换上方分类查看其他稿件。'}</p></div>`}</div><div class="review-pagination"><span class="hint">共 ${rows.length} 篇 · 第 ${workQueuePage+1} / ${pages} 页</span><div class="flex">${action('上一页','work-queue-page','-1',workQueuePage===0?'disabled':'')}${action('下一页','work-queue-page','1',workQueuePage>=pages-1?'disabled':'')}</div></div>`;
}
function reviewWorkspace(){
 resetWorkQueue();const groups=workQueueGroups(),jobs=(state.execution||[]).filter(j=>['failed','unknown'].includes(j.status));
 const waiting=(state.publication||[]).filter(p=>['awaiting_connector','wp_draft'].includes(p.status));
 const alerts=[...(jobs.length?[action(`${jobs.length} 项执行异常待处理`,'delivery-jobs')]:[]),...(waiting.length?[action(`${waiting.length} 项发布任务待交付`,'navigate','publish')]:[])];
 return head('待审图文',`${state.project.name} · 先看排版效果，确认后进入矩阵发布。`,canEdit()?action(icon('plus')+'创作新内容','compose'):'')+
 `<section class="review-workbench" aria-label="图文审核工作台"><div class="review-toolbar"><div class="review-tabs" role="group" aria-label="稿件状态">${[['review','已排版 · 待审核'],['preparation','待完善'],['approved','已通过 · 待发送'],['all','全部稿件']].map(([key,label])=>action(`${label} <span>${groups[key].length}</span>`,'work-queue-tab',key,`aria-pressed="${workQueueTab===key}" class="${workQueueTab===key?'selected':''}"`)).join('')}</div><label class="review-search"><span class="hide">搜索文章标题</span><input type="search" id="work-queue-search" aria-label="搜索文章标题" placeholder="搜索文章标题" value="${esc(workQueueSearch)}"></label></div><div id="work-queue-results">${workQueueCards()}</div></section>`+
 (alerts.length?`<div class="workspace-alerts">${alerts.join('')}</div>`:'')+
 `<section class="workspace-shortcuts" aria-label="日常工作入口">${[['skills','与内容专家对话','调用本企业知识创作'],['knowledge','企业知识库','核准资料与事实'],['assets','品牌图库','找配图与品牌素材'],['publish','矩阵发布','安排渠道交付与回执']].map(([route,label,desc])=>`<a href="#${route}"><strong>${label} →</strong><span>${desc}</span></a>`).join('')}</section>`+
 `<details class="workspace-operations"><summary>执行记录与项目工具</summary>${deliveryStrip()}<div class="workspace-operation-links">${action('项目协作记录','manager-open')}${action('查看交付记录','navigate','delivery')}</div></details>`;
}
function coreNavigation(){
 const primaryItems=[['workspace','grid'],['schedule','calendar'],['viral','pen'],['skills','bolt'],['repurpose','box'],['publish','send']],assets=[['brand','shield'],['knowledge','book'],['qa','book'],['assets','box']];
 const more=[['seo','globe'],['diagnosis','chart'],['leads','users'],['delivery','chart']];
 const activeKey=page()==='content'?'skills':page();
 const link=([key,i])=>`<a href="#${key}" class="navitem ${activeKey===key?'active':''}" ${activeKey===key?'aria-current="page"':''}>${icon(i)}${pageNames[key]}${key==='workspace'&&workQueueGroups().review.length?`<span class="count">${workQueueGroups().review.length}</span>`:''}</a>`;
 return `<a href="#screen" class="monitor-entry ${page()==='screen'?'active':''}" ${page()==='screen'?'aria-current="page"':''}>${icon('screen')}<span><strong>动态监控大屏</strong><small>查看企业整体进展</small></span>${icon('chevron')}</a><div class="navlabel">内容交付</div>`+primaryItems.map(link).join('')+'<div class="navlabel">企业资料</div>'+assets.map(link).join('')+`<details class="nav-more" ${more.some(([key])=>activeKey===key)?'open':''}><summary>更多工具</summary>${more.map(link).join('')}</details>`;
}
document.addEventListener('input',e=>{if(e.target.id!=='work-queue-search')return;resetWorkQueue();workQueueSearch=e.target.value;workQueuePage=0;$('#work-queue-results').innerHTML=workQueueCards();});
document.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action;if(!['work-queue-tab','work-queue-page'].includes(a))return;resetWorkQueue();if(a==='work-queue-tab'){if(!['review','preparation','approved','all'].includes(b.dataset.id))return;workQueueTab=b.dataset.id;workQueuePage=0;render();}else{workQueuePage+=Number(b.dataset.id);$('#work-queue-results').innerHTML=workQueueCards();}});
function scheduleActionQueue(){
 const groups=workQueueGroups(),selected=[...groups.review.slice(0,3),...groups.approved.slice(0,3),...groups.preparation.slice(0,2)];
 return panel('现在需要审核与发送',`${groups.review.length} 篇已排版待审核 · ${groups.approved.length} 篇已通过待发送 · ${groups.preparation.length} 篇待完善`,
 selected.length?selected.map(c=>`<div class="task"><div class="info"><h3>${esc(c.title)}</h3><p>v${c.revision} · ${workApprovalValid(c)?'审核通过 · 待交付':hasReviewLayout(c)&&c.status==='pending'?'已排版 · 待审核':esc(c.status==='approved'&&!workApprovalValid(c)?'审批需复核':statuses[c.status]?.[0]||c.status)} · ${c.scheduled?fmt(c.scheduled):'尚未安排时间'}</p></div>${workApprovalValid(c)?primary('安排发布','work-queue-publish',c.id):action('预览审核','preview',c.id)}</div>`).join(''):'<p class="hint">当前没有待处理稿件，已有安排见下方日历。</p>',action('查看全部待审图文 →','work-queue-open','review'));
}
function publishReadyQueue(){
 if(publishTarget())return '';
 const rows=workQueueGroups().approved;
 return panel('审核通过 · 待发送',`${rows.length} 篇等待渠道交付`,rows.length?rows.map(c=>`<div class="task"><div class="info"><h3>${esc(c.title)}</h3><p>已通过 v${c.revision} · ${c.channels.map(esc).join(' / ')}</p></div>${primary('安排发布','work-queue-publish',c.id)}</div>`).join(''):'<p class="hint">暂无审核通过的待发稿件。先在工作台核对图文并完成审核。</p>',action('回到待审图文','work-queue-open','review'));
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(!b)return;if(b.dataset.action==='work-queue-open'){resetWorkQueue();workQueueTab='review';workQueuePage=0;workQueueSearch='';location.hash='workspace';render();}if(b.dataset.action==='work-queue-publish'){const c=state.content.find(c=>c.id===b.dataset.id);if(c)openPublishTarget(pid,c.id,c.revision);}});

function computeCreditEntry(){return `<div class="compute-credit-entry"><div><strong>算力积分</strong><span>余额 — · 计费待接入</span></div>${action('充值','credits','','class="small"')}</div>`;}
function computeCredits(){const rows=(state.execution||[]).filter(j=>j.result?.usage);const sum=k=>rows.reduce((n,j)=>n+(j.result.usage[k]||0),0);openModal('算力积分与充值',`<div class="metric-value">—<small>积分余额尚未接入</small></div><p>充值入口已保留。支付和积分账本尚未接通，当前不能在线充值。</p><h3>本企业模型用量记录</h3><p>有用量回执的任务 ${rows.length} 项 · 输入 ${sum('prompt_tokens')} tokens · 输出 ${sum('completion_tokens')} tokens</p><p class="hint">这是执行回执汇总，部分供应商可能不返回全部用量；不是积分余额或账单。已配置的模型服务可能产生供应商费用。</p>${action('查看执行明细','delivery-jobs')}`);}
