// 项目与截图价格由用户提供；价格口径确认前不推算原价。
const testingPriceMode="pending";
const testingItems=[
  {
    "id": "test-chronic",
    "name": "慢病风险四项",
    "sourcePrice": 325,
    "topic": "基础指标",
    "note": "糖化血红蛋白、维生素 D、同型半胱氨酸、尿酸。需结合病史及其他检查解读，不能覆盖所有慢病风险。"
  },
  {
    "id": "test-amh",
    "name": "卵巢年龄评估（AMH）",
    "sourcePrice": 210,
    "topic": "激素评估",
    "note": "AMH 可辅助评估卵巢储备，不能直接等同于卵巢年龄，也不能单独预测自然受孕机会。"
  },
  {
    "id": "test-telomere",
    "name": "端粒长度检测",
    "sourcePrice": 990,
    "topic": "衰老研究",
    "note": "了解所测样本的端粒长度。不同方法和样本存在差异，不能据此精确推算寿命或诊断衰老。"
  },
  {
    "id": "test-methylation",
    "name": "甲基化年龄检测",
    "sourcePrice": 600,
    "topic": "衰老研究",
    "note": "依据特定甲基化模型估算生物学年龄，结果依赖模型与样本，不等同于真实寿命或疾病诊断。"
  },
  {
    "id": "test-nad",
    "name": "NAD+ 检测",
    "sourcePrice": 425,
    "topic": "代谢评估",
    "note": "测量特定样本中的 NAD+ 相关指标。先确认检测方法、参考范围与临床适用性，不能凭读数自行决定输注或补充方案。"
  },
  {
    "id": "test-organic-acids",
    "name": "全套新陈代谢分析（有机酸75项）",
    "sourcePrice": 1900,
    "topic": "代谢评估",
    "note": "包含有机酸相关指标，具体清单及样本要求需确认。单项异常不能直接判定营养缺乏或疾病。"
  },
  {
    "id": "test-gut",
    "name": "医疗版肠道菌群基因测序",
    "sourcePrice": 990,
    "topic": "菌群检测",
    "note": "需填写肠道问卷；了解样本菌群组成。结果受饮食、用药和方法影响，不应单凭报告诊断或制定治疗。"
  },
  {
    "id": "test-igg",
    "name": "慢性食物敏（120种IgG）",
    "sourcePrice": 1900,
    "topic": "食物相关",
    "note": "供应目录原名。食物 IgG 阳性常反映接触或耐受，不能用于诊断食物过敏或不耐受，不据此大范围忌口。建议先咨询过敏专科。"
  },
  {
    "id": "test-oral",
    "name": "口腔菌群基因测序",
    "sourcePrice": 840,
    "topic": "菌群检测",
    "note": "了解口腔样本中菌群信息；不能替代口腔检查，也不能仅凭菌群结果确定牙周治疗方案。"
  },
  {
    "id": "test-family",
    "name": "阖家欢精准基因检测（70万位点）1980项",
    "sourcePrice": 2990,
    "topic": "基因检测",
    "note": "目录标注70万位点、1980项，具体位点、报告项目及适用人群需核实。遗传倾向不等于必然患病。"
  },
  {
    "id": "test-exome",
    "name": "个人基因组全外显子测序",
    "sourcePrice": 8000,
    "topic": "基因检测",
    "note": "聚焦外显子区域，不能检出全部遗传变异。检测前确认临床问题、覆盖范围、遗传咨询及意外发现处理。"
  },
  {
    "id": "test-genome",
    "name": "个人全基因组测序",
    "sourcePrice": 14000,
    "topic": "基因检测",
    "note": "覆盖范围较广，仍受技术和解释能力限制。需明确检测目的、数据保存、知情同意及遗传咨询安排。"
  },
  {
    "id": "test-alcohol",
    "name": "酒精代谢基因（乙醇、乙醛脱氢酶突变基因）",
    "sourcePrice": 275,
    "topic": "基因检测",
    "note": "了解部分酒精代谢相关遗传差异，不等于测出安全饮酒量，也不能证明饮酒无害。"
  },
  {
    "id": "test-mthfr",
    "name": "MTHFR基因（叶酸代谢）",
    "sourcePrice": 280,
    "topic": "基因检测",
    "note": "了解部分叶酸代谢相关位点。不能单凭基因型判断叶酸缺乏或自行增加补充剂剂量。"
  },
  {
    "id": "test-apoe",
    "name": "血脂代谢基因（APOE）",
    "sourcePrice": 280,
    "topic": "基因检测",
    "note": "APOE 与脂质代谢及某些疾病风险相关，结果不是诊断。检测前了解可能出现的风险信息及遗传咨询选择。"
  },
  {
    "id": "test-male",
    "name": "个人健康体检基因检测（57个位点男73项）",
    "sourcePrice": 600,
    "topic": "基因检测",
    "note": "目录标注男性57个位点、73项，具体项目清单需确认。风险解读需结合年龄、家族史和临床检查。"
  },
  {
    "id": "test-female",
    "name": "个人健康体检基因检测（62个位点女75项）",
    "sourcePrice": 600,
    "topic": "基因检测",
    "note": "目录标注女性62个位点、75项，具体项目清单需确认。基因检测不能代替常规体检和筛查。"
  },
  {
    "id": "test-vitd",
    "name": "25羟基维生素D",
    "sourcePrice": 150,
    "topic": "营养评估",
    "note": "常用于评估维生素 D 状态。是否需要检测及如何解读，应结合个人风险、症状和专业建议。"
  },
  {
    "id": "test-liver",
    "name": "肝脏健康评估",
    "sourcePrice": 990,
    "topic": "健康评估",
    "note": "结合检测指标、症状和用药背景了解肝脏健康。具体检查组合与解读服务需先核实，单项结果不能确定病因或换算排毒能力。"
  },
  {
    "id": "test-immune",
    "name": "免疫年龄评估",
    "sourcePrice": 990,
    "topic": "衰老研究",
    "note": "需确认评估指标、模型及参考人群。“免疫年龄”并非统一临床诊断标准，不能据此保证抗感染能力。"
  },
  {
    "id": "test-stress",
    "name": "抗压力荷尔蒙评估",
    "sourcePrice": 1250,
    "topic": "激素评估",
    "note": "需确认具体激素指标、采样时间及方法。激素可随昼夜节律、药物和身体状态变化，单次结果不代表抗压能力。"
  },
  {
    "id": "test-environment",
    "name": "环境荷尔蒙",
    "sourcePrice": 1150,
    "topic": "暴露评估",
    "note": "需确认所测物质、样本及检出限。检出不等于已造成健康损害，不凭报告自行使用排毒或螯合治疗。"
  },
  {
    "id": "test-estrogen",
    "name": "雌激素代谢分析",
    "sourcePrice": 1050,
    "topic": "激素评估",
    "note": "了解具体雌激素代谢相关指标，先确认样本及适用场景。结果受生理阶段和用药影响，不自行调整激素用药。"
  },
  {
    "id": "test-elements",
    "name": "营养与重毒性元素分析（39项+6项比值）",
    "sourcePrice": 600,
    "topic": "营养评估",
    "note": "目录标注39项与6项比值，具体元素及样本需确认。不能用比值单独诊断缺乏、中毒或决定补充方案。"
  },
  {
    "id": "test-ige",
    "name": "急性食物过敏（39种IgE+总IgE）",
    "sourcePrice": 600,
    "topic": "食物相关",
    "note": "特异性 IgE 可辅助评估致敏情况，阳性不一定意味着临床过敏，需结合反应史由医生解读。出现呼吸困难等急症应立即就医。"
  }
] ;
function testingPrice(p){if(testingPriceMode==='pending')return '<p class="testing-price-pending">活动价格核对中</p>';const original=testingPriceMode==='original'?p.sourcePrice:p.sourcePrice*2;const sale=original/2;const money=n=>n.toLocaleString('zh-CN',{maximumFractionDigits:2});return `<div class="testing-price"><strong>¥${money(sale)}</strong><span class="testing-discount">5折</span><del>原价 ¥${money(original)}</del></div>`}
function testingArtwork(p){const themes={'基础指标':'biomarkers','基因检测':'genetics','衰老研究':'genetics','菌群检测':'microbiome','营养评估':'nutrition','代谢评估':'metabolism','激素评估':'hormones','食物相关':'foods','健康评估':'liver','暴露评估':'environment'};const science=typeof testingScience==='undefined'?null:testingScience[p.id];const file=science?science.image:(themes[p.topic]||'biomarkers')+'.webp';return `<figure class="testing-artwork" style="margin:0;background:#f4f0f8"><img src="/static/assets/testing/${file}" alt="${esc(science?science.title+'科普图：'+science.points.map(x=>x[0]).join('、')+'；'+science.limit:p.name+'相关主题插画')}" loading="lazy" width="1254" height="1254" style="display:block;width:100%;height:auto;aspect-ratio:1;object-fit:contain"><figcaption style="padding:4px 14px 8px;font-size:11px;color:#766b84">${esc(science?'原理示意 · 非个人报告 · '+science.limit:p.topic+' · 主题示意')}</figcaption></figure>`}

function testingCards(){return `<p class="shop-category-note">按检测方向了解项目，预约前由客服核对服务机构、采样要求与报告范围。</p>${testingItems.map((p,i)=>`<article class="shop-card testing-card">${testingArtwork(p)}<div class="journey-body"><span class="journey-location">${p.topic}</span><h3><a href="#shop/${p.id}">${p.name}</a></h3><p>${p.note}</p>${testingPrice(p)}<div class="journey-bottom"><a class="guide-link" href="#shop/${p.id}">了解检测 →</a><button class="primary" data-testing-buy="${p.id}">直接购买</button></div><div class="actions"><button class="secondary full" data-service-inquiry="${p.name}预约咨询">预约了解详情</button></div></div></article>`).join('')}`}
function testingDetail(p){return `<a href="#shop" class="travel-back">← 返回好物商城</a><article class="travel-detail">${testingArtwork(p)}<div class="detail-body"><span class="eyebrow">精准检测 / ${p.topic}</span><h1>${p.name}</h1>${testingPrice(p)}<section><h2>这个项目了解什么</h2><p>${p.note}</p></section>${typeof testingScienceGuide==='function'?testingScienceGuide(p):''}<section class="lifestyle-note"><h2>预约前，帮你核对清楚</h2><p>由平台客服确认承接机构、项目清单、采样方式、是否空腹、报告周期，以及费用是否包含采样、寄送与解读。未核实的信息以确认结果为准。</p></section><section><h2>检测与报告解读</h2><p>检测应结合个人需要选择。结果不等于疾病诊断，异常结果由相应专业人员进一步评估；基因项目还需确认知情同意和数据隐私安排。</p></section><button class="primary full" data-testing-buy="${p.id}">直接购买</button><button class="secondary full" data-service-inquiry="${p.name}预约咨询">预约了解详情</button><p class="small muted">当前提供项目展示与站内咨询，尚未开通检测付款和机构预约确认。</p></div></article>`}

function testingBuy(id){const p=testingItems.find(x=>x.id===id);if(!p)return;showForm('购买检测 · '+p.name,`<p>${esc(p.note)}</p>${testingPrice(p)}<p class="notice">该项目暂未开通购买。价格、承接机构和采样服务待确认，正式支付尚未接通。</p><p>确认服务包含的项目、采样方式、报告周期与退款规则后，才能支付。当前不会创建订单或扣款。</p>`,'向智能客服了解',()=>openServiceChat(p.name+'预约咨询'),{local:true});document.getElementById('form').onsubmit=e=>{e.preventDefault();openServiceChat(p.name+'预约咨询')}}
document.addEventListener('click',e=>{const b=e.target.closest('[data-testing-buy]');if(b)testingBuy(b.dataset.testingBuy)});
