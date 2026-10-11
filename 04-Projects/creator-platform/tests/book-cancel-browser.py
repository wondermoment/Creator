"""Native dialog/fetch cancellation against a disposable loopback fixture server.
No application backend, model, database, user profile or persistent uploads.
"""
import asyncio
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/BOOK-CANCEL-BROWSER-20261007.json'
FILES = ['app.js', 'book-reader.js', 'coach-chat.js', 'chat-format.js', 'request-errors.js']
CODE = {name: (ROOT / 'frontend' / name).read_text(encoding='utf-8') for name in FILES}
app = CODE['app.js']
bootstrap = '\n'.join(app.splitlines()[:2]) + '\n' + app[app.index('async function api('):app.index('function toast(')] + app[app.index('let formGeneration='):app.index('\nfunction record()')]
bootstrap += '''
const houBooks=[{id:'a',title:'合成书A'},{id:'b',title:'合成书B'}];
function render(){} function toast(){} async function reload(){}
window.observed=[];
const nativeFetch=window.fetch.bind(window);
window.fetch=(url,options={})=>{
 const row={url:String(url),aborted:false,rejected:false,bodyRejected:false};window.observed.push(row);
 options.signal?.addEventListener('abort',()=>row.aborted=true,{once:true});
 return nativeFetch(url,options).then(response=>{
  row.headers=true;const original=response.json.bind(response);
  response.json=()=>original().catch(error=>{row.bodyRejected=true;throw error});return response;
 },error=>{row.rejected=true;throw error});
};
document.getElementById('close').onclick=()=>document.getElementById('modal').close();
document.getElementById('replace').onclick=()=>showForm('合成新表单','<input id="new-draft">','保存',()=>{},{local:true});
'''
HTML = '''<!doctype html><html lang="zh"><meta charset="utf-8"><title>隔离取消验证</title>
<main id="app"></main><dialog id="modal"><button id="close" type="button">关闭</button>
<button id="replace" type="button">切换表单</button><h2 id="modal-title"></h2>
<form id="form"><div id="fields"></div><p id="form-error"></p><button id="submit">提交</button></form></dialog>
''' + ''.join(f'<script src="/static/{name}"></script>' for name in ['bootstrap.js', 'request-errors.js', 'chat-format.js', 'coach-chat.js', 'book-reader.js']) + '</html>'


class Fixture:
    def __init__(self):
        self.phase = ''
        self.release = threading.Event()
        self.entered = threading.Event()
        self.finished = threading.Event()
        self.counts = {}
        self.requests = []


fixture = Fixture()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.serve()

    def do_POST(self):
        # Discard synthetic request bytes in memory; never write uploaded files.
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.serve()

    def serve(self):
        f = fixture
        path = self.path
        if path == '/':
            body, mime = HTML.encode(), 'text/html; charset=utf-8'
        elif path.startswith('/static/'):
            name = path.split('/')[-1]
            body, mime = (bootstrap if name == 'bootstrap.js' else CODE[name]).encode(), 'text/javascript; charset=utf-8'
        else:
            f.requests.append({'path': path, 'method': self.command})
            f.counts[path] = f.counts.get(path, 0) + 1
            data = [] if path.endswith('/history') else {'ready': True, 'model_ready': True, 'name': 'synthetic.txt', 'chunks': 2}
            if path.endswith('/chat'):
                data = {'answer': '合成完整回答', 'sources': []}
            body, mime = json.dumps(data, ensure_ascii=False).encode(), 'application/json'
        target = {'history': '/api/books/a/history', 'status': '/api/books/a', 'reload': '/api/books/a', 'upload-status': '/api/books/a', 'upload': '/api/books/a/source', 'upload-body': '/api/books/a/source', 'chat': '/api/books/a/chat', 'chat-body': '/api/books/a/chat'}.get(f.phase)
        count = 2 if f.phase in ['reload', 'upload-status'] else 1
        gated = path == target and f.counts.get(path) == count
        partial = gated and f.phase.endswith('-body')
        try:
            if gated and not partial:
                f.entered.set()
                if not f.release.wait(20):
                    return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if partial:
                self.wfile.write(body[:1]); self.wfile.flush()
                f.entered.set()
                if not f.release.wait(20):
                    return
                self.wfile.write(body[1:])
            else:
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Expected for browser-aborted fixture requests.
        finally:
            if gated:
                f.finished.set()


async def main():
    global fixture
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    report = {'scope': 'Native Edge dialog/fetch plus synthetic HTTP server; production frontend functions; no real project backend or model', 'checks': [], 'source_sha256': {n: hashlib.sha256((ROOT / 'frontend' / n).read_bytes()).hexdigest() for n in FILES}}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='msedge')
        report['browser'] = browser.version
        try:
            for phase in ['history', 'status', 'reload', 'upload', 'upload-body', 'upload-status', 'chat', 'chat-body']:
                for action in ['close', 'replace']:
                    fixture = Fixture(); fixture.phase = phase
                    context = await browser.new_context()
                    # Never allow a request to the application server or external hosts.
                    await context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') else route.abort())
                    page = await context.new_page()
                    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
                    try:
                        await page.goto(origin)
                        await page.wait_for_load_state('networkidle')
                        assert await page.locator('#modal #close').count() == 1
                        await page.evaluate("()=>{window.openDone=false;openReadingChat('a').then(()=>window.openDone=true)}")
                        if phase not in ['history', 'status']:
                            await page.wait_for_function('window.openDone && !document.getElementById("reading-send").disabled')
                            if phase == 'reload':
                                # Trigger the same handler as the manual retry button (hidden after successful load).
                                await page.evaluate('()=>{window.operationDone=false;document.getElementById("reading-reload").onclick().then(()=>window.operationDone=true)}')
                            elif phase.startswith('upload'):
                                await page.locator('summary').click()
                                await page.locator('#reading-file').set_input_files({'name': 'synthetic.txt', 'mimeType': 'text/plain', 'buffer': b'Synthetic source only.'})
                                await page.evaluate('''()=>{const b=document.getElementById('reading-upload'),handler=b.onclick;b.onclick=()=>{window.operationDone=false;return handler().finally(()=>window.operationDone=true)}}''')
                                await page.get_by_role('button', name='上传并建立原文索引').click()
                            else:
                                await page.locator('#reading-question').fill('合成取消测试问题')
                                await page.evaluate('''()=>{const b=document.getElementById('reading-send'),handler=b.onclick;b.onclick=()=>{window.operationDone=false;return handler().finally(()=>window.operationDone=true)}}''')
                                await page.get_by_role('button', name='发送问题').click()
                        assert await asyncio.to_thread(fixture.entered.wait, 5), phase
                        if phase.endswith('-body'):
                            await page.wait_for_function('window.observed.some(x=>x.headers && x.url.endsWith("' + ('/source' if phase == 'upload-body' else '/chat') + '"))')
                        await page.locator('#' + action).click()
                        await page.wait_for_function('window.observed.some(x=>x.aborted && (x.rejected || x.bodyRejected))', timeout=5000)
                        await page.wait_for_function('window.' + ('openDone' if phase in ['history', 'status'] else 'operationDone'), timeout=5000)
                        # Fixture handler remains blocked: cancellation never means backend rollback.
                        assert not fixture.release.is_set()
                        if action == 'replace':
                            await page.locator('#new-draft').fill('保留新表单草稿')
                        else:
                            assert not await page.locator('#modal').evaluate('(d)=>d.open')
                        observed = await page.evaluate('window.observed')
                        fixture.release.set()
                        assert await asyncio.to_thread(fixture.finished.wait, 5)
                        await page.evaluate("openReadingChat('b')")
                        await page.locator('#reading-question').fill('新窗口合成问题')
                        await page.get_by_role('button', name='发送问题').click()
                        await page.wait_for_function('document.getElementById("reading-log").textContent.includes("合成完整回答") && !document.getElementById("reading-send").disabled')
                        if phase == 'history':
                            assert not any(r['path'] == '/api/books/a' for r in fixture.requests)
                        if phase in ['upload', 'upload-body']:
                            assert fixture.counts['/api/books/a'] == 1, 'late upload must not request source status'
                        assert not errors, errors
                        report['checks'].append({'phase': phase, 'action': action, 'pass': True, 'aborted': [x for x in observed if x['aborted']], 'requests': fixture.requests, 'page_errors': errors})
                    finally:
                        fixture.release.set()
                        await context.close()
            report['pass'] = True
        except Exception as e:
            report['pass'] = False
            report['error'] = repr(e)
            report['failed_case'] = {'phase': phase, 'action': action}
            raise
        finally:
            fixture.release.set()
            await browser.close()
            server.shutdown(); server.server_close()
            report['limitations'] = ['Synthetic server and page, not full product/backend integration', 'No actual PDF indexing/cloud model/persistent writes', 'No measured production cancellation latency or backend task/resource termination']
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'pass': report['pass'], 'cases': len(report['checks']), 'browser': report['browser']}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
