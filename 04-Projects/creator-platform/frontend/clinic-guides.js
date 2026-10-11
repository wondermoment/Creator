/* Chinese editorial summaries, not a booked itinerary or independent efficacy review.
   Raw official-page captures and image provenance: output/clinic-research-20261005. */
const clinicGuides={
 'Clinique La Prairie':{
  checked:'2026-10-05',image:'clp-lake.webp',caption:'瑞士蒙特勒院区与日内瓦湖环境；图片不代表中国安吉院区。',photoSource:'https://cliniquelaprairie.com/destinations/switzerland-montreux/',
  intro:'这家机构值得重点了解的，是医生如何把检查结果转成后续计划。健康诊断评估面向“我应该先弄清哪些健康风险”，体重管理则进一步涉及营养、活动和行为习惯。两者目标不同，不宜只按检查数量或入住天数来比较。',
  programmes:[
   {name:'健康诊断评估',english:'Health Diagnostic',scope:'官网介绍为 3 天 · 蒙特勒与安吉均有项目',description:'到访前先与医生沟通，入住后进行初次评估，再根据年龄、病史与健康状况选择检查。官网描述了血液检查、影像、骨密度以及心肺相关评估；这些是项目范围，并非每位客人都应完成的固定清单。',details:[['先把问题交给医生','提前提供近期报告和用药清单，说明是无症状风险筛查，还是已有症状需要诊断。原有报告是否可复用、是否需要空腹，应提前确认。'],['两个院区各有侧重','安吉页面列有遗传检测、营养与代谢评估、物理治疗和运动相关评估；蒙特勒列有肺科、消化科、骨骼等专科参与。具体检查与医生安排仍需所选院区确认。'],['离院时带走什么','官网提到医生复诊与个性化书面建议。建议把报告获取方式、异常结果后续转诊、复查时间和责任医生一起问清。']],question:'我已有近半年的体检报告，哪些可以复用？新增检查会如何影响后续决定？'},
   {name:'健康体重管理',english:'Healthy Weight',scope:'官网介绍为 7 天 · 此项目页标注瑞士蒙特勒',description:'内容围绕医学评估、营养、运动与心理支持展开。与单纯追求短期掉秤相比，更适合先了解身体组成、饮食习惯和可持续的活动安排；短期体重变化不等于长期健康收益。',details:[['营养和运动一起安排','页面介绍营养咨询、个性化饮食计划与工作坊、运动评估、个人训练及户外活动。能否参加、强度如何调整，需要结合体力和病史决定。'],['监测用来解决什么问题','项目介绍连续血糖监测。应询问测量结果由谁解释、是否适用于自己，以及设备是否包含在费用内；非糖尿病人使用监测设备并不自动意味着获得明确健康收益。'],['返家后的执行支持','官网提到出院摘要、实用资料及医生和营养师随访电话。应确认次数、服务期限、语言与时区，避免回家后只剩一份难以执行的报告。']],question:'返家后一个月怎么继续饮食与训练计划？随访包含几次，发现异常由谁处理？'}
  ],
  decision:'如果首要目标是读懂风险与报告，可先咨询健康诊断评估；如果重点是体重和生活习惯，可了解健康体重项目。不要把蒙特勒的 7 天项目直接当作安吉可订套餐。',
  cautions:'影像筛查需讨论必要性、辐射与偶然发现，不能因套餐包含就全部接受。涉及限制进食时，糖尿病用药、妊娠或进食障碍等情况须先经医生评估。遗传、微量元素或“生物年龄”等指标的临床意义应逐项解释，不等于证明可以延寿。',
  costs:'要求分列医疗评估、可选检查、住宿餐食、陪同者费用和离院随访。官网标价可能随院区、房型与日期变化，本页不提供实时价格或可订日期。',
  sources:[{name:'健康诊断评估 · 官方项目页',url:'https://cliniquelaprairie.com/programs/health-diagnostic/'},{name:'健康体重管理 · 官方项目页',url:'https://cliniquelaprairie.com/programs/healthy-weight/'},{name:'蒙特勒院区与环境 · 官方介绍',url:'https://cliniquelaprairie.com/destinations/switzerland-montreux/'}]
 },
 'Lanserhof':{
  checked:'2026-10-05',image:'lanserhof-sylt.webp',caption:'德国 Sylt 院区的沙丘与建筑环境；不代表 Lans 或 Tegernsee 院区。',photoSource:'https://lanserhof.com/en/lanserhof-sylt/medical-programs/essential-health-check-sylt',
  intro:'这里可以重点比较两种需求：一是围绕睡眠困扰找原因、调整日常节奏；二是在较短时间内集中评估健康状态。先确定自己希望解决的问题，再看医生、检查和后续指导是否匹配，而不是把康养体验都当作医疗治疗。',
  programmes:[
   {name:'睡眠评估与节奏调整',english:'Deep Sleep',scope:'官方睡眠专题 · 具体方案和院区需确认',description:'官网介绍从睡眠史、压力、药物与生活节奏入手，结合问卷、活动记录及按需要安排的睡眠实验室检查。核心问题是区分睡眠习惯、情绪压力与需要专科诊治的睡眠障碍，而不只是增加放松活动。',details:[['先描述睡眠的实际样子','记录入睡时间、夜间醒来、白天困倦、打鼾与咖啡因摄入。若已有呼吸暂停或正在用药，应在咨询前说明，确认是否需先到当地睡眠专科。'],['把评估转成日常安排','页面介绍日光、餐食与运动节奏、睡眠卫生指导、放松训练，并提及失眠认知行为治疗相关元素。需要询问实际由谁实施、包含多少次和如何评估改善。'],['不同方案不能混为一谈','专题列有较长的 Neuro Sleep Reset 与 Sylt 的短期 Neuro Sleep Compact。神经反馈、输注等附加项目与失眠认知行为治疗的证据不同，应分别询问必要性和风险。']],question:'我的睡眠问题需要做哪类评估？返家后的睡眠计划由谁跟进，如何判断有效？'},
   {name:'Sylt 基础健康评估',english:'Essential Health Check Sylt',scope:'德国 Sylt · 天数、晚数与费用需书面确认',description:'项目页介绍医生初诊、进一步咨询与最终回顾，列有实验室及尿液检查、身体组成、握力、腹部和甲状腺超声等内容，并安排运动或放松活动。检查是否适合仍以个人评估为依据。',details:[['体能不只看体重','官网列有 VO₂max 结果解读、握力与身体组成等内容。可以询问结果如何用于设定适合自己的活动目标，以及原有慢性病会怎样影响测试安排。'],['把医疗与体验分开看','按摩、冷疗等体验不等于诊断或疾病治疗。比较报价时，区分医生时间、检查、康养体验和可选加项，避免只看项目数量。'],['先确认实际停留安排','同一网页的标题、正文和预订选项对天数、晚数及价格呈现不一致，因此此处不写固定行程。请机构出具逐日安排与明确报价后再考虑交通住宿。']],question:'请确认实际住几晚，以及住宿、医疗值班费用和额外检查是否包含在总价里。'}
  ],
  decision:'若主要是长期睡不好，先问睡眠评估能否识别需要专科处理的问题；若只是希望集中回顾健康状态，可比较 Sylt 的短期评估。不同院区团队与设备不应默认相同。',
  cautions:'长期失眠、明显打鼾伴呼吸暂停或严重白天嗜睡应优先正规诊治。限制饮食、禁食、冷疗和输注等项目需分别评估适用性；“排毒”“再生”或生物年龄相关宣传不能作为已证实抗衰疗效。',
  costs:'Sylt 项目页说明住宿另计，药物与补充剂不包含在项目价内，并有每日医疗值班费用；未使用服务的处理也有约定。先拿到含税总价、包含项、可选项及取消政策，再比较，不沿用网页中不一致的价格选项。',
  sources:[{name:'Deep Sleep · 官方睡眠专题',url:'https://lanserhof.com/en/focus-areas/deep-sleep'},{name:'Essential Health Check Sylt · 官方项目页',url:'https://lanserhof.com/en/lanserhof-sylt/medical-programs/essential-health-check-sylt'}]
 }
};
function clinicPhoto(c){const g=clinicGuides[c.name];return g?`<figure class="clinic-photo"><img src="/static/assets/clinics/${g.image}" alt="${esc(g.caption)}" width="${c.name==='Lanserhof'?1600:1024}" height="${c.name==='Lanserhof'?1600:682}" loading="lazy"><figcaption>${esc(g.caption)} <a href="${g.photoSource}" target="_blank" rel="noopener noreferrer">图片来源 ↗</a></figcaption></figure>`:''}
function clinicProgrammeGuide(c){const g=clinicGuides[c.name];if(!g)return '';
 return `<section class="clinic-programmes"><h2>先看懂两种不同的健康目标</h2><p>${g.intro}</p>${g.programmes.map((p,i)=>`<article class="guide-day"><span class="chip">0${i+1} · ${p.english}</span><h3>${p.name}</h3><p><strong>${p.scope}</strong></p><p>${p.description}</p>${p.details.map(([title,body])=>`<h4>${title}</h4><p>${body}</p>`).join('')}<div class="guide-practical"><strong>咨询时可以这样问</strong><p>${p.question}</p></div></article>`).join('')}<h3>怎么选择更适合自己的方向</h3><p>${g.decision}</p><h3>费用怎么比较</h3><p>${g.costs}</p><h3>哪些情况要先与医生讨论</h3><p>${g.cautions}</p></section>`
}
function clinicSources(c){const g=clinicGuides[c.name];return g?`<section class="clinic-sources"><h2>继续阅读官方资料</h2><p>核对日期：${g.checked}。以上为官方商业项目介绍的中文整理，不是独立疗效研究，也不是已确认的预订套餐。</p><ul>${g.sources.map(s=>`<li><a href="${s.url}" target="_blank" rel="noopener noreferrer">${s.name} ↗</a></li>`).join('')}</ul></section>`:''}
function clinicChatReference(c){const g=clinicGuides[c.name];return {name:c.name,locations:c.label,summary:c.lead,evidenceStatus:g?'官方商业项目介绍的中文整理，非独立疗效证据':c.name==='SHA'?'本轮官网访问受限；既有概述不能视为最新已核实服务':'仅用户提供名称与城市，资质地址服务尚未核实',checked:g?.checked||null,programmes:g?g.programmes.map(p=>({name:p.name,scope:p.scope,description:p.description,question:p.question})):[],decision:g?.decision||c.strength,costs:g?.costs||'费用待机构确认',cautions:g?.cautions||c.ask,limits:c.limit,sources:g?.sources||[],bookingStatus:'尚未建立平台合作；无实时价格或可订日期，不可代为预约或联系机构。检查和医疗适用性需医生评估。'}}
