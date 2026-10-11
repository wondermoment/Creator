import asyncio
import json
import time
from pathlib import Path
from backend.app.coach_chat import Message,chat

async def main():
    question='这本书的底层知识框架与第一性原理是什么？'
    context=json.dumps({'book':'NOMA餐厅发酵指南','author':'René Redzepi、David Zilber','mode':'书籍主题交流：未提供全文，不得声称读过本书、编造章节页码或把通用知识当原书观点。不确定作者版本或内容时明确说明，可请用户粘贴摘录。'},ensure_ascii=False)
    started=time.monotonic()
    result=await chat('research-learning',Message(question=question,history=[{'role':'user','content':context}]))
    row={'question':question,'context':context,'seconds':round(time.monotonic()-started,2),'method':'imported current route via local Codex ChatGPT login; running HTTP server unchanged',**result}
    (Path(__file__).resolve().parents[1]/'docs/NOMA-LOCAL-CONCISE-20261006.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(row,ensure_ascii=True))

if __name__=='__main__':asyncio.run(main())
