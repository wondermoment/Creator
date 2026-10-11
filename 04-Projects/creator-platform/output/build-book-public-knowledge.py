"""Build an editorial reference layer from the saved, actually fetched sources.
No book fulltext is imported and no user library is modified.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT / 'output' / name).read_text(encoding='utf-8'))

catalog = read('book-research-catalog.json')
weread = read('book-public-weread.json')
authorities = read('book-public-authorities.json')
papers = read('book-public-papers.json')
sources = {}
authority_notes = {
 'physical-activity': 'WHO将身体活动与心血管、代谢、心理和功能健康联系起来；任何活动优于不活动，应按能力循序增加。一般建议不等于个体运动处方。',
 'healthy-diet': 'WHO强调充足、平衡、适度、多样的饮食，增加蔬果、豆类与全谷物，限制盐、游离糖及不健康脂肪；整体模式比单一超级食物重要。',
 'aging-health': 'WHO以功能能力理解健康老龄化，内在能力与环境共同决定生活能力，不能只按年龄或一个生物标志物判断。',
 'meditation-safety': 'NCCIH介绍冥想对部分身心结局的研究，也指出研究质量和安全资料有限，有人出现焦虑等负面体验；不能取代常规医疗。',
 'genes': '基因是遗传的基本单位，部分基因指导蛋白质合成，也有基因产生功能性RNA；基因、调控和环境共同影响表型。',
 'dna': 'DNA储存遗传信息，碱基序列与双链结构支持信息复制；识别遗传变异不等于能预测所有疾病。',
 'epigenetics': '表观遗传调控改变基因活动而不改变DNA序列；不同细胞和环境会影响调控状态，不代表意念能随意改写疾病结局。',
 'noncoding': '非编码DNA不提供蛋白质合成指令，但其中一部分参与调控、功能RNA和染色体结构；不能推断全部非编码区都有已知功能。',
 'cells': '细胞是生命的基本结构和功能单位；细胞器分工进行营养利用、能量转化、遗传信息保存与物质处理。',
 'endocrine': '激素是化学信使；过多、过少或组织反应异常都可能导致疾病，症状不能直接等同某种激素缺乏。',
 'telomere-nobel': '2009年诺贝尔生理学或医学奖表彰端粒和端粒酶保护染色体的发现；获奖机制不是延寿产品的疗效证明。',
 'enzyme-nobel': '1946年诺贝尔化学奖涉及酶可结晶及酶、病毒蛋白纯化的发现；历史贡献不构成口服酵素的健康功效证据。',
 'chinese-medicine': 'NCCIH分别讨论针灸、太极、中草药的证据与风险；不同措施证据不同，草药质量、污染和药物相互作用需关注。',
 'cancer-prevention': 'NCI介绍生活方式、环境暴露与部分疫苗等癌症风险因素和预防措施；风险可降低，不能保证不患癌。',
 'synthetic-biology': 'NHGRI将合成生物学描述为为有用目的重新设计生物体，涉及医药、农业与制造；工程潜力需与生物安全和伦理共同评估。',
 'circadian': 'NIGMS介绍约24小时生物节律；光暗是重要线索，进食、活动等也会影响节律。机制知识不等于自行调整药物服用时间。',
}
for key, note in authority_notes.items():
    raw = authorities[key]
    assert raw.get('text') and not raw.get('error')
    sources[key] = dict(title=raw['title'].strip(), url=raw['url'], checked=raw['checked'], kind='institution_public_page', scope='已读取机构公开科普页面；中文为编辑概述', note=note)

paper_notes = {
 'aging': '2023年综述提出相互关联的12项衰老标志，涵盖基因组、端粒、表观遗传、蛋白稳态、自噬、营养感知、线粒体、细胞衰老、干细胞、细胞通讯、炎症与菌群。机制综述不是人体延寿疗效试验。',
 'exercise-brain': '120名老年人的随机试验观察到有氧运动组前部海马体积与空间记忆变化；特定人群的结果不能推广为运动治愈所有心理问题。',
 'meditation': '47项试验、3515人的系统综述发现部分焦虑、抑郁、疼痛结局有小到中等改善；没有证明冥想优于所有积极治疗。',
 'microbiome-diet': '17周健康成人饮食试验每组18人；发酵食物组的菌群多样性及部分炎症标志物发生变化，纤维组反应有差异，未测量延寿。',
 'calorie-restriction': 'CALERIE的220名非肥胖成人两年试验事后分析发现DunedinPACE小幅变化，PhenoAge和GrimAge未显著改变；没有人体寿命结局，不支持所有人自行限热量。',
}
for key, note in paper_notes.items():
    raw = papers[key]['records'][0]
    sources['paper-'+key] = dict(title=raw['title'], url=raw['url'], checked=papers[key]['checked'], kind='paper_abstract', scope='仅核对Europe PMC期刊摘要，未审阅全文', note=note, doi=raw['doi'])

# Each row: ID | conceptual framework | reading value | critical reading limit | complementary source keys.
# For topic_only entries these are study prompts, never claims about the unread book.
rows = '''
zhang-running|以跑步连接身体活动、情绪体验与日常习惯，检视速度、力量、时间和装备的常见误区。|把跑步变成可持续的生活习惯，先关注身体反馈和恢复。|公开简介不能支持把“治愈”理解为治病，也不能推导个体训练强度；疼痛与急症需停止并评估。|physical-activity,paper-exercise-brain
zhang-control|用运动、饮食、休息和心态四个维度组织精力管理，把一次性目标转为日常系统。|把精力不足拆成可以观察和调整的生活环节，而非一味增加自律。|持续疲劳或焦虑可能有临床原因；精力管理框架不能代替检查或治疗。|physical-activity,healthy-diet
new-longevity-singularity|围绕AI和长寿主题，分别核对衰老机制、预测指标、临床干预和真实健康结局。|建立技术进展到个人决策之间的证据阶梯。|尚无本书可靠内容来源；不能把封面未来愿景当作已实现的人体延寿，更不能编造作者章节。|paper-aging,aging-health
new-noma|公开介绍按曲、康普茶、酱油、味噌、乳酸发酵、醋、鱼露及黑化果蔬展开，展示发酵如何改变风味。|从发酵类型和风味用途理解厨房技法，而不只记成品食谱。|未读取配方正文，不能猜测盐度、温度、时长或替换比例；霉变和未知发酵物不可凭试吃判断安全。|paper-microbiome-diet
new-synthetic-biology|学习生物体设计、遗传信息与工程应用之间的关系。|把生命科技拆成可检验的设计目标和应用条件。|仅有合成生物学主题资料，不能声称是本书完整框架；技术可行性不等于医疗产品有效。|synthetic-biology,dna
new-singularity-nearer|以AI、生物技术、纳米技术的指数型发展推演人机融合和社会变化。|帮助比较技术进展与线性直觉的差异，提出未来情景。|时间表和寿命预测仍是作者的未来判断，不能当作已验证事实或个人健康承诺。|synthetic-biology,aging-health
new-microbiome-master-key|从人与微生物的共生关系理解饮食、睡眠、环境和健康老龄化。|将纤维、发酵食物与长期生活环境放在同一个生态视角下考察。|特定菌群或炎症指标改变不等于延寿；益生菌效果依菌株、人群和目标不同。|paper-microbiome-diet,healthy-diet
new-what-is-health|作者以应变稳态解释大脑如何预测需求、调控能量与行为，并联系奖励和社会环境。|把健康放回资源、生活情境与社会条件中理解。|这是解释框架，不能据此把高血压、肥胖或成瘾简化成单一原因或自行停药。|endocrine,aging-health
new-super-agers|从功能能力、慢病风险与生活环境辨别健康老龄化证据。|用可保持的活动能力和生活质量评价所谓年轻化指标。|本书公开正文与具体观点尚未核实，暂提供主题学习；不能把通用老龄化知识归给作者。|aging-health,paper-aging
new-we-are-as-gods|用指数型技术和思维模型的变化讨论人类能力、资源和未来社会。|追问技术变得便宜和普及时，组织与个人的判断如何更新。|未来情景和技术乐观论不是已实现的健康效果，也需考虑分配、治理与可及性。|synthetic-biology,aging-health
new-getting-older|从功能、生活环境和个人目标讨论老龄生活的选择。|把“活得久”具体化为日常能力、参与和支持。|尚未核实本书介绍或章节；这些是主题参考，不是作者医疗建议。|aging-health
new-biomanufacturing|以生物体为工程系统理解材料、医药和制造应用。|先辨别设计目标、产物、规模化与安全约束。|只有生物制造相关机构科普，未核实本书内容；不可编造书内案例或把工程能力等同疗效。|synthetic-biology,cells
hou-1|把人类历史放入生物与文化共同演变的视角，讨论认知、农业与科学的变迁。|用跨时代框架追问合作、制度和叙事如何改变人类生活。|宏观叙事会压缩差异，不能把历史解释当作每个个体的必然规律。|genes
hou-2|从人类历史延伸到未来，讨论幸福、长生与人机关系的可能变化。|用未来问题反过来审视今天的价值选择。|思想实验和趋势推演不能当预测模型；不把未来长生当作当前医学事实。|aging-health
hou-3|通过人体各系统及科学发现理解身体如何运行。|把器官和日常体验联系起来，建立基础人体知识。|科普叙事不能替代诊断；出版后的医学更新需另外核对。|cells,endocrine
hou-4|从昼夜节律理解睡眠、活动、进食与健康的时间安排。|除了做什么，还追问何时做及节律是否稳定。|个人作息和疾病不同，不能从一般节律原理推出统一最佳时间或改药时间。|circadian
hou-5|从细胞分工、遗传信息和环境适应认识生命系统。|先建立尺度：分子、细胞、个体与环境。|书名版本和作者尚未确认，主题知识不冒充本书摘要。|cells,dna
hou-6|作者从衰老的信息与表观遗传调控角度提出延缓衰老的研究设想。|促使读者区分衰老机制是否可研究、可干预与已经临床证明。|人体逆龄和延寿尚未由这些假说证明；动物或机制结果不能推出补剂和药物方案。|paper-aging,paper-calorie-restriction
hou-7|以主动预防和健康寿命为目标，将运动、营养、风险管理与情绪健康联系起来。|把年老时想保留的能力提前变为可持续行动。|个人化医学讨论不等于人人需要相同筛查或检测；成本、误报与个体风险需权衡。|physical-activity,aging-health
hou-8|以衰老生物学研究说明多个细胞和分子机制可能成为干预目标。|把衰老视为可研究的问题，比较不同干预的证据成熟度。|实验室有希望不等于人类已可用，临床有效性和安全性需分开验证。|paper-aging
hou-9|讨论未来寿命变化以及个人生活、健康与社会安排的准备。|提前思考更长生命可能带来的生活规划问题。|未来技术预测和健康建议证据等级不同，不能保证读者达到某个寿命。|aging-health,paper-aging
hou-10|围绕饮食及衰老相关机制讨论生活方式选择。|把日常食物选择与长期风险联系，并追问研究支持什么结局。|膳食模式的健康证据不能自动延伸为单一成分、补剂或自噬机制的延寿承诺。|healthy-diet,paper-aging
hou-11|从活动、膳食和环境支持理解可持续健康习惯。|以容易坚持、可以观察的行动代替追逐单一抗衰秘诀。|作者版本未核实，当前是习惯主题资料，不是本书的具体方法清单。|physical-activity,healthy-diet,aging-health
hou-12|公开介绍涵盖衰老概念、测量、演化、细胞遗传学、生理疾病及干预研究。|用多层尺度分析衰老，不将一个标志物等同整个衰老过程。|教材也有出版时限，干预结论应核对新研究及其物种、人群和终点。|paper-aging
hou-13|通过遗传学历史及人类经验讨论基因、疾病、身份和伦理。|同时思考遗传信息的解释力与被误用的风险。|基因并非命运，单基因解释不能套用到复杂行为和多数慢病。|genes,dna
hou-14|解释DNA序列之外的基因活动调控及其科学发展。|区分遗传编码与何时何处表达，让环境影响有机制层解释。|表观遗传不是随心所欲改写DNA，跨代和生活干预结论需逐项核对。|epigenetics
hou-15|通过DNA相关发现理解生命信息和遗传学的科学历程。|把分子结构、信息复制与生物学解释联系起来。|历史叙述与当代临床应用要区分，遗传检测解释需要当前证据。|dna,genes
hou-16|讨论非编码DNA及其调控等作用，挑战“没有蛋白编码就没有价值”的直觉。|帮助理解基因组调控不能只看蛋白质编码区。|不能从部分非编码序列有功能推断全部序列均有已知功能。|noncoding
hou-17|以细胞发现和医学史理解生命协作、功能失常与治疗探索。|从器官病名回到细胞之间如何协同工作。|细胞治疗的前景不代表每种商业细胞项目都获证实或适用。|cells
hou-18|从细胞器、分工、能量转化和遗传信息认识细胞。|将细胞看作多个过程协作的系统。|本书介绍未核实，当前用机构基础材料教学，不编造作者故事。|cells
hou-19|图书馆书目介绍将线粒体与能量、演化、繁殖和衰老等问题联系起来。|用能量约束理解生命复杂性，而不是只把线粒体当“电池”。|跨演化尺度的解释不等于人体疾病已可用单一线粒体疗法解决。|cells,paper-aging
hou-20|从端粒研究延伸到压力、生活方式与环境的健康讨论。|把细胞研究与长期生活条件联系，同时关注测量的意义。|端粒长度不是个人寿命计算器，诺贝尔奖不为端粒酶或抗衰商品背书。|telomere-nobel,paper-aging
hou-21|作者提出从代谢和线粒体功能理解精神障碍的假说。|将精神健康与身体能量代谢联系，提出可继续验证的问题。|不是所有精神疾病统一病因的共识；不可据书停精神科药物或自行生酮治疗。|cells
hou-22|从食物、营养素到代谢过程和健康结局建立分层解释。|判断分子机制能否被人体饮食研究支持。|本书版本与内容未核实，机制不能直接推导补剂剂量和延寿效果。|healthy-diet,cells
hou-23|先以膳食、活动、环境和疾病风险为主题建立证据核对框架。|将生活史作为问题背景，再用可验证的结局评价干预。|本书具体框架未核实；不可将“根源”叙事等同所有功能医学检测或补剂有效。|healthy-diet,physical-activity
hou-24|通过癌症科学与治疗史理解疾病、研究和患者体验的关系。|认识癌症治疗是多条路径不断检验的过程。|不是个人治疗指南；不同癌种和分期不能共用一个饮食或治疗答案。|cancer-prevention
hou-25|从可改变暴露、生活方式和有证据的预防措施理解癌症风险。|区分风险降低、筛查早发现与治疗三个不同目的。|本书版本未核实；抗癌食物和零风险承诺不受这些资料支持。|cancer-prevention
hou-26|医学教材系统讨论激素、内分泌器官及相关疾病。|从反馈调节和组织反应理解症状与检验为何需结合解读。|当前公开书目为第11版；旧教材不能当现行处方依据，也不混用其他版章节页码。|endocrine
hou-27|作者以胰岛素抵抗为中心讨论代谢异常及其与疾病的联系。|认识同一个代谢环节可能参与多种健康问题。|中心视角不等于所有疾病只有一个原因；不能据此自行停药、极端限碳。|endocrine,healthy-diet
hou-28|从细胞能量利用、激素信号和组织反应学习代谢调节。|追问同一营养状态下不同组织如何分工。|未核实该书具体内容和版本；主题知识不冒充教材原文。|cells,endocrine
hou-29|用酶结晶和纯化的科学史讨论如何建立可检验的生化知识。|关注研究者怎样把活性现象变成可研究的物质。|未核实书目作者，诺贝尔发现不为商业酵素保健品背书。|enzyme-nobel
hou-30|结合书封指向的基因编辑主题，先学习DNA信息、工程设计与验证之间的关系。|区分遗传信息的改变、细胞层面结果与实际应用目标。|图示为酶学方法系列的基因编辑相关分册，具体版本和章节未核实；机构科普不提供实验方案，也不等于本书摘要。|dna,synthetic-biology
hou-31|通过先天和适应性免疫、抗体、信号与免疫异常认识防御系统。|把免疫理解为识别和调节的协作，而不是越强越好。|“增强免疫”不是通用治疗目标；感染、自身免疫和过敏需不同处理。|cells
hou-32|围绕食物、微生物与慢性炎症讨论疾病风险。|将免疫状态放入饮食和生活环境中理解。|疲劳不能自行诊断慢性炎症；饮食试验中的指标变化不等于已治病或延寿。|paper-microbiome-diet,healthy-diet
hou-33|学习整体膳食模式、代谢和炎症标志物之间的证据层次。|先找人体结局，再判断个性化饮食说法是否可靠。|本书具体方案未核实；不能认可“根源逆转慢病”的普遍疗效。|healthy-diet,paper-microbiome-diet
hou-34|从菌群、宿主和衰老标志的关联学习肠道与老龄化研究。|区分观察关联、机制推测与人群干预结果。|书目版本未核实；菌群多样性增加不自动等于人寿命延长。|paper-microbiome-diet,paper-aging
hou-35|从膳食干预与个体菌群反应差异理解精准营养问题。|认识相同饮食在不同人群可能产生不同指标变化。|书目版本未核实；商业菌群检测不能据此保证给出唯一正确食谱。|paper-microbiome-diet,healthy-diet
hou-36|以肠道、饮食和宿主反应为主题建立可验证的问题。|区分“第二大脑”的比喻和有具体测量的人体研究。|同名版本未确认，不假定作者；当前资料不支持精确章节或将情绪全部归因肠道。|paper-microbiome-diet
hou-37|公开书目介绍从饮食、睡眠、压力和肠道皮肤联系讨论护肤。|提醒读者把皮肤放入整体生活背景中理解。|标题中的百分比不是对所有皮肤病的治愈率；不能取代皮肤科评估或保证靠营养修复。|healthy-diet
hou-38|逐项比较中医相关措施与常规临床证据、安全和适用性。|把针灸、太极和草药分开评价，避免笼统判定。|作者版本未核实，不能提供该书临床方剂；草药与处方药相互作用需专业核对。|chinese-medicine
hou-39|讨论身体活动与学习、情绪及脑功能的联系。|将运动作为支持脑健康的日常行为，并比较不同研究结局。|不能接受宣传中“解决99%内耗”等概括；老年人海马试验不等于所有人或所有精神问题有效。|paper-exercise-brain,physical-activity
hou-40|从情绪、身体体验与压力调节出发，学习可观察的身心关系。|允许觉察体验，同时对身体症状保留医学评估。|作者版本未核实；不能把疾病归咎于情绪或把“排毒”当医学机制。|meditation-safety,paper-meditation
hou-41|以PERMA组织幸福：积极情绪、投入、关系、意义和成就。|将幸福从单一开心扩展为多维生活目标。|是心理学框架，不能保证消除抑郁或用积极心态否定困难。|aging-health
hou-42|公开介绍以日常觉察、艺术观看及冥想练习讨论身心放松。|让注意力回到当下体验，用温和练习观察惯性反应。|未读取具体练习全文；正念可能有负面体验，明显不适应停止并求助。|meditation-safety,paper-meditation
hou-43|以当下觉察讨论人与思维、情绪及自我叙事的关系。|练习观察思维而非自动认同每个念头。|属于精神哲学和体验指导，不能当临床疗效证明，也不应忽视现实问题。|meditation-safety
hou-44|先区分可测量的细胞能量代谢、主观精力与日常恢复。|用清楚定义避免把物理能量、疲劳和灵性隐喻混为一谈。|作者版本未核实，不把“能量频率”等说法当已证实医学机制或归给本书。|cells,physical-activity
'''.strip().splitlines()

books = {}
by_id = {b['id']: b for b in catalog}
for row in rows:
    book_id, framework, value, limits, keys = row.split('|')
    book = by_id[book_id]
    source_ids = keys.split(',')
    basis = 'topic_only'
    if book_id in weread:
        raw = weread[book_id]
        key = 'book-'+book_id
        sources[key] = dict(title=book['title']+' · 微信读书公开介绍', url=raw['url'], checked=raw['checked'], kind='book_public_description', scope='公开图书介绍，含出版宣传；未读取全文，不作独立科学证据', note=framework)
        source_ids.insert(0,key)
        basis='book_public_overview'
    elif book_id in ('hou-19','hou-37'):
        raw = read('book-public-research/'+book_id+'.json')['sources'][0]
        assert raw.get('description')
        key='book-'+book_id
        sources[key] = dict(title=raw['title']+' · Open Library书目介绍',url=raw['url'],checked='2026-10-06',kind='library_description',scope='原版图书书目介绍，未核对中文译本全文或页码',note=framework)
        source_ids.insert(0,key)
        basis='book_public_overview'
    books[book_id] = dict(title=book['title'],author=book.get('author','待核实'),basis=basis,
        framework=framework,reading_value=value,critical_reading=limits,source_ids=source_ids,
        replacement='用户上传原文后优先原文检索；本层保留为公开参考，不冒充全文Skill')

assert set(books)==set(by_id),set(by_id)-set(books)
payload=dict(version='2026-10-06-public-v1',layer='public_reference',books=books,sources=sources)
path=ROOT/'backend/app/book_public_knowledge.json'
path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'books':len(books),'book_overviews':sum(b['basis']=='book_public_overview' for b in books.values()),'topic_only':sum(b['basis']=='topic_only' for b in books.values()),'sources':len(sources)}))
