"""Validate model-produced analysis before rendering structured method cards."""
import json
import re
from content_modules import clean_module

SECTIONS = {'audience':'主题与受众','hook':'标题与开篇','structure':'框架与逻辑',
            'evidence':'论证与价值','ending':'结尾与行动','expression':'表达方式',
            'reuse':'企业复用模板','limits':'适用边界与待补事实'}

INSTRUCTION = '''仅拆解方法，不复述长篇原文。输出一个 JSON 对象，不加 Markdown 围栏。
sections 包含八个字符串字段：audience、hook、structure、evidence、ending、expression、reuse、limits。
每个字段用简洁中文给出“观察到的方法→为何有用（推测）→本企业怎么复用”。
structure 必须覆盖开头、中段和结尾；视频仅按提供的字幕分析节奏，未提供画面不得声称看过。
excerpts 是至多4项的数组，每项包含 text（原文中准确连续的短片段，最多100字）和 timestamp（仅当输入明确含该时间码时填写，否则空字符串）。
不要编造引语、时间戳、传播数据或高流量结论。不要将参考作者的企业事实写成本企业事实。
reuse 用占位符表达可复用模板，如【客户问题】【已核准事实】【适用条件】，避免复制原作者独特句子。
顶层必须同时包含 sections、excerpts、modules 三个字段。sections 是报告概览，不能替代 modules。
modules 数组（最多20项）是用于保存和再次创作的独立方法。只要有原文支持的可复用方法，就输出对应模块；仅在无可提炼方法时返回空数组，不为凑数补全全部分类。
category 从 topic选题、title标题、opening开篇、structure框架、evidence论证、expression表达、ending结尾、template模板、storyboard视频节奏、limits边界 中选择；标题与开篇必须分开。
每项必须包含 category（上述英文分类键，如 "opening"，不填写中文类别名），title（120字内的具体名称），body（方法与价值，5000字内），template（可替换占位符模板，3000字内），scenario（适用场景与限制，1000字内），tags（200字内），excerpt（可选，原文连续短片段，不超过300字）。不支持的模块不输出，不编造原文。
modules 单项形状：{"category":"opening","title":"方法名称","body":"观察到的方法与价值","template":"【客户问题】→【判断条件】","scenario":"适用场景及边界","tags":"方法标签","excerpt":""}。这是字段示例，不是来源证据；不得将示例作为实际拆解内容。
每个模块增加 excerpt_source：title 表示摘录来自输入的参考标题，body 表示来自正文；excerpt 必须是对应字段里的连续片段，不能将标题与正文拼接成引语。
提交前核对：category 为英文键；title/body 非空；标题与开篇各自独立；template 使用变量表达方法，scenario 说明适用条件；原文不支持时明确缺口，不能臆造。'''


def structured_analysis(answer, source, source_title=""):
    cleaned=re.sub(r'^```(?:json)?\s*|\s*```$', '', answer.strip())
    try: data=json.loads(cleaned)
    except (ValueError,TypeError): return None
    if not isinstance(data,dict) or not isinstance(data.get('sections'),dict): return None
    sections=data['sections']
    if any(not isinstance(sections.get(k),str) or not sections[k].strip() or len(sections[k])>5000 for k in SECTIONS): return None
    excerpts=[]
    for item in data.get('excerpts',[])[:4] if isinstance(data.get('excerpts'),list) else []:
        if not isinstance(item,dict): continue
        quote=item.get('text','');stamp=item.get('timestamp','')
        if not isinstance(quote,str) or not 1<=len(quote)<=100 or quote not in source: continue
        # A timecode must co-occur with its quote in the same source line.
        valid_stamp=isinstance(stamp,str) and re.fullmatch(r'(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[,.]\d{3})?',stamp)
        if stamp and (not valid_stamp or not any(stamp in line and quote in line for line in source.splitlines())): stamp=''
        excerpts.append({'text':quote,'timestamp':stamp or ''})
    modules=[]
    for item in data.get('modules',[])[:20] if isinstance(data.get('modules'),list) else []:
        try: modules.append(clean_module(item,source,source_title))
        except ValueError: continue
    return {'sections':{k:sections[k].strip() for k in SECTIONS},'excerpts':excerpts,'modules':modules}


def analysis_text(data):
    return '\n\n'.join('## '+label+'\n'+data['sections'][key] for key,label in SECTIONS.items())
