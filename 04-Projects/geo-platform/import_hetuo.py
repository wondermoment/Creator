"""Idempotent local import of user-supplied Hetuo sources. No network or publishing."""
import json
import re
from pathlib import Path
import server as s
import source_import as imp

DESKTOP=Path('C:/Users/pc02a/Desktop')
BATCH='hetuo-20261002'
ARTICLES=DESKTOP/'和拓化学文章合集-0915/和拓化学文章合集-0915'
SOCIAL=DESKTOP/'和拓公众号 文章+图/和拓公众号 文章+图'
BROCHURE=DESKTOP/'和拓宣传册2025/和拓宣传册2025'
EXTRA=['用户意图.xlsx','硅晶前处理革命 PPT 逐字稿 .docx','知识库：逐字稿-和拓宣传册.docx','硅晶涂装前处理革命-和拓化学2026.pptx','和拓企业介绍-2024版.pptx','和拓化学官网全部逐字稿.md','和拓（HEROTO）企业综合介绍-系统梳理版.docx','硅晶三折页+企业宣传单页.docx','和拓公司介绍-文字版.docx']

def run():
    sources=[(p,'待发布原稿') for p in sorted(ARTICLES.glob('*.docx')) if not p.name.startswith('~$')]
    sources += [(DESKTOP/n,'用户意图' if n.endswith('.xlsx') else '企业与产品资料') for n in EXTRA]
    sources += [(p,'历史品牌内容') for p in sorted(SOCIAL.iterdir()) if p.suffix in ('.docx','.md') and p.name!='王总访谈逐字稿.docx']
    result=[]
    with s.db() as c:
        owner=c.execute("SELECT m.user_id FROM projects p JOIN members m ON p.id=m.project_id WHERE p.name=? AND m.role='owner'",('创造者智能流',)).fetchall()
        if len(owner)!=1: raise RuntimeError('无法唯一确定当前客户空间所有者')
        actor=owner[0][0]
        existing=c.execute("SELECT p.id FROM projects p JOIN members m ON m.project_id=p.id WHERE p.name=? AND m.user_id=?",('和拓实业',actor)).fetchone()
        pid=existing[0] if existing else s.create_project(c,actor,'和拓实业','https://www.heroto.com.cn',['硅晶与硅烷、陶化有什么区别？','硅晶前处理适合哪些基材和涂层体系？','如何验证附着力与盐雾性能？','如何评估旧线改造、综合成本与废水处理？'])
        for path,category in sources:
            if not path.is_file(): raise FileNotFoundError(str(path))
            if path.name=='方案.docx':
                # Known unrelated document in the supplied folder; do not re-import on retries.
                continue
            entry=imp.ingest(vars(s),c,pid,path,category,BATCH); result.append(entry)
        # Keep every original page in order; no OCR facts invented from page images.
        brochure={}
        for n in range(1,15):
            path=BROCHURE/f'{n}.png'
            brochure[n]=imp.store_asset(vars(s),c,pid,path.read_bytes(),f'和拓宣传册2025-{n:02d}.png',{'batch':BATCH,'path':str(path),'page_image':n},'图片')
        docs={k['title']:k['id'] for k in s.items(c,pid,'knowledge')}
        for folder in sorted(SOCIAL.iterdir()):
            if not folder.is_dir(): continue
            label=folder.name.removeprefix('和拓文章配图-').removeprefix('维也纳').rstrip('·')
            kid=docs.get(label)
            for path in sorted(folder.rglob('*')):
                if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp') or not path.is_file(): continue
                raw=path.read_bytes()
                if not imp.valid_image(raw,path.suffix.lower()): continue
                imp.store_asset(vars(s),c,pid,raw,folder.name+'-'+path.name,{'batch':BATCH,'path':str(path),'article':folder.name,'knowledge_id':kid},'图片')
        # The XLSX is an editorial intent map, not evidence of actual customer enquiries.
        intent_doc=next(k for k in s.items(c,pid,'knowledge') if k['title']=='用户意图')
        for b in intent_doc['blocks']:
            if not b.get('cells') or len(b['cells'])<2: continue
            key=BATCH+':intent:'+b['location']
            if any(i.get('import_key')==key for i in s.items(c,pid,'insight')): continue
            vals={re.sub(r'\d','',x['cell']):x['value'] for x in b['cells']}
            if not re.match(r'L[123]',vals.get('B','')): continue
            s.put(c,pid,'insight',{'title':vals.get('D',vals['B'])[:180],'platform':'用户意图表 · 策划资料','url':'','question':vals.get('E','')[:3000],'keyword':vals.get('C','')[:200],'opportunity':vals.get('F','')[:1500],'cta':vals.get('G',''),'intent_code':vals['B'],'source':'customer_spreadsheet','source_id':intent_doc['id'],'source_location':b['location'],'import_key':key})
        if not s.items(c,pid,'brand'):
            s.put(c,pid,'brand',{'version':1,'status':'draft','positioning':'和拓实业（上海）有限公司 / 和拓化学 HEROTO。围绕金属表面处理提供化学品及配套技术服务。企业自述，待客户核准。','audience':'制造业采购、工艺工程师、品质及环保负责人、企业经营者。','pain_points':'掉漆返锈、盐雾验证、旧线改造、处理成本、废液维护与稳定生产。','voice':'专业、具体、克制；先解释工况与适用边界，再给方案与验证路径。','preferred':'让表面处理更简单、更环保；硅晶；涂装前处理；先小试验证，再评估导入。品牌口号源于宣传册。','forbidden':'未经证据核准不得宣称保证环评通过、适用所有金属或所有行业、无条件零排放；性能、节水节电和降本数值必须附条件。','source_ids':[r['knowledge_id'] for r in result if '宣传册' in r['title'] or '公司介绍' in r['title']]})
        for r in result[:8]:
            kid=r['knowledge_id']; k=s.resource(c,pid,kid,'knowledge')
            if any(x.get('original_knowledge_id')==kid for x in s.items(c,pid,'content')): continue
            n=int(re.match(r'(\d+)',k['title']).group(1))
            blocks=k['blocks']; body='\n\n'.join(b['text'] for b in blocks if b['text'].strip())
            # Preserve all original figures; supplement with explicitly sourced brochure images.
            supplement={1:[4],2:[5],3:[4,10],4:[5,8],5:[5],6:[5,10],7:[10],8:[3,4,10]}[n]
            figures=[{'asset_id':brochure[p],'caption':f'和拓宣传册 2025 · 原图 {p}（宣传资料，指标须另附检测或测算依据）','after':max(2,len(blocks)//(len(supplement)+1)*(j+1))} for j,p in enumerate(supplement)]
            image_ids=list(dict.fromkeys(k.get('image_ids',[])+[f['asset_id'] for f in figures]))
            sources_snapshot=[{'id':kid,'title':k['title'],'version':1,'source':k['source'],'body':k['body'],'excerpt':body[:800]}]
            notes=['本批由客户指定为待发布稿，不计入历史已发布量。','保留原文，配图与版式为本次整理；客户须核准技术与商业表述。','建议首发渠道：搜狐号（飞书待发清单）；账号、时间与接口待确认。']
            if n==1: notes.append('飞书编辑意见：补充与硅烷、陶化的直接比较；原稿未擅自改写。')
            if n==6: notes.append('标题含“零排放”：建议客户确认后改为“硅晶工艺如何验证附着力、盐雾表现与废水管理？”')
            content={'title':k['title'],'body':body,'status':'pending','revision':1,'approved_revision':None,'review_note':'','skill_name':'客户原稿 · 图文编排','skill_version':1,'prompt_snapshot':'原文导入；不调用模型补造参数。','sources':sources_snapshot,'channels':['搜狐号'],'keyword':'硅晶涂装前处理','intent':'制造业采购与技术选型','customer_question':'','scheduled':'','generator':'客户提供原稿 · 本地整理排版','history':[],'origin':'customer_prepublication','original_knowledge_id':kid,'import_batch':BATCH,'layout':{'version':1,'body_sha256':imp.hashlib.sha256(body.encode()).hexdigest(),'blocks':blocks,'figures':figures,'cover_id':brochure[1]},'review_notes':notes,'platform_payloads':{'搜狐号':{'title':k['title'],'body':body,'cover_id':brochure[1],'attachment_ids':image_ids,'cta_url':''}}}
            s.put(c,pid,'content',content)
        # Source registration is not a publication receipt.
        links=[{'name':'内容创作记录','url':'https://q1wlsi2t9ng.feishu.cn/docx/BudgdZnWAoWu93xtq8VcWfSDngg','note':'已查看目录与编辑意见；另见 0924 批 15 个标题，正文未完整提取。'}, {'name':'内容发布记录','url':'https://q1wlsi2t9ng.feishu.cn/sheets/Ikr4s9wyChl1eutGCkucWGlrnWc?sheet=c437cf','note':'顶部 8 篇搜狐稿日期及链接为空，按待发处理；下方列举网已有链接，未逐条核验，不计入本批发送。'}]
        old=s.items(c,pid,'import_batch')
        info={'batch':BATCH,'name':'和拓实业 · 真实资料样板','source_files':len(sources),'unique_documents':len(s.items(c,pid,'knowledge')),'image_assets':sum(a['category']=='图片' for a in s.items(c,pid,'asset')),'prepared_articles':8,'links':links,'notes':['官网地址来源于宣传册，未做在线权属验证。','2024 企业介绍、2025 宣传册与 2026 产品资料保留各自版本，未自动替代。','重复内容按 SHA-256 去重，来源路径保留。'],'records':result}
        s.put(c,pid,'import_batch',info,old[0]['id'] if old else None)
        s.event(c,pid,actor,'导入和拓样板资料',f'{len(sources)} 份来源文件；8 篇待客户审核稿；无对外发送')
    manifest={'project_id':pid,**info}
    (s.ROOT/'.runtime/hetuo-manifest.json').write_text(s.dump(manifest),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('records','links','notes')},ensure_ascii=False))

if __name__=='__main__': run()
