"""Import an explicitly supplied Feishu clipboard HTML export, without network access.

Only visible content is extracted. Embedded metadata/scripts never become instructions.
Existing imported content is left untouched on retries or source changes.
"""
import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import source_import as imp

PID = 'a46fb911b04fbf0b783c7bf5'
BATCH = 'hetuo-feishu-0924-20261002'
LABEL = '飞书 0924 · 新增 15 篇'
DOC = 'https://q1wlsi2t9ng.feishu.cn/docx/BudgdZnWAoWu93xtq8VcWfSDngg'
SHEET = 'https://q1wlsi2t9ng.feishu.cn/sheets/Ikr4s9wyChl1eutGCkucWGlrnWc?sheet=c437cf'


def extract_articles(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    root = soup.select_one('[data-lark-html-role="root"]')
    if root is None:
        raise ValueError('缺少飞书复制导出的正文根节点')
    for node in root.select('script,style,iframe,object'):
        node.decompose()
    active = False
    rows = []
    for element in root.children:
        if not getattr(element, 'name', None):
            continue
        text = element.get_text('', strip=False).replace('\u200b', '').strip()
        if element.name == 'h1':
            active = text == '稿件内容-0924'
            continue
        if not active:
            continue
        anchor = next((x.removeprefix('old-record-id-') for x in element.get('class', []) if x.startswith('old-record-id-')), '')
        if element.name == 'h2':
            if not anchor or not re.match(r'^\d+、', text):
                raise ValueError('文章缺少稳定来源标识或编号')
            rows.append({'title': text, 'anchor': anchor, 'blocks': []})
            continue
        if not rows:
            continue
        table = element if element.name == 'table' else element.find('table')
        if table:
            text = '\n'.join(' | '.join(cell.get_text(' ', strip=True) for cell in tr.find_all(['td', 'th'], recursive=False)) for tr in table.find_all('tr'))
        if text:
            rows[-1]['blocks'].append({'text': text, 'type': 'table' if table else 'paragraph', 'location': DOC + '#' + anchor, 'image_ids': []})
    for row in rows:
        row['body'] = '\n\n'.join(b['text'] for b in row['blocks'])
        row['source'] = DOC + '#' + row['anchor']
        row['sha256'] = hashlib.sha256(row['body'].encode()).hexdigest()
        if len(row['body']) < 500 or '暂时无法在飞书文档外展示此内容' in row['body']:
            raise ValueError('正文不完整：' + row['title'])
    return rows


def category(title):
    if '磷化哪个好' in title or '路线差距' in title:
        return '工艺对比与性能验证'
    if '环保' in title or '绿色' in title:
        return '环保与综合成本'
    return '供应商与药剂选型'


def import_rows(g, c, pid, rows, raw_html):
    old = {x.get('source_url'): x for x in g['items'](c, pid, 'content') if x.get('import_batch') == BATCH}
    # Plain-text attachment preserves the original HTML without serving active markup.
    aid = imp.store_asset(g, c, pid, raw_html, '飞书创作记录-原始HTML.txt', {'url': DOC, 'batch': BATCH}, '资料')
    asset = g['resource'](c, pid, aid, 'asset')
    asset.update(collection='待发布原稿与配图', tags=['飞书', '0924批次', '原始导出'])
    g['put'](c, pid, 'asset', asset, aid)
    imported, skipped, conflicts = [], [], []
    for row in rows:
        previous = old.get(row['source'])
        if previous:
            (skipped if previous.get('source_body_sha256') == row['sha256'] else conflicts).append(previous['id'])
            continue
        topic = category(row['title'])
        md = '# ' + row['title'] + '\n\n来源：' + row['source'] + '\n\n' + row['body']
        original_id = imp.store_asset(g, c, pid, md.encode(), row['title'] + '.md', {'url': row['source'], 'batch': BATCH, 'original_export_asset': aid}, '资料')
        a = g['resource'](c, pid, original_id, 'asset')
        a.update(collection='待发布原稿与配图', tags=['待发布', '飞书0924', topic])
        g['put'](c, pid, 'asset', a, original_id)
        kid = g['put'](c, pid, 'knowledge', {'title': row['title'], 'category': '待发布原稿', 'body': row['body'], 'blocks': row['blocks'], 'source': row['source'], 'source_sha256': row['sha256'], 'source_export_asset': aid, 'asset_id': original_id, 'status': 'pending', 'version': 1, 'image_ids': [], 'origin': 'customer_source', 'import_batch': BATCH})
        for label, pattern, requirement in imp.CLAIMS:
            matches = [b for b in row['blocks'] if re.search(pattern, b['text'])]
            if matches:
                g['put'](c, pid, 'evidence_claim', {'title': label, 'knowledge_id': kid, 'source_title': row['title'], 'status': 'pending', 'requirement': requirement, 'excerpts': [{'location': b['location'], 'text': b['text']} for b in matches], 'source_version': 1, 'import_batch': BATCH})
        outline = [b['text'] for b in row['blocks'] if re.match(r'^(?:[一二三四五六七八九十]+|\d+)[、.．]', b['text']) and len(b['text']) < 100]
        notes = ['飞书 0924 新增批次：保留正文及内嵌表格；渠道和封面尚未选定。', '台账未发现本篇刊发记录；这不代表已验证全网从未发布。', '盐雾、零排放、降本等表述须核准适用条件和报告；审核前不得发送。']
        if 11 <= int(row['title'].split('、')[0]) <= 14:
            notes.append('11—14 篇标题与论证结构相近；建议审核时区分受众和搜索意图，避免同渠道重复铺稿。')
        item = {'title': row['title'], 'body': row['body'], 'status': 'pending', 'revision': 1, 'approved_revision': None, 'review_note': '', 'history': [], 'channels': [], 'scheduled': '', 'skill_name': '客户原稿 · 飞书提取', 'skill_version': 1, 'prompt_snapshot': '忠实提取用户提供的飞书正文与表格，不用模型补造事实。', 'generator': '飞书原稿 · 本地结构化整理', 'origin': 'customer_prepublication', 'import_batch': BATCH, 'batch_label': LABEL, 'source_url': row['source'], 'source_body_sha256': row['sha256'], 'original_knowledge_id': kid, 'sources': [{'id': kid, 'title': row['title'], 'version': 1, 'source': row['source'], 'body': row['body'], 'excerpt': row['body'][:800]}], 'keyword': re.sub(r'^\d+、', '', row['title']).split('？')[0], 'intent': topic, 'customer_question': '', 'editorial_summary': {'category': topic, 'opening_excerpt': row['blocks'][1 if len(row['blocks']) > 1 else 0]['text'][:220], 'outline': outline, 'tables': sum(b['type'] == 'table' for b in row['blocks'])}, 'review_notes': notes, 'preparation_status': '待选渠道、配图及客户审核', 'layout': {'version': 1, 'body_sha256': row['sha256'], 'blocks': row['blocks'], 'figures': [], 'cover_id': ''}, 'platform_payloads': {}}
        imported.append(g['put'](c, pid, 'content', item))
    return {'imported': imported, 'skipped': skipped, 'source_changed': conflicts, 'source_export_asset': aid}


def run():
    import server as s
    source = s.ROOT / 'research/feishu-20261002/creation-record.html'
    raw = source.read_bytes()
    rows = extract_articles(raw)
    if [int(r['title'].split('、')[0]) for r in rows] != list(range(1, 16)):
        raise ValueError('新增批次必须恰好包含连续编号 1—15 的文章')
    with s.db() as c:
        p = s.project(c, PID)
        if p['name'] != '和拓实业' or p['website'] != 'https://www.heroto.com.cn':
            raise ValueError('企业身份不匹配，拒绝导入')
        result = import_rows(vars(s), c, PID, rows, raw)
        previous = next((b for b in s.items(c, PID, 'import_batch') if b.get('batch') == BATCH), None)
        history = [
            {'row': 15, 'date_label': '9月28日', 'article_number': 1, 'channel': '列举网', 'url': 'https://sh.lieju.com/huagongyuanliao/113672301.html'},
            {'row': 16, 'date_label': '9月29日', 'article_number': 1, 'channel': '列举网', 'url': 'https://sh.lieju.com/huagongyuanliao/113828244.html'},
            {'row': 17, 'date_label': '9月30日', 'article_number': 2, 'channel': '列举网', 'url': 'https://sh.lieju.com/huagongyuanliao/114003038.html'},
            {'row': 18, 'date_label': '10月1日', 'article_number': 3, 'channel': '列举网', 'url': 'https://sh.lieju.com/huagongyuanliao/114048237.html'},
        ]
        record = {'batch': BATCH, 'name': LABEL, 'prepared_articles': 15, 'tables': sum(sum(b['type'] == 'table' for b in r['blocks']) for r in rows), 'links': [{'name': '新增文章来源', 'url': DOC + '#T9madJogooRfq3xVRD1cm8LWn6b', 'note': '完整提取 15 篇正文及表格；原始 HTML 以纯文本附件归档。'}, {'name': '发布台账', 'url': SHEET, 'note': '已查看行 1—28；4 条链接属于首批文章 1—3。新增 15 篇未见记录。链接尚未逐条外站验活，不计为系统发布。'}], 'historical_records': history, 'records': [{'title': r['title'], 'source': r['source'], 'body_sha256': r['sha256'], 'characters': len(r['body'])} for r in rows]}
        s.put(c, PID, 'import_batch', record, previous['id'] if previous else None)
        first = next((b for b in s.items(c, PID, 'import_batch') if b.get('batch') == 'hetuo-20261002'), None)
        if first:
            first['links'][0]['note'] = '飞书 0924 批次已另行完整导入 15 篇；保留首批 8 篇独立版本。'
            s.put(c, PID, 'import_batch', first, first['id'])
        # Evidence from the user's ledger remains historical evidence, not connector receipts.
        for content in s.items(c, PID, 'content'):
            if content.get('import_batch') != 'hetuo-20261002':
                continue
            number = int(content['title'].split('、')[0])
            matches = [x for x in history if x['article_number'] == number]
            if matches:
                content['historical_publication_evidence'] = matches
                note = '发布台账另有本篇列举网链接；当前搜狐号稿仍待发。历史链接尚未外站验活，不代表本版本已发送。'
                if note not in content['review_notes']:
                    content['review_notes'].append(note)
                s.put(c, PID, 'content', content, content['id'])
        if result['imported']:
            actor = c.execute("SELECT user_id FROM members WHERE project_id=? AND role='owner' LIMIT 1", (PID,)).fetchone()[0]
            s.event(c, PID, actor, '导入飞书新增待发稿', '15 篇原文、表格与来源；未批准、未对外发送')
    report = {**result, 'articles': record['records'], 'tables': record['tables'], 'project_id': PID}
    (s.ROOT / 'deliverables/feishu-import-report.json').write_text(s.dump(report), encoding='utf8')
    print(json.dumps({'new': len(result['imported']), 'skipped': len(result['skipped']), 'source_changed': len(result['source_changed']), 'tables': record['tables'], 'characters': sum(len(r['body']) for r in rows)}, ensure_ascii=False))


if __name__ == '__main__':
    run()
