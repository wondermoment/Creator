import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
rows=json.loads(Path('output/imagegen/recipe-handwritten-manifest.json').read_text('utf-8'))
rows=[x for x in rows if x['id']!='tofu']
prompt='''Use native built-in image_gen through ChatGPT login only. NO API keys or paid API. Attached is the user APPROVED watercolor handwritten ingredient-card style. Generate ONE separate square high resolution ingredient card PER recipe below, 25 images total, one image_gen call per recipe. Continue until all25 completed. Each card: exact Chinese recipe name as handwritten title; subtitle 一人份 · 食材准备; delicate realistic watercolor ingredients arranged on warm ivory paper with sage ceramics and generous blank margins. Dark brown legible Chinese handwritten labels with fine curved arrows pointing to correct ingredient. Use EXACT names and quantities from ingredients, no invented quantities. Keep cooked versus dry weights explicit. Small amounts remain 少量 or 适量. Do not draw cooking steps on these cards. Do not mix multiple recipes in one image. Match approved image elegance and typography. Check Chinese labels, no English headings, no logos. Return EACH recipe id and actual generated file path immediately after its generation so files can be integrated incrementally. Do not edit project. Recipe data JSON follows:\n'''+json.dumps(rows,ensure_ascii=False)
Path('output/imagegen/all-handwritten-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-i',str(Path('output/imagegen/tofu-handwritten-preview.png').resolve()),'-']
with Path('output/imagegen/all-handwritten-result.txt').open('wb') as out:
 r=subprocess.run(args,input=prompt.encode(),stdout=out,stderr=out,env=environment('.runtime'),timeout=7200)
print('Finished',r.returncode)
