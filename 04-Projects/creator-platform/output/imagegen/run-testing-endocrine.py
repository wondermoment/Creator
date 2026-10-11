import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt=Path('output/imagegen/testing-endocrine-prompt.txt').read_text('utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-']
with Path('output/imagegen/testing-endocrine-result.txt').open('wb') as out:
 r=subprocess.run(args,input=prompt.encode(),stdout=out,stderr=out,env=environment('.runtime'),timeout=1800)
print('Finished',r.returncode)
