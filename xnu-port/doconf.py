#!/usr/bin/env python3
"""doconf for Linux: a port of xnu's SETUP/config/doconf (a csh script).
MASTER files are filtered by -DPLATFORM_x -DCPU_x -DSOC_CONFIG_x -DSYS_x
with xnu's own SETUP/unifdef, converted into the `opt [value]` syntax the
config program reads, then config -c builds the Makefile and headers.
Options: -c -cpu X -soc X -platform X -d OBJDIR -m MASTERDIR -s SOURCEDIR
         -verbose [-p] SYS...
Required environment: OBJROOT SRCROOT (as on a Mac build)."""
import os, re, subprocess, sys

CONFIG_DIR = os.path.join(os.environ.get("OBJROOT", ""), "SETUP", "config")
opts = {"cpu": None, "soc": "", "platform": "", "objdir": "../BUILD",
        "master": ".", "source": ".", "doconfig": False, "profile": False,
        "verbose": False}
args = sys.argv[1:]
syses = []
while args and args[0].startswith("-"):
    o = args.pop(0)
    if o in ("-c", "-config"):
        opts["doconfig"] = True
    elif o in ("-cpu", "-soc", "-platform", "-d", "-m", "-s"):
        key = {"-cpu": "cpu", "-soc": "soc", "-platform": "platform",
               "-d": "objdir", "-m": "master", "-s": "source"}[o]
        opts[key] = args.pop(0)
    elif o in ("-p", "-profile"):
        opts["profile"] = True
    elif o == "-verbose":
        opts["verbose"] = True
    else:
        sys.exit(f"doconf: {o}: unknown switch")
syses = args or ["GENERIC"]
if not opts["cpu"]:
    sys.exit("doconf: MACHINE not set")
cpu = opts["cpu"].lower()
ID = opts["cpu"].upper()
master = opts["master"] + "/MASTER"
cands = [f"{master}.{cpu}.{opts['soc']}.{opts['platform']}",
         f"{master}.{cpu}.{opts['soc']}",
         f"{master}.{cpu}.{opts['platform']}",
         f"{master}.{cpu}"]
master_cpu = next((c for c in cands if os.path.isfile(c)), None)
if master_cpu is None:
    sys.exit(f"doconf: no MASTER.{cpu}* in {opts['master']}")
# unifdef: dxb uses the Darwin one; ours is beside the original tools, so
# the checkout copy of this script matches it by absolute path.
import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
unifdef = os.path.join(HERE, "unifdef")
if not os.path.exists(unifdef):
    unifdef = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unifdef")
define = ("-DPLATFORM_" + opts["platform"] + " -DCPU_" + cpu +
          " -DSOC_CONFIG_" + opts["soc"] + " ")
avp = "-DSOC_IS_VIRTUALIZED" if opts["soc"].startswith("vm") else "-USOC_IS_VIRTUALIZED"
_o = opts
for SYS in syses:
    opts_obj = _o["objdir"]
    opts = _o
    SYSID = f"{SYS}_{ID}"
    conf = os.path.join(opts["objdir"], f"config.{SYSID}")
    text = ""
    for f in (master, master_cpu):
        text += open(f).read()
        if not text.endswith("\n"):
            text += "\n"
    text += f"+{SYS}\n"
    for f in (master, master_cpu):
        text += open(f).read()
        if not text.endswith("\n"):
            text += "\n"
    p = subprocess.run([unifdef, "-t"] + (define + f"-DSYS_{SYS}").split() + [avp, "-"],
                       input=text, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"doconf: unifdef failed for {SYSID}: {p.stderr}")
    # the sed/awk pipeline: collect name=[..] definitions, then expand
    lines = p.stdout.split("\n")
    m = {}
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("+"):
            i += 1
            break
        mo = re.match(r"^#\s*([^ ]*)\s*=\s*\[(.*)\].*$", l.replace("\t", " "))
        if mo:
            m.setdefault(mo.group(1), "")
            m[mo.group(1)] += " " + mo.group(2)
        i += 1
    # expand recursive definitions (same algorithm as the awk script)
    f = {}
    stack = []
    if " " in lines[i - 1:]:
        pass
    # find the line after +SYS (the "# ..." definitions block above ends at '')
    j = i
    # skip option-looking lines (start '#' or empty)
    while j < len(lines) and (lines[j] == "" or lines[j].startswith("#")):
        j += 1
    def expand(name, depth=0):
        if depth > 50:
            return
        for tok in reversed(m.get(name, "").split(" ")):
            if not tok:
                continue
            expand(tok, depth + 1)
            f.setdefault(tok, "+")
    if j < len(lines):
        toks = lines[j].split("#")
        if len(toks) >= 2:
            for t in reversed(toks[1:]):
                expand(t[1:])
    out = []
    for k in range(j, len(lines)):
        l = lines[k]
        if not l:
            continue
        if "#" in l:
            name, val = l.split("#", 1)
            if name and f.get(name) == "+":
                out.append(val)
            elif not name and not val:
                pass
        else:
            out.append(l)
    # configuration name -> enabled attributes (+/* and - excluded)
    defs = {}
    for name, val in m.items():
        toks = [x for x in val.split() if x]
        defs[name] = toks
    sel = syses[0] if syses else "GENERIC"
    active = set()

    def enable(name, seen=()):
        if name in seen or name not in defs:
            return
        for tok in defs[name]:
            if tok.startswith("-") or tok.startswith("*"):
                continue
            active.add(tok)
            enable(tok, seen + (name,))

    enable(sel)
    # options/selfs from the unifdef output (lines without a selector pass)
    resolved = []
    for l in p.stdout.split("\n"):
        l = l.replace("\t", " ")
        if "+" in l or not l.strip():
            continue
        if l.lstrip().startswith("#"):
            continue
        parts = l.split("#")
        body = parts[0].rstrip()
        if not body:
            continue
        k = re.search(r"<\s*(.*?)\s*>\s*$", l)
        if k:
            want = [x for x in k.group(1).split(",") if x]
            pos = [x for x in want if not x.startswith("!")]
            neg = [x[1:] for x in want if x.startswith("!")]
            if pos:
                if not any(x in active for x in pos):
                    continue
            elif neg:
                if any(x in active for x in neg):
                    continue
        resolved.append(body)
    out = resolved
    tmp = conf + ".new"
    with open(tmp, "w") as fh:
        fh.write("\n".join(out) + "\n")
    if os.path.exists(conf):
        subprocess.run(["diff", conf, tmp])
    os.replace(tmp, conf)
    if opts["doconfig"]:
        params = [os.path.join(CONFIG_DIR, "config"), "-c", opts["source"]]
        if opts["profile"]:
            params.append("-p")
        params.append(conf)
        sys.exit(subprocess.call(params))
