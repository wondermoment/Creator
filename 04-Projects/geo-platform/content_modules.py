"""Reusable method fragments; never promote reference material to company facts."""
MODULE_TYPES = {'topic':'选题与受众','title':'标题钩子','opening':'开篇引入',
                'structure':'内容框架','evidence':'论证与价值','expression':'表达句式',
                'ending':'结尾与行动','template':'复用模板','storyboard':'视频节奏',
                'limits':'适用边界','unclassified':'待整理'}


def clean_module(value, source, source_title=""):
    if not isinstance(value, dict) or value.get('category') not in MODULE_TYPES:
        raise ValueError('请选择有效模块分类')
    result={'category':value['category']}
    for key, limit in [('title',120),('body',5000),('template',3000),('scenario',1000),('tags',200),('excerpt',300)]:
        text=value.get(key,'')
        if not isinstance(text,str) or len(text)>limit: raise ValueError('模块字段过长或格式错误')
        result[key]=text.strip()
    if not result['title'] or not result['body']: raise ValueError('模块名称和方法内容不能为空')
    origin=value.get('excerpt_source') or ''
    if origin not in ('', 'body', 'title'): raise ValueError('请选择有效的摘录出处')
    quote=result['excerpt']
    if not origin:
        origin='body' if not quote or quote in source else 'title' if source_title and quote in source_title else 'body'
    evidence=source_title if origin=='title' else source
    if quote and quote not in evidence: raise ValueError('原文摘录必须是所选出处中的连续片段')
    result['excerpt_source']=origin
    return result


def candidates(structure, answer, source, source_title=""):
    modules=[]
    for item in (structure or {}).get('modules',[])[:20]:
        try: modules.append(clean_module(item,source,source_title))
        except ValueError: continue
    if modules: return modules
    mapping={'audience':('topic','选题与受众'),'hook':('opening','标题与开篇（待细分）'),
             'structure':('structure','内容框架'),'evidence':('evidence','论证与价值'),
             'expression':('expression','表达句式'),'ending':('ending','结尾与行动'),
             'reuse':('template','复用模板'),'limits':('limits','适用边界')}
    for key,(category,title) in mapping.items():
        body=(structure or {}).get('sections',{}).get(key,'')
        if isinstance(body,str) and body.strip():
            modules.append(clean_module({'category':category,'title':title,'body':body},source))
    # Legacy free-text output stays explicitly unclassified instead of invented splitting.
    if not modules and answer.strip():
        modules=[clean_module({'category':'unclassified','title':'原拆解待整理','body':answer[:5000]},source)]
    return modules
