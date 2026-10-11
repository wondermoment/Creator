"""One user-requested value-card sample; never bulk-replace customer artwork."""
import argparse
import copy
import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PROJECT = 'a46fb911b04fbf0b783c7bf5'
CONTENT = 'c15f3aebb03773f2b82fae53'
PREVIOUS_ASSET = '83b0bda87f4f73a421b630af'
TEMPLATE = Path('C:/Users/pc02a/Desktop/和拓-配图模版.png')
OUTPUT = ROOT / 'outputs' / 'hetuo-value-card-sample.png'
COPY = {
    'eyebrow': '前处理选型 · 核心价值',
    'headline': '好涂层，先打好底',
    'subhead': '选型要看涂层的长期表现',
    'points': [('附着力', '涂层结合牢不牢'), ('耐腐蚀性', '环境考验扛不扛得住'), ('使用寿命', '长期使用靠不靠谱')],
}


def render():
    im = Image.open(TEMPLATE).convert('RGB')
    d = ImageDraw.Draw(im)
    scale = im.width / 2048

    def text(x, y, value, size, color, bold=False):
        font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc', round(size * scale))
        assert d.textlength(value, font=font) <= (1980 - x) * scale
        d.text((round(x * scale), round(y * scale)), value, font=font, fill=color, anchor='lt')

    def line(x1, y1, x2, y2, color, width=2):
        d.line(tuple(round(v * scale) for v in (x1, y1, x2, y2)), fill=color, width=round(width * scale))

    # Keep every added pixel inside the customer's right white panel.
    text(468, 55, COPY['eyebrow'], 31, '#008e79', True)
    text(460, 117, COPY['headline'], 112, '#153d51', True)
    text(468, 268, COPY['subhead'], 39, '#456a73')
    for i, (title, supporting) in enumerate(COPY['points']):
        x = 470 + i * 492
        line(x, 363, x + 72, 363, '#009980', 7)
        text(x, 390, title, 62, '#008d74', True)
        text(x, 478, supporting, 32, '#315761')
        if i < 2:
            line(x + 441, 387, x + 441, 520, '#d2e8e5')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUTPUT, optimize=True)
    return OUTPUT.read_bytes()


def apply(raw):
    import server as s
    from sample_review import layout_current
    from source_import import store_asset
    with s.db() as c:
        assert s.project(c, PROJECT)['website'].rstrip('/') == 'https://www.heroto.com.cn'
        item = s.resource(c, PROJECT, CONTENT, 'content')
        if item.get('layout', {}).get('value_card_sample') == '20261002-v1':
            return {'unchanged': True, 'revision': item['revision']}
        assert item['revision'] == 2 and item['status'] == 'pending', 'Article changed; inspect before applying'
        assert layout_current(item), 'Current layout must be valid'
        assert item['layout']['figures'][0]['asset_id'] == PREVIOUS_ASSET
        assert not any(p.get('content_id') == CONTENT and p['status'] != 'cancelled' for p in s.items(c, PROJECT, 'publication'))
        source = item['layout']['blocks'][1]['text']
        assert all(t in source for t in ('附着力', '耐腐蚀性', '寿命'))
        snapshot = copy.deepcopy({k: item.get(k) for k in ('revision', 'title', 'body', 'channels', 'status', 'layout', 'platform_payloads')})
        aid = store_asset(vars(s), c, PROJECT, raw, '和拓-前处理核心价值-设计样版.png', {
            'type': 'article_value_card_sample', 'content_id': CONTENT,
            'source_revision': 2, 'source_block': 1, 'source_excerpt': source,
            'body_sha256': hashlib.sha256(item['body'].encode()).hexdigest(),
            'replaces_asset_id': PREVIOUS_ASSET, 'copy': COPY,
        }, '图片')
        asset = s.resource(c, PROJECT, aid, 'asset')
        asset.update(collection='和拓文章品牌配图', tags=['和拓实业', '价值提炼', '设计样版'],
                     description='客户要求的单张设计样版；大标题与三项价值维度，未新增量化效果承诺。')
        s.put(c, PROJECT, 'asset', asset, aid)
        item.setdefault('history', []).append(snapshot)
        item['layout']['figures'][0].update(asset_id=aid, caption='前处理选型：关注附着力、耐腐蚀性与使用寿命')
        item['layout']['value_card_sample'] = '20261002-v1'
        for variant in item.get('platform_payloads', {}).values():
            variant['attachment_ids'] = [aid if a == PREVIOUS_ASSET else a for a in variant.get('attachment_ids', [])]
        item.pop('quality', None)
        item.update(revision=3, approved_revision=None, review_note='', preparation_status='首张价值图设计样版 · 待客户审阅')
        item.setdefault('review_notes', []).append('首张正文图改为价值提炼样版；其余配图保留，待确认设计方向。')
        s.put(c, PROJECT, 'content', item, CONTENT)
        s.event(c, PROJECT, 'local-design-assistant', '更新单张价值图样版', CONTENT + ' · v2 → v3 · 用户授权，仅替换首张正文图，保留旧图和历史')
        return {'content_id': CONTENT, 'revision': 3, 'asset_id': aid}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    raw = render()
    print(apply(raw) if args.apply else str(OUTPUT))
