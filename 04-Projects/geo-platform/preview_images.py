"""Render a self-contained, tenant-checked reader document without network access."""
import math
import threading
from pathlib import Path

from fastapi import HTTPException

_RENDER_SLOT = threading.BoundedSemaphore(1)


def render_images(document):
    if not _RENDER_SLOT.acquire(blocking=False):
        raise HTTPException(429, '正在生成预览图片，请稍后重试')
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
            options = {'executable_path': str(edge)} if edge.is_file() else {}
            browser = p.chromium.launch(headless=True, **options)
            try:
                context = browser.new_context(viewport={'width': 430, 'height': 900}, device_scale_factor=2,
                                              service_workers='block', accept_downloads=False)
                context.route('**/*', lambda route: route.abort())
                page = context.new_page()
                page.set_default_timeout(20000)
                page.set_content(document, wait_until='load')
                page.add_style_tag(content='.reader-shell{margin:0!important;box-shadow:none!important}.reader-tools{display:none!important}body{background:white!important}')
                page.evaluate('document.fonts.ready')
                if not page.evaluate('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)'):
                    raise HTTPException(409, '预览配图未能完整加载，请修复后重试')
                height = math.ceil(page.locator('.reader-shell').bounding_box()['height'])
                if height > 30000:
                    raise HTTPException(413, '文章过长，请拆分文章后生成预览图片')
                raw = page.screenshot(full_page=True, type='png', timeout=20000)
            finally:
                browser.close()
        return raw
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, '图片生成暂不可用，请重试或下载 HTML 预览稿；管理员请检查 Playwright 浏览器环境') from exc
    finally:
        _RENDER_SLOT.release()
