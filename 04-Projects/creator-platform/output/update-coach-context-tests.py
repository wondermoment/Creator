from pathlib import Path
root=Path(__file__).resolve().parents[1]
for name in ['coach-skill-flow','research-chat-flow','nutrient-chat-flow','testing-chat-flow']:
    p=root/f'tests/{name}.cjs'
    text=p.read_text('utf-8')
    text=text.replace("return {answer:","return {context_version:1,answer:").replace("return{answer:","return{context_version:1,answer:")
    p.write_text(text,encoding='utf-8')
p=root/'frontend/index.html'
text=p.read_text('utf-8').replace('coach-chat.js?v=urgent-help-10','coach-chat.js?v=context-11')
p.write_text(text,encoding='utf-8')
