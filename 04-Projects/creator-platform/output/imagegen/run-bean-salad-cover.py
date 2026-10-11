import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='Use native image_gen only. Generate one beautiful realistic editorial food photograph, landscape 3:2, warm white ceramic bowl of warm WHITE CANNELLINI BEAN salad with clearly visible plump ivory white beans, cooked broccoli florets, ripe red tomato pieces, light olive oil lemon dressing, slice of whole wheat bread beside bowl. Exact ingredients only, no green peas, no avocado, no pasta. Natural soft window light, ivory linen, pale wood table, refined appetizing healthy home cooking, three-quarter close view with whole bowl visible and generous margins. NO text NO letters NO nutritional label NO watermark NO collage. Return actual generated file path. No API keys, do not edit project files.'
Path('output/imagegen/bean-salad-cover-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-']
r=subprocess.run(args,input=prompt.encode(),capture_output=True,env=environment('.runtime'),timeout=420)
Path('output/imagegen/bean-salad-cover-result.txt').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace')[-2000:])
