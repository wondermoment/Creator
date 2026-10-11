import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='Use built-in image_gen only, no API keys. Generate one elegant watercolor cookbook sheet, square 2x2 equal panels with ivory gutters, NO text. Top left: ingredients for Chinese steamed white fish fillet, ginger, scallions, zucchini, carrots and brown rice. Top right: white fish fillet on ceramic plate with ginger and scallions inside a metal steamer above a saucepan, lid lifted, gentle steam. Bottom left: carrot and zucchini pieces lightly cooking in pan. Bottom right: finished steamed white fish with ginger scallions, vegetables and brown rice in separate ceramic dishes. Soft luminous watercolor washes, warm paper, refined realistic food, no hands. Return actual image path.'
Path('output/imagegen/fish-watercolor-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-']
r=subprocess.run(args,input=prompt.encode(),capture_output=True,env=environment('.runtime'),timeout=360)
Path('output/imagegen/fish-watercolor-result.txt').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace')[-4500:])
