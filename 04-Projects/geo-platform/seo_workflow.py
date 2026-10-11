"""Deterministic checks and actionable guidance, not a ranking score."""
import re
GUIDES = {
    '页面索引指令': ('P0', '先确认此页面是否应该出现在搜索结果。若是公开产品或资料页，核对是否误设 noindex；私有或重复页面可有意保留。', '检查 CMS 的搜索可见性与 meta robots，必要时由网站管理员调整；本项不代表 robots.txt、HTTP响应头或搜索引擎已经收录。'),
    '移动端视口': ('P1', '为响应式页面设置 viewport，并在手机上人工检查阅读、缩放和横向溢出。', '通常使用 meta name="viewport" content="width=device-width, initial-scale=1"。存在声明不等于移动端体验已经验收。'),
    '页面语言': ('P2', '声明页面正文的主要语言，帮助工具正确理解内容。', '在 html 标签填写适用的 lang，例如中文 zh-CN。多语言 hreflang 关系需另行核对。'),
    '页面标题': ('P1', '为这个页面设置独有的 title，概括主题与用户问题，再自然带上企业名。不要重复堆词。', '在 CMS 的 SEO 标题字段或 HTML <title> 中修改；打开页面源码核对。'),
    '页面描述': ('P1', '用一两句话概括页面可解决的问题和适用对象，不写未经证明的效果。', '填写 meta name="description"；保存发布后重新检查当前页面。'),
    'H1 数量': ('P1', '设置一个清晰的主标题；正文子标题用 H2/H3，避免模板重复输出主标题。', '在正文和模板中核对 H1 数量。此处采用一个主标题的编辑规范，不代表搜索排名规则。'),
    'Canonical 声明': ('P2', '由网站维护人员确定规范 URL，再在 head 设置 canonical。不要把不同产品都指向首页。', '检查 rel="canonical" 的目标可访问且内容对应；本工具仅检查声明是否存在。'),
    '图片替代文本': ('P2', '为有信息的图片写简短 alt，说明产品、工况或图中内容。装饰图片可使用空 alt。', '在媒体库或 img 标签中处理，再人工区分装饰图；缺失提示不等于所有图片都必须填字。'),
}


def checks(parser):
    values = [('页面索引指令', not any(x in ('noindex','none') for x in re.split(r'[,;\s]+', parser.robots.lower())), parser.robots or '未声明 meta robots，未检查响应头和 robots.txt'),
              ('页面标题', bool(parser.title.strip()), parser.title),
              ('页面描述', bool(parser.description), parser.description),
              ('H1 数量', parser.h1 == 1, str(parser.h1)),
              ('Canonical 声明', bool(parser.canonical), parser.canonical),
              ('图片替代文本', parser.missing_alt == 0, f'{parser.images} 张图片，{parser.missing_alt} 张未提供非空 alt'),
              ('移动端视口', 'width=device-width' in parser.viewport.lower().replace(' ',''), parser.viewport),
              ('页面语言', bool(parser.language.strip()), parser.language)]
    return [{'name': name, 'ok': ok, 'value': value, 'priority': GUIDES[name][0],
             'recommendation': GUIDES[name][1], 'implementation': GUIDES[name][2]}
            for name, ok, value in values]
