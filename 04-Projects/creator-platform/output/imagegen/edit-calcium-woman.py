import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='''Use native built-in image_gen EDIT through ChatGPT login ONLY, no API key or paid API. Attached image is the EDIT TARGET. Replace only the elderly gray-haired woman on the LEFT with a confident middle-aged East Asian female business owner approximately 40-45 years old. She has polished dark shoulder-length hair, natural attractive face, an elegant tailored muted lavender business blazer over ivory blouse, understated jewelry and an engaged warm smile. Her presence should feel capable, sophisticated and approachable. Keep her seated at the table consulting the dietitian; preserve overall pose and composition. Keep the younger female dietitian on the RIGHT in her white coat, her food checklist clipboard, salad bowl, cup, table, plants and warm office interior. Preserve exact headline 先看饮食摄入 at top, readable and unclipped. Square format, same detailed warm ivory/lavender/gold watercolor editorial illustration style. Do not introduce new people, logos or extra text. Return one edited image and real output file path. Do not edit project files.'''
Path('output/imagegen/calcium-woman-edit-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','--image',str(Path('frontend/assets/nutrients/calcium-flow-3.webp').resolve()),'-']
with Path('output/imagegen/calcium-woman-edit-result.txt').open('wb') as out:r=subprocess.run(args,input=prompt.encode(),stdout=out,stderr=out,env=environment('.runtime'),timeout=1800)
print('Finished',r.returncode)
