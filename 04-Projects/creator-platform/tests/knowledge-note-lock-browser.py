"""Native Edge/Chromium locks + storage, disposable context, synthetic fixture.

All network requests are intercepted. Uses production note code and showForm,
but not the full app/backend; no user profile or existing user data is accessed.
"""
import asyncio
import hashlib
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/KNOWLEDGE-NOTE-LOCK-BROWSER-20261006.json'
KEY = 'wld-reading-notes'
LOCK = 'wld-reading-notes-write'
HTML = '''<!doctype html><html lang="zh"><meta charset="utf-8">
<title>合成笔记保存测试</title><main id="app"></main>
<dialog id="modal"><h2 id="modal-title"></h2><form id="form">
<div id="fields"></div><p id="form-error" role="alert"></p>
<button id="submit" type="submit">保存</button></form></dialog></html>'''


async def main():
    report = {'scope': 'Native Web Locks/localStorage/dialog/forms; synthetic fixture and records; isolated nonpersistent browser context; all network intercepted', 'checks': []}
    scripts = {name: (ROOT / 'frontend' / name).read_text(encoding='utf-8') for name in ['app.js', 'travel.js', 'chat-format.js', 'book-reader.js']}
    report['source_sha256'] = {name: hashlib.sha256((ROOT / 'frontend' / name).read_bytes()).hexdigest() for name in scripts}
    # Extract unchanged production helpers; fixture supplies only unrelated UI.
    form = scripts['app.js'].split('function showForm(', 1)[1].split('\nfunction record()', 1)[0]
    form = 'function showForm(' + form
    storage = next(line for line in scripts['travel.js'].splitlines() if line.startswith('function travelSave('))
    bootstrap = '\n'.join(scripts['app.js'].splitlines()[:2]) + '''
let formGeneration=0;
const houBooks=[{id:'synthetic-book',title:'合成测试书'}];
function render(){document.getElementById('app').innerHTML=personalKnowledgeNotes()}
function toast(message){window.lastToast=message}
''' + form + '\n' + storage
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='msedge')
        report['browser'] = browser.version
        context = await browser.new_context()
        requests = []
        async def intercept(route):
            requests.append({'method': route.request.method, 'url': route.request.url})
            if route.request.is_navigation_request():
                await route.fulfill(status=200, content_type='text/html', body=HTML)
            else:
                await route.abort()
        await context.route('**/*', intercept)
        async def page():
            page = await context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto('http://127.0.0.1:8765/__synthetic_note_lock__')
            await page.wait_for_load_state('networkidle')
            await page.add_script_tag(content=bootstrap)
            await page.add_script_tag(content=scripts['chat-format.js'])
            await page.add_script_tag(content=scripts['book-reader.js'])
            assert await page.evaluate('isSecureContext && !!navigator.locks')
            # Inspect actual fixture DOM before choosing its controls.
            assert await page.locator('dialog#modal form#form button[type=submit]').count() == 1
            return page
        async def notes(page):
            return await page.evaluate('readerNotes()')
        async def open_manual(page, text):
            await page.evaluate("openBookInsights('synthetic-book')")
            await page.locator('textarea[name=excerpt]').fill(text)
        async def hold(page):
            await page.evaluate('''name=>{window.lockHeld=false;window.held=navigator.locks.request(name,async()=>{
              window.lockHeld=true;await new Promise(resolve=>window.releaseLock=resolve);
            })}''', LOCK)
            await page.wait_for_function('window.lockHeld')
        async def pending(page, count):
            await page.wait_for_function('''async ({name,count}) => (await navigator.locks.query()).pending.filter(x=>x.name===name).length===count''', arg={'name': LOCK, 'count': count})
        try:
            a, b, holder = await page(), await page(), await page()
            assert await a.evaluate('(key)=>localStorage.getItem(key)', KEY) is None
            await a.evaluate('(key)=>localStorage.setItem(key,JSON.stringify([{excerpt:"synthetic legacy",extra:"preserved"}]))', KEY)
            await hold(holder)
            await open_manual(a, 'tab A manual')
            await open_manual(b, 'tab B manual')
            await asyncio.gather(a.locator('#submit').click(), b.locator('#submit').click())
            await pending(holder, 2)
            assert await a.locator('#submit').is_disabled() and await b.locator('#submit').is_disabled()
            assert len(await notes(a)) == 1
            await holder.evaluate('window.releaseLock()')
            await asyncio.gather(a.wait_for_function('!document.getElementById("modal").open'), b.wait_for_function('!document.getElementById("modal").open'))
            rows = await notes(a)
            assert {r['excerpt'] for r in rows} == {'synthetic legacy', 'tab A manual', 'tab B manual'}
            assert rows[-1]['extra'] == 'preserved'
            report['checks'].append({'case': 'two real tabs queued behind native lock; manual UI saves both records', 'pass': True, 'rows': len(rows)})

            await hold(holder)
            await open_manual(a, 'timeout draft retained')
            before = await a.evaluate('(key)=>localStorage.getItem(key)', KEY)
            await a.locator('#submit').click()
            await pending(holder, 1)
            await a.wait_for_function('document.getElementById("form-error").textContent.includes("超时且未写入")', timeout=10000)
            assert await a.locator('textarea[name=excerpt]').input_value() == 'timeout draft retained'
            assert not await a.locator('#submit').is_disabled()
            assert await a.evaluate('(key)=>localStorage.getItem(key)', KEY) == before
            await pending(holder, 0)
            await holder.evaluate('window.releaseLock()')
            await holder.evaluate('window.held')
            assert await notes(a) == rows
            await a.locator('#submit').click()
            await a.wait_for_function('!document.getElementById("modal").open')
            assert len(await notes(a)) == 4
            report['checks'].append({'case': 'native five-second timeout removes pending request, keeps form draft, no late write; manual retry succeeds', 'pass': True})

            await hold(holder)
            await open_manual(b, 'lock owner closed')
            await b.locator('#submit').click()
            await pending(a, 1)
            await holder.close()
            await b.wait_for_function('!document.getElementById("modal").open')
            assert len(await notes(b)) == 5
            report['checks'].append({'case': 'closing native lock owner releases lock; queued tab recovers', 'pass': True})

            await asyncio.gather(*[page.evaluate('''async label=>{for(let i=0;i<10;i++)await appendReadingNote({id:label+i,excerpt:label+i})}''', label) for page, label in [(a, 'batch-A-'), (b, 'batch-B-')]])
            rows = await notes(a)
            report['batch_observed'] = {'a': rows, 'b': await notes(b)}
            assert await a.evaluate('(key)=>localStorage.getItem(key)', KEY) == '[{"excerpt":"synthetic legacy","extra":"preserved"}]'
            assert len(rows) == 25, f'Expected 25, received {len(rows)}'
            assert len({r['id'] for r in rows if r.get('id', '').startswith('batch-')}) == 20
            await b.evaluate('''async()=>{const row={role:'assistant',content:'synthetic AI reply'};
              await Promise.all([saveReadingLocal({id:'synthetic-book',title:'合成测试书'},row,'q'),saveReadingLocal({id:'synthetic-book',title:'合成测试书'},row,'q')]);
              if(!row.localSaved)throw Error('No saved marker');}''')
            assert len(await notes(a)) == 26
            report['checks'].append({'case': '20 interleaved native writes preserve all rows; concurrent duplicate AI save adds one', 'pass': True})

            before = await a.evaluate('(key)=>localStorage.getItem(key)', KEY)
            await a.evaluate('(key)=>localStorage.setItem(key,"{synthetic broken")', KEY)
            await open_manual(a, 'preserve on corruption')
            await a.locator('#submit').click()
            await a.wait_for_function('document.getElementById("form-error").textContent.includes("格式异常")')
            assert await a.evaluate('(key)=>localStorage.getItem(key)', KEY) == '{synthetic broken'
            assert await a.locator('textarea[name=excerpt]').input_value() == 'preserve on corruption'
            await a.evaluate('({key,value})=>localStorage.setItem(key,value)', {'key': KEY, 'value': before})
            await a.locator('#submit').click()
            await a.wait_for_function('!document.getElementById("modal").open')
            assert len(await notes(a)) == 27
            report['checks'].append({'case': 'native localStorage corruption does not get overwritten; retained form saves after synthetic storage restored', 'pass': True})
            fresh = await page()
            persisted = await notes(fresh)
            assert len(persisted) == 27
            assert len([n for n in persisted if n.get('id', '').startswith('batch-')]) == 20
            assert await fresh.evaluate('(key)=>localStorage.getItem(key)', KEY) == '[{"excerpt":"synthetic legacy","extra":"preserved"}]'
            report['checks'].append({'case': 'fresh tab reads all 27 records; legacy raw array unchanged', 'pass': True})
            assert not errors, errors
            report['pass'] = True
        except Exception as error:
            report['pass'] = False
            report['error'] = repr(error)
            raise
        finally:
            report['page_errors'] = errors
            report['intercepted_requests'] = requests
            report['limitations'] = ['Synthetic fixture, not full product/backend end-to-end', 'No OS suspension/process crash/browser quota test', 'Existing old-version tabs do not participate in lock', 'No real model call or medical validation']
            await context.close()
            await browser.close()
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'pass': report['pass'], 'browser': report['browser'], 'checks': len(report['checks']), 'report': str(REPORT)}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
