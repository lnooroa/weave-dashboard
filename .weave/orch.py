#!/usr/bin/env python3
import os, re, json, time, subprocess, pathlib, textwrap
from urllib import request as urlreq
from urllib.error import HTTPError, URLError

# ---- env/context ----
ISSUE_NO   = os.environ["ISSUE_NUMBER"]
TITLE      = os.environ.get("ISSUE_TITLE","")
BODY       = os.environ.get("ISSUE_BODY","")
GH_REPO    = os.environ["GH_REPO"]
GH_TOKEN   = os.environ["GH_TOKEN"]
LLM_KEY    = os.environ.get("LLM_API_KEY","").strip()
LLM_URL    = (os.environ.get("LLM_BASE_URL") or "https://api.openai.com").rstrip("/")
LLM_MODEL  = os.environ.get("LLM_MODEL") or "gpt-4o-mini"

ROOT = pathlib.Path(".")
LOG_DIR = ROOT/".weave"/"logs"; LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR/f"issue-{ISSUE_NO}.log"

# ---- policy ----
POLICY_PATH = ROOT/".weave"/"policy.json"
DEFAULT_POLICY = {
  "enabled": True,
  "max_loops": 4,
  "build_cmd": "npm run build",
  "allow_run": ["npm","npx","pnpm","yarn","node","bun","echo","printf","mkdir","touch","cp","mv","rm","sed","awk","bash","sh","curl"]
}
if not POLICY_PATH.exists():
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_PATH.write_text(json.dumps(DEFAULT_POLICY, indent=2))
policy = {**DEFAULT_POLICY, **json.loads(POLICY_PATH.read_text())}

def save_policy(p): POLICY_PATH.write_text(json.dumps(p, indent=2))

# ---- quick admin commands (no LLM) ----
tlow = TITLE.lower().strip()
if tlow.startswith("policy:"):
    cmd = tlow.split(":",1)[1].strip()
    if cmd == "disable":
        policy["enabled"] = False; save_policy(policy)
    elif cmd == "enable":
        policy["enabled"] = True; save_policy(policy)
    elif cmd.startswith("loops"):
        n = re.findall(r"\d+", cmd); 
        if n: policy["max_loops"] = int(n[0]); save_policy(policy)
    # commit policy change
    subprocess.run("git add -A", shell=True); 
    subprocess.run('git -c user.name=policy-bot -c user.email=policy@bot commit -m "policy: update" || true', shell=True)
    subprocess.run("git push || true", shell=True)
    print("Policy updated; exiting."); exit(0)

if not policy.get("enabled", True):
    print("Orchestrator disabled by policy; exiting."); exit(0)

# ---- helpers ----
ALLOW = set(policy["allow_run"])
def allowed(cmd:str)->bool:
    first = (cmd.strip().split() or [""])[0]
    return first in ALLOW

def run_cmd(cmd:str, timeout=420):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s"

def write(path, content):
    p = ROOT/pathlib.Path(path)
    if ".." in p.resolve().relative_to(ROOT).parts:
        return f"SKIP WRITE {path} (unsafe)"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"WROTE {path} ({len(content)} bytes)"

def base_dir():
    for d in ["app","src/app","src/pages","pages"]:
        if (ROOT/d).exists(): return d
    (ROOT/"app").mkdir(exist_ok=True)
    return "app"

def write_page(slug:str, code:str):
    d = base_dir()
    path = (f"{d}/{slug.lstrip('/')}.tsx") if ("pages" in d) else (f"{d}/{slug.lstrip('/')}/page.tsx")
    return write(path, code)

def git_commit_if_changed(msg="orchestrator: apply"):
    subprocess.run("git add -A", shell=True)
    rc = subprocess.run("git diff --cached --quiet", shell=True).returncode
    if rc != 0:
        subprocess.run('git -c user.name=orchestrator-bot -c user.email=orchestrator@bot commit -m "{}"'.format(msg), shell=True)
        subprocess.run("git push", shell=True)
        return True
    return False

def build_once():
    # ensure deps
    subprocess.run("npm ci || npm install", shell=True, check=False)
    rc,out = run_cmd(policy["build_cmd"], timeout=900)
    return rc,out

def comment_on_issue(text:str):
    safe = text.replace("\\","\\\\").replace('"','\\"')
    data = json.dumps({"body": text}).encode("utf-8")
    url  = f"https://api.github.com/repos/{GH_REPO}/issues/{ISSUE_NO}/comments"
    req  = urlreq.Request(url, data=data, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    })
    try: urlreq.urlopen(req).read()
    except Exception as e: print("Comment error:", e)

def call_llm(prompt:str):
    if not LLM_KEY:
        # fallback: deterministic plan that writes a summary page
        return {"steps":[{"type":"WRITE","path": write_page("task-summary", f"""export default function Page(){{
  return(<main style={{padding:24,fontFamily:'system-ui, Arial'}}><h1>Task</h1>
  <pre style={{whiteSpace:'pre-wrap'}}>{json.dumps({"title":TITLE,"body":BODY})}</pre></main>);}}""")}]}    
    data = {
        "model": LLM_MODEL,
        "messages":[
            {"role":"system","content":"Return STRICT JSON only: {\"steps\":[...]} (no prose). Use minimal safe steps."},
            {"role":"user","content": prompt}
        ],
        "temperature":0.1
    }
    req = urlreq.Request(
        LLM_URL + "/v1/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers={"Authorization": f"Bearer {LLM_KEY}", "Content-Type":"application/json"}
    )
    js = json.loads(urlreq.urlopen(req).read().decode("utf-8"))
    content = js["choices"][0]["message"]["content"]
    try: return json.loads(content)
    except: 
        m = re.search(r"\{.*\}\s*$", content, re.S)
        return json.loads(m.group(0)) if m else {"steps":[]}

def plan_prompt(build_err:str=None, prev=None):
    allow_list = ", ".join(sorted(ALLOW))
    return textwrap.dedent(f"""
      You are building a Next.js app (App Router if app/ exists). 
      TASK = {TITLE}
      DETAILS = {BODY}
      Allowed RUN first-words: {allow_list}
      Produce JSON only: {{"steps":[...]}} where each step is:
        - WRITE: {{"type":"WRITE","path":"relative/path","content":"<file text>"}}
        - RUN  : {{"type":"RUN","cmd":"..."}}
      Constraints:
        - Keep steps small and safe (non-interactive, pass --yes).
        - If TSX, ensure valid React code.
        - App Router pages live at app/<slug>/page.tsx; API at app/api/<name>/route.ts
      {("BUILD_ERROR: " + build_err) if build_err else ""}
      {("PREV_PLAN: " + json.dumps(prev)) if prev else ""}
    """).strip()

def apply_plan(plan):
    changed=False; logs=[]
    for st in plan.get("steps",[]):
        t=st.get("type","").upper()
        if t=="WRITE":
            logs.append(write(st.get("path",""), st.get("content","")))
            changed=True
        elif t=="RUN":
            cmd=st.get("cmd","").strip()
            if not allowed(cmd): logs.append(f"SKIP RUN {cmd} (not allowed)"); continue
            rc,out = run_cmd(cmd, timeout=600)
            logs.append(f"RUN {cmd}\nRC={rc}\n{out[-2000:]}")
            if re.search(r"install|add|init|generate", cmd): changed=True
    return changed, logs

def write_log(blocks):
    with open(LOG_FILE,"w",encoding="utf-8") as f:
        for b in blocks: f.write(b+"\n")

# ---- main loop ----
log_blocks=[]; 
log_blocks.append(f"TITLE: {TITLE}")
success=False; plan=None; last_err=""; loops=policy["max_loops"]

for i in range(1, loops+1):
    plan = call_llm(plan_prompt(build_err=None if i==1 else last_err, prev=plan))
    ch, step_logs = apply_plan(plan); log_blocks += [f"\n== PLAN {i} ==\n"+json.dumps(plan,indent=2), "\n== STEP LOGS ==\n"+"\n".join(step_logs)]
    if ch: git_commit_if_changed(f"orchestrator: plan {i}")
    rc, out = build_once(); log_blocks += [f"\n== BUILD {i} (rc={rc}) tail ==\n{out[-3000:]}"]
    if rc==0: success=True; break
    last_err = out[-3000:]
    # stop if no change happened and same error keeps repeating
    if not ch and last_err: continue

write_log(log_blocks)
comment_on_issue(f"**orchestrator result:** {'SUCCESS' if success else 'FAILED'} after {i} loop(s).\n\nSee logs:\n```\n{open(LOG_FILE,'r',encoding='utf-8').read()[-9000:]}\n```")
print("done:", "success" if success else "failed")
