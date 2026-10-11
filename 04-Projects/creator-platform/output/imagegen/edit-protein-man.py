import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='''Use the native built-in image_gen edit capability through ChatGPT login ONLY, no API key or paid API. The attached image is the EDIT TARGET. User requests: replace only the elderly white-haired man on the left with a handsome healthy middle-aged East Asian man approximately 40-45 years old, short dark hair, natural attractive face, fit but realistic build, friendly confident smile. Keep his purple T-shirt, seated dumbbell training pose, friendly interaction with the female trainer. Preserve the woman on the right, her coaching support gesture, balanced food plate and all food on table, gym setting, square framing, warm ivory/lavender/gold watercolor editorial style. Preserve exact heading 饮食与力量训练 at top, readable and unclipped. Do not change other people into elderly figures. No photorealistic style, no new characters, no added captions. Generate one edited image and return actual output file path, do not edit project files.'''
Path('output/imagegen/protein-man-edit-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','--image',str(Path('frontend/assets/nutrients/protein-flow-3.webp').resolve()),'-']
with Path('output/imagegen/protein-man-edit-result.txt').open('wb') as out:r=subprocess.run(args,input=prompt.encode(),stdout=out,stderr=out,env=environment('.runtime'),timeout=1800)
print('Finished',r.returncode)
