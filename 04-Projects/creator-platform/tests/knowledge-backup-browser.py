"""Isolated native browser download, synthetic storage; no real user profile."""
import asyncio
import hashlib
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


async def main():
    code = (ROOT / 'frontend/book-reader.js').read_text(encoding='utf-8')
    report = {'scope': 'Native Edge download and localStorage; synthetic page/records; nonpersistent isolated context; all network intercepted', 'source_sha256': hashlib.sha256((ROOT / 'frontend/book-reader.js').read_bytes()).hexdigest(), 'checks': []}
    requests, errors, downloads = [], [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='msedge')
        report['browser'] = browser.version
        context = await browser.new_context(accept_downloads=True)
        async def intercept(route):
            requests.append({'method': route.request.method, 'url': route.request.url})
            if route.request.is_navigation_request():
                await route.fulfill(content_type='text/html', body='<html lang="zh"><meta charset="utf-8"><main id="app"></main></html>')
            else:
                await route.abort()
        await context.route('**/*', intercept)
        try:
            page = await context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('download', lambda d: downloads.append(d))
            await page.goto('http://127.0.0.1:8765/__synthetic_backup__')
            await page.wait_for_load_state('networkidle')
            await page.add_script_tag(content="const houBooks=[];const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;');")
            await page.add_script_tag(content=code)
            entries = {'wld-reading-notes': '[{"excerpt":"中文旧笔记","extra":"原样"}]', 'wld-reading-note:test': '{"id":"test","excerpt":"新笔记"}', 'unrelated-token': 'must-not-export'}
            await page.evaluate('rows=>{for(const [k,v] of Object.entries(rows))localStorage.setItem(k,v);document.getElementById("app").innerHTML=personalKnowledgeNotes()}', entries)
            # Inspect actual rendered control before operating it.
            assert await page.get_by_role('button', name='导出本机笔记').count() == 1
            assert await page.get_by_text('文件未加密', exact=False).count() == 1
            for mode in ['valid', 'damaged']:
                if mode == 'damaged':
                    entries['wld-reading-note:test'] = '{broken 原始内容'
                    await page.evaluate('value=>{localStorage.setItem("wld-reading-note:test",value);document.getElementById("app").innerHTML=personalKnowledgeNotes()}', entries['wld-reading-note:test'])
                    assert await page.get_by_text('无法确认笔记是否为空。修复读取前请勿清除浏览器数据。').count() == 1
                async with page.expect_download() as event:
                    await page.get_by_role('button', name='导出本机笔记').click()
                download = await event.value
                assert await download.failure() is None
                assert download.suggested_filename.startswith('wld-reading-notes-') and download.suggested_filename.endswith('.json')
                file = json.loads(Path(await download.path()).read_text(encoding='utf-8'))
                assert file['format'] == 'wld-local-reading-backup' and file['version'] == 1
                exported = {row['key']: row['value'] for row in file['entries']}
                assert exported == {k: v for k, v in entries.items() if k != 'unrelated-token'}
                assert await page.evaluate('Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))') == entries
                assert '已发起下载' in await page.locator('[data-knowledge-export-status]').inner_text()
                report['checks'].append({'case': mode + ' records downloaded; exact raw strings preserved; unrelated storage excluded; zero storage mutation', 'pass': True})
            await page.evaluate('''()=>{localStorage.removeItem('wld-reading-notes');localStorage.removeItem('wld-reading-note:test');document.getElementById('app').innerHTML=personalKnowledgeNotes()}''')
            await page.get_by_role('button', name='导出本机笔记').click()
            assert '没有可导出' in await page.locator('[data-knowledge-export-status]').inner_text()
            assert len(downloads) == 2
            assert not await page.get_by_role('button', name='导出本机笔记').is_disabled()
            report['checks'].append({'case': 'empty storage creates no download; status and button recover', 'pass': True})
            assert not errors, errors
            report['pass'] = True
        except Exception as error:
            report['pass'] = False
            report['error'] = repr(error)
            raise
        finally:
            report['page_errors'] = errors
            report['intercepted_requests'] = requests
            report['download_count'] = len(downloads)
            report['limitations'] = ['Synthetic page, not full product end-to-end', 'Export is not import/restore validation or transactional snapshot', 'Browser access denial/download blocking only covered by synthetic unit tests']
            await context.close()  # Also removes its temporary download files.
            await browser.close()
            (ROOT / 'docs/KNOWLEDGE-BACKUP-BROWSER-20261007.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'pass': report['pass'], 'checks': len(report['checks']), 'downloads': report['download_count']}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
