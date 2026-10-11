"""Context-specific value cards for the three remaining figures of one article."""
import argparse
import copy
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from design_hetuo_value_sample import PROJECT, CONTENT, TEMPLATE, ROOT

OUT = ROOT / 'outputs'
INK, GREEN, MUTED = '#153d51', '#008e79', '#456a73'
SPECS = [
    {'index': 1, 'old': '68c8ad67618abd1828f25df1', 'blocks': [5, 6, 7],
     'title': '先看产线，再定方案', 'caption': '产品选型：先明确应用场景与工艺，再匹配产品系列', 'file': 'hetuo-value-02-selection.png'},
    {'index': 2, 'old': '5c97ee092130cc1c4b5081b4', 'blocks': [13, 16, 18],
     'title': '零排放，先看水去哪儿', 'caption': '采购核查：看清水洗环节、循环回用与排放去向', 'file': 'hetuo-value-03-water.png'},
    {'index': 3, 'old': '5882150bf12d8ef4c0659123', 'blocks': [22, 23],
     'title': '选工艺，先看流程差异', 'caption': '工艺对比：核对水洗流程、处理配套与适用条件', 'file': 'hetuo-value-04-comparison.png'},
]


class Canvas:
    def __init__(self):
        self.im = Image.open(TEMPLATE).convert('RGB')
        self.d = ImageDraw.Draw(self.im)
        self.s = self.im.width / 2048
        self.copy = []

    def text(self, x, y, value, size, color=INK, bold=False, width=None):
        font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc', round(size * self.s))
        assert self.d.textlength(value, font=font) <= (width or 1980-x) * self.s, value
        self.d.text((round(x*self.s), round(y*self.s)), value, font=font, fill=color, anchor='lt')
        self.copy.append(value)

    def line(self, box, fill, width=2):
        self.d.line(tuple(round(v*self.s) for v in box), fill=fill, width=round(width*self.s))

    def rect(self, box, fill):
        self.d.rectangle(tuple(round(v*self.s) for v in box), fill=fill)

    def save(self, file):
        OUT.mkdir(exist_ok=True)
        self.im.save(OUT/file, optimize=True)
        return self.copy


def render():
    a = Canvas()
    a.text(470, 57, '应用选型 · 从产线出发', 31, GREEN, True)
    a.text(462, 150, '先看产线', 110, bold=True)
    a.text(462, 295, '再定方案', 110, GREEN, True)
    a.text(474, 478, '场景不同，选型路径不同', 36, MUTED)
    a.line((1140, 131, 1140, 515), '#c9e3df')
    for y, n, title, detail in [(134, '01', '明确场景', '卷材、零部件还是大工件'),
                               (273, '02', '确认工艺', '喷淋、浸渍、辊涂或擦洗'),
                               (412, '03', '匹配型号', '按应用场景选择产品系列')]:
        a.text(1200, y+4, n, 40, GREEN, True)
        a.text(1310, y, title, 58, bold=True)
        a.text(1310, y+77, detail, 31, MUTED)
    SPECS[0]['copy'] = a.save(SPECS[0]['file'])

    a = Canvas()
    a.text(470, 55, '采购判断 · 核对工艺边界', 31, GREEN, True)
    a.text(460, 126, '零排放，先看水去哪儿', 94, bold=True)
    a.text(471, 264, '沿着水的去向，把技术路线问清楚', 41, MUTED)
    for x, title in [(470, '水洗环节'), (995, '循环回用'), (1520, '排放去向')]:
        a.rect((x, 365, x+430, 502), '#edf7f4')
        a.text(x+37, 402, title, 65, GREEN, True, width=390)
    for x in (932, 1457):
        a.line((x, 432, x+38, 432), '#219f93', 4)
        a.line((x+26, 422, x+38, 432, x+26, 442), '#219f93', 4)
    SPECS[1]['copy'] = a.save(SPECS[1]['file'])

    a = Canvas()
    a.text(470, 52, '采购问答 · 工艺路线怎么比', 31, GREEN, True)
    a.text(462, 118, '选工艺，先看流程差异', 94, bold=True)
    a.rect((470, 268, 1175, 513), '#f0f5f8')
    a.rect((1210, 268, 1950, 513), '#edf7f4')
    a.text(505, 297, '传统磷化路线', 36, MUTED, True)
    a.text(505, 361, '多道水洗', 75, INK, True)
    a.text(507, 462, '关注后续废水处理配套', 33, MUTED)
    a.text(1248, 297, '硅晶路线', 36, GREEN, True)
    a.text(1248, 361, '免水洗方案', 75, GREEN, True)
    a.text(1250, 462, '核实适用工况与排放边界', 33, MUTED)
    a.text(471, 542, '按具体产线方案核对，不能只凭工艺名称作结论。', 26, MUTED)
    SPECS[2]['copy'] = a.save(SPECS[2]['file'])
    # Review all variants at the same scale before changing the article.
    sheet = Image.new('RGB', (1440, 3*442), '#edf1f4')
    for i, spec in enumerate(SPECS):
        im = Image.open(OUT/spec['file']); im.thumbnail((1400, 410))
        sheet.paste(im, (20, i*442+18))
    sheet.save(OUT/'hetuo-article-three-values.jpg', quality=94)


def apply():
    import server as s
    from sample_review import layout_current
    from source_import import store_asset
    with s.db() as c:
        assert s.project(c, PROJECT)['website'].rstrip('/') == 'https://www.heroto.com.cn'
        item = s.resource(c, PROJECT, CONTENT, 'content')
        if item.get('layout', {}).get('value_series') == '20261002-v1':
            return {'unchanged': True, 'revision': item['revision']}
        assert item['revision'] == 3 and item['status'] == 'pending' and layout_current(item)
        assert not any(p.get('content_id') == CONTENT and p['status'] != 'cancelled' for p in s.items(c, PROJECT, 'publication'))
        assert not any(j.get('status') in ('queued', 'running') and j.get('payload', {}).get('content_id') == CONTENT for j in s.items(c, PROJECT, 'execution'))
        for spec in SPECS:
            assert item['layout']['figures'][spec['index']]['asset_id'] == spec['old']
        item.setdefault('history', []).append(copy.deepcopy({k: item.get(k) for k in ('revision', 'title', 'body', 'channels', 'status', 'layout', 'platform_payloads')}))
        changes = {}
        for spec in SPECS:
            refs = [{'index': n, 'text': item['layout']['blocks'][n]['text']} for n in spec['blocks']]
            aid = store_asset(vars(s), c, PROJECT, (OUT/spec['file']).read_bytes(), spec['title']+'.png', {
                'type': 'article_context_value_card', 'content_id': CONTENT, 'source_revision': 3,
                'source_blocks': refs, 'copy': spec['copy'], 'replaces_asset_id': spec['old'],
                'body_sha256': hashlib.sha256(item['body'].encode()).hexdigest(),
            }, '图片')
            asset = s.resource(c, PROJECT, aid, 'asset')
            asset.update(collection='和拓文章品牌配图', tags=['和拓实业', '价值提炼', '文章配图'], description=spec['caption'])
            s.put(c, PROJECT, 'asset', asset, aid)
            item['layout']['figures'][spec['index']].update(asset_id=aid, caption=spec['caption'])
            changes[spec['old']] = aid
        for variant in item.get('platform_payloads', {}).values():
            variant['attachment_ids'] = [changes.get(a, a) for a in variant.get('attachment_ids', [])]
        item['layout']['value_series'] = '20261002-v1'
        item.pop('quality', None)
        item.update(revision=4, approved_revision=None, review_note='', preparation_status='4 张上下文价值图已排版 · 待客户审阅')
        item['review_notes'] = [n for n in item.get('review_notes', []) if '首张正文图改为' not in n]
        item['review_notes'].append('本篇四张正文图已按上下文提炼为价值图；标题与技术结论仍待客户核准。')
        s.put(c, PROJECT, 'content', item, CONTENT)
        s.event(c, PROJECT, 'local-design-assistant', '更新单篇上下文价值配图', CONTENT+' · v3 → v4 · 按用户确认设计更新后三张，保留旧图与历史')
        return {'revision': 4, 'replaced': changes}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--apply', action='store_true'); args = p.parse_args()
    render()
    print(apply() if args.apply else str(OUT/'hetuo-article-three-values.jpg'))
