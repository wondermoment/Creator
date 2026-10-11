"""Optional heavy parsers run outside the web process. stdout is a JSON protocol."""
import asyncio
import json
import sys


if __name__ == '__main__':
    if sys.argv[1] == '--html':
        source = sys.stdin.buffer.read().decode('utf-8')
        async def parse():
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
            from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
            # HTTP strategy processes raw HTML without rendering active scripts or subresources.
            async with AsyncWebCrawler(crawler_strategy=AsyncHTTPCrawlerStrategy()) as crawler:
                result = await crawler.arun('raw:' + source, config=CrawlerRunConfig())
                if not result.success: raise RuntimeError('HTML extraction failed')
                return [{'page': 1, 'text': str(result.markdown)}]
        pages = asyncio.run(parse())
    else:
        from docling.document_converter import DocumentConverter
        result = DocumentConverter().convert(sys.argv[1], max_num_pages=200)
        doc = result.document
        pages = [{'page': n, 'text': doc.export_to_markdown(page_no=n)} for n in sorted(doc.pages)]
    sys.stdout.buffer.write(json.dumps(pages, ensure_ascii=False).encode('utf-8'))
