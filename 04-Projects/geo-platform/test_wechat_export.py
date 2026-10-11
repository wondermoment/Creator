import hashlib
import io
import json
import unittest
import zipfile
from unittest.mock import patch

import test_workflow
from test_workflow import server
import source_import
from PIL import Image


class WechatExportTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def fixture(self):
        raw = io.BytesIO()
        Image.new('RGB', (40, 20), 'green').save(raw, format='PNG')
        with server.db() as c:
            aid = source_import.store_asset(vars(server), c, self.pid, raw.getvalue(), 'test.png', {}, '图片')
            body = '第一段 <script>正文</script>\n\n二、说明'
            item = {'title': '标题 <测试>', 'body': body, 'revision': 1, 'status': 'pending', 'sources': [],
                    'review_notes': ['PRIVATE-NOTE'], 'prompt_snapshot': 'SECRET-PROMPT',
                    'layout': {'body_sha256': hashlib.sha256(body.encode()).hexdigest(), 'cover_id': aid,
                               'blocks': [{'text': body.split('\n\n')[0], 'image_ids': [aid]}, {'text': '二、说明'}],
                               'figures': [{'asset_id': aid, 'after': 1, 'caption': '独立配图'}]}}
            rid = server.put(c, self.pid, 'content', item)
        return rid, aid, raw.getvalue()

    def test_editable_text_and_ordered_original_images(self):
        rid, aid, raw = self.fixture()
        url = self.url + '/contents/' + rid + '/wechat-preview?revision=1'
        response = self.a.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('&lt;script&gt;正文&lt;/script&gt;', response.text)
        self.assertNotIn('<script>', response.text)
        self.assertNotIn('PRIVATE-NOTE', response.text)
        self.assertNotIn('SECRET-PROMPT', response.text)
        self.assertNotIn('/assets/', response.text)
        self.assertIn('尚未同步', response.text)
        archive = self.a.get(url + '&download=true')
        self.assertEqual(archive.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
            manifest = json.loads(z.read('manifest.json'))
            self.assertFalse(manifest['synced'])
            self.assertFalse(manifest['published'])
            self.assertEqual([x['after_block'] for x in manifest['images']], [None, 0, 1])
            self.assertEqual(z.read(manifest['cover']), raw)
            self.assertEqual(len(manifest['assets']), 1)
            body = z.read('body.html').decode()
            self.assertEqual(body.count('<img '), 2)
            self.assertLess(body.index('正文'), body.index('<img '))
            self.assertLess(body.index('<img '), body.index('二、说明'))
            self.assertNotIn('标题', body)
            self.assertNotIn('尚未同步', body)

    def test_scope_revision_layout_and_sources_fail_closed(self):
        rid, aid, _ = self.fixture()
        url = self.url + '/contents/' + rid + '/wechat-preview?revision=1'
        self.assertEqual(self.b.get(url).status_code, 404)
        self.assertEqual(self.a.get(url.replace('revision=1', 'revision=2')).status_code, 409)
        with server.db() as c:
            item = server.resource(c, self.pid, rid, 'content')
            item['knowledge_outdated'] = True
            server.put(c, self.pid, 'content', item, rid)
        self.assertEqual(self.a.get(url).status_code, 409)
        with server.db() as c:
            item['knowledge_outdated'] = False
            item['layout']['outdated'] = True
            server.put(c, self.pid, 'content', item, rid)
        self.assertEqual(self.a.get(url + '&download=true').status_code, 409)

    def test_corrupted_asset_is_rejected(self):
        rid, aid, _ = self.fixture()
        with server.db() as c:
            asset = server.resource(c, self.pid, aid, 'asset')
        (server.DB_PATH.parent / 'assets' / self.pid / asset['storage_key']).write_bytes(b'bad')
        self.assertEqual(self.a.get(self.url + '/contents/' + rid + '/wechat-preview?revision=1').status_code, 409)

    def test_changes_during_serialization_block_both_formats(self):
        import wechat_export
        original = wechat_export.document
        for download in (False, True):
            for change in ('revision', 'layout', 'source', 'asset', 'permission'):
                with self.subTest(download=download, change=change):
                    # Independent tenants keep permission revocation isolated.
                    self.setUp()
                    rid, aid, _ = self.fixture()

                    def serialize_then_change(*args):
                        result = original(*args)
                        with server.db() as c:
                            item = server.resource(c, self.pid, rid, 'content')
                            if change == 'permission':
                                c.execute('DELETE FROM members WHERE project_id=?', (self.pid,))
                            elif change == 'asset':
                                asset = server.resource(c, self.pid, aid, 'asset')
                                image = io.BytesIO()
                                Image.new('RGB', (40, 20), 'red').save(image, format='PNG')
                                raw = image.getvalue()
                                (server.DB_PATH.parent / 'assets' / self.pid / asset['storage_key']).write_bytes(raw)
                                asset['sha256'] = hashlib.sha256(raw).hexdigest()
                                server.put(c, self.pid, 'asset', asset, aid)
                            else:
                                if change == 'revision': item['revision'] += 1
                                if change == 'layout': item['layout']['figures'][0]['caption'] = '新版图注'
                                if change == 'source': item['knowledge_outdated'] = True
                                server.put(c, self.pid, 'content', item, rid)
                        return result

                    with patch.object(wechat_export, 'document', side_effect=serialize_then_change):
                        response = self.a.get(self.url + '/contents/' + rid + '/wechat-preview?revision=1' + ('&download=true' if download else ''))
                    self.assertEqual(response.status_code, 404 if change == 'permission' else 409, response.text[:200])
                    self.assertNotIn('content-disposition', response.headers)


if __name__ == '__main__':
    unittest.main()
