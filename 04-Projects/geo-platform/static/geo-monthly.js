'use strict';
// Counts describe recorded observations, never platform-wide visibility.
function geoMonthKey(value){
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value))return null;
 const [y,m,d]=value.slice(0,10).split('-').map(Number);
 if(m<1||m>12||d<1||d>new Date(Date.UTC(y,m,0)).getUTCDate())return null;
 const t=Date.parse(value);if(!Number.isFinite(t))return null;
 return new Date(t+8*3600000).toISOString().slice(0,7);
}
function geoMonthBefore(month){const [y,m]=month.split('-').map(Number);return new Date(Date.UTC(y,m-2,1)).toISOString().slice(0,7);}
function geoMonthlyData(reports,platform='',now=new Date()){
 const groups=new Map(),seen=new Set();let skipped=0,duplicates=0;
 for(const report of reports||[]){if(report.status==='sample')continue;
  for(const s of report.samples||[]){
   if(s.source!=='manual'||typeof s.answer!=='string'||!s.answer.trim()||!s.question?.trim()||!s.platform||(platform&&s.platform!==platform))continue;
   const month=geoMonthKey(s.observed_at),stamp=Date.parse(s.observed_at);
   if(!month||stamp>now.getTime()){skipped++;continue;}
   // Different ISO offsets/precision can identify the very same observation.
   const key=JSON.stringify([s.platform,s.question,stamp,s.answer,s.mentioned,s.citation,s.recommended]);
   if(seen.has(key)){duplicates++;continue;}seen.add(key);
   const r=groups.get(month)||{month,samples:0,mentions:0,citations:0,recommended:0,recommendationKnown:0,latest:new Map()};
   r.samples++;r.mentions+=s.mentioned===true?1:0;r.citations+=s.citation?1:0;
   if(typeof s.recommended==='boolean'){r.recommendationKnown++;r.recommended+=s.recommended?1:0;}
   const pair=JSON.stringify([s.platform,s.question.trim()]);
   const latest=r.latest.get(pair),mentioned=s.mentioned===true;
   if(!latest||stamp>latest.stamp)r.latest.set(pair,{stamp,mentioned,conflict:false});
   else if(stamp===latest.stamp&&mentioned!==latest.mentioned)latest.conflict=true;
   groups.set(month,r);
  }
 }
 if(!groups.size)return {rows:[],skipped,duplicates};
 let month=geoMonthKey(now.toISOString());const first=[...groups.keys()].sort()[0],rows=[];
 // Bound a malformed historical date without creating an unbounded page.
 for(let i=0;i<120&&month>=first;i++,month=geoMonthBefore(month)){
  const r=groups.get(month)||{month,samples:0,mentions:0,citations:0,recommended:0,recommendationKnown:0,latest:new Map()};
  const prev=groups.get(geoMonthBefore(month)),pairs=prev?[...r.latest.keys()].filter(k=>prev.latest.has(k)&&!r.latest.get(k).conflict&&!prev.latest.get(k).conflict):[];
  rows.push({...r,latest:undefined,conflicts:[...r.latest.values()].filter(x=>x.conflict).length,rate:r.samples?100*r.mentions/r.samples:null,
   paired:pairs.length,delta:pairs.length?100*pairs.reduce((n,k)=>n+Number(r.latest.get(k).mentioned)-Number(prev.latest.get(k).mentioned),0)/pairs.length:null});
 }
 return {rows,skipped,duplicates};
}
let geoMonthlyPlatform='';
function geoMonthlyPanel(){
 const report=geoMonthlyData(state.diagnosis,geoMonthlyPlatform),rate=n=>n===null?'未采样':n.toFixed(1)+'%';
 const filter=`<label>统计平台<select id="geo-monthly-platform"><option value="">全部平台</option>${me.platforms.map(p=>`<option value="${esc(p)}" ${p===geoMonthlyPlatform?'selected':''}>${esc(p)}</option>`).join('')}</select></label>`;
 const body=report.rows.length?`<div class="table-wrap"><table><thead><tr><th>月份</th><th>回答样本</th><th>品牌提及</th><th>提及率</th><th>同题环比</th><th>附引用回答</th><th>明确推荐</th></tr></thead><tbody>${report.rows.map(r=>`<tr><td>${r.month}</td><td>${r.samples||'未采样'}</td><td>${r.samples?r.mentions:'—'}</td><td>${rate(r.rate)}</td><td>${r.delta===null?'无可比样本':`${r.delta>0?'+':''}${r.delta.toFixed(1)} 个百分点`}<div class="hint">${r.paired?'同平台同题 '+r.paired+' 对；每月取最新一条':''}</div>${r.conflicts?`<div class="hint">${r.conflicts} 题最新同刻标注冲突，未用于环比</div>`:''}</td><td>${r.samples?r.citations:'—'}</td><td>${r.recommendationKnown?`${r.recommended} / ${r.recommendationKnown} 条已标注`:'未标注'}</td></tr>`).join('')}</tbody></table></div>`:'<p class="hint">暂无可统计的人工采样。录入实际平台回答后自动按月累计；没有记录不显示零分。</p>';
 return panel('月度变化统计','北京时间自然月 · 仅统计人工录入的实际回答',filter+body+`${report.duplicates?`<p class="hint">已合并 ${report.duplicates} 条重复记录（同平台、问题、实际时刻、回答及标注相同）；原始证据保留。</p>`:''}<p class="hint">环比使用相邻月同平台、同问题的最新回答配对；无共同问题不计算；最新同刻提及标注冲突的题目排除，原始记录仍保留在月度样本数与提及率中，需复核。样本数量与题目覆盖不同，不能据此归因优化效果。引用指附有地址，不等于引用本企业；提及不等于推荐。示例、模型 API 与外部汇总不混入。</p>${report.skipped?`<p class="hint">${report.skipped} 条记录日期无效或晚于当前时间，未纳入。</p>`:''}`);
}
document.addEventListener('change',e=>{if(e.target.id==='geo-monthly-platform'){geoMonthlyPlatform=e.target.value;const el=document.getElementById('geo-monthly');if(el)el.innerHTML=geoMonthlyPanel();}});
