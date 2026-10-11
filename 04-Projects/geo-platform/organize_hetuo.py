"""Source-linked extraction drafts and asset collections for the authorized pilot."""
import server as s
from import_hetuo import BATCH

def run():
    with s.db() as c:
        p=c.execute('SELECT id FROM projects WHERE name=?',('和拓实业',)).fetchall()
        if len(p)!=1: raise RuntimeError('样板项目不唯一')
        pid=p[0][0]; docs=s.items(c,pid,'knowledge'); by_id={k['id']:k for k in docs}
        for a in s.items(c,pid,'asset'):
            refs=a.get('source_refs',[]); origin=' '.join(str(r) for r in refs)
            linked=[by_id[k] for k in by_id if by_id[k].get('asset_id') in [r.get('document_asset') for r in refs]]
            if '宣传册2025' in origin: collection='宣传册原页'
            elif '用户意图.xlsx' in origin: collection='用户意图'
            elif any(k['category']=='待发布原稿' for k in linked) or '文章合集-0915' in origin: collection='待发布原稿与配图'
            elif '和拓公众号' in origin: collection='历史品牌文章与配图'
            elif any('.pptx' in k.get('source','') for k in linked) or '.pptx' in origin: collection='企业与产品演示资料'
            else: collection='企业品牌与技术资料'
            a['collection']=collection
            a['tags']=['和拓实业','HEROTO',collection]
            a['related_knowledge_ids']=list(dict.fromkeys([k['id'] for k in linked]+[r['knowledge_id'] for r in refs if r.get('knowledge_id')]))
            a['description']='原始资料，保留来源与版本；图片中的参数与效果表述需结合技术资料核准。' if a['category']=='图片' else '客户提供原文件，可下载查阅；提取文本在企业知识库。'
            s.put(c,pid,'asset',a,a['id'])
        def match(*parts): return [k['id'] for k in docs if any(t in k['title'] for t in parts) and not k.get('derived')]
        drafts=[
            ('和拓品牌内核与表达规范 · 提炼稿','品牌档案',match('企业综合介绍','公司介绍','和拓宣传册'),
             '主体：和拓实业（上海）有限公司。品牌：和拓化学 / HEROTO。来源为企业自述，企业名称与品牌关系待客户核准。\n\n核心表达：让表面处理更简单、更环保。面向制造业采购、工艺、品质与环保负责人，以具体工况、适用条件、验证过程解释技术价值。\n\n品牌范围：卷材、涂装前处理、塑性加工、机械加工、水处理。硅晶是重点产品方向，不等同于企业全部业务。\n\n内容顺序：客户问题 → 工况边界 → 方案与产品 → 可验证证据 → 小试与导入建议。禁止把宣传稿中的数字当作无条件承诺。'),
            ('和拓五大产品线与选型索引 · 提炼稿','产品',match('宣传册','企业综合介绍'),
             '1. 卷材：卷钢、卷铝处理；清洗、轧制润滑、硅晶及自动检测加药。\n2. 涂装前处理：清洗、硅烷、硅晶等，按基材、油污、工艺方式及涂层体系选型。\n3. 塑性加工：一液型润滑剂、活性拉拔油。\n4. 机械加工：金属加工液、硅基切割液、清洗与防锈。\n5. 水处理：油漆废水与冷却循环水。\n\n宣传册原图10（印刷页17–18）列出的硅晶型号：B-8810、B-8501、B-8506、B-8507。用途、温度、浸泡/喷淋/擦洗条件请逐项对照原图，不跨型号合并。\n\n这是导航索引，不是替代 TDS/SDS 的产品技术规格书。'),
            ('硅晶技术证据与口径核验清单 · 提炼稿','技术资料',match('附着力0级','硅晶前处理革命','老板问得'),
             '性能：附着力0级、盐雾500/1000/1500小时必须分别绑定检测标准、基材、前处理、涂层、膜厚、划线方法与判定标准。\n\n环保：区分无漂洗工序废水、槽液维护/循环处理、固废与整厂排放。环评结论必须针对具体项目，不使用保证通过。\n\n经济：不同资料出现节水98%/99%、节电70%/70–90%、设备投入降低50%/70%等口径。暂并列保留，要求基准产线、产能、单价、测算周期，不自动选最大值。\n\n术语：核对“磷、铬、锌、锰等重金属”的分组表述、反应机理文字、不同镀层与涂装前处理的工艺边界。\n\n背书：客户名称、第三方测试、专利、资质、碳达峰政策年份应补原证据和对外使用范围。'),
            ('和拓视觉素材使用指南 · 提炼稿','品牌档案',match('和拓宣传册'),
             '品牌视觉：HEROTO 标识、蓝绿配色、白底工业信息图，依据2025宣传册原图。平台自身继续沿用既定Google配色，不替换企业素材原色。\n\n资产集：宣传册原页、待发布原稿与配图、历史品牌文章与配图、企业与产品演示资料、企业品牌与技术资料、用户意图。\n\n使用规则：优先匹配文章工况与产品；会议图片只说明对应活动，不能当作性能测试证据。不得改动证书、报告、图表中的数值。\n\n原图保留完整版本，平台封面裁切后应检查Logo、人物、数字与图注。素材版权及人物肖像使用范围由客户确认。'),
            ('首批8篇内容发布准备清单 · 提炼稿','交付规范',match('硅晶表面处理到底','掉漆','选磷化','成本中心','老板问得','附着力0级','客户最关心','2026年金属'),
             '状态：客户指定的8篇待发布稿，已保留原文并准备图文预览，不计入已发布成果。\n\n建议首批渠道：搜狐号，来自飞书待发清单；尚未绑定账号、排定时间或对外发送。\n\n客户审核：标题与品牌名称 → 参数与效果依据 → 图文对应与授权 → 咨询入口 → 最终渠道版本。\n\n审核通过后：按当前版本导出发布包/创建交付任务，记录最终地址及平台回执。浏览器草稿与正式发布必须分开。\n\n第一篇仍需回应飞书编辑意见：补充与硅烷、陶化直接比较。第六篇标题“零排放”建议按实际工况与废水管理边界调整，原稿未擅自改写。'),
            ('用户意图与内容布局 · 提炼稿','用户意图',match('用户意图'),
             '原始用户意图表逐单元格保留坐标，选题记录进入内容创作下的洞察栏目。它是策划输入，不代表平台搜索量或真实询盘数量。\n\n建议布局：基础认知、产线痛点、工艺对比、应用场景、成本落地、质检环保、供应商选择。每个选题应连接可用产品资料及待补证据，再安排创作。\n\n采购决策问题优先保留基材、涂层体系、质量标准、产能和旧线条件，避免仅围绕泛品牌词批量重复写稿。')]
        for title,category,ids,body in drafts:
            if any(k['title']==title for k in docs): continue
            s.put(c,pid,'knowledge',{'title':title,'category':category,'body':body,'source':'客户原资料交叉整理；提炼稿待客户确认','status':'pending','version':1,'derived':True,'source_ids':ids,'source_snapshots':[{'id':k,'title':by_id[k]['title'],'version':by_id[k]['version']} for k in ids],'import_batch':BATCH})
        a=s.items(c,pid,'import_batch')[0]
        a['derived_documents']=len(drafts); a['collections']=sorted(set(x.get('collection','未分类') for x in s.items(c,pid,'asset')))
        s.put(c,pid,'import_batch',a,a['id'])
        print(s.dump({'project':pid,'derived_documents':len(drafts),'collections':a['collections']}))

if __name__=='__main__': run()
