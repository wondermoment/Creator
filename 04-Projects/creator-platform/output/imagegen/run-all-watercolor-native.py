import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
rows=json.loads(Path('output/imagegen/recipe-step-manifest.json').read_text('utf-8'))
rows=[x for x in rows if x['id'] not in ('fish','salmon')];rows.sort(key=lambda x:x['id']!='chickpea')
prompt='Generate cookbook watercolor step sheets using ONLY built-in image_gen, NO shell, API keys, external APIs or other tools. For EACH recipe below call image_gen once and return recipe id + actual generated path. Do all 20 recipes, do not stop after first. Each image is square 2x2 equal panels with generous ivory gutters: top left ingredients, top right step1, bottom left step2, bottom right step3/finished dish. Follow that recipe ingredients and actual cooking steps exactly. Elegant appetizing realistic watercolor, warm white paper, sage accents, no text or numbers, no people. Read Chinese recipes below. Outputs go to built-in default.\n'+json.dumps(rows,ensure_ascii=False)
Path('output/imagegen/all-watercolor-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-']
with Path('output/imagegen/all-watercolor-result.txt').open('wb') as out:
 r=subprocess.run(args,input=prompt.encode(),stdout=out,stderr=out,env=environment('.runtime'),timeout=3600)
print('Finished:',r.returncode)
